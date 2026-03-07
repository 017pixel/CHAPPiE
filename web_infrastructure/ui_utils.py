from __future__ import annotations

from typing import Mapping, Sequence, TypeVar

T = TypeVar("T")

UI_VERSION = "13.4"

EMOTION_DEFAULTS = {
    "happiness": 50,
    "trust": 50,
    "energy": 100,
    "curiosity": 50,
    "motivation": 80,
    "frustration": 0,
    "sadness": 0,
}

EMOTION_DISPLAY_ORDER = (
    "happiness",
    "trust",
    "energy",
    "curiosity",
    "motivation",
    "frustration",
    "sadness",
)

EMOTION_LABELS = {
    "happiness": "Freude",
    "trust": "Vertrauen",
    "energy": "Energie",
    "curiosity": "Neugier",
    "motivation": "Motivation",
    "frustration": "Frustration",
    "sadness": "Traurigkeit",
}

EMOTION_COLORS = {
    "happiness": "#81c784",
    "trust": "#00a3cc",
    "energy": "#f5f5f5",
    "curiosity": "#ff6b9d",
    "motivation": "#a0a0a0",
    "frustration": "#ff8a65",
    "sadness": "#7986cb",
}


def _clamp_emotion_value(value, default: int) -> int:
    try:
        numeric = int(round(float(value)))
    except (TypeError, ValueError):
        numeric = default
    return max(0, min(100, numeric))


def normalize_emotions(emotions: Mapping[str, int] | None) -> dict[str, int]:
    source = dict(emotions or {})
    normalized = dict(EMOTION_DEFAULTS)
    normalized["happiness"] = _clamp_emotion_value(
        source.get("happiness", source.get("joy", EMOTION_DEFAULTS["happiness"])),
        EMOTION_DEFAULTS["happiness"],
    )
    for key, default in EMOTION_DEFAULTS.items():
        if key == "happiness":
            continue
        normalized[key] = _clamp_emotion_value(source.get(key, default), default)
    return normalized


def chunk_items(items: Sequence[T], chunk_size: int) -> list[list[T]]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    return [list(items[index:index + chunk_size]) for index in range(0, len(items), chunk_size)]