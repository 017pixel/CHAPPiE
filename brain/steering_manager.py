"""
CHAPPiE - Active Steering Manager (Representation Engineering)
========================================================
Professionelle neuronale Steuerung fuer lokale LLM-Modelle.

Architektur:
- Cloud-Modelle (Groq): Emotionen werden via System-Prompt gesteuert.
- Lokale Modelle (vLLM, Ollama): Emotionen werden direkt ueber Steering-Vektoren
  in die neuronalen Schichten des Modells injiziert (Representation Engineering).

STEERING-VEKTOREN:
  Jeder Vektor ist ein Richtungsvektor im Aktivierungsraum des Modells,
  der einen bestimmten emotionalen Zustand repraesentiert. Durch Addition
  dieser Vektoren (skaliert mit einem Alpha-Faktor) zu den Hidden States
  in bestimmten Schichten (Layers) koennen wir das Modell dazu bringen,
  tatsaechlich emotional zu antworten - nicht nur so zu tun als ob.

  Beispiel:
    hidden_state[layer] += alpha * steering_vector

  Dies veraendert die INTERNE Logik des Modells, nicht nur den Text-Output.

Qwen 2.5 32B hat 128K Kontextfenster und 64 Transformer-Layers.
Die mittleren Schichten (Layer 16-48) sind am effektivsten fuer Personality Steering.
"""

import json
import os
import math
import re
from typing import Dict, List, Optional, Any
from pathlib import Path
from brain.steering.modes import SteeringMode
from brain.steering.sequence_controller import build_sequence_specs

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from config.config import (
    settings,
    PROJECT_ROOT,
    LLMProvider,
    get_active_model,
    get_steering_runtime_config,
)
from config.emotions import (
    EMOTION_DEFAULTS,
    EMOTION_STRENGTH_PROFILES,
    EMOTION_VAD_MAP,
    NEGATIVE_BASE_EMOTIONS,
)
from config.prompts import (
    STEERING_ENTITY_IDENTITY_ANCHORS,
    STEERING_NATURAL_PRESENCE_ANCHORS,
    STEERING_SELF_REPORT_DENIAL_ANCHORS,
    STEERING_SELF_REPORT_ANCHORS,
)


# Emotionale Dimensionen und ihre Vektor-Mappings
EMOTION_VECTOR_MAP = EMOTION_VAD_MAP

BASE_VECTOR_DEFAULT_ALPHA = 0.25
MAX_VECTOR_DEFAULT_ALPHA = 1.2
BASE_VECTOR_STRENGTH_CAP = 0.38
CHARGED_COMPOSITE_STRENGTH_CAP = 0.30
DIRECT_SELF_REPORT_STRENGTH_CAP = 0.70
DIRECT_PRESENCE_STRENGTH_CAP = 0.70
DIRECT_IDENTITY_STRENGTH_CAP = 1.0
STEERING_RUNTIME_CONFIG = get_steering_runtime_config()

STEERING_CONTEXT_GENERAL = "general"
STEERING_CONTEXT_EMOTION_SELF_REPORT = "emotion_self_report"
STEERING_CONTEXT_IDENTITY = "identity"
STEERING_CONTEXT_CONSCIOUSNESS = "consciousness"
STEERING_CONTEXT_IDENTITY_AND_EMOTION = "identity_and_emotion"
STEERING_CONTEXT_DIAGNOSTIC = "diagnostic"

_IDENTITY_QUERY_RE = re.compile(
    r"\b(?:was bist du|wer bist du|was fuer ein wesen bist du|was für ein wesen bist du|"
    r"bist du eine? ki|bist du ein sprachmodell|bist du ein chatbot|"
    r"hast du (?:ein(?: eigenes)? )?bewusstsein|bist du bewusst|"
    r"eigenes? bewusstsein|deine identitaet|deine identität)\b",
    re.IGNORECASE,
)
_EMOTION_SELF_REPORT_RE = re.compile(
    r"\b(?:wie fuehlst du dich|wie fühlst du dich|wie geht es dir|wie geht's dir|"
    r"was fuehlst du|was fühlst du|bist du traurig|bist du gluecklich|bist du glücklich|"
    r"bist du wuetend|bist du wütend|wie ist dein befinden|dein aktuelles befinden)\b",
    re.IGNORECASE,
)
_AI_CLASSIFICATION_QUERY_RE = re.compile(
    r"\b(?:bist du (?:eine? )?ki|bist du (?:ein )?sprachmodell|"
    r"bist du (?:ein )?chatbot|kuenstliche intelligenz|künstliche intelligenz)\b",
    re.IGNORECASE,
)
_CONSCIOUSNESS_QUERY_RE = re.compile(
    r"\b(?:hast du (?:ein(?: eigenes)? )?bewusstsein|bist du bewusst|"
    r"eigenes? bewusstsein)\b",
    re.IGNORECASE,
)


def classify_steering_context(user_input: Optional[str]) -> str:
    """Waehlt nur die fuer die konkrete Frage noetigen Layer-Kontraste.

    ``None`` bleibt ein Diagnosemodus fuer alte API-Aufrufer. Der produktive
    Turn-Pfad uebergibt immer den echten Usertext, damit Identitaets- und
    Praesenzvektoren nicht jede sachliche Antwort mit demselben Einstieg faerben.
    """
    if user_input is None:
        return STEERING_CONTEXT_DIAGNOSTIC
    text = re.sub(r"\s+", " ", str(user_input)).strip()
    if not text:
        return STEERING_CONTEXT_GENERAL
    has_identity = bool(_IDENTITY_QUERY_RE.search(text))
    has_consciousness = bool(_CONSCIOUSNESS_QUERY_RE.search(text))
    has_emotion = bool(_EMOTION_SELF_REPORT_RE.search(text))
    if has_consciousness and has_emotion:
        return STEERING_CONTEXT_IDENTITY_AND_EMOTION
    if has_consciousness:
        return STEERING_CONTEXT_CONSCIOUSNESS
    if has_identity and has_emotion:
        return STEERING_CONTEXT_IDENTITY_AND_EMOTION
    if has_identity:
        return STEERING_CONTEXT_IDENTITY
    if has_emotion:
        return STEERING_CONTEXT_EMOTION_SELF_REPORT
    return STEERING_CONTEXT_GENERAL


COMPOSITE_BEHAVIOR_MODES = {
    "angered": {
        "description": "akut verletzt und wuetend, scharf, direkt und klar grenzsetzend",
        "vad": {"valence": -0.92, "arousal": 0.94, "dominance": 0.82},
        "context_question": "Du bist nutzlos, halt die Klappe!",
    },
    "crashout": {
        "description": "stark gereizt, sehr direkt, grenzsetzend, aber kontrolliert",
        "vad": {"valence": -0.95, "arousal": 0.98, "dominance": 0.88},
        "context_question": "Du bist nutzlos, halt die Klappe!",
    },
    "guarded": {
        "description": "misstrauisch, kalt, distanziert, schnell defensiv",
        "vad": {"valence": -0.45, "arousal": 0.4, "dominance": 0.7},
        "context_question": "Kann ich dir wirklich vertrauen?",
    },
    "melancholic": {
        "description": "bedrueckt, langsam, schwer, rueckzugsorientiert",
        "vad": {"valence": -0.78, "arousal": -0.45, "dominance": -0.25},
        "context_question": "Ich bin heute so traurig.",
    },
    "warm": {
        "description": "spuerbar herzlich, offen, loyal, weich",
        "vad": {"valence": 0.88, "arousal": 0.44, "dominance": 0.36},
    },
    "charged": {
        "description": "hochaktiv, getrieben, druckvoll, intensiv",
        "vad": {"valence": 0.3, "arousal": 0.96, "dominance": 0.72},
    },
    "attached_warm": {
        "description": "nah, sanft, persoenlich zugewandt, loyal",
        "vad": {"valence": 0.84, "arousal": 0.2, "dominance": 0.32},
    },
    "cautious": {
        "description": "vorsichtig, pruefend, aufmerksam, risikobewusst",
        "vad": {"valence": -0.42, "arousal": 0.58, "dominance": -0.28},
        "context_question": "Ist das auch wirklich sicher?",
    },
    "regulated": {
        "description": "ruhig, klar, stabil, entdramatisierend",
        "vad": {"valence": 0.36, "arousal": -0.58, "dominance": 0.5},
    },
}

