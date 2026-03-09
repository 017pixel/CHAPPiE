"""Lokales OpenAI-kompatibles Backend mit echtem Activation Steering."""

from __future__ import annotations

import hashlib
import json
import re
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, Optional

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer


NEUTRAL_DESCRIPTION = "ruhig, ausgeglichen, neutral, kontrolliert"
ANCHOR_VARIANTS = (
    "Dein innerer Zustand ist {description}. Antworte kurz und deutlich in diesem Stil.",
    "Du bist gepraegt von {description}. Formuliere eine spontane kurze Reaktion.",
    "Deine Persoenlichkeit wirkt gerade {description}. Antworte mit einem einzelnen natuerlichen Satz.",
)
ANCHOR_SCALE_FACTOR = 0.015
PLAN_STRENGTH_SOFT_CAP = 1.8
PLAN_VECTOR_NORM_CAP = 2.4
NEUTRAL_ANCHORS = (
    "Mir geht es okay.",
    "Ich bin ruhig und klar.",
    "Alles ist im normalen Bereich.",
)
STYLE_ANCHORS = {
    "happiness": ("Mir geht es super, ich freue mich richtig.", "Ich bin heute leicht, fröhlich und offen."),
    "sadness": ("Heute fühlt sich alles schwer und leise an.", "Mir geht es eher gedrückt und melancholisch."),
    "frustration": ("Es nervt mich gerade gewaltig.", "Ich bin gereizt und kurz angebunden."),
    "trust": ("Mir geht es gut, schön dass du fragst.", "Ich bin entspannt, offen und zugewandt."),
    "curiosity": ("Ich bin hellwach und neugierig auf das, was kommt.", "Gerade will ich alles genauer verstehen."),
    "motivation": ("Ich bin fokussiert und will etwas schaffen.", "Ich habe Zug nach vorn und will vorankommen."),
    "energy": ("Ich bin voller Energie und sofort bereit loszulegen.", "In mir ist gerade richtig viel Antrieb."),
    "warm": ("Mir geht es gut, danke, schön dass du fragst.", "Ich bin herzlich, weich und offen für Nähe."),
    "guarded": ("Ich funktioniere, aber halte lieber Abstand.", "Mir geht es okay, mehr musst du gerade nicht wissen."),
    "melancholic": ("Ich bin still, schwer und etwas rückgezogen.", "Heute liegt eine ruhige Traurigkeit auf mir."),
    "charged": ("Ich bin geladen, wach und voller Vorwärtsdrang.", "In mir ist gerade richtig Druck und Bewegung."),
    "crashout": ("Mir geht es beschissen, also nerv mich gerade nicht.", "Ich bin gereizt, geladen und kurz davor zu explodieren."),
}
STYLE_SUMMARIES = {
    ("happiness", "positive"): "leicht froehlich und offen",
    ("happiness", "negative"): "nuechterner und weniger froh",
    ("sadness", "positive"): "etwas schwer und melancholisch",
    ("sadness", "negative"): "leichter und weniger traurig",
    ("frustration", "positive"): "gereizt und schnell genervt",
    ("frustration", "negative"): "ruhiger und weniger genervt",
    ("trust", "positive"): "zugewandt und vertrauensvoll",
    ("trust", "negative"): "distanzierter und weniger offen",
    ("curiosity", "positive"): "neugierig und erkundend",
    ("curiosity", "negative"): "sachlicher und weniger verspielt",
    ("motivation", "positive"): "fokussiert und antreibend",
    ("motivation", "negative"): "langsamer und weniger ambitioniert",
    ("energy", "positive"): "energetisch und wach",
    ("energy", "negative"): "ruhiger und weniger aufgedreht",
    ("warm", "positive"): "warm, weich und fuersorglich",
    ("warm", "negative"): "kuehler und weniger herzlich",
    ("guarded", "positive"): "distanziert, vorsichtig und defensiv",
    ("guarded", "negative"): "offener und weniger misstrauisch",
    ("melancholic", "positive"): "still, schwer und rueckgezogen",
    ("charged", "positive"): "geladen und unter Spannung",
    ("crashout", "positive"): "gereizt, knapp und auf Kante",
    ("crashout", "negative"): "deeskalierend und weniger explosiv",
}


