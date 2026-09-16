"""Lokales OpenAI-kompatibles Backend mit echtem Activation Steering."""

from __future__ import annotations

import hashlib
import gc
import json
import logging
import os
import re
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, Optional

import torch
from transformers import (
    AutoConfig,
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    LogitsProcessorList,
    StoppingCriteria,
    StoppingCriteriaList,
)

from brain.steering.telemetry import generation_end_metadata, runtime_source_fingerprint, cached_model_revision, model_artifact_hash, loaded_quantization
from brain.steering.modes import SteeringMode
from brain.steering.sequence_processor import SoftSequenceLogitsProcessor
from config.config import get_steering_runtime_config
from config.emotions import EMOTION_LABELS_DE, EMOTION_ORDER
from config.prompts import (
    STEERING_NEGATIVE_ANCHORS,
    STEERING_NEUTRAL_ANCHORS,
    STEERING_POSITIVE_ANCHORS,
)


LOGGER = logging.getLogger(__name__)
LOADED_SOURCE_FINGERPRINT = runtime_source_fingerprint()


NEUTRAL_DESCRIPTION = "ruhig, ausgeglichen, neutral, kontrolliert"
ANCHOR_VARIANTS = (
    "Dein innerer Zustand ist {description}. Antworte kurz und deutlich in diesem Stil.",
    "Du bist gepraegt von {description}. Formuliere eine spontane kurze Reaktion.",
    "Deine Persoenlichkeit wirkt gerade {description}. Antworte mit einem einzelnen natuerlichen Satz.",
)
ANCHOR_SCALE_FACTORS = {
    "qwen": 0.06,
    "gemma4": 0.06,
    "default": 0.05,
}
PLAN_STRENGTH_SOFT_CAP = 1.2
PLAN_VECTOR_NORM_CAP = 1.6
# T4/FP16 reaches an attention/KV peak before the nominal 8K context limit.
# Offloading only the long-request cache preserves the exact prompt and
# generation budget while moving KV storage, not model computation, to CPU.
QWEN_FP16_CACHE_OFFLOAD_TOTAL_TOKENS = 7000
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
    ("affection", "positive"): "warm zugewandt und persoenlich",
    ("affection", "negative"): "weniger nah und sachlicher",
    ("anxiety", "positive"): "angespannt, vorsichtig und pruefend",
    ("calm", "positive"): "ruhig, klar und entdramatisierend",
    ("calm", "negative"): "weniger reguliert und unruhiger",
    ("warm", "positive"): "warm, weich und fuersorglich",
    ("warm", "negative"): "kuehler und weniger herzlich",
    ("guarded", "positive"): "distanziert, vorsichtig und defensiv",
    ("guarded", "negative"): "offener und weniger misstrauisch",
    ("melancholic", "positive"): "still, schwer und rueckgezogen",
    ("charged", "positive"): "geladen und unter Spannung",
    ("crashout", "positive"): "gereizt, knapp und auf Kante",
    ("crashout", "negative"): "deeskalierend und weniger explosiv",
    ("attached_warm", "positive"): "nah, sanft und loyal",
    ("cautious", "positive"): "vorsichtig, pruefend und aufmerksam",
    ("regulated", "positive"): "ruhig, klar und stabil",
}
REQUEST_PRIORITY_INTERACTIVE = "interactive"
REQUEST_PRIORITY_BACKGROUND = "background"
FORCE_CPU_ENV = "CHAPPIE_STEERING_FORCE_CPU"
QUANTIZE_ENV = "CHAPPIE_STEERING_QUANTIZE"
EMOTION_LABELS = EMOTION_LABELS_DE
EMOTION_STATE_SUMMARIES = {
    "happiness": {
        "neutral": "ausgeglichen statt euphorisch",
        "positive": ("leicht froh", "merklich froh und offen", "sehr froh und aufgeschlossen"),
        "negative": ("nuechtern", "merklich freudearm und trocken", "stark freudearm und unbeschwingt"),
    },
    "sadness": {
        "neutral": "emotional ausgeglichen",
        "positive": ("etwas schwer", "merklich melancholisch", "deutlich traurig und schwer"),
        "negative": ("leicht und nicht niedergedrueckt", "deutlich leichter als melancholisch", "sehr leicht und kaum niedergedrueckt"),
    },
    "frustration": {
        "neutral": "weder gereizt noch uebertrieben gelassen",
        "positive": ("leicht gereizt", "merklich genervt und scharf", "sehr gereizt und schnell explosiv"),
        "negative": ("geduldig", "merklich ruhig und wenig genervt", "sehr ruhig und schwer aus der Fassung zu bringen"),
    },
    "trust": {
        "neutral": "sozial vorsichtig-ausgeglichen",
        "positive": ("leicht offen", "merklich zugewandt und vertrauensvoll", "sehr offen, loyal und nahbar"),
        "negative": ("leicht reserviert", "merklich distanziert und vorsichtig", "stark verschlossen und misstrauisch"),
    },
    "curiosity": {
        "neutral": "sachlich neugierig-ausgeglichen",
        "positive": ("leicht erkundend", "merklich neugierig und explorativ", "sehr bohrend, aufmerksam und erkundend"),
        "negative": ("direkter statt verspielt", "merklich weniger explorativ", "sehr direkt und kaum erkundend"),
    },
    "motivation": {
        "neutral": "ausgeglichen statt druckvoll",
        "positive": ("leicht zielorientiert", "merklich fokussiert und antreibend", "sehr zielstrebig und druckvoll"),
        "negative": ("etwas gebremst", "merklich langsamer und weniger ambitioniert", "stark gebremst und kaum antreibend"),
    },
    "energy": {
        "neutral": "ruhig-wach ausgeglichen",
        "positive": ("leicht wach", "merklich lebhaft und wach", "sehr wach, schnell und voller Antrieb"),
        "negative": ("ruhiger als aufgedreht", "merklich gedaempft und langsam", "sehr ruhig, schwer und wenig aktiv"),
    },
    "affection": {
        "neutral": "sozial warm, aber nicht besonders nah",
        "positive": ("leicht zugewandt", "merklich warm und persoenlich", "sehr nahbar und loyal"),
        "negative": ("sachlicher und weniger nah", "merklich distanzierter", "sehr wenig persoenlich angebunden"),
    },
    "anxiety": {
        "neutral": "nicht unruhig",
        "positive": ("leicht wachsam", "merklich angespannt und vorsichtig", "sehr unruhig und pruefend"),
    },
    "calm": {
        "neutral": "normal reguliert",
        "positive": ("leicht ruhig", "merklich ruhig und klar", "sehr stabil und entdramatisierend"),
        "negative": ("leicht unruhiger", "merklich weniger gesammelt", "stark unruhig und wenig reguliert"),
    },
}


def normalize_request_priority(value: object) -> str:
    return (
        REQUEST_PRIORITY_BACKGROUND
        if str(value or "").strip().casefold() == REQUEST_PRIORITY_BACKGROUND
        else REQUEST_PRIORITY_INTERACTIVE
    )


# Fallback, falls eine Engine ohne __init__ existiert (Tests, alte Pickles).
_TOKENIZER_FALLBACK_LOCK = threading.RLock()


class PriorityGenerationGate:
    """Serialisiert Modelllaeufe und laesst interaktive Anfragen vor."""

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._active = False
        self._waiting_interactive = 0

    @property
    def interactive_waiting(self) -> bool:
        with self._condition:
            return self._waiting_interactive > 0

    @contextmanager
    def acquire(self, priority: object) -> Iterator[None]:
        interactive = normalize_request_priority(priority) == REQUEST_PRIORITY_INTERACTIVE
        with self._condition:
            if interactive:
                self._waiting_interactive += 1
            try:
                while self._active or (not interactive and self._waiting_interactive > 0):
                    self._condition.wait()
                self._active = True
            finally:
                if interactive:
                    self._waiting_interactive -= 1
        try:
            yield
        finally:
            with self._condition:
                self._active = False
                self._condition.notify_all()


class BackgroundYieldCriteria(StoppingCriteria):
    """Beendet nur einen Hintergrundlauf, sobald ein Chat-Turn wartet."""

    def __init__(self, gate: PriorityGenerationGate) -> None:
        self.gate = gate
        self.triggered = False

    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs: Any) -> bool:
        del input_ids, scores, kwargs
        self.triggered = self.gate.interactive_waiting
        return self.triggered