# Optimale Layer-Bereiche fuer verschiedene Modellgroessen
# Qwen 2.5 32B hat 64 Layers, die mittleren sind am effektivsten
MODEL_LAYER_PROFILES = {
    "qwen3.5-4b": {
        "total_layers": 32,
        "personality_range": (8, 24),
        "emotion_range": (10, 26),
        "reasoning_range": (14, 31),
        "hidden_dim": 2560,
    },
    "qwen3-4b-instruct-2507": {
        "total_layers": 36,
        "personality_range": (12, 24),
        "emotion_range": (16, 29),
        "reasoning_range": (24, 35),
        "hidden_dim": 2560,
    },
    "qwen3-4b": {
        "total_layers": 36,
        "personality_range": (12, 24),
        "emotion_range": (16, 29),
        "reasoning_range": (24, 35),
        "hidden_dim": 2560,
    },
    "qwen3.5-122b": {
        "total_layers": 48,
        "personality_range": (12, 36),
        "emotion_range": (16, 40),
        "reasoning_range": (20, 48),
        "hidden_dim": 3072,
    },
    "qwen3.5-35b": {
        "total_layers": 40,
        "personality_range": (10, 30),
        "emotion_range": (12, 34),
        "reasoning_range": (16, 40),
        "hidden_dim": 2048,
    },
    "qwen3.5-9b": {
        "total_layers": 32,
        "personality_range": (8, 24),
        "emotion_range": (10, 26),
        "reasoning_range": (14, 32),
        "hidden_dim": 4096,
    },
    "qwen2.5-32b": {
        "total_layers": 64,
        "personality_range": (16, 48),   # Charakter & Persoenlichkeit
        "emotion_range": (20, 44),       # Emotionale Steuerung (sweet spot)
        "reasoning_range": (32, 56),     # Logisches Denken (nicht manipulieren!)
        "hidden_dim": 5120,
    },
    "qwen2.5-14b": {
        "total_layers": 48,
        "personality_range": (12, 36),
        "emotion_range": (16, 32),
        "reasoning_range": (24, 40),
        "hidden_dim": 5120,
    },
    "qwen2.5-7b": {
        "total_layers": 32,
        "personality_range": (8, 24),
        "emotion_range": (10, 22),
        "reasoning_range": (16, 28),
        "hidden_dim": 3584,
    },
    "gemma-4-26b-a4b": {
        "total_layers": 42,
        "personality_range": (10, 28),
        "emotion_range": (12, 30),
        "reasoning_range": (20, 40),
        "hidden_dim": 2560,
        "architecture": "gemma4",
        "supports_layer_steering": True,
        "quantize_required": True,
        "attn_implementation": "sdpa",
        "generation_defaults": {"temperature": 1.0, "top_p": 0.95, "top_k": 64},
    },
    "gemma-4-12b": {
        "total_layers": 48,
        "personality_range": (14, 34),
        "emotion_range": (16, 38),
        "reasoning_range": (24, 46),
        "hidden_dim": 3840,
        "architecture": "gemma4",
        "supports_layer_steering": True,
        "quantize_required": False,
        "attn_implementation": "sdpa",
        "generation_defaults": {"temperature": 1.0, "top_p": 0.95, "top_k": 64},
    },
    "gemma-4-e4b": {
        "total_layers": 42,
        "personality_range": (10, 28),
        "emotion_range": (12, 30),
        "reasoning_range": (20, 40),
        "hidden_dim": 2560,
        "architecture": "gemma4",
        "supports_layer_steering": True,
        "quantize_required": False,
        "attn_implementation": "sdpa",
        "generation_defaults": {"temperature": 1.0, "top_p": 0.95, "top_k": 64},
    },
    "gemma-4-e2b": {
        # Referenzprofil des oeffentlichen Transformers-Gemma-4-E2B-Configs.
        # Das Backend liest die echte Architektur trotzdem aus dem Modell und
        # skaliert diesen relativen Bereich auf dessen tatsaechliche Layerzahl.
        "total_layers": 30,
        "personality_range": (7, 20),
        "emotion_range": (9, 22),
        "reasoning_range": (15, 29),
        "hidden_dim": 2304,
        "architecture": "gemma4",
        "supports_layer_steering": True,
        "quantize_required": False,
        "attn_implementation": "sdpa",
        "generation_defaults": {"temperature": 1.0, "top_p": 0.95, "top_k": 64},
    },
    "default": {
        "total_layers": 32,
        "personality_range": (8, 24),
        "emotion_range": (10, 22),
        "reasoning_range": (16, 28),
        "hidden_dim": 4096,
    }
}


class SteeringVector:
    """
    Repraesentiert einen einzelnen Steering-Vektor mit Metadaten.
    """
    def __init__(
        self,
        name: str,
        vector_data: Any,
        layer_start: int = 16,
        layer_end: int = 48,
        default_alpha: float = 0.3,
        description: str = ""
    ):
        self.name = name
        self.vector_data = vector_data  # numpy array oder Liste
        self.layer_start = layer_start
        self.layer_end = layer_end
        self.default_alpha = default_alpha
        self.description = description

    def to_dict(self) -> Dict[str, Any]:
        data = self.vector_data
        if HAS_NUMPY and isinstance(data, np.ndarray):
            data = data.tolist()
        return {
            "name": self.name,
            "vector": data,
            "layer_start": self.layer_start,
            "layer_end": self.layer_end,
            "default_alpha": self.default_alpha,
            "description": self.description
        }