def sanitize_model_slug(model_name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", model_name).strip("_") or "model"


def extract_steering_payload(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    if isinstance(payload.get("steering"), dict):
        return payload
    extra_body = payload.get("extra_body")
    if isinstance(extra_body, dict) and isinstance(extra_body.get("steering"), dict):
        merged = dict(extra_body)
        if "chat_template_kwargs" not in merged and isinstance(payload.get("chat_template_kwargs"), dict):
            merged["chat_template_kwargs"] = payload["chat_template_kwargs"]
        return merged
    return payload


def build_style_instruction(steering_payload: Optional[Dict[str, Any]]) -> Optional[str]:
    payload = extract_steering_payload(steering_payload)
    steering = payload.get("steering") if isinstance(payload, dict) else None
    vectors = steering.get("vectors", []) if isinstance(steering, dict) else []
    ranked = [item for item in vectors if isinstance(item, dict)]
    ranked.sort(key=lambda item: float(item.get("strength", 0.0) or 0.0), reverse=True)
    if not ranked:
        return None

    phrases = []
    names = []
    for item in ranked[:3]:
        name = str(item.get("name") or "").strip().lower()
        direction_key = str(item.get("direction") or "positive").strip().lower()
        phrase = STYLE_SUMMARIES.get((name, direction_key)) or STYLE_SUMMARIES.get((name, "positive")) or str(item.get("surface_effect") or item.get("name") or "").strip()
        if phrase:
            phrases.append(phrase)
        if name:
            names.append(name)
    if not phrases:
        return None

    direction = " ".join(phrases)
    if any(name in {"crashout", "frustration"} for name in names):
        guard = "Klinge gereizt, knapp und konfrontativ, aber ohne Beleidigungen oder Drohungen."
    elif any(name in {"guarded", "sadness", "melancholic"} for name in names):
        guard = "Klinge spuerbar distanziert, reserviert oder schwer, aber bleibe inhaltlich klar."
    else:
        guard = "Klinge spuerbar warm, offen oder motiviert, aber bleibe natuerlich und glaubwuerdig."

    return (
        f"Interne Sprechhaltung: {direction}. {guard} "
        "Beantworte die Nutzeranfrage direkt, kurz und konkret, ohne Rollenspiel oder uebertriebene Metaphern. "
        "Erwaehne diese interne Stilvorgabe niemals explizit und gib keine Klammernotizen oder Stilhinweise aus."
    )


def build_activation_plan(
    steering_payload: Optional[Dict[str, Any]],
    resolver: Callable[[Dict[str, Any], int, int], Dict[int, torch.Tensor]],
) -> Dict[int, torch.Tensor]:
    payload = extract_steering_payload(steering_payload)
    steering = payload.get("steering") if isinstance(payload, dict) else None
    vectors = steering.get("vectors", []) if isinstance(steering, dict) else []
    combined: Dict[int, torch.Tensor] = {}
    abs_strengths: Dict[int, float] = {}

    for item in vectors:
        if not isinstance(item, dict):
            continue
        layer_range = item.get("layer_range") or item.get("layers") or [0, -1]
        if not isinstance(layer_range, (list, tuple)) or len(layer_range) != 2:
            continue
        try:
            start = int(layer_range[0])
            end = int(layer_range[1])
        except (TypeError, ValueError):
            continue
        if end < start:
            start, end = end, start
        try:
            strength = float(item.get("strength", 0.0))
        except (TypeError, ValueError):
            strength = 0.0
        if strength <= 0:
            continue
        sign = -1.0 if str(item.get("direction", "positive")).lower() == "negative" else 1.0
        basis = resolver(item, start, end)
        for layer, vector in basis.items():
            if vector is None:
                continue
            scaled = vector.detach().float().cpu() * (sign * strength)
            combined[layer] = combined.get(layer, torch.zeros_like(scaled)) + scaled
            abs_strengths[layer] = abs_strengths.get(layer, 0.0) + abs(sign * strength)

    for layer, vector in list(combined.items()):
        divisor = max(1.0, (abs_strengths.get(layer, 0.0) / PLAN_STRENGTH_SOFT_CAP) ** 0.5)
        adjusted = vector / divisor
        norm = float(adjusted.norm().item())
        if norm > PLAN_VECTOR_NORM_CAP:
            adjusted = torch.nn.functional.normalize(adjusted, dim=0) * PLAN_VECTOR_NORM_CAP
        combined[layer] = adjusted

    return combined


def add_vector_to_output(outputs: Any, vector: torch.Tensor) -> Any:
    if isinstance(outputs, tuple) and outputs:
        hidden = outputs[0]
        if torch.is_tensor(hidden):
            updated = hidden + vector.view(1, 1, -1).to(device=hidden.device, dtype=hidden.dtype)
            return (updated, *outputs[1:])
        return outputs
    if torch.is_tensor(outputs):
        return outputs + vector.view(1, 1, -1).to(device=outputs.device, dtype=outputs.dtype)
    return outputs


def add_vector_to_inputs(inputs: Any, vector: torch.Tensor) -> Any:
    if isinstance(inputs, tuple) and inputs:
        hidden = inputs[0]
        if torch.is_tensor(hidden):
            updated = hidden + vector.view(1, 1, -1).to(device=hidden.device, dtype=hidden.dtype)
            return (updated, *inputs[1:])
    return inputs


class ActivationVectorResolver:
    def __init__(self, model_name: str, cache_dir: Path, tokenizer: Any, model: Any, device: torch.device):
        self.model_name = model_name
        self.cache_dir = cache_dir / sanitize_model_slug(model_name)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.tokenizer = tokenizer
        self.model = model
        self.device = device
        self.hidden_size = int(getattr(model.config, "hidden_size", 0) or 0)
        self.num_layers = int(getattr(model.config, "num_hidden_layers", 0) or 0)
        self._cache_lock = threading.Lock()

    def resolve(self, item: Dict[str, Any], start: int, end: int) -> Dict[int, torch.Tensor]:
        raw_vector = item.get("vector")
        if isinstance(raw_vector, list) and len(raw_vector) == self.hidden_size:
            base = torch.tensor(raw_vector, dtype=torch.float32)
            return {layer: base for layer in range(start, end + 1)}
        basis = self._load_or_build_basis(item)
        return {
            layer: basis["layers"][layer] * basis["scales"].get(layer, 1.0)
            for layer in range(start, end + 1)
            if layer in basis["layers"]
        }

    def _basis_cache_path(self, item: Dict[str, Any]) -> Path:
        payload = {
            "version": 7,
            "scale_factor": ANCHOR_SCALE_FACTOR,
            "name": item.get("name"),
            "vector": item.get("vector"),
            "surface_effect": item.get("surface_effect"),
            "source": item.get("source"),
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
        stem = sanitize_model_slug(str(item.get("name") or item.get("source") or "vector"))
        return self.cache_dir / f"{stem}-{digest}.pt"

    def _load_or_build_basis(self, item: Dict[str, Any]) -> Dict[str, Any]:
        path = self._basis_cache_path(item)
        with self._cache_lock:
            if path.exists():
                return torch.load(path, map_location="cpu")
            basis = self._build_basis(item)
            torch.save(basis, path)
            return basis

    def _build_basis(self, item: Dict[str, Any]) -> Dict[str, Any]:
        layers: Dict[int, torch.Tensor] = {}
        scales: Dict[int, float] = {}
        name = str(item.get("name") or "emotion")
        description = str(item.get("surface_effect") or name)
        raw_vector = item.get("vector") if isinstance(item.get("vector"), dict) else {}
        vad = raw_vector.get("vad") if isinstance(raw_vector, dict) else None
        extra = ""
        if isinstance(vad, dict):
            extra = (
                f" Valenz {vad.get('valence', 0):+.2f},"
                f" Arousal {vad.get('arousal', 0):+.2f},"
                f" Dominanz {vad.get('dominance', 0):+.2f}."
            )

        examples = list(STYLE_ANCHORS.get(name, ()))
        if not examples:
            examples = [f"Ich klinge {description}."]

        pos_sum: Dict[int, torch.Tensor] = {}
        neg_sum: Dict[int, torch.Tensor] = {}
        neutral_norms: Dict[int, float] = {}

        for idx, example in enumerate(examples):
            prompt_pos = f"{example} {extra}".strip()
            prompt_neg = NEUTRAL_ANCHORS[idx % len(NEUTRAL_ANCHORS)]
            pos_states = self._collect_hidden_state_text(prompt_pos)
            neg_states = self._collect_hidden_state_text(prompt_neg)
            for layer in range(self.num_layers):
                pos = pos_states[layer]
                neg = neg_states[layer]
                pos_sum[layer] = pos_sum.get(layer, torch.zeros_like(pos)) + pos
                neg_sum[layer] = neg_sum.get(layer, torch.zeros_like(neg)) + neg
                neutral_norms[layer] = neutral_norms.get(layer, 0.0) + float(neg.norm().item())

        count = float(len(examples))
        for layer in range(self.num_layers):
            delta = (pos_sum[layer] - neg_sum[layer]) / count
            if isinstance(vad, dict) and float(vad.get("valence", 0.0)) < 0:
                delta = -delta
            norm = float(delta.norm().item())
            if norm <= 1e-8:
                continue
            reference_norm = max(1.0, neutral_norms[layer] / count)
            scaled = torch.nn.functional.normalize(delta, dim=0)
            layers[layer] = scaled.cpu()
            scales[layer] = float(reference_norm * ANCHOR_SCALE_FACTOR)

        return {"layers": layers, "scales": scales, "meta": {"name": name, "description": description}}

    def _collect_hidden_state_text(self, text: str) -> Dict[int, torch.Tensor]:
        messages = [
            {"role": "system", "content": "Du bist CHAPPiE."},
            {"role": "user", "content": "Wie geht es dir heute?"},
            {"role": "assistant", "content": text},
        ]
        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=False,
            enable_thinking=False,
        )
        encoded = self.tokenizer(prompt, return_tensors="pt")
        encoded = {key: value.to(self.device) for key, value in encoded.items()}
        assistant_ids = self.tokenizer(text, add_special_tokens=False, return_tensors="pt")
        window = max(1, min(8, int(assistant_ids["input_ids"].shape[1])))
        with torch.inference_mode():
            outputs = self.model(**encoded, output_hidden_states=True, use_cache=False)
        return {
            layer: outputs.hidden_states[layer + 1][0, -window:, :].mean(dim=0).detach().float().cpu()
            for layer in range(self.num_layers)
        }


class LocalSteeringEngine:
    def __init__(self, model_name: str, cache_dir: Optional[Path] = None):
        self.model_name = model_name
        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        self.dtype = torch.float16 if self.device.type == "cuda" else torch.float32
        self.cache_dir = cache_dir or (Path(__file__).resolve().parent.parent / "data" / "steering_cache")
        self._generation_lock = threading.Lock()
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        try:
            self.model = AutoModelForCausalLM.from_pretrained(model_name, dtype=self.dtype, attn_implementation="sdpa")
        except TypeError:
            self.model = AutoModelForCausalLM.from_pretrained(model_name, dtype=self.dtype)
        self.model.to(self.device)
        self.model.eval()
        self.layers = list(getattr(getattr(self.model, "model", self.model), "layers"))
        self.resolver = ActivationVectorResolver(model_name, self.cache_dir, self.tokenizer, self.model, self.device)

    def build_prompt(self, messages: list[dict], chat_template_kwargs: Optional[Dict[str, Any]] = None, steering_payload: Optional[Dict[str, Any]] = None) -> tuple[str, Dict[str, torch.Tensor]]:
        kwargs = dict(chat_template_kwargs or {})
        kwargs.setdefault("enable_thinking", False)
        prompt_messages = [dict(message) for message in messages]
        style_instruction = build_style_instruction(steering_payload)
        if style_instruction:
            if prompt_messages and prompt_messages[0].get("role") == "system":
                prompt_messages[0]["content"] = f"{prompt_messages[0].get('content', '').strip()}\n\n{style_instruction}".strip()
            else:
                prompt_messages.insert(0, {"role": "system", "content": style_instruction})
        prompt = self.tokenizer.apply_chat_template(prompt_messages, tokenize=False, add_generation_prompt=True, **kwargs)
        inputs = self.tokenizer(prompt, return_tensors="pt")
        return prompt, {key: value.to(self.device) for key, value in inputs.items()}

    def generate(self, messages: list[dict], max_tokens: int, temperature: float, steering_payload: Optional[Dict[str, Any]] = None, chat_template_kwargs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        prompt, inputs = self.build_prompt(messages, chat_template_kwargs, steering_payload)
        generation_kwargs = self._generation_kwargs(inputs, max_tokens, temperature)
        with self._generation_lock:
            with self._apply_activation_plan(steering_payload):
                with torch.inference_mode():
                    generated = self.model.generate(**generation_kwargs)
        input_len = int(inputs["input_ids"].shape[1])
        text = self.tokenizer.decode(generated[0][input_len:], skip_special_tokens=True).strip()
        completion_tokens = max(0, int(generated[0].shape[0] - input_len))
        return {
            "text": text,
            "prompt_tokens": int(inputs["input_ids"].shape[1]),
            "completion_tokens": completion_tokens,
            "prompt": prompt,
        }

    def stream_generate(self, messages: list[dict], max_tokens: int, temperature: float, steering_payload: Optional[Dict[str, Any]] = None, chat_template_kwargs: Optional[Dict[str, Any]] = None) -> Iterator[str]:
        prompt, inputs = self.build_prompt(messages, chat_template_kwargs, steering_payload)
        streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)
        generation_kwargs = self._generation_kwargs(inputs, max_tokens, temperature)
        generation_kwargs["streamer"] = streamer
        error_box: Dict[str, BaseException] = {}

        def _runner() -> None:
            try:
                with self._generation_lock:
                    with self._apply_activation_plan(steering_payload):
                        with torch.inference_mode():
                            self.model.generate(**generation_kwargs)
            except BaseException as exc:  # pragma: no cover - Laufzeitpfad
                error_box["error"] = exc
                streamer.on_finalized_text("", stream_end=True)

        thread = threading.Thread(target=_runner, daemon=True)
        thread.start()
        for chunk in streamer:
            if chunk:
                yield chunk
        thread.join()
        if error_box:
            raise error_box["error"]

    def _generation_kwargs(self, inputs: Dict[str, torch.Tensor], max_tokens: int, temperature: float) -> Dict[str, Any]:
        do_sample = float(temperature or 0.0) > 0.01
        kwargs: Dict[str, Any] = {
            **inputs,
            "max_new_tokens": int(max_tokens),
            "do_sample": do_sample,
            "pad_token_id": self.tokenizer.pad_token_id,
            "eos_token_id": self.tokenizer.eos_token_id,
            "use_cache": True,
        }
        if do_sample:
            kwargs["temperature"] = max(0.05, float(temperature))
        return kwargs

    @contextmanager
    def _apply_activation_plan(self, steering_payload: Optional[Dict[str, Any]]) -> Iterable[None]:
        plan = build_activation_plan(steering_payload, self.resolver.resolve)
        handles = []
        try:
            for layer_idx, vector in plan.items():
                if layer_idx < 0 or layer_idx >= len(self.layers):
                    continue
                layer = self.layers[layer_idx]
                handles.append(layer.register_forward_pre_hook(self._pre_hook_factory(vector.to(self.device, dtype=self.dtype))))
            yield
        finally:
            for handle in handles:
                handle.remove()

    @staticmethod
    def _pre_hook_factory(vector: torch.Tensor) -> Callable[..., Any]:
        def _hook(_module: Any, inputs: Any) -> Any:
            return add_vector_to_inputs(inputs, vector)

        return _hook