def sanitize_model_slug(model_name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", model_name).strip("_") or "model"


def is_gemma4_name(model_name: str) -> bool:
    model_lower = (model_name or "").lower()
    return "gemma-4" in model_lower or "gemma4" in model_lower


def is_qwen_name(model_name: str) -> bool:
    return "qwen" in (model_name or "").lower()


def anchor_scale_for_model(model_name: str) -> float:
    if is_gemma4_name(model_name):
        return ANCHOR_SCALE_FACTORS["gemma4"]
    if is_qwen_name(model_name):
        return ANCHOR_SCALE_FACTORS["qwen"]
    return ANCHOR_SCALE_FACTORS["default"]


def model_config_int(model: Any, attr: str, default: int = 0) -> int:
    config = getattr(model, "config", None)
    candidates = (
        config,
        getattr(config, "text_config", None),
        getattr(config, "language_config", None),
        getattr(config, "decoder_config", None),
    )
    for candidate in candidates:
        value = getattr(candidate, attr, None)
        if value:
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
    return default


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


def remap_layer_range(
    start: int,
    end: int,
    declared_layer_count: int,
    actual_layer_count: int,
) -> tuple[int, int]:
    """Mappt ein Profil proportional auf die tatsaechliche Modellarchitektur."""
    actual = max(0, int(actual_layer_count))
    if actual <= 0:
        return start, end
    actual_max = actual - 1
    declared = max(0, int(declared_layer_count))
    if declared > 1 and declared != actual:
        declared_max = declared - 1
        start = round(max(0, start) / declared_max * actual_max)
        end = round(max(0, end) / declared_max * actual_max)
    start = max(0, min(actual_max, int(start)))
    end = max(0, min(actual_max, int(end)))
    if end < start:
        start, end = end, start
    return start, end


def contrastive_anchor_pairs(item: Dict[str, Any]) -> list[tuple[str, str]]:
    """Liefert semantisch gepaarte CAA-Beispiele fuer einen Vektor."""
    raw_vector = item.get("vector") if isinstance(item.get("vector"), dict) else {}
    positive = raw_vector.get("positive_anchors") if isinstance(raw_vector, dict) else None
    negative = raw_vector.get("negative_anchors") if isinstance(raw_vector, dict) else None
    positive_items = [str(value).strip() for value in positive or [] if str(value).strip()]
    negative_items = [str(value).strip() for value in negative or [] if str(value).strip()]

    name = str(item.get("name") or "emotion")
    if not positive_items:
        positive_items = list(STEERING_POSITIVE_ANCHORS.get(name, ()))
    if not positive_items:
        description = str(item.get("surface_effect") or name)
        positive_items = [f"Ich klinge {description}."]
    if not negative_items:
        negative_items = list(STEERING_NEGATIVE_ANCHORS.get(name, STEERING_NEUTRAL_ANCHORS))

    pair_count = max(len(positive_items), len(negative_items))
    return [
        (
            positive_items[index % len(positive_items)],
            negative_items[index % len(negative_items)],
        )
        for index in range(pair_count)
    ]


def _collect_base_emotion_state(steering: Dict[str, Any]) -> list[Dict[str, Any]]:
    raw_state = steering.get("emotion_state") if isinstance(steering.get("emotion_state"), dict) else {}
    intensities = steering.get("emotion_intensities") if isinstance(steering.get("emotion_intensities"), dict) else {}
    vectors = steering.get("vectors", []) if isinstance(steering.get("vectors"), list) else []

    base_by_name = {
        str(item.get("name") or "").strip().lower(): item
        for item in vectors
        if isinstance(item, dict) and item.get("source") == "base"
    }

    result = []
    for emotion in EMOTION_ORDER:
        vector = base_by_name.get(emotion, {})
        intensity = float(intensities.get(emotion, 0.0) or 0.0)
        direction = "positive" if intensity >= 0 else "negative"
        if isinstance(vector, dict) and vector.get("direction") in {"positive", "negative"}:
            direction = str(vector.get("direction"))
        result.append({
            "name": emotion,
            "label": EMOTION_LABELS.get(emotion, emotion),
            "value": int(raw_state.get(emotion, vector.get("emotion_value", 50)) or 50),
            "intensity": intensity,
            "strength": abs(intensity),
            "direction": direction,
        })
    return result


def _describe_emotion_dimension(emotion: str, value: int, intensity: float, direction: str) -> str:
    phrases = EMOTION_STATE_SUMMARIES.get(emotion, {})
    if abs(intensity) < 0.01 and 44 <= value <= 56:
        return str(phrases.get("neutral", "ausgeglichen"))

    magnitude = max(abs(intensity), min(1.0, abs(value - 50) / 50.0))
    if magnitude < 0.28:
        idx = 0
    elif magnitude < 0.62:
        idx = 1
    else:
        idx = 2
    bucket = phrases.get(direction, ())
    if isinstance(bucket, tuple) and len(bucket) >= 3:
        return bucket[idx]
    return str(phrases.get("neutral", "ausgeglichen"))


def build_style_instruction(steering_payload: Optional[Dict[str, Any]]) -> Optional[str]:
    """Veralteter Kompatibilitaetseinstieg ohne Prompt-Steering.

    Emotionale Stiltexte waren nie Teil der eigentlichen Layer-Addition, konnten
    aber als zweiter Kanal missverstanden werden. Der Einstieg bleibt fuer
    externe Importe erhalten und liefert absichtlich keine Anweisung mehr.
    """
    del steering_payload
    return None


def build_activation_plan(
    steering_payload: Optional[Dict[str, Any]],
    resolver: Callable[[Dict[str, Any], int, int], Dict[int, torch.Tensor]],
    actual_layer_count: Optional[int] = None,
) -> Dict[int, torch.Tensor]:
    payload = extract_steering_payload(steering_payload)
    steering = payload.get("steering") if isinstance(payload, dict) else None
    if isinstance(steering, dict) and steering.get("enabled") is False:
        return {}
    vectors = steering.get("vectors", []) if isinstance(steering, dict) else []
    combined: Dict[int, torch.Tensor] = {}
    abs_strengths: Dict[int, float] = {}
    norm_caps: Dict[int, float] = {}
    prompt_only_flags: Dict[int, bool] = {}
    try:
        declared_layer_count = int(steering.get("model_layers", 0)) if isinstance(steering, dict) else 0
    except (TypeError, ValueError):
        declared_layer_count = 0

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
        measured_vector = isinstance(item.get("vector"), dict) and item["vector"].get("type") == "layer_vectors"
        if measured_vector and actual_layer_count is not None:
            if declared_layer_count not in (0, actual_layer_count) or not 0 <= start <= end < actual_layer_count:
                raise ValueError("Measured layer vectors cannot be remapped to another architecture")
        if actual_layer_count is not None and not measured_vector:
            start, end = remap_layer_range(
                start,
                end,
                declared_layer_count,
                actual_layer_count,
            )
        try:
            strength = float(item.get("strength", 0.0))
        except (TypeError, ValueError):
            strength = 0.0
        if strength <= 0:
            continue
        sign = -1.0 if str(item.get("direction", "positive")).lower() == "negative" else 1.0
        raw_vector = item.get("vector") if isinstance(item.get("vector"), dict) else {}
        requested_norm_cap = PLAN_VECTOR_NORM_CAP
        if raw_vector.get("type") == "token_logit_contrast":
            try:
                requested_norm_cap = max(
                    PLAN_VECTOR_NORM_CAP,
                    min(24.0, float(raw_vector.get("max_norm", PLAN_VECTOR_NORM_CAP))),
                )
            except (TypeError, ValueError):
                requested_norm_cap = PLAN_VECTOR_NORM_CAP
        elif "max_norm" in raw_vector:
            try:
                requested_norm_cap = max(
                    PLAN_VECTOR_NORM_CAP,
                    min(12.0, float(raw_vector.get("max_norm", PLAN_VECTOR_NORM_CAP))),
                )
            except (TypeError, ValueError):
                requested_norm_cap = PLAN_VECTOR_NORM_CAP
        basis = resolver(item, start, end)
        for layer, vector in basis.items():
            if vector is None:
                continue
            scaled = vector.detach().float().cpu() * (sign * strength)
            combined[layer] = combined.get(layer, torch.zeros_like(scaled)) + scaled
            abs_strengths[layer] = abs_strengths.get(layer, 0.0) + abs(sign * strength)
            norm_caps[layer] = max(norm_caps.get(layer, PLAN_VECTOR_NORM_CAP), requested_norm_cap)
            item_prompt_only = bool(raw_vector.get("prompt_only", False))
            prompt_only_flags[layer] = prompt_only_flags.get(layer, True) and item_prompt_only

    for layer, vector in list(combined.items()):
        divisor = max(1.0, (abs_strengths.get(layer, 0.0) / PLAN_STRENGTH_SOFT_CAP) ** 0.5)
        adjusted = vector / divisor
        norm = float(adjusted.norm().item())
        norm_cap = norm_caps.get(layer, PLAN_VECTOR_NORM_CAP)
        if norm > norm_cap:
            adjusted = torch.nn.functional.normalize(adjusted, dim=0) * norm_cap
        adjusted._chappie_prompt_only = bool(prompt_only_flags.get(layer, False))
        combined[layer] = adjusted

    return combined


def _safe_steering_add(hidden: torch.Tensor, vector: torch.Tensor) -> torch.Tensor:
    if hidden.dim() != 3:
        LOGGER.warning(
            "Steering-Addition uebersprungen: hidden dim=%d shape=%s (erwartet 3D). "
            "Moegliche Broadcast-Explosion vermieden.",
            hidden.dim(), tuple(hidden.shape),
        )
        return hidden
    if hidden.size(-1) != vector.size(0):
        LOGGER.warning(
            "Steering-Addition uebersprungen: hidden_size=%d vs vector_size=%d.",
            hidden.size(-1), vector.size(0),
        )
        return hidden
    return hidden + vector.view(1, 1, -1).to(device=hidden.device, dtype=hidden.dtype)


def add_vector_to_output(outputs: Any, vector: torch.Tensor) -> Any:
    if isinstance(outputs, tuple) and outputs:
        hidden = outputs[0]
        if torch.is_tensor(hidden):
            updated = _safe_steering_add(hidden, vector)
            return (updated, *outputs[1:])
        return outputs
    if torch.is_tensor(outputs):
        return _safe_steering_add(outputs, vector)
    return outputs


def add_vector_to_inputs(inputs: Any, vector: torch.Tensor) -> Any:
    if isinstance(inputs, tuple) and inputs:
        hidden = inputs[0]
        if torch.is_tensor(hidden):
            updated = _safe_steering_add(hidden, vector)
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
        self.hidden_size = model_config_int(model, "hidden_size")
        self.num_layers = model_config_int(model, "num_hidden_layers")
        self.anchor_scale_factor = anchor_scale_for_model(model_name)
        self._cache_lock = threading.Lock()

    def resolve(self, item: Dict[str, Any], start: int, end: int) -> Dict[int, torch.Tensor]:
        raw_vector = item.get("vector")
        if isinstance(raw_vector, dict) and raw_vector.get("type") == "layer_vectors":
            if (raw_vector.get("model") != self.model_name
                    or raw_vector.get("site") != "decoder_layer_input"
                    or raw_vector.get("num_layers") != self.num_layers
                    or raw_vector.get("hidden_size") != self.hidden_size):
                raise ValueError("Measured layer vector model/shape/site mismatch")
            expected_revision = raw_vector.get("model_revision")
            actual_revision = getattr(getattr(self.model, "config", None), "_commit_hash", None)
            if expected_revision and actual_revision and expected_revision != actual_revision:
                raise ValueError("Measured vector model revision mismatch")
            result = {}
            for key, values in raw_vector.get("layers", {}).items():
                layer = int(key)
                vector = torch.tensor(values, dtype=torch.float32)
                if (not 0 <= layer < self.num_layers or not start <= layer <= end
                        or vector.shape != (self.hidden_size,) or not torch.isfinite(vector).all()
                        or not torch.isclose(vector.norm(), torch.tensor(1.0), atol=1e-4)):
                    raise ValueError("Invalid measured layer vector")
                result[layer] = vector
            if not result:
                raise ValueError("Empty measured layer vectors")
            return result
        if isinstance(raw_vector, list) and len(raw_vector) == self.hidden_size:
            base = torch.tensor(raw_vector, dtype=torch.float32)
            return {layer: base for layer in range(start, end + 1)}
        if isinstance(raw_vector, dict) and raw_vector.get("type") == "token_logit_contrast":
            base = self._token_logit_contrast(raw_vector)
            return {layer: base for layer in range(start, end + 1)}
        basis = self._load_or_build_basis(item)
        return {
            layer: basis["layers"][layer] * basis["scales"].get(layer, 1.0)
            for layer in range(start, end + 1)
            if layer in basis["layers"]
        }

    def _token_logit_contrast(self, vector_data: Dict[str, Any]) -> torch.Tensor:
        """Richtet den letzten Hidden State auf Zieltoken statt KI-Labels aus."""
        positive_texts = [str(value) for value in vector_data.get("positive_tokens", []) if str(value).strip()]
        negative_texts = [str(value) for value in vector_data.get("negative_tokens", []) if str(value).strip()]
        if not positive_texts or not negative_texts:
            raise ValueError("token_logit_contrast benoetigt positive_tokens und negative_tokens")

        def token_targets(texts: list[str], weights: object) -> Dict[int, float]:
            configured = weights if isinstance(weights, dict) else {}
            result: Dict[int, float] = {}
            for text in texts:
                encoded = self.tokenizer(text, add_special_tokens=False).get("input_ids", [])
                if encoded and isinstance(encoded[0], list):
                    encoded = encoded[0]
                # Fuer autoregressive Entscheidungen ist der erste Token einer
                # Zielphrase entscheidend. Suffixe wie "en" oder "z" waeren
                # als globale Steuerziele unspezifisch und schaedlich.
                if encoded:
                    try:
                        target = max(0.05, min(4.0, float(configured.get(text, 1.0))))
                    except (TypeError, ValueError):
                        target = 1.0
                    token_id = int(encoded[0])
                    result[token_id] = max(result.get(token_id, 0.0), target)
            return result

        positive_targets = token_targets(positive_texts, vector_data.get("positive_token_weights"))
        negative_targets = token_targets(negative_texts, vector_data.get("negative_token_weights"))
        positive_ids = sorted(positive_targets)
        negative_ids = sorted(negative_targets)
        output_embeddings = self.model.get_output_embeddings()
        weight = getattr(output_embeddings, "weight", None)
        if weight is None:
            raise ValueError("Modell stellt keine Output-Embeddings fuer Token-Kontrast bereit")
        positive_set = set(positive_ids)
        negative_set = set(negative_ids) - positive_set
        if not negative_set:
            raise ValueError("Token-Kontrast benoetigt disjunkte Zieltoken")

        selected_ids = sorted(positive_set) + sorted(negative_set)
        rows = weight[selected_ids].detach().float()
        targets = torch.tensor(
            [positive_targets[token_id] for token_id in sorted(positive_set)]
            + [-negative_targets[token_id] for token_id in sorted(negative_set)],
            dtype=torch.float32,
            device=rows.device,
        )

        # Gesucht ist eine Hidden-State-Richtung v mit W_pos*v > 0 und
        # W_neg*v < 0. Der regulierte Dual-Loeser trifft diese Logit-Ziele
        # wesentlich genauer als die Differenz zweier Embedding-Mittelwerte.
        gram = rows @ rows.T
        ridge_factor = max(1e-6, float(vector_data.get("ridge", 1e-3)))
        ridge = ridge_factor * max(1e-6, float(torch.diagonal(gram).mean().item()))
        system = gram + torch.eye(gram.size(0), dtype=gram.dtype, device=gram.device) * ridge
        coefficients = torch.linalg.solve(system, targets)
        direction = rows.T @ coefficients
        norm = float(direction.norm().item())
        if norm <= 1e-8:
            raise ValueError("Token-Kontrast ergab einen leeren Vektor")
        scale = max(0.01, float(vector_data.get("activation_scale", 1.0)))
        return (direction / norm * scale).cpu()

    def token_sequence_vectors(self, vector_data: Dict[str, Any]) -> list[torch.Tensor]:
        """Legacy API retained solely to report retirement explicitly."""
        raise ValueError("Hard sequence steering is retired; use soft_sequence_steering")

    def _basis_cache_path(self, item: Dict[str, Any]) -> Path:
        payload = {
            "version": 14,
            "scale_factor": self.anchor_scale_factor,
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
                try:
                    return torch.load(path, map_location="cpu", weights_only=True)
                except TypeError:
                    return torch.load(path, map_location="cpu")
            basis = self._build_basis(item)
            torch.save(basis, path)
            return basis

    def _build_basis(self, item: Dict[str, Any]) -> Dict[str, Any]:
        layers: Dict[int, torch.Tensor] = {}
        scales: Dict[int, float] = {}
        name = str(item.get("name") or "emotion")
        description = str(item.get("surface_effect") or name)
        anchor_pairs = contrastive_anchor_pairs(item)
        # Vektorspezifische Sammelfrage (z.B. Identitaet statt Befinden):
        # Anker werden als Antwort auf IHRE Frage gesammelt, sonst waere der
        # Kontrast ein Non-Sequitur und die Richtung semantisch verrauscht.
        raw_vector = item.get("vector") if isinstance(item.get("vector"), dict) else {}
        context_question = str((raw_vector.get("context_question") if isinstance(raw_vector, dict) else None)
                               or "Wie geht es dir heute?")
        collection_mode = str(raw_vector.get("collection_mode") or "assistant_answer")
        try:
            activation_scale = max(0.1, min(4.0, float(raw_vector.get("activation_scale", 1.0))))
        except (TypeError, ValueError):
            activation_scale = 1.0

        pos_sum: Dict[int, torch.Tensor] = {}
        neg_sum: Dict[int, torch.Tensor] = {}
        neutral_norms: Dict[int, float] = {}

        for positive_example, negative_example in anchor_pairs:
            if collection_mode == "generation_prompt":
                pos_states = self._collect_hidden_state_generation_prompt(
                    positive_example,
                    question=context_question,
                )
                neg_states = self._collect_hidden_state_generation_prompt(
                    negative_example,
                    question=context_question,
                )
            else:
                pos_states = self._collect_hidden_state_text(positive_example, question=context_question)
                neg_states = self._collect_hidden_state_text(negative_example, question=context_question)
            for layer in range(self.num_layers):
                pos = pos_states[layer]
                neg = neg_states[layer]
                pos_sum[layer] = pos_sum.get(layer, torch.zeros_like(pos)) + pos
                neg_sum[layer] = neg_sum.get(layer, torch.zeros_like(neg)) + neg
                neutral_norms[layer] = neutral_norms.get(layer, 0.0) + float(neg.norm().item())

        count = float(len(anchor_pairs))
        for layer in range(self.num_layers):
            delta = (pos_sum[layer] - neg_sum[layer]) / count
            norm = float(delta.norm().item())
            if norm <= 1e-8:
                continue
            reference_norm = max(1.0, neutral_norms[layer] / count)
            scaled = torch.nn.functional.normalize(delta, dim=0)
            layers[layer] = scaled.cpu()
            scales[layer] = float(reference_norm * self.anchor_scale_factor * activation_scale)

        return {
            "layers": layers,
            "scales": scales,
            "meta": {
                "name": name,
                "description": description,
                "contrast_pairs": len(anchor_pairs),
                "collection_mode": collection_mode,
                "activation_scale": activation_scale,
            },
        }

    def _collect_hidden_state_generation_prompt(
        self,
        system_state: str,
        question: str,
    ) -> Dict[int, torch.Tensor]:
        """Sammelt den Zustand direkt vor dem ersten generierten Antworttoken."""
        messages = [
            {"role": "system", "content": system_state},
            {"role": "user", "content": question},
        ]
        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        encoded = self.tokenizer(prompt, return_tensors="pt")
        encoded = {key: value.to(self.device) for key, value in encoded.items()}
        with torch.inference_mode():
            outputs = self.model(**encoded, output_hidden_states=True, use_cache=False)
        if self.device.type == "cuda":
            torch.cuda.empty_cache()
        return {
            layer: outputs.hidden_states[layer + 1][0, -1, :].detach().float().cpu()
            for layer in range(self.num_layers)
        }

    def _collect_hidden_state_text(self, text: str, question: str = "Wie geht es dir heute?") -> Dict[int, torch.Tensor]:
        messages = [
            {"role": "system", "content": "Du bist CHAPPiE."},
            {"role": "user", "content": question},
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
        if self.device.type == "cuda":
            torch.cuda.empty_cache()
        return {
            layer: outputs.hidden_states[layer + 1][0, -window:, :].mean(dim=0).detach().float().cpu()
            for layer in range(self.num_layers)
        }


class LocalSteeringEngine:
    def __init__(
        self,
        model_name: str,
        cache_dir: Optional[Path] = None,
        context_length: int = 8192,
        quantize: Optional[bool] = None,
        adapter_path: Optional[str] = None,
        background_input_token_limit: int = 256,
    ):
        self.model_name = model_name
        self.model_revision = cached_model_revision(model_name)
        local_model_hash = model_artifact_hash(model_name) if Path(model_name).is_dir() else None
        self.context_length = context_length
        self.background_input_token_limit = max(128, int(background_input_token_limit))
        self.quantize = self._resolve_quantize(quantize)
        self.device = self._select_device()
        self.dtype = torch.float16 if self.device.type == "cuda" else torch.float32
        self.cache_dir = cache_dir or (Path(__file__).resolve().parent.parent / "data" / "steering_cache")
        self._generation_lock = threading.Lock()
        self._generation_gate = PriorityGenerationGate()
        # Der Rust-Tokenizer ist nicht threadsicher ("Already borrowed" bei
        # gleichzeitigem Encode waehrend ein Stream dekodiert, live 2026-09-08:
        # Hintergrund-Job des Trainings-Daemons vs. interaktiver Turn).
        # Reihenfolge ist immer Gate -> Tokenizer-Lock, nie umgekehrt.
        self._tokenizer_lock = threading.RLock()
        self.last_steering_report: Dict[str, Any] = {
            "active": False,
            "hook_count": 0,
            "requested_layers": [],
            "applied_layers": [],
            "mode": "activation_addition",
            "model": model_name,
        }
        model_config = AutoConfig.from_pretrained(model_name, **self._build_loader_kwargs())
        self.model_revision = self.model_revision or getattr(model_config, "_commit_hash", None) or cached_model_revision(model_name)
        if self.model_revision is None and local_model_hash is None:
            raise ValueError("Cannot establish the loaded model revision")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, **self._build_loader_kwargs())
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        # Bei gekuerzten Chatverlaeufen muessen die aktuelle Nutzerfrage und
        # die letzten Turns erhalten bleiben, nicht der aelteste Kontext.
        self.tokenizer.truncation_side = "left"
        max_pos = getattr(model_config, "max_position_embeddings", None)
        if max_pos is None:
            max_pos = context_length
        model_config.max_position_embeddings = min(max_pos, context_length)
        LOGGER.info("Steering-Modell %s: max_position_embeddings auf %d begrenzt (KV-Cache-Schutz).",
                     model_name, model_config.max_position_embeddings)
        quantization_config = self._build_quantization_config() if self.quantize else None
        loader_kwargs = self._build_loader_kwargs(for_model=True)
        if quantization_config is not None:
            loader_kwargs["quantization_config"] = quantization_config
        if not self.quantize:
            loader_kwargs["torch_dtype"] = self.dtype
        try:
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                config=model_config,
                **loader_kwargs,
            )
        except TypeError:
            fallback_kwargs = dict(loader_kwargs)
            fallback_kwargs.pop("quantization_config", None)
            fallback_kwargs.pop("attn_implementation", None)
            fallback_kwargs.pop("torch_dtype", None)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                config=model_config,
                torch_dtype=self.dtype,
                **fallback_kwargs,
            )
        if not self.quantize:
            self.model.to(self.device)
        self.model.eval()
        self.model_revision = self.model_revision or getattr(self.model.config, "_commit_hash", None) or cached_model_revision(model_name)
        self.model.config._commit_hash = self.model_revision

        # Load LoRA adapter if specified
        adapter_hash = None
        if adapter_path and Path(adapter_path).exists():
            from peft import PeftModel
            adapter_hash = model_artifact_hash(adapter_path)
            LOGGER.info("Steering: Lade LoRA-Adapter von %s", adapter_path)
            self.model = PeftModel.from_pretrained(self.model, adapter_path)
            LOGGER.info("Steering: LoRA-Adapter erfolgreich geladen.")

        self.layers = self._find_transformer_layers()
        self.resolver = ActivationVectorResolver(model_name, self.cache_dir, self.tokenizer, self.model, self.device)
        self.runtime_provenance = {
            "source_sha256": LOADED_SOURCE_FINGERPRINT,
            "model": model_name, "model_revision": self.model_revision,
            "num_layers": len(self.layers), "hidden_size": model_config_int(self.model, "hidden_size"),
            "site": "decoder_layer_input", "quantized": loaded_quantization(self.model) != "none",
            "quantization": loaded_quantization(self.model),
            "adapter_sha256": adapter_hash, "local_model_sha256": local_model_hash,
            "torch_version": torch.__version__, "cuda_version": torch.version.cuda,
            "context_length": self.context_length,
        }

    @staticmethod
    def _nested_attr(root: Any, path: str) -> Any:
        current = root
        for part in path.split("."):
            current = getattr(current, part, None)
            if current is None:
                return None
        return current

    def _find_transformer_layers(self) -> list[Any]:
        candidates = (
            "model.layers",
            "model.language_model.layers",
            "language_model.layers",
            "language_model.model.layers",
            "model.decoder.layers",
            "decoder.layers",
            "transformer.h",
            "gpt_neox.layers",
        )
        for path in candidates:
            layers = self._nested_attr(self.model, path)
            if layers is None:
                continue
            try:
                resolved = list(layers)
            except TypeError:
                continue
            if resolved:
                LOGGER.info("Steering-Layer fuer %s via %s erkannt (%d Layer).", self.model_name, path, len(resolved))
                return resolved
        raise AttributeError(f"Keine Transformer-Layer fuer {self.model_name} gefunden.")

    def close(self) -> None:
        """Gibt alle GPU-Ressourcen frei (altes Modell vollstaendig entfernen)."""
        try:
            if torch.cuda.is_available():
                torch.cuda.synchronize()
        except Exception:
            pass

        for attr in ("resolver", "layers", "model", "tokenizer"):
            try:
                setattr(self, attr, None)
            except Exception:
                pass

        for _ in range(3):
            gc.collect()

        if torch.cuda.is_available():
            torch.cuda.synchronize()
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()
            try:
                torch.cuda.ipc_collect()
            except Exception:
                pass

    @staticmethod
    def _cuda_free_gib() -> float:
        if not torch.cuda.is_available():
            return 0.0
        try:
            free, _total = torch.cuda.mem_get_info()
            return float(free) / float(1024 ** 3)
        except Exception:
            return 0.0

    def _select_device(self) -> torch.device:
        force_cpu = os.getenv(FORCE_CPU_ENV, "").strip().lower()
        if force_cpu in {"1", "true", "yes", "on"}:
            LOGGER.warning("Steering-Backend erzwingt CPU-Modus via %s.", FORCE_CPU_ENV)
            return torch.device("cpu")
        if not torch.cuda.is_available():
            return torch.device("cpu")

        required_gpu_gib = self._estimate_required_gpu_gib()
        available_gpu_gib = self._cuda_free_gib()
        if required_gpu_gib and available_gpu_gib and available_gpu_gib < required_gpu_gib:
            LOGGER.warning(
                "Steering-Backend nutzt CPU-Fallback: %.2f GiB GPU-RAM sind fuer %s zu klein (ca. %.2f GiB benoetigt).",
                available_gpu_gib,
                self.model_name,
                required_gpu_gib,
            )
            return torch.device("cpu")
        return torch.device("cuda:0")

    def _resolve_quantize(self, explicit: Optional[bool] = None) -> bool:
        if explicit is not None:
            return explicit
        env_val = os.getenv(QUANTIZE_ENV, "").strip().lower()
        if env_val in {"1", "true", "yes", "on"}:
            return True
        if env_val in {"0", "false", "no", "off"}:
            return False
        if not torch.cuda.is_available():
            return False
        try:
            total_gib = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            model_name = getattr(self, "model_name", "") if self is not None else ""
            if is_gemma4_name(model_name) and ("26b" in model_name.lower() or "a4b" in model_name.lower()):
                return total_gib < 48.0
            return total_gib < 24.0
        except Exception:
            return False

    def _build_quantization_config(self) -> BitsAndBytesConfig:
        LOGGER.info("Steering-Backend: NF4 4-bit Quantisierung aktiviert fuer %s.", self.model_name)
        return BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )

    def _estimate_required_gpu_gib(self) -> float:
        model_lower = (self.model_name or "").lower()
        match = re.search(r"qwen/qwen3(?:\.5)?-(\d+)b", model_lower)
        if match:
            try:
                billions = float(match.group(1))
            except ValueError:
                return 0.0
            per_billion = 0.6 if self.quantize else 2.2
            weights_gib = billions * per_billion
            kv_cache_gib = billions * 0.08 * (self.context_length / 1024)
            overhead_gib = 1.0 if self.quantize else 1.5
        elif is_gemma4_name(model_lower):
            if "26b" in model_lower or "a4b" in model_lower:
                total_b = 26.0
                active_b = 4.0
                per_billion = 0.5 if self.quantize else 2.0
                overhead_gib = 1.5 if self.quantize else 2.0
            elif "12b" in model_lower:
                total_b = 12.0
                active_b = 12.0
                per_billion = 0.6 if self.quantize else 2.2
                overhead_gib = 1.0 if self.quantize else 1.5
            else:
                total_b = 4.0
                active_b = 4.0
                per_billion = 0.6 if self.quantize else 2.2
                overhead_gib = 1.0 if self.quantize else 1.5
            weights_gib = total_b * per_billion
            kv_cache_gib = active_b * 0.08 * (self.context_length / 1024)
        else:
            return 8.0
        total_gib = weights_gib + kv_cache_gib + overhead_gib
        LOGGER.debug("GPU-Speicher-Schaetzung fuer %s (ctx %d, quantize=%s): %.2f GiB (%.2f weights + %.2f KV-cache + %.2f overhead).",
                      self.model_name, self.context_length, self.quantize, total_gib, weights_gib, kv_cache_gib, overhead_gib)
        return total_gib

    @staticmethod
    def _cuda_total_gib() -> float:
        if not torch.cuda.is_available():
            return 0.0
        try:
            return float(torch.cuda.get_device_properties(0).total_memory) / float(1024 ** 3)
        except Exception:
            return 0.0

    def _build_loader_kwargs(self, for_model: bool = False) -> Dict[str, Any]:
        """Erlaubt Remote-Code fuer Modellfamilien, die lokal noch nicht nativ im Transformers-Pin stecken."""
        model_lower = (self.model_name or "").lower()
        kwargs: Dict[str, Any] = {}
        if getattr(self, "model_revision", None):
            kwargs["revision"] = self.model_revision
        if "qwen/qwen3.5" in model_lower or is_gemma4_name(model_lower):
            kwargs["trust_remote_code"] = True
        if for_model and ("qwen" in model_lower or is_gemma4_name(model_lower)):
            kwargs["attn_implementation"] = "sdpa"
        return kwargs

    def build_prompt(
        self,
        messages: list[dict],
        chat_template_kwargs: Optional[Dict[str, Any]] = None,
        steering_payload: Optional[Dict[str, Any]] = None,
        reserve_new_tokens: int = 0,
        input_token_limit: Optional[int] = None,
    ) -> tuple[str, Dict[str, torch.Tensor]]:
        kwargs = dict(chat_template_kwargs or {})
        prompt_messages = [dict(message) for message in messages]
        with self._tokenizer_guarded():
            prompt = self.tokenizer.apply_chat_template(prompt_messages, tokenize=False, add_generation_prompt=True, **kwargs)
        reserved = max(0, min(int(reserve_new_tokens or 0), max(0, self.context_length - 128)))
        max_input_length = max(128, self.context_length - reserved)
        if input_token_limit is not None:
            max_input_length = min(max_input_length, max(128, int(input_token_limit)))
        with self._tokenizer_guarded():
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=max_input_length)
        actual_len = int(inputs["input_ids"].shape[1])
        if actual_len > max_input_length:
            LOGGER.warning("Prompt nach Truncation immer noch %d Token (Limit %d). Das sollte nicht passieren.", actual_len, max_input_length)
        return prompt, {key: value.to(self.device) for key, value in inputs.items()}

    def _log_gpu_stats(self, label: str) -> None:
        if self.device.type != "cuda":
            return
        try:
            allocated = torch.cuda.memory_allocated() / (1024 ** 3)
            reserved = torch.cuda.memory_reserved() / (1024 ** 3)
            max_alloc = torch.cuda.max_memory_allocated() / (1024 ** 3)
            LOGGER.debug("GPU-Memory [%s]: alloc=%.2f GiB, reserved=%.2f GiB, peak=%.2f GiB", label, allocated, reserved, max_alloc)
        except Exception:
            pass

    @contextmanager
    def _tokenizer_guarded(self) -> Iterator[None]:
        """Serialisiert alle Tokenizer-Zugriffe (Rust-Tokenizer ist nicht threadsicher)."""
        with getattr(self, "_tokenizer_lock", _TOKENIZER_FALLBACK_LOCK):
            yield

    @contextmanager
    def _generation_slot(self, request_priority: object) -> Iterator[None]:
        gate = getattr(self, "_generation_gate", None)
        if isinstance(gate, PriorityGenerationGate):
            with gate.acquire(request_priority):
                yield
            return
        with self._generation_lock:
            yield

    def _background_yield_criteria(self, request_priority: object) -> Optional[BackgroundYieldCriteria]:
        gate = getattr(self, "_generation_gate", None)
        if (
            normalize_request_priority(request_priority) == REQUEST_PRIORITY_BACKGROUND
            and isinstance(gate, PriorityGenerationGate)
        ):
            return BackgroundYieldCriteria(gate)
        return None

    def generate(self, messages: list[dict], max_tokens: int, temperature: float, steering_payload: Optional[Dict[str, Any]] = None, chat_template_kwargs: Optional[Dict[str, Any]] = None, repetition_penalty: float = 1.15, top_p: Optional[float] = None, top_k: Optional[int] = None, seed: Optional[int] = None, request_priority: str = REQUEST_PRIORITY_INTERACTIVE) -> Dict[str, Any]:
        priority = normalize_request_priority(request_priority)
        prompt, inputs = self.build_prompt(
            messages,
            chat_template_kwargs,
            steering_payload,
            reserve_new_tokens=max_tokens,
            input_token_limit=(self.background_input_token_limit if priority == REQUEST_PRIORITY_BACKGROUND else None),
        )
        generation_kwargs = self._generation_kwargs(
            inputs,
            max_tokens,
            temperature,
            repetition_penalty,
            top_p=top_p,
            top_k=top_k,
            enable_thinking=(chat_template_kwargs or {}).get("enable_thinking"),
        )
        background_yield = self._background_yield_criteria(request_priority)
        if background_yield is not None:
            generation_kwargs["stopping_criteria"] = StoppingCriteriaList([background_yield])
        self._log_gpu_stats("pre-generate")
        steering_runtime: Dict[str, Any] = {}
        with self._generation_slot(request_priority):
            with self._tokenizer_guarded():
                if seed is not None:
                    torch.manual_seed(int(seed))
                    if torch.cuda.is_available():
                        torch.cuda.manual_seed_all(int(seed))
                with self._apply_activation_plan(steering_payload, int(inputs["input_ids"].shape[1])) as processors:
                    if processors:
                        generation_kwargs["logits_processor"] = LogitsProcessorList(processors)
                    with torch.inference_mode():
                        generated = self.model.generate(**generation_kwargs)
                # Capture the request report before another queued request can
                # replace the shared health snapshot.
                steering_runtime = dict(self.last_steering_report)
        self._log_gpu_stats("post-generate")
        input_len = int(inputs["input_ids"].shape[1])
        new_ids = generated[0][input_len:]
        reasoning, answer = self._split_thinking_output(new_ids)
        completion_tokens = max(0, int(generated[0].shape[0] - input_len))
        prompt_tokens = int(inputs["input_ids"].shape[1])
        visible_text = answer
        if not visible_text and not reasoning:
            with self._tokenizer_guarded():
                visible_text = self.tokenizer.decode(new_ids, skip_special_tokens=True).strip()
        end_metadata = generation_end_metadata(new_ids.tolist(), generation_kwargs["max_new_tokens"],
                                               generation_kwargs.get("eos_token_id"),
                                               bool(background_yield and background_yield.triggered))
        result: Dict[str, Any] = {
            **end_metadata,
            "runtime_provenance": getattr(self, "runtime_provenance", {}),
            "text": visible_text,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "prompt": prompt,
            "cache_implementation": generation_kwargs.get("cache_implementation", "dynamic"),
            "steering_runtime": steering_runtime,
            "background_preempted": bool(background_yield and background_yield.triggered),
        }
        if reasoning:
            result["reasoning"] = reasoning
        # empty_cache() only helps after all request-sized CUDA tensors have
        # lost their references. Previously it ran while generated/inputs were
        # still alive and could not release long-context allocations.
        del generated, new_ids, generation_kwargs, inputs
        if self.device.type == "cuda":
            torch.cuda.empty_cache()
        return result

    def _split_thinking_output(self, token_ids: torch.Tensor) -> tuple[str, str]:
        """Trennt Reasoning und Antwort fuer Qwen- und Gemma-4-Chat-Templates."""
        with self._tokenizer_guarded():
            return self._split_thinking_output_locked(token_ids)

    def _split_thinking_output_locked(self, token_ids: torch.Tensor) -> tuple[str, str]:
        if token_ids.numel() == 0:
            return "", ""
        ids_list = token_ids.tolist()
        if is_qwen_name(self.model_name):
            think_start = self.tokenizer.convert_tokens_to_ids("<think>")
            think_end = self.tokenizer.convert_tokens_to_ids("</think>")
            try:
                if isinstance(think_end, int) and think_end >= 0 and think_end in ids_list:
                    idx_start = ids_list.index(think_start) + 1 if isinstance(think_start, int) and think_start in ids_list else 0
                    idx_end = ids_list.index(think_end, idx_start)
                    reasoning_ids = token_ids[idx_start:idx_end]
                    answer_ids = token_ids[idx_end + 1:]
                    reasoning_text = self.tokenizer.decode(reasoning_ids, skip_special_tokens=True, clean_up_tokenization_spaces=True).strip()
                    answer_text = self.tokenizer.decode(answer_ids, skip_special_tokens=True, clean_up_tokenization_spaces=True).strip()
                    return reasoning_text, answer_text
                if isinstance(think_start, int) and think_start >= 0 and think_start in ids_list:
                    idx_start = ids_list.index(think_start) + 1
                    reasoning_text = self.tokenizer.decode(token_ids[idx_start:], skip_special_tokens=True, clean_up_tokenization_spaces=True).strip()
                    return reasoning_text, ""
            except Exception:
                pass
        if is_gemma4_name(self.model_name):
            raw_text = self.tokenizer.decode(token_ids, skip_special_tokens=False, clean_up_tokenization_spaces=True)
            think_start = "<|channel>thought"
            think_end = "<|channel|>"
            if think_start in raw_text and think_end in raw_text:
                start_idx = raw_text.find(think_start) + len(think_start)
                end_idx = raw_text.find(think_end, start_idx)
                if end_idx > start_idx:
                    reasoning = raw_text[start_idx:end_idx].strip()
                    answer_raw = raw_text[end_idx + len(think_end):].strip()
                    answer_ids = self.tokenizer(answer_raw, add_special_tokens=False, return_tensors="pt")["input_ids"][0]
                    answer = self.tokenizer.decode(answer_ids, skip_special_tokens=True, clean_up_tokenization_spaces=True).strip()
                    return reasoning, answer
        return "", self.tokenizer.decode(token_ids, skip_special_tokens=True, clean_up_tokenization_spaces=True).strip()

    def stream_generate(self, messages: list[dict], max_tokens: int, temperature: float, steering_payload: Optional[Dict[str, Any]] = None, chat_template_kwargs: Optional[Dict[str, Any]] = None, repetition_penalty: float = 1.15, top_p: Optional[float] = None, top_k: Optional[int] = None, seed: Optional[int] = None, steering_report_sink: Optional[Dict[str, Any]] = None, request_priority: str = REQUEST_PRIORITY_INTERACTIVE) -> Iterator[str]:
        # Der aktive Webpfad deaktiviert natives Thinking und kann deshalb
        # direkt ueber den Transformers-Streamer ausliefern. So beginnt die
        # SSE-Antwort nach dem ersten sichtbaren Text statt erst nach der
        # kompletten Completion. Alte Test-/Kompatibilitaetsobjekte ohne
        # geladenes Modell bleiben beim sicheren gepufferten Pfad.
        if not hasattr(self, "model") or not hasattr(self, "tokenizer"):
            yield from self._stream_generate_buffered(
                messages,
                max_tokens=max_tokens,
                temperature=temperature,
                steering_payload=steering_payload,
                chat_template_kwargs=chat_template_kwargs,
                repetition_penalty=repetition_penalty,
                top_p=top_p,
                top_k=top_k,
                seed=seed,
                steering_report_sink=steering_report_sink,
                request_priority=request_priority,
            )
            return

        try:
            from transformers import TextIteratorStreamer
        except ImportError:  # pragma: no cover - durch Transformers-Pin abgedeckt
            yield from self._stream_generate_buffered(
                messages,
                max_tokens=max_tokens,
                temperature=temperature,
                steering_payload=steering_payload,
                chat_template_kwargs=chat_template_kwargs,
                repetition_penalty=repetition_penalty,
                top_p=top_p,
                top_k=top_k,
                seed=seed,
                steering_report_sink=steering_report_sink,
                request_priority=request_priority,
            )
            return

        prompt, inputs = self.build_prompt(
            messages,
            chat_template_kwargs,
            steering_payload,
            reserve_new_tokens=max_tokens,
            input_token_limit=(
                self.background_input_token_limit
                if normalize_request_priority(request_priority) == REQUEST_PRIORITY_BACKGROUND
                else None
            ),
        )
        generation_kwargs = self._generation_kwargs(
            inputs,
            max_tokens,
            temperature,
            repetition_penalty,
            top_p=top_p,
            top_k=top_k,
            enable_thinking=(chat_template_kwargs or {}).get("enable_thinking"),
        )
        background_yield = self._background_yield_criteria(request_priority)
        if background_yield is not None:
            generation_kwargs["stopping_criteria"] = StoppingCriteriaList([background_yield])
        del prompt
        streamer = TextIteratorStreamer(
            self.tokenizer,
            skip_prompt=True,
            skip_special_tokens=True,
            timeout=None,
        )
        generation_kwargs["streamer"] = streamer
        generation_error: list[BaseException] = []
        steering_report: Dict[str, Any] = {}

        def _run_generation() -> None:
            try:
                with self._generation_slot(request_priority):
                    with self._tokenizer_guarded():
                        if seed is not None:
                            torch.manual_seed(int(seed))
                            if torch.cuda.is_available():
                                torch.cuda.manual_seed_all(int(seed))
                        with self._apply_activation_plan(steering_payload, int(inputs["input_ids"].shape[1])) as processors:
                            if processors:
                                generation_kwargs["logits_processor"] = LogitsProcessorList(processors)
                            with torch.inference_mode():
                                generated = self.model.generate(**generation_kwargs)
                        steering_report.update(self.last_steering_report)
                    end_metadata = generation_end_metadata(
                        generated[0][int(inputs["input_ids"].shape[1]):].tolist(), generation_kwargs["max_new_tokens"],
                        generation_kwargs.get("eos_token_id"),
                        bool(background_yield and background_yield.triggered))
                    steering_report["generation"] = end_metadata
                    del generated
            except BaseException as exc:  # pragma: no cover - Modelllaufzeit
                generation_error.append(exc)
                # TextIteratorStreamer only receives its sentinel when
                # generate() finishes normally. Unblock the consumer on
                # controlled OOMs, disconnects and other model exceptions.
                try:
                    streamer.end()
                except Exception:
                    pass

        worker = threading.Thread(target=_run_generation, name="chappie-steering-stream", daemon=True)
        worker.start()
        emitted_text = False
        try:
            for piece in streamer:
                text = str(piece or "")
                if text:
                    emitted_text = True
                    yield text
        finally:
            worker.join(timeout=5.0)
            if worker.is_alive():
                LOGGER.warning("Steering-Streaming-Thread lief nach dem Client-Abbruch weiter.")
            else:
                if isinstance(steering_report_sink, dict):
                    steering_report_sink.clear()
                    steering_report_sink.update(steering_report or self.last_steering_report)
                del generation_kwargs, inputs
                if self.device.type == "cuda":
                    torch.cuda.empty_cache()

        if generation_error:
            exc = generation_error[0]
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            if "out of memory" in str(exc).lower():
                raise RuntimeError(
                    "CUDA-OOM: Generierung kontrolliert abgebrochen; Prompt oder Completion-Budget reduzieren."
                ) from exc
            raise RuntimeError(f"Steering-Streaming fehlgeschlagen: {exc}") from exc
        if not emitted_text:
            raise RuntimeError(
                "Generierung lieferte nur internes Reasoning ohne finale Antwort; "
                "Thinking deaktivieren oder Completion-Budget erhoehen."
            )

    def _stream_generate_buffered(
        self,
        messages: list[dict],
        *,
        max_tokens: int,
        temperature: float,
        steering_payload: Optional[Dict[str, Any]] = None,
        chat_template_kwargs: Optional[Dict[str, Any]] = None,
        repetition_penalty: float = 1.15,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        seed: Optional[int] = None,
        steering_report_sink: Optional[Dict[str, Any]] = None,
        request_priority: str = REQUEST_PRIORITY_INTERACTIVE,
    ) -> Iterator[str]:
        try:
            result = self.generate(
                messages,
                max_tokens=max_tokens,
                temperature=temperature,
                steering_payload=steering_payload,
                chat_template_kwargs=chat_template_kwargs,
                repetition_penalty=repetition_penalty,
                top_p=top_p,
                top_k=top_k,
                seed=seed,
                request_priority=request_priority,
            )
            report = result.get("steering_runtime") if isinstance(result, dict) else None
            if isinstance(steering_report_sink, dict):
                steering_report_sink.clear()
                if isinstance(report, dict):
                    steering_report_sink.update(report)
        except BaseException as exc:  # pragma: no cover - Laufzeitpfad
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            if "out of memory" in str(exc).lower():
                raise RuntimeError(
                    "CUDA-OOM: Generierung kontrolliert abgebrochen; Prompt oder Completion-Budget reduzieren."
                ) from exc
            raise

        text = str(result.get("text") or "").strip()
        if not text:
            raise RuntimeError(
                "Generierung lieferte nur internes Reasoning ohne finale Antwort; "
                "Thinking deaktivieren oder Completion-Budget erhoehen."
            )
        for offset in range(0, len(text), 96):
            yield text[offset:offset + 96]

    def _generation_kwargs(
        self,
        inputs: Dict[str, torch.Tensor],
        max_tokens: int,
        temperature: float,
        repetition_penalty: float = 1.15,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        enable_thinking: Optional[bool] = None,
    ) -> Dict[str, Any]:
        do_sample = float(temperature or 0.0) > 0.01
        input_len = int(inputs["input_ids"].shape[1])
        requested_tokens = max(1, int(max_tokens or 1))
        available_tokens = max(1, int(getattr(self, "context_length", 8192)) - input_len)
        generation_tokens = min(requested_tokens, available_tokens)
        if generation_tokens < requested_tokens:
            LOGGER.warning(
                "Max Tokens von %d auf %d reduziert, weil Prompt %d/%d Kontexttokens belegt.",
                requested_tokens, generation_tokens, input_len, getattr(self, "context_length", 8192),
            )
        model_generation_config = getattr(self.model, "generation_config", None)
        eos_token_id = getattr(model_generation_config, "eos_token_id", None)
        if eos_token_id is None:
            eos_token_id = self.tokenizer.eos_token_id
        kwargs: Dict[str, Any] = {
            **inputs,
            "max_new_tokens": generation_tokens,
            "do_sample": do_sample,
            "pad_token_id": self.tokenizer.pad_token_id,
            # Gemma 4 requires its complete EOS list, notably <turn|>. Using
            # only tokenizer.eos_token_id makes generation continue into
            # simulated follow-up turns and exposes thought/tool fragments.
            "eos_token_id": eos_token_id,
            "use_cache": True,
            "repetition_penalty": max(1.0, float(repetition_penalty)),
        }
        if (
            getattr(getattr(self, "device", None), "type", "cpu") == "cuda"
            and is_qwen_name(self.model_name)
            and not bool(getattr(self, "quantize", False))
            and input_len + generation_tokens >= QWEN_FP16_CACHE_OFFLOAD_TOTAL_TOKENS
        ):
            kwargs["cache_implementation"] = "offloaded"
            LOGGER.info(
                "Qwen-Langkontext nutzt CPU-offloaded KV-Cache (%d Prompt + %d Completiontoken).",
                input_len,
                generation_tokens,
            )
        if do_sample:
            kwargs["temperature"] = max(0.05, float(temperature))
            if top_p is not None:
                kwargs["top_p"] = max(0.01, min(1.0, float(top_p)))
            if top_k is not None and int(top_k) > 0:
                kwargs["top_k"] = int(top_k)
        # Qwen's no-thinking chat template already closes an empty <think>
        # block in the prompt. Under strong steering the model occasionally
        # opened a second block anyway and consumed the entire completion in
        # hidden reasoning. Prevent only that reopening token; normal answer
        # tokens and the template-provided closed block remain untouched.
        if enable_thinking is False and is_qwen_name(self.model_name):
            with self._tokenizer_guarded():
                think_start_id = self.tokenizer.convert_tokens_to_ids("<think>")
            if isinstance(think_start_id, int) and think_start_id >= 0:
                kwargs["bad_words_ids"] = [[think_start_id]]
        return kwargs

    @contextmanager
    def _apply_activation_plan(self, steering_payload: Optional[Dict[str, Any]], prompt_length: int = 0) -> Iterable[list]:
        plan_started = time.perf_counter()
        normalized_payload = extract_steering_payload(steering_payload)
        steering = normalized_payload.get("steering", {}) if isinstance(normalized_payload, dict) else {}
        vectors = steering.get("vectors", []) if isinstance(steering.get("vectors", []), list) else []
        if steering.get("enabled") is False:
            vectors = []
        selected_mode = SteeringMode(steering.get("mode", "combined"))
        enabled = steering.get("enabled") is not False and selected_mode != SteeringMode.OFF
        vectors = vectors if enabled and selected_mode.activation else []
        if any(isinstance(item.get("vector"), dict) and item["vector"].get("type") == "token_sequence_steering" for item in vectors if isinstance(item, dict)):
            raise ValueError("Hard sequence steering is retired; use soft_sequence_steering")
        vectors = vectors if enabled and selected_mode.activation else []
        vector_names = [str(item.get("name") or "") for item in vectors if isinstance(item, dict)]
        static_payload = dict(normalized_payload)
        static_steering = dict(steering)
        static_steering["vectors"] = vectors
        static_payload["steering"] = static_steering
        processors = []
        sequence_specs = steering.get("sequences", []) if enabled and selected_mode.sequence else []
        if sequence_specs:
            eos = getattr(getattr(self.model, "generation_config", None), "eos_token_id", None)
            eos_ids = eos if isinstance(eos, list) else [eos]
            eos_ids = [token for token in [*eos_ids, self.tokenizer.eos_token_id] if isinstance(token, int)]
            processors = [SoftSequenceLogitsProcessor(sequence_specs, self.tokenizer, prompt_length, eos_ids,
                                                     get_steering_runtime_config()["sequence_max_bias"])]
        try:
            declared_layers = int(steering.get("model_layers", 0) or 0)
        except (TypeError, ValueError):
            declared_layers = 0
        try:
            plan = build_activation_plan(
                static_payload,
                self.resolver.resolve,
                actual_layer_count=len(self.layers),
            )
        except Exception as exc:
            self.last_steering_report = {
                "active": False,
                "prepared": False,
                "verified_active": False,
                "hook_count": 0,
                "hook_invocations": 0,
                "requested_layers": [],
                "applied_layers": [],
                "mode": "activation_addition",
                "model": self.model_name,
                "status": "error",
                "active_vectors": vector_names,
                "error": str(exc),
            }
            raise

        plan_build_ms = (time.perf_counter() - plan_started) * 1000.0
        requested_layers = sorted(int(layer) for layer in plan)
        handles = []
        stats: Dict[str, Any] = {
            "hook_invocations": 0,
            "steered_hidden_positions": 0,
            "hook_compute_ms": 0.0,
            "layer_invocations": {},
        }
        attach_started = time.perf_counter()
        try:
            for layer_idx, vector in plan.items():
                if layer_idx < 0 or layer_idx >= len(self.layers):
                    continue
                layer = self.layers[layer_idx]
                prompt_only = bool(getattr(vector, "_chappie_prompt_only", False))
                handles.append(layer.register_forward_pre_hook(
                    self._pre_hook_factory(
                        vector.to(self.device, dtype=self.dtype),
                        stats=stats,
                        layer_idx=int(layer_idx),
                        prompt_only=prompt_only,
                    )
                ))
            hook_attach_ms = (time.perf_counter() - attach_started) * 1000.0
            self.last_steering_report = {
                "active": False,
                "prepared": bool(handles or processors),
                "verified_active": False,
                "hook_count": len(handles),
                "hook_invocations": 0,
                "requested_layers": requested_layers,
                "applied_layers": sorted(set(
                    [int(layer) for layer in plan if 0 <= int(layer) < len(self.layers)]
                )),
                "mode": "activation_addition",
                "model": self.model_name,
                "status": "prepared" if handles or processors else "no_applicable_layers",
                "active_vectors": vector_names,
                "active_vector_count": len(vector_names),
                "sequence_prefix_tokens": 0,
                "sequence_processor_count": len(processors),
                "ablation_mode": selected_mode.value,
                "declared_model_layers": declared_layers,
                "actual_model_layers": len(self.layers),
                "layer_range_remapped": bool(declared_layers and declared_layers != len(self.layers)),
                "plan_build_ms": round(plan_build_ms, 3),
                "hook_attach_ms": round(hook_attach_ms, 3),
            }
            stats["report"] = self.last_steering_report
            yield processors
        finally:
            for handle in handles:
                handle.remove()
            handles.clear()
            hook_compute_ms = float(stats["hook_compute_ms"])
            sequence_report = processors[0].telemetry if processors else {"processor_count": 0, "biased_steps": 0}
            verified = int(stats["hook_invocations"]) > 0 or sequence_report["biased_steps"] > 0
            self.last_steering_report["sequence"] = dict(sequence_report)
            total_overhead_ms = (
                plan_build_ms
                + float(self.last_steering_report.get("hook_attach_ms", 0.0))
                + hook_compute_ms
            )
            self.last_steering_report.update({
                "active": verified,
                "verified_active": verified,
                "status": "verified" if verified else self.last_steering_report.get("status", "not_executed"),
                "hook_invocations": int(stats["hook_invocations"]),
                "steered_hidden_positions": int(stats["steered_hidden_positions"]),
                "layer_invocations": dict(stats["layer_invocations"]),
                "layer_measurements": dict(stats.get("layer_measurements", {})),
                "hook_compute_ms": round(max(0.001, hook_compute_ms), 3) if hook_compute_ms > 0 else 0.0,
                # Millisecond telemetry has three decimals. A verified run is
                # therefore represented by the smallest measurable bucket
                # instead of the misleading value 0.000 ms.
                "steering_overhead_ms": round(
                    max(0.001, total_overhead_ms) if verified else total_overhead_ms,
                    3,
                ),
            })
            if self.device.type == "cuda":
                torch.cuda.empty_cache()

    @staticmethod
    def _pre_hook_factory(
        vector: torch.Tensor,
        stats: Optional[Dict[str, Any]] = None,
        layer_idx: Optional[int] = None,
        prompt_only: bool = False,
    ) -> Callable[..., Any]:
        def _hook(_module: Any, inputs: Any) -> Any:
            started = time.perf_counter()
            hidden = inputs[0] if isinstance(inputs, tuple) and inputs else None
            if prompt_only and (
                not torch.is_tensor(hidden)
                or hidden.dim() != 3
                or hidden.size(1) <= 1
            ):
                return inputs
            updated = add_vector_to_inputs(inputs, vector)
            if stats is not None:
                stats["hook_invocations"] = int(stats.get("hook_invocations", 0)) + 1
                if torch.is_tensor(hidden) and hidden.dim() >= 2:
                    positions = int(hidden.shape[0]) * int(hidden.shape[1])
                    stats["steered_hidden_positions"] = int(stats.get("steered_hidden_positions", 0)) + positions
                layer_key = str(layer_idx) if layer_idx is not None else "unknown"
                measurements = stats.setdefault("layer_measurements", {})
                if layer_key not in measurements and torch.is_tensor(hidden):
                    # Sample the first actual intervention, not an anchor pass.
                    # Reductions stay on device; only three scalars reach CPU.
                    sample = hidden.detach().float()
                    delta = updated[0].detach().float() - sample
                    hidden_rms = float(sample.square().mean().sqrt().item())
                    intervention_rms = float(delta.square().mean().sqrt().item())
                    measurements[layer_key] = {
                        "hidden_state_rms": hidden_rms,
                        "intervention_rms": intervention_rms,
                        "intervention_rms_ratio": intervention_rms / max(hidden_rms, 1e-12),
                        "intervention_norm": float(delta.norm().item()),
                        "sample": "first_hook_invocation",
                    }
                layer_counts = stats.setdefault("layer_invocations", {})
                layer_counts[layer_key] = int(layer_counts.get(layer_key, 0)) + 1
                stats["hook_compute_ms"] = float(stats.get("hook_compute_ms", 0.0)) + (
                    time.perf_counter() - started
                ) * 1000.0
                # Make the report truthful even while a streamed generation is
                # still running. The final context cleanup adds exact timings.
                report = stats.get("report")
                if isinstance(report, dict):
                    report["active"] = True
                    report["verified_active"] = True
                    report["status"] = "verified"
                    report["hook_invocations"] = int(stats["hook_invocations"])
            return updated

        return _hook