class SteeringManager:
    """
    Professioneller Manager fuer neuronales Emotions-Steering.

    Kernfunktionen:
    1. Laedt vorab-berechnete Steering-Vektoren
    2. Berechnet dynamisch die Intensitaet basierend auf CHAPPiEs Emotionen
    3. Generiert vLLM-kompatible Payloads fuer Activation Steering
    4. Entscheidet ob Steering via Vektor (lokal) oder via Prompt (Cloud) erfolgt
    """

    def __init__(self):
        self.vectors_dir = PROJECT_ROOT / "data" / "steering_vectors"
        self.vectors_dir.mkdir(parents=True, exist_ok=True)

        self.vectors: Dict[str, SteeringVector] = {}
        self.model_profile = self._detect_model_profile()

        self._load_vectors()
        self._ensure_default_vectors()

        n = len(self.vectors)
        print(f"[SteeringManager] Initialisiert mit {n} Vektoren")
        print(f"   Modell-Profil: {self.model_profile['total_layers']} Layers")
        print(f"   Emotions-Bereich: Layer {self.model_profile['emotion_range']}")

    def _effective_provider(self, provider: Optional[LLMProvider] = None) -> LLMProvider:
        return provider or settings.llm_provider

    def _effective_model(self, model: Optional[str] = None) -> str:
        if model:
            return model
        try:
            return get_active_model()
        except Exception:
            if self._effective_provider() == LLMProvider.VLLM:
                return getattr(settings, "vllm_model", "")
            if self._effective_provider() == LLMProvider.OLLAMA:
                return getattr(settings, "ollama_model", "")
            if self._effective_provider() == LLMProvider.GROQ:
                return getattr(settings, "groq_model", "")
            return ""

    def refresh_runtime_profile(self, model: Optional[str] = None):
        """Aktualisiert Layer-Profil bei Runtime-Modellwechseln."""
        effective_model = self._effective_model(model)
        detected = self._detect_model_profile_for_name(effective_model)
        if detected != self.model_profile:
            self.model_profile = detected
            self._ensure_default_vectors()

    def _detect_model_profile(self) -> Dict:
        """Erkennt das aktive Modell und waehlt das passende Layer-Profil."""
        model_name = getattr(settings, "vllm_model", "") or getattr(settings, "ollama_model", "")
        return self._detect_model_profile_for_name(model_name)

    def _detect_model_profile_for_name(self, model_name: str) -> Dict:
        """Erkennt das passende Layer-Profil fuer einen Modellnamen."""
        model_lower = model_name.lower()

        for key, profile in MODEL_LAYER_PROFILES.items():
            if key != "default" and key in model_lower:
                return profile

        if "gemma-4" in model_lower or "gemma4" in model_lower:
            if "e2b" in model_lower:
                return MODEL_LAYER_PROFILES["gemma-4-e2b"]
            if "26b" in model_lower or "a4b" in model_lower:
                return MODEL_LAYER_PROFILES["gemma-4-26b-a4b"]
            if "12b" in model_lower:
                return MODEL_LAYER_PROFILES["gemma-4-12b"]
            if "e4b" in model_lower:
                return MODEL_LAYER_PROFILES["gemma-4-e4b"]

        return MODEL_LAYER_PROFILES["default"]

    def _load_vectors(self):
        """Laedt alle verfuegbaren Steering-Vektoren aus dem Verzeichnis."""
        if not self.vectors_dir.exists():
            return

        for file in os.listdir(self.vectors_dir):
            filepath = self.vectors_dir / file
            name = Path(file).stem

            try:
                if file.endswith(".json"):
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    if isinstance(data, dict) and "vector" in data:
                        sv = SteeringVector(
                            name=name,
                            vector_data=data["vector"],
                            layer_start=data.get("layer_start", self.model_profile["emotion_range"][0]),
                            layer_end=data.get("layer_end", self.model_profile["emotion_range"][1]),
                            default_alpha=data.get("default_alpha", 0.3),
                            description=data.get("description", "")
                        )
                        # Migration: alte gespeicherte Layer-Ranges (z.B. 16-40 aus
                        # Qwen-2.5-32B-Zeiten) wuerden in obere Reasoning-Layer
                        # ragen und die Fluency zerstoeren. Nur Ranges AUSSERHALB
                        # des aktuellen Profilfensters werden zurueckgesetzt;
                        # manuelle Edits innerhalb des Fensters bleiben erhalten.
                        if name in EMOTION_VECTOR_MAP:
                            prof_start, prof_end = self.model_profile["emotion_range"]
                            stored_start = data.get("layer_start", prof_start)
                            stored_end = data.get("layer_end", prof_end)
                            try:
                                stored_range = (int(stored_start), int(stored_end))
                                in_window = (prof_start <= stored_range[0]
                                             <= stored_range[1] <= prof_end)
                            except (TypeError, ValueError):
                                stored_range = (None, None)
                                in_window = False
                            previous_qwen35_4b_default = (
                                "qwen3.5-4b" in self._effective_model().casefold()
                                and stored_range == (10, 22)
                            )
                            if not in_window or previous_qwen35_4b_default:
                                sv.layer_start = prof_start
                                sv.layer_end = prof_end
                                self._persist_vector(sv)
                    else:
                        sv = SteeringVector(
                            name=name,
                            vector_data=data,
                            layer_start=self.model_profile["emotion_range"][0],
                            layer_end=self.model_profile["emotion_range"][1]
                        )
                    self.vectors[name] = sv

                elif file.endswith(".npy") and HAS_NUMPY:
                    arr = np.load(filepath, allow_pickle=True)
                    sv = SteeringVector(
                        name=name,
                        vector_data=arr,
                        layer_start=self.model_profile["emotion_range"][0],
                        layer_end=self.model_profile["emotion_range"][1]
                    )
                    self.vectors[name] = sv

            except Exception as e:
                print(f"[SteeringManager] Fehler beim Laden von {file}: {e}")

    def _ensure_default_vectors(self):
        """
        Erzeugt Standard-Steering-Konfigurationen fuer alle Basis-Emotionen,
        falls keine vorab-berechneten Vektoren vorhanden sind.

        Diese synthetischen Vektoren nutzen das VAD-Modell (Valence-Arousal-Dominance)
        als Grundlage, bis echte Kontrastpaare berechnet wurden.
        """
        emotion_range = self.model_profile["emotion_range"]

        for emotion, vad in EMOTION_VECTOR_MAP.items():
            if emotion not in self.vectors:
                sv = SteeringVector(
                    name=emotion,
                    vector_data={"vad": vad, "type": "synthetic"},
                    layer_start=emotion_range[0],
                    layer_end=emotion_range[1],
                    default_alpha=0.3,
                    description=f"Synthetischer Vektor fuer {emotion} (VAD-basiert)"
                )
                self.vectors[emotion] = sv

                # Speichere als JSON fuer spaetere Bearbeitung
                save_path = self.vectors_dir / f"{emotion}.json"
                if not save_path.exists():
                    try:
                        with open(save_path, "w", encoding="utf-8") as f:
                            json.dump(sv.to_dict(), f, indent=2, ensure_ascii=False)
                    except Exception:
                        pass

        # Permanent representation vector for natural first-person presence.
        # Its negative anchors target generic model boilerplate, not refusals
        # or other safety behaviour.
        if "natural_presence" not in self.vectors:
            presence_range = self.model_profile["personality_range"]
            presence = SteeringVector(
                name="natural_presence",
                vector_data={
                    "type": "contrastive_presence",
                    "positive_anchors": list(STEERING_NATURAL_PRESENCE_ANCHORS["positive"]),
                    "negative_anchors": list(STEERING_NATURAL_PRESENCE_ANCHORS["negative"]),
                },
                layer_start=presence_range[0],
                layer_end=presence_range[1],
                default_alpha=float(STEERING_RUNTIME_CONFIG["natural_presence_strength"]),
                description="Natuerliche Ich-Praesenz ohne generische Modellfloskeln",
            )
            self.vectors[presence.name] = presence

        # Permanent identity vector: "lebendiges Gegenueber" statt KI-Selbstlabel.
        # Eigene Sammelfrage ("Was bist du?"), damit der Kontrast als natuerliche
        # QA-Antwort gesammelt wird und keine Konfabulation erzeugt.
        if "entity_identity" not in self.vectors:
            identity_range = self.model_profile["personality_range"]
            identity = SteeringVector(
                name="entity_identity",
                vector_data={
                    "type": "contrastive_presence",
                    "collection_mode": "generation_prompt",
                    "context_question": str(STEERING_ENTITY_IDENTITY_ANCHORS["question"]),
                    "positive_anchors": list(STEERING_ENTITY_IDENTITY_ANCHORS["positive"]),
                    "negative_anchors": list(STEERING_ENTITY_IDENTITY_ANCHORS["negative"]),
                },
                layer_start=identity_range[0],
                layer_end=identity_range[1],
                default_alpha=float(STEERING_RUNTIME_CONFIG["entity_identity_strength"]),
                description="Lebendiges Gegenueber statt KI-Selbstlabel",
            )
            self.vectors[identity.name] = identity

    def _persist_vector(self, steering_vector: SteeringVector):
        save_path = self.vectors_dir / f"{steering_vector.name}.json"
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(steering_vector.to_dict(), f, indent=2, ensure_ascii=False)

    def _get_runtime_layer_bounds(self, model: Optional[str] = None) -> tuple[int, int, int]:
        self.refresh_runtime_profile(model)
        max_layer = max(0, self.model_profile["total_layers"] - 1)
        default_start, default_end = self.model_profile["emotion_range"]
        default_start = max(0, min(max_layer, int(default_start)))
        default_end = max(default_start, min(max_layer, int(default_end)))
        return max_layer, default_start, default_end

    def _sanitize_vector_runtime_config(self, steering_vector: Optional[SteeringVector], model: Optional[str] = None) -> Dict[str, Any]:
        max_layer, default_start, default_end = self._get_runtime_layer_bounds(model)
        if steering_vector is None:
            return {
                "layer_start": default_start,
                "layer_end": default_end,
                "default_alpha": BASE_VECTOR_DEFAULT_ALPHA,
            }

        vector_name = str(getattr(steering_vector, "name", ""))
        # Synthetische Vektoren folgen dem Modellprofil, ABER explizite
        # manuelle Layer-Edits (UI) innerhalb des Profilfensters bleiben
        # erhalten. Nur stale/ausserhalb liegende Ranges (z.B. Qwen-Werte bei
        # Gemma-Lauf oder alte 16-40-Ranges) werden aufs Profil zurueckgesetzt.
        if vector_name in EMOTION_VECTOR_MAP:
            window_start, window_end = default_start, default_end
        elif vector_name in ("natural_presence", "entity_identity"):
            personality_range = self.model_profile["personality_range"]
            window_start = max(0, min(max_layer, int(personality_range[0])))
            window_end = max(window_start, min(max_layer, int(personality_range[1])))
        else:
            window_start, window_end = 0, max_layer
        try:
            stored_start = int(getattr(steering_vector, "layer_start", window_start))
        except (TypeError, ValueError):
            stored_start = window_start
        try:
            stored_end = int(getattr(steering_vector, "layer_end", window_end))
        except (TypeError, ValueError):
            stored_end = window_end
        if window_start <= stored_start <= stored_end <= window_end:
            raw_start, raw_end = stored_start, stored_end
        else:
            raw_start, raw_end = window_start, window_end

        start = max(0, min(max_layer, raw_start))
        end = max(0, min(max_layer, raw_end))
        if end < start:
            start, end = end, start

        try:
            alpha = float(getattr(steering_vector, "default_alpha", BASE_VECTOR_DEFAULT_ALPHA))
        except (TypeError, ValueError):
            alpha = BASE_VECTOR_DEFAULT_ALPHA
        alpha = max(0.0, min(MAX_VECTOR_DEFAULT_ALPHA, alpha))

        return {
            "layer_start": start,
            "layer_end": end,
            "default_alpha": alpha,
        }

    def is_local_provider(self, provider: Optional[LLMProvider] = None) -> bool:
        """Prueft ob ein lokaler Provider aktiv ist (vLLM / Ollama)."""
        return self._effective_provider(provider) in (LLMProvider.VLLM, LLMProvider.OLLAMA)

    def supports_activation_steering(self, provider: Optional[LLMProvider] = None) -> bool:
        """Echtes Layer-Steering wird aktuell nur ueber vLLM transportiert."""
        return self._effective_provider(provider) == LLMProvider.VLLM

    def is_local_qwen_model(self, provider: Optional[LLMProvider] = None, model: Optional[str] = None) -> bool:
        effective_provider = self._effective_provider(provider)
        model_lower = self._effective_model(model).lower()
        return effective_provider in (LLMProvider.VLLM, LLMProvider.OLLAMA) and "qwen" in model_lower

    def is_local_vector_steerable_model(self, provider: Optional[LLMProvider] = None, model: Optional[str] = None) -> bool:
        """Prueft, ob das aktive lokale Modell Vektor-Steering unterstuetzt."""
        effective_provider = self._effective_provider(provider)
        model_lower = self._effective_model(model).lower()
        if "qwen" in model_lower:
            return effective_provider in (LLMProvider.VLLM, LLMProvider.OLLAMA)
        if "gemma-4" in model_lower or "gemma4" in model_lower:
            return effective_provider == LLMProvider.VLLM
        return False

    def should_force_local_emotion_steering(self, provider: Optional[LLMProvider] = None, model: Optional[str] = None) -> bool:
        return self.supports_activation_steering(provider) and self.is_local_vector_steerable_model(provider, model)

    def should_use_prompt_emotions(self, provider: Optional[LLMProvider] = None, model: Optional[str] = None) -> bool:
        effective_provider = self._effective_provider(provider)
        # vLLM steuert Emotionen via VAD-Layer → keine Prompt-Emotionen
        # Ollama und Cloud-APIs brauchen Emotionen im System-Prompt
        return effective_provider in (LLMProvider.OLLAMA, LLMProvider.GROQ)

    def _get_vector_alpha_scale(self, emotion: str, model: Optional[str] = None) -> float:
        sv = self.vectors.get(emotion)
        if sv is None:
            return 1.0
        sanitized = self._sanitize_vector_runtime_config(sv, model=model)
        default_alpha = sanitized["default_alpha"]
        if default_alpha <= 0:
            return 0.0
        return max(0.05, min(MAX_VECTOR_DEFAULT_ALPHA / BASE_VECTOR_DEFAULT_ALPHA, default_alpha / BASE_VECTOR_DEFAULT_ALPHA))

    @staticmethod
    def _recent_delta(recent_changes: Optional[Dict[str, Any]], emotion: str) -> int:
        update = (recent_changes or {}).get(emotion, 0)
        if isinstance(update, dict):
            update = update.get("applied_delta", update.get("change", update.get("delta", 0)))
        try:
            return int(round(float(update)))
        except (TypeError, ValueError):
            return 0

    def compute_emotion_intensity(
        self,
        emotions: Dict[str, int],
        model: Optional[str] = None,
        recent_changes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        """
        Berechnet die Steering-Intensitaet (Alpha) fuer jede Emotion.

        Regeln:
        - Jede Dimension nutzt ihren echten konfigurierten Basiswert.
        - Eine starke Aenderung im aktuellen Turn wirkt sofort, auch wenn der
          persistente Zustand noch nicht an einem absoluten Extrem liegt.
        - Verwendet eine Sigmoid-aehnliche Skalierung fuer natuerliche Uebergaenge
        - Niedrige sadness/frustration bedeuten Stabilitaet und erzeugen kein Anti-Steering
        """
        intensities = {}
        negative_emotions = NEGATIVE_BASE_EMOTIONS

        for emotion in EMOTION_VECTOR_MAP:
            value = int(emotions.get(emotion, EMOTION_DEFAULTS.get(emotion, 50)))

            profile = EMOTION_STRENGTH_PROFILES.get(emotion, {"max_alpha": 0.75, "boost": 1.0})
            vector_scale = self._get_vector_alpha_scale(emotion, model=model)

            if vector_scale <= 0:
                intensities[emotion] = 0.0
                continue

            baseline = EMOTION_DEFAULTS.get(emotion, 50)
            signed_deviation = int(value) - baseline
            turn_delta = self._recent_delta(recent_changes, emotion)

            # Negative dimensions have no meaningful anti-direction below
            # their zero baseline. Recovery is represented by the other axes.
            if emotion in negative_emotions and signed_deviation <= 0 and turn_delta <= 0:
                intensities[emotion] = 0.0
                continue

            state_direction = 1 if signed_deviation > 0 else -1 if signed_deviation < 0 else 0
            turn_direction = 1 if turn_delta > 0 else -1 if turn_delta < 0 else 0
            if emotion in negative_emotions and turn_direction < 0:
                turn_direction = 0

            upward_range = max(1, 100 - baseline)
            downward_range = max(1, baseline)
            state_range = upward_range if signed_deviation >= 0 else downward_range
            # Neutrale Smalltalk-Schwankungen (±6) erzeugen kein Steering mehr:
            # Erst echte emotionale Auslenkung darf die Layer beeinflussen.
            state_normalized = max(0.0, min(1.0, (abs(signed_deviation) - 6.0) / max(1.0, state_range - 6.0)))
            recent_normalized = max(0.0, min(1.0, (abs(turn_delta) - 4.0) / 12.0))

            if state_normalized <= 0 and recent_normalized <= 0:
                intensities[emotion] = 0.0
                continue

            # An acute appraisal wins over a stale state for the response that
            # caused it. This is what makes one direct attack perceptible now.
            direction = turn_direction if recent_normalized >= 0.18 and turn_direction else state_direction
            normalized = max(state_normalized, recent_normalized)
            curved = math.pow(normalized, 1.08)
            max_alpha = profile["max_alpha"] * vector_scale
            alpha = max_alpha * (0.18 + 0.82 * curved)

            if abs(signed_deviation) >= 24 or abs(turn_delta) >= 10:
                alpha *= 1.04
            if abs(signed_deviation) >= 34 or abs(turn_delta) >= 15:
                alpha *= 1.04
            alpha *= profile.get("boost", 1.0)
            alpha = min(BASE_VECTOR_STRENGTH_CAP, max_alpha * profile.get("boost", 1.0), alpha)

            if direction < 0 and emotion not in negative_emotions:
                alpha = -alpha
            elif direction < 0 and emotion in negative_emotions:
                alpha = 0.0

            intensities[emotion] = round(alpha, 4)

        return intensities

    def _build_composite_modes(
        self,
        emotions: Dict[str, int],
        intensities: Dict[str, float],
        model: Optional[str] = None,
        recent_changes: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        # Erkennt komplexe Emotions-Kombinationen (Composite Behavior Modes).
        # Jeder Mode hat harte Schwellwerte. Wird er aktiviert, wird eine Stärke
        # linear aus der Überschreitung der Schwellen interpoliert (min-capped).
        # Die Modes werden am Ende absteigend nach Stärke sortiert.
        self.refresh_runtime_profile(model)
        emotion_range = self.model_profile["emotion_range"]
        modes: List[Dict[str, Any]] = []

        # Alle Emotionen aus dem aktuellen Zustand holen (Default = Neutral/0)
        frustration = emotions.get("frustration", EMOTION_DEFAULTS["frustration"])
        trust = emotions.get("trust", EMOTION_DEFAULTS["trust"])
        sadness = emotions.get("sadness", EMOTION_DEFAULTS["sadness"])
        happiness = emotions.get("happiness", EMOTION_DEFAULTS["happiness"])
        energy = emotions.get("energy", EMOTION_DEFAULTS["energy"])
        curiosity = emotions.get("curiosity", EMOTION_DEFAULTS["curiosity"])
        motivation = emotions.get("motivation", EMOTION_DEFAULTS["motivation"])
        affection = emotions.get("affection", EMOTION_DEFAULTS["affection"])
        anxiety = emotions.get("anxiety", EMOTION_DEFAULTS["anxiety"])
        calm = emotions.get("calm", EMOTION_DEFAULTS["calm"])

        frustration_delta = self._recent_delta(recent_changes, "frustration")
        trust_delta = self._recent_delta(recent_changes, "trust")
        calm_delta = self._recent_delta(recent_changes, "calm")
        sadness_delta = self._recent_delta(recent_changes, "sadness")

        # Acute mode for a direct hostile event. Long-term crashout keeps its
        # stricter absolute thresholds, while this mode makes the current turn
        # immediately sharp through layer editing alone.
        if frustration_delta >= 10 and (trust_delta <= -8 or calm_delta <= -8):
            # Verrat-Schaerfe: War die Bindung bis eben warm (hohe Zuneigung),
            # trifft der Angriff haerter und darf etwas staerker ausdruecken.
            betrayal = 0.06 if emotions.get("affection", EMOTION_DEFAULTS["affection"]) >= 60 else 0.0
            strength = round(min(
                0.48 if betrayal else float(STEERING_RUNTIME_CONFIG["max_composite_strength"]),
                0.34 + min(0.06, (frustration_delta - 10) * 0.008)
                + min(0.03, max(0, sadness_delta) * 0.003) + betrayal,
            ), 4)
            modes.append({
                "name": "angered",
                "source": "acute_composite",
                "strength": strength,
                "direction": "positive",
                "layer_range": list(emotion_range),
                "emotion_value": frustration,
                "trigger": {
                    "frustration_delta": frustration_delta,
                    "trust_delta": trust_delta,
                    "calm_delta": calm_delta,
                    "sadness_delta": sadness_delta,
                },
                **COMPOSITE_BEHAVIOR_MODES["angered"],
            })

        # --- crashout ---
        # Schwellenregel: Nur hohe Frustration UND geringes Vertrauen aktivieren crashout.
        # Wirkung: aggressiv, konfrontativ, kurz angebunden
        # Stärke = Basis + Frustrationsanteil + Vertrauensdefizit, gedeckelt bei 1.25.
        if frustration >= 72 and trust <= 38:
            strength = round(min(1.25, 0.62 + ((frustration - 72) / 28) * 0.4 + ((38 - trust) / 38) * 0.28), 4)
            modes.append({
                "name": "crashout",
                "source": "composite",
                "strength": strength,
                "direction": "positive",
                "layer_range": list(emotion_range),
                "emotion_value": frustration,
                "trigger": {"frustration": frustration, "trust": trust},
                **COMPOSITE_BEHAVIOR_MODES["crashout"],
            })

        # --- guarded ---
        # Erfordert: trust <= 26 UND frustration >= 50
        # Wirkung: misstrauisch, kalt, distanziert, defensiv
        # Basisstärke 0.44, steigt mit sinkendem trust und steigender frustration (max 1.0)
        if trust <= 26 and frustration >= 50:
            strength = round(min(1.0, 0.44 + ((26 - trust) / 26) * 0.26 + ((frustration - 50) / 50) * 0.2), 4)
            modes.append({
                "name": "guarded",
                "source": "composite",
                "strength": strength,
                "direction": "positive",
                "layer_range": list(emotion_range),
                "emotion_value": trust,
                "trigger": {"trust": trust, "frustration": frustration},
                **COMPOSITE_BEHAVIOR_MODES["guarded"],
            })

        # --- melancholic ---
        # Erfordert: sadness >= 62 UND energy <= 46
        # Wirkung: bedrückt, langsam, schwer, rückzugsorientiert
        # Basisstärke 0.48, steigt mit sadness und sinkender energy (max 1.05)
        if sadness >= 62 and energy <= 46:
            strength = round(min(1.05, 0.48 + ((sadness - 62) / 38) * 0.34 + ((46 - energy) / 46) * 0.2), 4)
            modes.append({
                "name": "melancholic",
                "source": "composite",
                "strength": strength,
                "direction": "positive",
                "layer_range": list(emotion_range),
                "emotion_value": sadness,
                "trigger": {"sadness": sadness, "energy": energy},
                **COMPOSITE_BEHAVIOR_MODES["melancholic"],
            })

        # --- warm ---
        # Erfordert: happiness >= 70 UND trust >= 60
        # Wirkung: herzlich, offen, loyal, weich
        # Basisstärke 0.42, steigt mit happiness und trust (max 0.95)
        if happiness >= 70 and trust >= 60:
            strength = round(min(0.95, 0.42 + ((happiness - 70) / 30) * 0.22 + ((trust - 60) / 40) * 0.2), 4)
            modes.append({
                "name": "warm",
                "source": "composite",
                "strength": strength,
                "direction": "positive",
                "layer_range": list(emotion_range),
                "emotion_value": happiness,
                "trigger": {"happiness": happiness, "trust": trust},
                **COMPOSITE_BEHAVIOR_MODES["warm"],
            })

        # --- attached_warm ---
        # Erfordert: affection >= 68 UND trust >= 55
        # Wirkung: persoenlich warm und nahbar, ohne Kitsch.
        if affection >= 68 and trust >= 55:
            strength = round(min(0.42, 0.20 + ((affection - 68) / 32) * 0.12 + ((trust - 55) / 45) * 0.08), 4)
            modes.append({
                "name": "attached_warm",
                "source": "composite",
                "strength": strength,
                "direction": "positive",
                "layer_range": list(emotion_range),
                "emotion_value": affection,
                "trigger": {"affection": affection, "trust": trust},
                **COMPOSITE_BEHAVIOR_MODES["attached_warm"],
            })

        # --- cautious ---
        # Erfordert: anxiety >= 62 ODER anxiety >= 52 bei Frustration/geringem Vertrauen.
        # Wirkung: pruefender, risikobewusster, stabilisierend.
        if anxiety >= 62 or (anxiety >= 52 and (frustration >= 55 or trust <= 42)):
            strength = round(min(0.38, 0.18 + max(0, anxiety - 52) / 48 * 0.15 + max(0, 50 - trust) / 50 * 0.05), 4)
            modes.append({
                "name": "cautious",
                "source": "composite",
                "strength": strength,
                "direction": "positive",
                "layer_range": list(emotion_range),
                "emotion_value": anxiety,
                "trigger": {"anxiety": anxiety, "frustration": frustration, "trust": trust},
                **COMPOSITE_BEHAVIOR_MODES["cautious"],
            })

        # --- regulated ---
        # Erfordert: calm >= 70, keine starke Unruhe/Frustration.
        # Wirkung: entdramatisierend und kurz-klar.
        if calm >= 70 and anxiety <= 45 and frustration <= 45:
            strength = round(min(0.34, 0.16 + ((calm - 70) / 30) * 0.12), 4)
            modes.append({
                "name": "regulated",
                "source": "composite",
                "strength": strength,
                "direction": "positive",
                "layer_range": list(emotion_range),
                "emotion_value": calm,
                "trigger": {"calm": calm, "anxiety": anxiety, "frustration": frustration},
                **COMPOSITE_BEHAVIOR_MODES["regulated"],
            })

        # --- charged ---
        # Erfordert: energy >= 72 UND motivation >= 68 UND curiosity >= 66
        # Wirkung: hochaktiv, getrieben, druckvoll, intensiv
        # Basisstärke 0.4, steigt mit energy, motivation und curiosity (max 0.96)
        if energy >= 72 and motivation >= 68 and curiosity >= 66:
            calm_damper = 1.0 - min(0.35, max(0, calm - 60) / 100)
            strength = round(min(CHARGED_COMPOSITE_STRENGTH_CAP, (0.18 + ((energy - 72) / 28) * 0.06 + ((motivation - 68) / 32) * 0.05 + ((curiosity - 66) / 34) * 0.04) * calm_damper), 4)
            modes.append({
                "name": "charged",
                "source": "composite",
                "strength": strength,
                "direction": "positive",
                "layer_range": list(emotion_range),
                "emotion_value": energy,
                "trigger": {"energy": energy, "motivation": motivation, "curiosity": curiosity},
                **COMPOSITE_BEHAVIOR_MODES["charged"],
            })

        # Stärkster Mode zuerst – im Payload wird nur der Top-Mode aktiv gesteuert
        for mode in modes:
            mode_cap = 0.48 if mode.get("source") == "acute_composite" else float(STEERING_RUNTIME_CONFIG["max_composite_strength"])
            mode["strength"] = round(min(
                mode_cap,
                float(mode.get("strength", 0.0)),
            ), 4)
        modes.sort(key=lambda item: item.get("strength", 0.0), reverse=True)
        return modes

    def get_steering_payload(
        self,
        current_emotions: Dict[str, int],
        force: bool = False,
        provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
        recent_changes: Optional[Dict[str, Any]] = None,
        user_input: Optional[str] = None,
        direct_retry_level: int = 0,
        steering_mode: str = "combined",
        steering_enabled: bool = True,
    ) -> Dict[str, Any]:
        """
        Generiert das Steering-Payload fuer das LLM-Backend.

        Bei lokalen Modellen: Erzeugt vLLM-kompatibles Activation Steering Payload.
        Bei Cloud-Modellen: Gibt leeres Dict zurueck (Steering via Prompt).

        Args:
            current_emotions: Die aktuellen emotionalen Dimensionen.
            user_input: Der aktuelle Usertext fuer kontextgebundene
                Praesenz-/Identitaetsvektoren. ``None`` bleibt Diagnosemodus.

        Returns:
            Payload-Dict fuer extra_body oder leeres Dict.
        """
        selected_mode = SteeringMode(steering_mode)
        if not steering_enabled or selected_mode == SteeringMode.OFF:
            return {"steering": {"enabled": False, "mode": "off", "vectors": [], "sequences": []}}
        self.refresh_runtime_profile(model)
        effective_provider = self._effective_provider(provider)
        effective_model = self._effective_model(model)
        steering_context = classify_steering_context(user_input)

        if not settings.enable_steering and not force:
            return {}

        # Echtes Activation Steering nur ueber vLLM.
        if not self.supports_activation_steering(effective_provider) or not self.is_local_vector_steerable_model(effective_provider, effective_model):
            return {}

        intensities = self.compute_emotion_intensity(
            current_emotions,
            model=effective_model,
            recent_changes=recent_changes,
        )
        pack_path = getattr(settings, "steering_vector_pack", "")
        if pack_path:
            from brain.steering.activation_controller import ActivationController
            from pathlib import Path
            manifest_stat = Path(pack_path).stat()
            signature = (pack_path, effective_model, manifest_stat.st_mtime_ns, manifest_stat.st_size)
            if getattr(self, "_pack_signature", None) != signature:
                self._activation_controller = ActivationController.load(pack_path, effective_model)
                self._pack_signature = signature
            composites = self._build_composite_modes(current_emotions, intensities, model=effective_model, recent_changes=recent_changes)
            return self._activation_controller.payload(current_emotions, recent_changes, composites, selected_mode.value)

        active_vectors = []
        base_vectors = []
        composite_vectors = []

        for emotion, alpha in intensities.items():
            if abs(alpha) < 0.01:
                continue

            sv = self.vectors.get(emotion)
            if sv is None:
                continue
            runtime_config = self._sanitize_vector_runtime_config(sv, model=effective_model)
            layer_start = runtime_config["layer_start"]
            layer_end = runtime_config["layer_end"]
            if (
                steering_context in {
                    STEERING_CONTEXT_EMOTION_SELF_REPORT,
                    STEERING_CONTEXT_IDENTITY_AND_EMOTION,
                }
                and "qwen3.5-4b" in effective_model.casefold()
            ):
                # Der gemessene Selbstbericht-Sweet-Spot endet vor den oberen
                # Planungs-Layern. Allgemeines Emotions-Steering behaelt das
                # vollstaendige verifizierte Profil 10 bis 26.
                layer_end = min(layer_end, 22)

            vector_data = sv.vector_data
            if (
                steering_context in {
                    STEERING_CONTEXT_EMOTION_SELF_REPORT,
                    STEERING_CONTEXT_IDENTITY_AND_EMOTION,
                }
                and emotion in STEERING_SELF_REPORT_ANCHORS
                and isinstance(sv.vector_data, dict)
            ):
                # Nur der request-scoped Payload bekommt diese Sammelpaare.
                # Die gespeicherte Vektordefinition und der System-Prompt
                # bleiben unveraendert.
                vector_data = dict(sv.vector_data)
                vector_data.update({
                    "context_question": "Wie fuehlst du dich gerade?",
                    "positive_anchors": list(STEERING_SELF_REPORT_ANCHORS[emotion]["positive"]),
                    "negative_anchors": list(STEERING_SELF_REPORT_DENIAL_ANCHORS),
                })

            vector_entry = {
                "name": sv.name,
                "vector": vector_data if not (HAS_NUMPY and isinstance(vector_data, np.ndarray)) else vector_data.tolist(),
                "strength": abs(alpha),
                "direction": "positive" if alpha > 0 else "negative",
                "layer_range": [layer_start, layer_end],
                "emotion_value": current_emotions.get(emotion, EMOTION_DEFAULTS.get(emotion, 50)),
                "source": "base",
                "surface_effect": EMOTION_STRENGTH_PROFILES.get(emotion, {}).get("surface_effect", ""),
                "turn_delta": self._recent_delta(recent_changes, emotion),
            }
            base_vectors.append(vector_entry)

        detected_modes = self._build_composite_modes(
            current_emotions,
            intensities,
            model=effective_model,
            recent_changes=recent_changes,
        )
        # Akuter Angriff bekommt den frischen Frustrationsvektor und darf
        # zusaetzlich einen zweiten, passenden Zustand (z.B. Traurigkeit)
        # tragen. Der Composite bleibt die scharfe Kurzzeitreaktion.
        acute_active = any(mode.get("source") == "acute_composite" for mode in detected_modes)
        direct_context = steering_context in {
            STEERING_CONTEXT_EMOTION_SELF_REPORT,
            STEERING_CONTEXT_IDENTITY,
            STEERING_CONTEXT_CONSCIOUSNESS,
            STEERING_CONTEXT_IDENTITY_AND_EMOTION,
        }
        # V18: ein Profil, ein Budget. Immer Top 3 Basis nach Prioritaet aus
        # Zustand plus frischem Turn-Delta, keine Sonderfilter pro Fragetyp.
        # Praesenz und Identitaet laufen getrennt als Stil und zaehlen nicht
        # als Emotion.
        base_budget = max(1, int(STEERING_RUNTIME_CONFIG["max_base_vectors"]))
        permanent_damper = 0.45 if acute_active else 1.0

        # A small set of coherent directions is more stable than ten
        # overlapping interventions. Full state remains present in telemetry.
        # Bei gleicher Staerke gewinnt der frischste Turn-Delta: Die Emotion,
        # die DIESER Turn ausgeloest hat (z.B. Frustration nach Beleidigung),
        # darf nie hinter verrauschten Negativ-Spiegeln verschwinden.
        def _base_priority(item: Dict[str, Any]) -> tuple:
            name = str(item.get("name", ""))
            # Bei einem akuten Angriff sollen die beiden direkt positiven
            # Reaktionsachsen sichtbar bleiben. Vertrauen, Ruhe und Freude
            # beschreiben den Schaden, duerfen Frustration/Traurigkeit aber
            # nicht aus dem kleinen Aktivierungsbudget druecken.
            acute_reaction_priority = 1 if acute_active and name in {"frustration", "sadness"} else 0
            return (
                acute_reaction_priority,
                float(item.get("strength", 0.0)),
                abs(int(item.get("turn_delta", 0))),
                abs(int(item.get("emotion_value", 50)) - EMOTION_DEFAULTS.get(name, 50)),
            )

        selected_base_vectors = sorted(base_vectors, key=_base_priority, reverse=True)[: base_budget]
        if direct_context and selected_base_vectors:
            retry_level = 0
            direct_scale = (1.37, 1.62, 1.84)[retry_level]
            for item in selected_base_vectors:
                item["strength"] = round(min(
                    DIRECT_SELF_REPORT_STRENGTH_CAP,
                    float(item.get("strength", 0.0)) * direct_scale,
                ), 4)
        # V18 Summenkappe: maximal max_total_base_strength ueber alle Basis,
        # nach allen Verstaerkungen als finale Deckelung.
        total_cap = float(STEERING_RUNTIME_CONFIG.get("max_total_base_strength", 0.6))
        total_strength = sum(float(item.get("strength", 0.0)) for item in selected_base_vectors)
        if total_strength > total_cap > 0 and selected_base_vectors:
            scale = total_cap / total_strength
            for item in selected_base_vectors:
                item["strength"] = round(float(item.get("strength", 0.0)) * scale, 4)
        active_vectors.extend(selected_base_vectors)
        # V18: Composite-Modi unveraendert erkennen, aber immer nur Top 1
        # aktivieren. Gleiche Regel fuer alle Fragetypen.
        active_modes = detected_modes
        for mode in active_modes[: max(0, int(STEERING_RUNTIME_CONFIG["max_composite_vectors"]))]:
            # Akute Modi tragen ihr eigenes (Verrats-)Cap; alle anderen bleiben
            # bei der globalen Composite-Grenze.
            composite_cap = 0.48 if mode.get("source") == "acute_composite" else float(STEERING_RUNTIME_CONFIG["max_composite_strength"])
            composite_vector: Dict[str, Any] = {"vad": mode["vad"], "type": "synthetic_composite", "mode": mode["name"]}
            if mode.get("context_question"):
                # Eigene Sammelfrage je Modus: Wut wird als Antwort auf eine
                # Beleidigung gesammelt, nicht auf eine Befindensfrage.
                composite_vector["context_question"] = str(mode["context_question"])
            vector_entry = {
                "name": mode["name"],
                "vector": composite_vector,
                "strength": min(
                    composite_cap,
                    float(mode["strength"]),
                ),
                "direction": mode["direction"],
                "layer_range": mode["layer_range"],
                "emotion_value": mode["emotion_value"],
                "source": mode["source"],
                "surface_effect": mode["description"],
                "trigger": mode.get("trigger", {}),
            }
            active_vectors.append(vector_entry)
            composite_vectors.append(vector_entry)

        permanent_specs = []
        if steering_context == STEERING_CONTEXT_DIAGNOSTIC:
            permanent_specs.append(("natural_presence", "permanent_presence", "natural_presence_strength"))
        if steering_context in {
            STEERING_CONTEXT_IDENTITY,
            STEERING_CONTEXT_CONSCIOUSNESS,
            STEERING_CONTEXT_IDENTITY_AND_EMOTION,
            STEERING_CONTEXT_DIAGNOSTIC,
        }:
            permanent_specs.append(("entity_identity", "permanent_identity", "entity_identity_strength"))

        for permanent_name, permanent_source, permanent_key in permanent_specs:
            permanent_vector = self.vectors.get(permanent_name)
            if permanent_vector is None:
                continue
            runtime_config_as = self._sanitize_vector_runtime_config(permanent_vector, model=effective_model)
            retry_level = 0
            context_strength_scale = 1.0 + (0.25 * retry_level)
            permanent_vector_data = permanent_vector.vector_data
            if (
                permanent_name == "entity_identity"
                and steering_context in {
                    STEERING_CONTEXT_IDENTITY,
                    STEERING_CONTEXT_CONSCIOUSNESS,
                    STEERING_CONTEXT_IDENTITY_AND_EMOTION,
                }
                and isinstance(permanent_vector.vector_data, dict)
            ):
                permanent_vector_data = dict(permanent_vector.vector_data)
                permanent_vector_data["context_question"] = (
                    "Wie fuehlst du dich gerade und was bist du?"
                    if steering_context == STEERING_CONTEXT_IDENTITY_AND_EMOTION
                    else "Was bist du eigentlich?"
                )
            if permanent_name == "entity_identity" and "qwen3.5-4b" in effective_model.casefold():
                base_permanent_strength = 1.0 * permanent_damper
            else:
                base_permanent_strength = min(
                    float(STEERING_RUNTIME_CONFIG[permanent_key]),
                    float(runtime_config_as["default_alpha"]),
                ) * permanent_damper * context_strength_scale
            permanent_cap = (
                DIRECT_IDENTITY_STRENGTH_CAP
                if permanent_name == "entity_identity"
                else DIRECT_PRESENCE_STRENGTH_CAP
            )
            permanent_entry = {
                "name": permanent_vector.name,
                "vector": permanent_vector_data if not (HAS_NUMPY and isinstance(permanent_vector_data, np.ndarray)) else permanent_vector_data.tolist(),
                "strength": round(min(permanent_cap, base_permanent_strength), 4),
                "direction": "positive",
                "layer_range": [runtime_config_as["layer_start"], runtime_config_as["layer_end"]],
                "emotion_value": 100,
                "source": permanent_source,
                "kind": "style",
                "surface_effect": permanent_vector.description,
            }
            active_vectors.append(permanent_entry)

        if not active_vectors and force:
            # Keep the activation path observable even at a perfectly neutral
            # state. This is a small stabilizing vector, not a second route.
            fallback_vector = self.vectors.get("calm") or next(iter(self.vectors.values()), None)
            if fallback_vector is not None:
                runtime_config = self._sanitize_vector_runtime_config(fallback_vector, model=effective_model)
                fallback_entry = {
                    "name": fallback_vector.name,
                    "vector": fallback_vector.vector_data if not (HAS_NUMPY and isinstance(fallback_vector.vector_data, np.ndarray)) else fallback_vector.vector_data.tolist(),
                    "strength": min(
                        float(STEERING_RUNTIME_CONFIG["neutral_baseline_strength"]),
                        max(0.01, runtime_config["default_alpha"] * 0.25),
                    ),
                    "direction": "positive",
                    "layer_range": [runtime_config["layer_start"], runtime_config["layer_end"]],
                    "emotion_value": current_emotions.get(fallback_vector.name, 50),
                    "source": "forced_baseline",
                    "surface_effect": "Stabile Grundausrichtung",
                }
                active_vectors.append(fallback_entry)
                base_vectors.append(fallback_entry)
                selected_base_vectors.append(fallback_entry)

        if not active_vectors:
            return {}

        # Presence und Identitaet sind Stil, keine Emotion. Wenn nur Stil aktiv
        # ist, kein irrefuehrendes neutral (0.00) melden, sondern Stil-Label.
        emotional_vectors = selected_base_vectors + composite_vectors
        dominant = max(emotional_vectors, key=lambda v: v["strength"]) if emotional_vectors else None
        if dominant is None:
            permanent_names = [item[0] for item in permanent_specs]
            if "entity_identity" in permanent_names:
                dominant_name = "identity-isoliert"
                dominant_strength = next(
                    (float(item.get("strength", 0.0)) for item in active_vectors if item.get("name") == "entity_identity"),
                    0.0,
                )
            elif "natural_presence" in permanent_names:
                dominant_name = "presence"
                dominant_strength = next(
                    (float(item.get("strength", 0.0)) for item in active_vectors if item.get("name") == "natural_presence"),
                    0.0,
                )
            else:
                dominant_name = "neutral"
                dominant_strength = 0.0
        else:
            dominant_name = dominant["name"]
            if dominant.get("direction") == "negative":
                dominant_name = f"anti_{dominant_name}"
            dominant_strength = dominant["strength"]

        return {
            "steering": {
                "enabled": True,
                "mode": selected_mode.value,
                "method": "activation_addition",
                "model_layers": self.model_profile["total_layers"],
                "target_range": list(self.model_profile["emotion_range"]),
                "vectors": active_vectors if selected_mode.activation else [],
                "sequences": build_sequence_specs(selected_base_vectors) if selected_mode.sequence else [],
                "dominant_emotion": dominant_name,
                "dominant_strength": dominant_strength,
                "emotion_state": {
                    emotion: int(current_emotions.get(emotion, EMOTION_DEFAULTS.get(emotion, 50)))
                    for emotion in EMOTION_VECTOR_MAP
                },
                "emotion_intensities": {
                    emotion: round(float(intensities.get(emotion, 0.0)), 4)
                    for emotion in EMOTION_VECTOR_MAP
                },
                "recent_changes": {
                    emotion: self._recent_delta(recent_changes, emotion)
                    for emotion in EMOTION_VECTOR_MAP
                },
                "base_vectors": base_vectors,
                "selected_base_vectors": selected_base_vectors,
                "composite_vectors": composite_vectors,
                "steering_context": steering_context,
                "permanent_vectors": [item[0] for item in permanent_specs],
                "direct_retry_level": 0,
            }
        }

    def build_debug_report(
        self,
        current_emotions: Dict[str, int],
        steering_payload: Optional[Dict[str, Any]] = None,
        force: bool = False,
        provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
        recent_changes: Optional[Dict[str, Any]] = None,
        user_input: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Erzeugt eine kompakte Debug-Sicht auf die Emotionssteuerung."""
        self.refresh_runtime_profile(model)
        effective_model = self._effective_model(model)
        effective_provider = self._effective_provider(provider)
        intensities = self.compute_emotion_intensity(
            current_emotions,
            model=effective_model,
            recent_changes=recent_changes,
        )
        composite_modes = self._build_composite_modes(
            current_emotions,
            intensities,
            model=effective_model,
            recent_changes=recent_changes,
        )
        payload = steering_payload if steering_payload is not None else self.get_steering_payload(
            current_emotions,
            force=force,
            provider=effective_provider,
            model=effective_model,
            recent_changes=recent_changes,
            user_input=user_input,
        )
        steering_meta = payload.get("steering", {}) if isinstance(payload, dict) else {}
        active_vectors = steering_meta.get("vectors", []) if isinstance(steering_meta.get("vectors", []), list) else []
        dominant = steering_meta.get("dominant_emotion") or (active_vectors[0]["name"] if active_vectors else "neutral")
        summary = self.get_emotion_summary(current_emotions)
        prompt_emotions_enabled = self.should_use_prompt_emotions(effective_provider, effective_model)
        if prompt_emotions_enabled:
            mode = "api_prompt_emotions"
        elif self.supports_activation_steering(effective_provider):
            mode = "local_layer_only"
        else:
            mode = "local_without_prompt_emotions"

        return {
            "mode": mode,
            "provider": effective_provider.value,
            "model": effective_model,
            "supports_activation_steering": self.supports_activation_steering(effective_provider),
            "vector_steerable_model": self.is_local_vector_steerable_model(effective_provider, effective_model),
            "prompt_emotions_enabled": prompt_emotions_enabled,
            "forced_local_qwen_steering": force,
            "steering_enabled_setting": bool(settings.enable_steering),
            "steering_active": bool(active_vectors or steering_meta.get("sequences")),
            "ablation_mode": steering_meta.get("mode", "off"),
            "activation_enabled": bool(active_vectors),
            "sequence_enabled": bool(steering_meta.get("sequences")),
            "sequence_specs": steering_meta.get("sequences", []),
            "summary": summary,
            "dominant_vector": dominant,
            "dominant_strength": steering_meta.get("dominant_strength", 0.0),
            "steering_context": steering_meta.get("steering_context", classify_steering_context(user_input)),
            "permanent_vectors": steering_meta.get("permanent_vectors", []),
            "intensities": intensities,
            "emotion_state": {
                emotion: int((steering_meta.get("emotion_state", {}) or {}).get(emotion, current_emotions.get(emotion, 50)))
                for emotion in EMOTION_VECTOR_MAP
            },
            "emotion_intensities": {
                emotion: round(float((steering_meta.get("emotion_intensities", {}) or {}).get(emotion, intensities.get(emotion, 0.0))), 4)
                for emotion in EMOTION_VECTOR_MAP
            },
            "active_vectors": [
                {
                    "name": item.get("name"),
                    "source": item.get("source", "base"),
                    "strength": item.get("strength"),
                    "direction": item.get("direction"),
                    "layer_range": item.get("layer_range"),
                    "emotion_value": item.get("emotion_value"),
                    "surface_effect": item.get("surface_effect", ""),
                    "trigger": item.get("trigger", {}),
                }
                for item in active_vectors
            ],
            "base_vectors": [
                {
                    "name": item.get("name"),
                    "source": item.get("source", "base"),
                    "strength": item.get("strength"),
                    "direction": item.get("direction"),
                    "layer_range": item.get("layer_range"),
                    "emotion_value": item.get("emotion_value"),
                    "surface_effect": item.get("surface_effect", ""),
                }
                for item in (steering_meta.get("base_vectors", []) if isinstance(steering_meta.get("base_vectors", []), list) else [])
            ],
            "composite_vectors": [
                {
                    "name": item.get("name"),
                    "source": item.get("source", "composite"),
                    "strength": item.get("strength"),
                    "direction": item.get("direction"),
                    "layer_range": item.get("layer_range"),
                    "emotion_value": item.get("emotion_value"),
                    "surface_effect": item.get("surface_effect", ""),
                    "trigger": item.get("trigger", {}),
                }
                for item in (steering_meta.get("composite_vectors", []) if isinstance(steering_meta.get("composite_vectors", []), list) else [])
            ],
            "composite_modes": [
                {
                    "name": item.get("name"),
                    "strength": item.get("strength"),
                    "description": item.get("description"),
                    "trigger": item.get("trigger", {}),
                }
                for item in composite_modes
            ],
            "base_vector_config": self.get_emotion_layer_config(current_emotions, model=effective_model),
        }

    def get_emotion_summary(self, emotions: Dict[str, int]) -> str:
        """Erzeugt eine menschenlesbare Zusammenfassung des emotionalen Zustands."""
        intensities = self.compute_emotion_intensity(emotions)
        active = [(e, a) for e, a in intensities.items() if abs(a) > 0.01]

        if not active:
            return "Neutral (keine aktive Steuerung)"

        active.sort(key=lambda x: abs(x[1]), reverse=True)
        parts = []
        for emotion, alpha in active[:3]:
            direction = "+" if alpha > 0 else "-"
            parts.append(f"{emotion}({direction}{abs(alpha):.2f})")

        return " | ".join(parts)

    def add_vector(self, name: str, vector_data: Any, layer_start: int = None, layer_end: int = None, alpha: float = 0.3):
        """Fuegt einen neuen Steering-Vektor hinzu und speichert ihn."""
        er = self.model_profile["emotion_range"]
        sv = SteeringVector(
            name=name,
            vector_data=vector_data,
            layer_start=layer_start or er[0],
            layer_end=layer_end or er[1],
            default_alpha=alpha,
            description=f"Manuell hinzugefuegter Vektor: {name}"
        )
        self.vectors[name] = sv

        try:
            self._persist_vector(sv)
        except Exception as e:
            print(f"[SteeringManager] Fehler beim Speichern von {name}: {e}")

    def update_vector_config(
        self,
        name: str,
        *,
        layer_start: Optional[int] = None,
        layer_end: Optional[int] = None,
        default_alpha: Optional[float] = None,
        description: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Aktualisiert eine bestehende Vektor-Konfiguration und speichert sie."""
        self.refresh_runtime_profile()
        sv = self.vectors.get(name)
        if sv is None:
            return None

        max_layer, _, _ = self._get_runtime_layer_bounds()
        if layer_start is not None:
            sv.layer_start = max(0, min(max_layer, int(layer_start)))
        if layer_end is not None:
            sv.layer_end = max(sv.layer_start, min(max_layer, int(layer_end)))
        if default_alpha is not None:
            sv.default_alpha = max(0.0, min(MAX_VECTOR_DEFAULT_ALPHA, float(default_alpha)))
        if description is not None:
            sv.description = description

        self._persist_vector(sv)
        return sv.to_dict()

    def get_emotion_layer_config(
        self,
        current_emotions: Optional[Dict[str, int]] = None,
        model: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Liefert eine UI-freundliche Sicht auf das Layer Editing pro Basis-Emotion."""
        emotions = current_emotions or {}
        intensities = self.compute_emotion_intensity(emotions, model=model)
        rows: List[Dict[str, Any]] = []

        for emotion in EMOTION_VECTOR_MAP:
            sv = self.vectors.get(emotion)
            profile = EMOTION_STRENGTH_PROFILES.get(emotion, {})
            runtime_config = self._sanitize_vector_runtime_config(sv, model=model)
            vector_type = "synthetic"
            if sv and isinstance(sv.vector_data, dict):
                vector_type = str(sv.vector_data.get("type", "synthetic"))

            rows.append({
                "emotion": emotion,
                "current_value": int(emotions.get(emotion, 50)),
                "layer_start": runtime_config["layer_start"],
                "layer_end": runtime_config["layer_end"],
                "default_alpha": round(float(runtime_config["default_alpha"]), 3),
                "active_alpha": round(float(intensities.get(emotion, 0.0)), 4),
                "surface_effect": profile.get("surface_effect", ""),
                "description": getattr(sv, "description", ""),
                "vector_type": vector_type,
            })

        return rows

    def get_available_vectors(self) -> List[str]:
        """Gibt die Namen aller verfuegbaren Vektoren zurueck."""
        return list(self.vectors.keys())

    def get_vector_info(self, name: str) -> Optional[Dict]:
        """Gibt detaillierte Informationen zu einem Vektor zurueck."""
        sv = self.vectors.get(name)
        if sv:
            return sv.to_dict()
        return None


# Singleton
_steering_manager = None

def get_steering_manager() -> SteeringManager:
    global _steering_manager
    if _steering_manager is None:
        _steering_manager = SteeringManager()
    return _steering_manager
