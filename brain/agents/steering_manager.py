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

from config.config import settings, PROJECT_ROOT, LLMProvider


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

# Optimale Layer-Bereiche fuer verschiedene Modellgroessen
# Qwen 2.5 32B hat 64 Layers, die mittleren sind am effektivsten
MODEL_LAYER_PROFILES = {
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

    def _detect_model_profile(self) -> Dict:
        """Erkennt das aktive Modell und waehlt das passende Layer-Profil."""
        model_name = getattr(settings, "vllm_model", "") or getattr(settings, "ollama_model", "")
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

    def is_local_provider(self) -> bool:
        """Prueft ob ein lokaler Provider aktiv ist (vLLM / Ollama)."""
        return settings.llm_provider in (LLMProvider.VLLM, LLMProvider.OLLAMA)

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

            # Berechne Abweichung vom Neutralpunkt (50)
            deviation = abs(value - 50)

            if deviation < 10:
                # Innerhalb des toten Bereichs: kein Steering
                intensities[emotion] = 0.0
                continue

            # Sigmoid-Skalierung: sanfter Anstieg, maximale Intensitaet bei Extremwerten
            # Formel: alpha = max_alpha * sigmoid((deviation - threshold) / steepness)
            max_alpha = 0.5
            threshold = 15.0
            steepness = 10.0

            x = (deviation - threshold) / steepness
            sigmoid = 1.0 / (1.0 + math.exp(-x))
            alpha = max_alpha * sigmoid

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

    def get_steering_payload(self, current_emotions: Dict[str, int]) -> Dict[str, Any]:
        """
        Generiert das Steering-Payload fuer das LLM-Backend.

        Bei lokalen Modellen: Erzeugt vLLM-kompatibles Activation Steering Payload.
        Bei Cloud-Modellen: Gibt leeres Dict zurueck (Steering via Prompt).

        Args:
            current_emotions: Die aktuellen 7 emotionalen Dimensionen.

        Returns:
            Payload-Dict fuer extra_body oder leeres Dict.
        """
        if not settings.enable_steering:
            return {}

        # Cloud-Modelle: Kein Vektor-Steering, nur Prompt-basiert
        if not self.is_local_provider():
            return {}

        intensities = self.compute_emotion_intensity(current_emotions)
        active_vectors = []

        for emotion, alpha in intensities.items():
            if abs(alpha) < 0.01:
                continue

            sv = self.vectors.get(emotion)
            if sv is None:
                continue

            active_vectors.append({
                "name": sv.name,
                "vector": sv.vector_data if not (HAS_NUMPY and isinstance(sv.vector_data, np.ndarray)) else sv.vector_data.tolist(),
                "strength": abs(alpha),
                "direction": "positive" if alpha > 0 else "negative",
                "layer_range": [sv.layer_start, sv.layer_end],
                "emotion_value": current_emotions.get(emotion, 50)
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

        save_path = self.vectors_dir / f"{name}.json"
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(sv.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[SteeringManager] Fehler beim Speichern von {name}: {e}")

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
