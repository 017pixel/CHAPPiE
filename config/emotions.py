"""Zentrale Emotionsdefinitionen fuer CHAPPiE."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping


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
