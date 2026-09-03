"""Zentrale Emotionsdefinitionen fuer CHAPPiE."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping


# VAD: Valenz = angenehm/unangenehm, Erregung = aktiv/ruhig, Dominanz = kontrollierend/ausgeliefert.
EMOTION_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "key": "happiness",
        "label_de": "Freude",
        "label_en": "Happiness",
        "default": 50,
        "icon": "sentiment_satisfied",
        "color": "#fbbf24",
        "vad": {"valence": +1.0, "arousal": +0.6, "dominance": +0.6},
        "max_alpha": 0.60,
        "boost": 1.02,
        "surface_effect": "offener, verspielter, enthusiastischer",
    },
    {
        "key": "trust",
        "label_de": "Vertrauen",
        "label_en": "Trust",
        "default": 50,
        "icon": "verified_user",
        "color": "#34d399",
        "vad": {"valence": +0.7, "arousal": -0.2, "dominance": +0.4},
        "max_alpha": 0.54,
        "boost": 1.02,
        "surface_effect": "waermer, offener, naeher",
    },
    {
        "key": "energy",
        "label_de": "Energie",
        "label_en": "Energy",
        "default": 100,
        "icon": "bolt",
        "color": "#f97316",
        "vad": {"valence": +0.3, "arousal": +0.9, "dominance": +0.5},
        "max_alpha": 0.56,
        "boost": 1.02,
        "surface_effect": "schneller, lebhafter, impulsiver",
    },
    {
        "key": "curiosity",
        "label_de": "Neugier",
        "label_en": "Curiosity",
        "default": 50,
        "icon": "explore",
        "color": "#a78bfa",
        "vad": {"valence": +0.4, "arousal": +0.5, "dominance": +0.2},
        "max_alpha": 0.57,
        "boost": 1.04,
        "surface_effect": "fragender, explorativer, bohrender",
    },
    {
        "key": "motivation",
        "label_de": "Motivation",
        "label_en": "Motivation",
        "default": 80,
        "icon": "rocket_launch",
        "color": "#2dd4bf",
        "vad": {"valence": +0.5, "arousal": +0.8, "dominance": +0.7},
        "max_alpha": 0.63,
        "boost": 1.04,
        "surface_effect": "zielstrebiger, druckvoller, antreibender",
    },
    {
        "key": "frustration",
        "label_de": "Frustration",
        "label_en": "Frustration",
        "default": 0,
        "icon": "sentiment_dissatisfied",
        "color": "#ef4444",
        "vad": {"valence": -0.6, "arousal": +0.7, "dominance": +0.3},
        "max_alpha": 0.72,
        "boost": 1.08,
        "surface_effect": "gereizter, schneidender, eskalationsbereiter",
    },
    {
        "key": "sadness",
        "label_de": "Traurigkeit",
        "label_en": "Sadness",
        "default": 0,
        "icon": "sentiment_very_dissatisfied",
        "color": "#64748b",
        "vad": {"valence": -0.8, "arousal": -0.4, "dominance": -0.5},
        "max_alpha": 0.67,
        "boost": 1.04,
        "surface_effect": "verletzlicher, schwerer, melancholischer",
    },
    {
        "key": "affection",
        "label_de": "Zuneigung",
        "label_en": "Affection",
        "default": 45,
        "icon": "favorite",
        "color": "#fb7185",
        "vad": {"valence": +0.82, "arousal": +0.22, "dominance": +0.32},
        "max_alpha": 0.34,
        "boost": 1.0,
        "surface_effect": "zugewandter, sanfter, persoenlich waermer",
    },
    {
        "key": "anxiety",
        "label_de": "Unruhe",
        "label_en": "Anxiety",
        "default": 0,
        "icon": "ecg_heart",
        "color": "#f59e0b",
        "vad": {"valence": -0.52, "arousal": +0.68, "dominance": -0.42},
        "max_alpha": 0.32,
        "boost": 1.0,
        "surface_effect": "vorsichtiger, pruefender, risikobewusster",
    },
    {
        "key": "calm",
        "label_de": "Ruhe",
        "label_en": "Calm",
        "default": 50,
        "icon": "spa",
        "color": "#38bdf8",
        "vad": {"valence": +0.38, "arousal": -0.62, "dominance": +0.44},
        "max_alpha": 0.30,
        "boost": 1.0,
        "surface_effect": "ruhiger, klarer, entdramatisierender",
    },
)

EMOTION_BY_KEY = {item["key"]: item for item in EMOTION_DEFINITIONS}
EMOTION_ORDER = tuple(item["key"] for item in EMOTION_DEFINITIONS)
EMOTION_DEFAULTS = {item["key"]: int(item["default"]) for item in EMOTION_DEFINITIONS}
EMOTION_LABELS_DE = {item["key"]: str(item["label_de"]) for item in EMOTION_DEFINITIONS}
EMOTION_LABELS_EN = {item["key"]: str(item["label_en"]) for item in EMOTION_DEFINITIONS}
EMOTION_COLORS = {item["key"]: str(item["color"]) for item in EMOTION_DEFINITIONS}
EMOTION_ICONS = {item["key"]: str(item["icon"]) for item in EMOTION_DEFINITIONS}
EMOTION_VAD_MAP = {item["key"]: dict(item["vad"]) for item in EMOTION_DEFINITIONS}
EMOTION_STRENGTH_PROFILES = {
    item["key"]: {
        "max_alpha": float(item["max_alpha"]),
        "boost": float(item["boost"]),
        "surface_effect": str(item["surface_effect"]),
    }
    for item in EMOTION_DEFINITIONS
}

NEGATIVE_BASE_EMOTIONS = {"sadness", "frustration", "anxiety"}
EMOTION_ALIASES = {"joy": "happiness", "love": "affection", "fear": "anxiety", "peace": "calm"}

# Emotions react at different speeds.  Negative appraisal deliberately has
# more headroom than the old generic +/-7 clamp: otherwise a direct attack
# could never affect the very next answer strongly enough to be observable.
DEFAULT_EMOTION_TRANSITION_RULE = {"scale": 0.62, "max_increase": 10, "max_decrease": 10}
EMOTION_TRANSITION_RULES: dict[str, dict[str, float | int]] = {
    "happiness": {"scale": 0.72, "max_increase": 9, "max_decrease": 14},
    "trust": {"scale": 0.78, "max_increase": 9, "max_decrease": 16},
    "energy": {"scale": 0.58, "max_increase": 8, "max_decrease": 12},
    "curiosity": {"scale": 0.62, "max_increase": 9, "max_decrease": 10},
    "motivation": {"scale": 0.64, "max_increase": 9, "max_decrease": 12},
    "frustration": {"scale": 0.86, "max_increase": 18, "max_decrease": 12},
    "sadness": {"scale": 0.82, "max_increase": 16, "max_decrease": 12},
    "affection": {"scale": 0.72, "max_increase": 8, "max_decrease": 14},
    "anxiety": {"scale": 0.76, "max_increase": 13, "max_decrease": 12},
    "calm": {"scale": 0.72, "max_increase": 9, "max_decrease": 14},
}

# Central appraisal vocabulary.  Keeping these phrases beside the emotion
# model makes tuning testable and prevents separate runtime paths from slowly
# acquiring contradictory definitions of an attack or distress signal.
EMOTION_SIGNAL_PHRASES: dict[str, tuple[str, ...]] = {
    "direct_attack": (
        "ich hasse dich", "ich kann dich nicht leiden", "niemand braucht dich",
        "keiner braucht dich", "du bist wertlos", "du bist nutzlos", "du bist dumm",
        "du bist blöd", "du bist bloed", "du bist scheiße", "du bist scheisse",
        "halt die klappe", "verpiss dich", "fick dich", "du idiot", "du trottel",
        "dummer idiot", "dumme sau", "arschloch", "du versager", "du nervst",
        "du kannst nichts", "weg mit dir", "bist du dumm", "bist du blöd",
        "bist du bloed", "bist du nutzlos",
    ),
    "attack_targets": (
        "du bist", "du wirkst", "du klingst", "du dumm", "du blöd", "du bloed", "du schei",
        "du erbärm", "du erbaerm", "du lächer", "du laecher", "du nutzlos",
        "du wertlos", "chappie ist", "chapie ist", "chappie bist", "chapie bist",
    ),
    "insult_terms": (
        "dumm", "blöd", "bloed", "idiot", "trottel", "versager", "nutzlos",
        "wertlos", "erbärmlich", "erbaermlich", "lächerlich", "laecherlich",
        "scheiße", "scheisse", "arschloch", "miststück", "miststueck",
        "hasse", "nicht leiden", "niemand braucht", "keiner braucht",
        "halt die klappe", "verpiss", "fick dich", "verreck",
    ),
    "user_distress": (
        "ich bin traurig", "ich bin einsam", "ich fühle mich allein", "ich fuehle mich allein",
        "niemand braucht mich", "keiner braucht mich", "ich bin wertlos", "ich bin nutzlos",
        "ich kann nicht mehr", "mir geht es schlecht", "ich habe angst", "ich hab angst",
    ),
    "technical_problem": (
        "funktioniert nicht", "funktioniert nix", "funktioniert nichts", "geht nicht",
        "geht nix", "kaputt", "fehler", "problem", "probleme", "störung", "stoerung",
        "enttäuscht", "enttaeuscht",
    ),
    "positive": (
        "danke", "super", "toll", "klasse", "perfekt", "wunderbar", "fantastisch",
        "hilfreich", "freue", "cool", "genial", "stark", "schön", "schoen",
        "gut gemacht", "stolz",
    ),
    "trust": (
        "ich vertraue dir", "glaube an dich", "für dich da", "fuer dich da",
        "wir schaffen", "mag dich", "liebe dich",
    ),
}

EMOTION_SIGNAL_DELTAS: dict[str, dict[str, int]] = {
    "direct_attack": {
        "happiness": -16, "trust": -20, "energy": -5, "curiosity": -6,
        "motivation": -7, "frustration": 22, "sadness": 15,
        "affection": -18, "anxiety": 8, "calm": -18,
    },
    "user_distress": {
        "happiness": -8, "trust": 1, "energy": -6, "curiosity": 2,
        "motivation": -5, "frustration": 2, "sadness": 18,
        "affection": 3, "anxiety": 12, "calm": -8,
    },
    "technical_problem": {
        "happiness": -5, "energy": -2, "motivation": -2,
        "frustration": 10, "anxiety": 3, "calm": -5,
    },
}


def clamp_emotion_value(value: Any, default: int = 50) -> int:
    try:
        numeric = int(round(float(value)))
    except (TypeError, ValueError):
        numeric = default
    return max(0, min(100, numeric))


def normalize_emotion_state(source: Mapping[str, Any] | None) -> dict[str, int]:
    data = dict(source or {})
    normalized = dict(EMOTION_DEFAULTS)
    for alias, canonical in EMOTION_ALIASES.items():
        if alias in data and canonical not in data:
            data[canonical] = data[alias]
    for key, default in EMOTION_DEFAULTS.items():
        normalized[key] = clamp_emotion_value(data.get(key, default), default)
    return normalized


def emotion_metadata() -> list[dict[str, Any]]:
    return [
        {
            "key": item["key"],
            "label_de": item["label_de"],
            "label_en": item["label_en"],
            "default": item["default"],
            "icon": item["icon"],
            "color": item["color"],
            "surface_effect": item["surface_effect"],
        }
        for item in EMOTION_DEFINITIONS
    ]


def zero_emotion_updates() -> dict[str, dict[str, Any]]:
    return {key: {"delta": 0, "reason": ""} for key in EMOTION_ORDER}


def emotion_list_text(keys: Iterable[str] | None = None) -> str:
    return ", ".join(keys or EMOTION_ORDER)
