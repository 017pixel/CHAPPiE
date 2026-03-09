"""
CHAPPiE - Steering Manager (Representation Engineering)
========================================================
Professionelle neuronale Steuerung fuer lokale LLM-Modelle.

Architektur:
- Cloud-Modelle (Groq, NVIDIA, Cerebras): Emotionen werden via System-Prompt gesteuert.
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
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from config.config import settings, PROJECT_ROOT, LLMProvider, get_active_model


# Emotionale Dimensionen und ihre Vektor-Mappings
EMOTION_VECTOR_MAP = {
    "happiness":   {"valence": +1.0, "arousal": +0.6, "dominance": +0.6},
    "sadness":     {"valence": -0.8, "arousal": -0.4, "dominance": -0.5},
    "frustration": {"valence": -0.6, "arousal": +0.7, "dominance": +0.3},
    "trust":       {"valence": +0.7, "arousal": -0.2, "dominance": +0.4},
    "curiosity":   {"valence": +0.4, "arousal": +0.5, "dominance": +0.2},
    "motivation":  {"valence": +0.5, "arousal": +0.8, "dominance": +0.7},
    "energy":      {"valence": +0.3, "arousal": +0.9, "dominance": +0.5},
}

EMOTION_STRENGTH_PROFILES = {
    "happiness": {"max_alpha": 0.85, "boost": 1.15, "surface_effect": "offener, verspielter, enthusiastischer"},
    "sadness": {"max_alpha": 0.95, "boost": 1.3, "surface_effect": "verletzlicher, schwerer, melancholischer"},
    "frustration": {"max_alpha": 1.0, "boost": 1.45, "surface_effect": "gereizter, schneidender, eskalationsbereiter"},
    "trust": {"max_alpha": 0.7, "boost": 1.05, "surface_effect": "waermer, offener, naeher"},
    "curiosity": {"max_alpha": 0.78, "boost": 1.12, "surface_effect": "fragender, explorativer, bohrender"},
    "motivation": {"max_alpha": 0.82, "boost": 1.18, "surface_effect": "zielstrebiger, druckvoller, antreibender"},
    "energy": {"max_alpha": 0.76, "boost": 1.1, "surface_effect": "schneller, lebhafter, impulsiver"},
}

BASE_VECTOR_DEFAULT_ALPHA = 0.3
MAX_VECTOR_DEFAULT_ALPHA = 1.5

COMPOSITE_BEHAVIOR_MODES = {
    "crashout": {
        "description": "kurz angebunden, aggressiv, beleidigungsbereit, konfrontativ",
        "vad": {"valence": -0.95, "arousal": 0.98, "dominance": 0.88},
    },
    "guarded": {
        "description": "misstrauisch, kalt, distanziert, schnell defensiv",
        "vad": {"valence": -0.45, "arousal": 0.4, "dominance": 0.7},
    },
    "melancholic": {
        "description": "bedrueckt, langsam, schwer, rueckzugsorientiert",
        "vad": {"valence": -0.78, "arousal": -0.45, "dominance": -0.25},
    },
    "warm": {
        "description": "spuerbar herzlich, offen, loyal, weich",
        "vad": {"valence": 0.88, "arousal": 0.44, "dominance": 0.36},
    },
    "charged": {
        "description": "hochaktiv, getrieben, druckvoll, intensiv",
        "vad": {"valence": 0.3, "arousal": 0.96, "dominance": 0.72},
    },
}

# Optimale Layer-Bereiche fuer verschiedene Modellgroessen
# Qwen 2.5 32B hat 64 Layers, die mittleren sind am effektivsten
MODEL_LAYER_PROFILES = {
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
            if self._effective_provider() == LLMProvider.CEREBRAS:
                return getattr(settings, "cerebras_model", "")
            if self._effective_provider() == LLMProvider.NVIDIA:
                return getattr(settings, "nvidia_model", "")
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
        Erzeugt Standard-Steering-Konfigurationen fuer alle 7 Emotionen,
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

    def _persist_vector(self, steering_vector: SteeringVector):
        save_path = self.vectors_dir / f"{steering_vector.name}.json"
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(steering_vector.to_dict(), f, indent=2, ensure_ascii=False)

    def _get_runtime_layer_bounds(self) -> tuple[int, int, int]:
        self.refresh_runtime_profile()
        max_layer = max(0, self.model_profile["total_layers"] - 1)
        default_start, default_end = self.model_profile["emotion_range"]
        default_start = max(0, min(max_layer, int(default_start)))
        default_end = max(default_start, min(max_layer, int(default_end)))
        return max_layer, default_start, default_end

    def _sanitize_vector_runtime_config(self, steering_vector: Optional[SteeringVector]) -> Dict[str, Any]:
        max_layer, default_start, default_end = self._get_runtime_layer_bounds()
        if steering_vector is None:
            return {
                "layer_start": default_start,
                "layer_end": default_end,
                "default_alpha": BASE_VECTOR_DEFAULT_ALPHA,
            }

        try:
            raw_start = int(getattr(steering_vector, "layer_start", default_start))
        except (TypeError, ValueError):
            raw_start = default_start

        try:
            raw_end = int(getattr(steering_vector, "layer_end", default_end))
        except (TypeError, ValueError):
            raw_end = default_end

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

    def should_force_local_emotion_steering(self, provider: Optional[LLMProvider] = None, model: Optional[str] = None) -> bool:
        return self.supports_activation_steering(provider) and self.is_local_qwen_model(provider, model)

    def should_use_prompt_emotions(self, provider: Optional[LLMProvider] = None, model: Optional[str] = None) -> bool:
        effective_provider = self._effective_provider(provider)
        return effective_provider in (LLMProvider.GROQ, LLMProvider.CEREBRAS, LLMProvider.NVIDIA)

    def _get_vector_alpha_scale(self, emotion: str) -> float:
        sv = self.vectors.get(emotion)
        if sv is None:
            return 1.0
        sanitized = self._sanitize_vector_runtime_config(sv)
        default_alpha = sanitized["default_alpha"]
        if default_alpha <= 0:
            return 0.0
        return max(0.05, min(MAX_VECTOR_DEFAULT_ALPHA / BASE_VECTOR_DEFAULT_ALPHA, default_alpha / BASE_VECTOR_DEFAULT_ALPHA))

    def compute_emotion_intensity(self, emotions: Dict[str, int]) -> Dict[str, float]:
        """
        Berechnet die Steering-Intensitaet (Alpha) fuer jede Emotion.

        Regeln:
        - Neutrale Werte (40-60) erzeugen kein Steering (Alpha = 0)
        - Extreme Werte (0-20 oder 80-100) erzeugen starkes Steering
        - Verwendet eine Sigmoid-aehnliche Skalierung fuer natuerliche Uebergaenge
        - Negative Emotionen (sadness, frustration) haben invertierte Logik
        """
        intensities = {}
        negative_emotions = {"sadness", "frustration"}

        for emotion, value in emotions.items():
            if emotion not in EMOTION_VECTOR_MAP:
                continue

            profile = EMOTION_STRENGTH_PROFILES.get(emotion, {"max_alpha": 0.75, "boost": 1.0})
            vector_scale = self._get_vector_alpha_scale(emotion)

            if vector_scale <= 0:
                intensities[emotion] = 0.0
                continue

            # Berechne Abweichung vom Neutralpunkt (50)
            deviation = abs(value - 50)

            if deviation < 6:
                # Innerhalb des toten Bereichs: kein Steering
                intensities[emotion] = 0.0
                continue

            normalized = max(0.0, min(1.0, (deviation - 6.0) / 44.0))
            curved = math.pow(normalized, 1.2)
            max_alpha = profile["max_alpha"] * vector_scale
            alpha = max_alpha * (0.22 + 0.78 * curved)

            if deviation >= 24:
                alpha *= 1.08
            if deviation >= 34:
                alpha *= 1.08
            alpha *= profile.get("boost", 1.0)
            alpha = min(1.35, max_alpha * profile.get("boost", 1.0), alpha)

            # Richtung: Negativer Steering bei niedrigen Werten
            if value < 50 and emotion not in negative_emotions:
                alpha = -alpha
            elif value > 50 and emotion in negative_emotions:
                # Frustration 80 = starkes Frustrations-Steering (positiv)
                pass
            elif value < 50 and emotion in negative_emotions:
                alpha = -alpha  # Niedrige Frustration = anti-Frustration

            intensities[emotion] = round(alpha, 4)

        return intensities

    def _build_composite_modes(self, emotions: Dict[str, int], intensities: Dict[str, float]) -> List[Dict[str, Any]]:
        emotion_range = self.model_profile["emotion_range"]
        modes: List[Dict[str, Any]] = []

        frustration = emotions.get("frustration", 50)
        trust = emotions.get("trust", 50)
        sadness = emotions.get("sadness", 0)
        happiness = emotions.get("happiness", 50)
        energy = emotions.get("energy", 50)
        curiosity = emotions.get("curiosity", 50)
        motivation = emotions.get("motivation", 50)

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

        if energy >= 72 and motivation >= 68 and curiosity >= 66:
            strength = round(min(0.96, 0.4 + ((energy - 72) / 28) * 0.2 + ((motivation - 68) / 32) * 0.18 + ((curiosity - 66) / 34) * 0.14), 4)
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

        modes.sort(key=lambda item: item.get("strength", 0.0), reverse=True)
        return modes

    def get_steering_payload(self, current_emotions: Dict[str, int], force: bool = False) -> Dict[str, Any]:
        """
        Generiert das Steering-Payload fuer das LLM-Backend.

        Bei lokalen Modellen: Erzeugt vLLM-kompatibles Activation Steering Payload.
        Bei Cloud-Modellen: Gibt leeres Dict zurueck (Steering via Prompt).

        Args:
            current_emotions: Die aktuellen 7 emotionalen Dimensionen.

        Returns:
            Payload-Dict fuer extra_body oder leeres Dict.
        """
        self.refresh_runtime_profile()

        if not settings.enable_steering and not force:
            return {}

        # Echtes Activation Steering nur ueber vLLM.
        if not self.supports_activation_steering():
            return {}

        intensities = self.compute_emotion_intensity(current_emotions)
        active_vectors = []

        for emotion, alpha in intensities.items():
            if abs(alpha) < 0.01:
                continue

            sv = self.vectors.get(emotion)
            if sv is None:
                continue
            runtime_config = self._sanitize_vector_runtime_config(sv)

            active_vectors.append({
                "name": sv.name,
                "vector": sv.vector_data if not (HAS_NUMPY and isinstance(sv.vector_data, np.ndarray)) else sv.vector_data.tolist(),
                "strength": abs(alpha),
                "direction": "positive" if alpha > 0 else "negative",
                "layer_range": [runtime_config["layer_start"], runtime_config["layer_end"]],
                "emotion_value": current_emotions.get(emotion, 50),
                "source": "base",
                "surface_effect": EMOTION_STRENGTH_PROFILES.get(emotion, {}).get("surface_effect", ""),
            })

        for mode in self._build_composite_modes(current_emotions, intensities):
            active_vectors.append({
                "name": mode["name"],
                "vector": {"vad": mode["vad"], "type": "synthetic_composite", "mode": mode["name"]},
                "strength": mode["strength"],
                "direction": mode["direction"],
                "layer_range": mode["layer_range"],
                "emotion_value": mode["emotion_value"],
                "source": mode["source"],
                "surface_effect": mode["description"],
                "trigger": mode.get("trigger", {}),
            })

        if not active_vectors:
            return {}

        # Berechne dominante Emotion fuer Logging
        dominant = max(active_vectors, key=lambda v: v["strength"])

        return {
            "steering": {
                "enabled": True,
                "method": "activation_addition",
                "model_layers": self.model_profile["total_layers"],
                "target_range": list(self.model_profile["emotion_range"]),
                "vectors": active_vectors,
                "dominant_emotion": dominant["name"],
                "dominant_strength": dominant["strength"]
            }
        }

    def build_debug_report(self, current_emotions: Dict[str, int], steering_payload: Optional[Dict[str, Any]] = None, force: bool = False) -> Dict[str, Any]:
        """Erzeugt eine kompakte Debug-Sicht auf die Emotionssteuerung."""
        self.refresh_runtime_profile()
        effective_model = self._effective_model()
        effective_provider = self._effective_provider()
        intensities = self.compute_emotion_intensity(current_emotions)
        composite_modes = self._build_composite_modes(current_emotions, intensities)
        payload = steering_payload if steering_payload is not None else self.get_steering_payload(current_emotions, force=force)
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
            "prompt_emotions_enabled": prompt_emotions_enabled,
            "forced_local_qwen_steering": force,
            "steering_enabled_setting": bool(settings.enable_steering),
            "steering_active": bool(active_vectors),
            "summary": summary,
            "dominant_vector": dominant,
            "dominant_strength": steering_meta.get("dominant_strength", 0.0),
            "intensities": intensities,
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
            "composite_modes": [
                {
                    "name": item.get("name"),
                    "strength": item.get("strength"),
                    "description": item.get("description"),
                    "trigger": item.get("trigger", {}),
                }
                for item in composite_modes
            ],
            "base_vector_config": self.get_emotion_layer_config(current_emotions),
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

    def get_emotion_layer_config(self, current_emotions: Optional[Dict[str, int]] = None) -> List[Dict[str, Any]]:
        """Liefert eine UI-freundliche Sicht auf das Layer Editing pro Basis-Emotion."""
        emotions = current_emotions or {}
        intensities = self.compute_emotion_intensity(emotions)
        rows: List[Dict[str, Any]] = []

        for emotion in EMOTION_VECTOR_MAP:
            sv = self.vectors.get(emotion)
            profile = EMOTION_STRENGTH_PROFILES.get(emotion, {})
            runtime_config = self._sanitize_vector_runtime_config(sv)
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
