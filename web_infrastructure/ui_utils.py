from __future__ import annotations

from typing import Any, Mapping, Sequence, TypeVar

T = TypeVar("T")

UI_VERSION = "13.6"

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


def clamp_numeric_value(value, minimum, maximum, default=None):
    """Klemmt numerische UI-Werte robust in einen erlaubten Bereich."""
    fallback = minimum if default is None else default
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = float(fallback)

    minimum_value = float(minimum)
    maximum_value = float(maximum)
    if minimum_value > maximum_value:
        minimum_value, maximum_value = maximum_value, minimum_value

    return max(minimum_value, min(maximum_value, numeric))


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


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def split_steering_vectors(report: Mapping[str, Any] | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    source = dict(report or {})
    base_vectors = [dict(item) for item in source.get("base_vectors", []) if isinstance(item, Mapping)]
    composite_vectors = [dict(item) for item in source.get("composite_vectors", []) if isinstance(item, Mapping)]

    if base_vectors or composite_vectors:
        return base_vectors, composite_vectors

    active_vectors = [dict(item) for item in source.get("active_vectors", []) if isinstance(item, Mapping)]
    base_vectors = [item for item in active_vectors if item.get("source", "base") == "base"]
    composite_vectors = [item for item in active_vectors if item.get("source", "base") != "base"]
    return base_vectors, composite_vectors


def build_steering_state_rows(report: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    source = dict(report or {})
    emotion_state = normalize_emotions(source.get("emotion_state", {}))
    emotion_intensities = source.get("emotion_intensities", {}) if isinstance(source.get("emotion_intensities", {}), Mapping) else {}
    legacy_intensities = source.get("intensities", {}) if isinstance(source.get("intensities", {}), Mapping) else {}
    base_vectors, _ = split_steering_vectors(source)
    base_by_name = {str(item.get("name") or ""): item for item in base_vectors}

    rows = []
    for emotion_key in EMOTION_DISPLAY_ORDER:
        vector = base_by_name.get(emotion_key, {})
        intensity = _safe_float(emotion_intensities.get(emotion_key, legacy_intensities.get(emotion_key, 0.0)), default=0.0)
        direction = str(vector.get("direction") or "").strip().lower()
        if direction not in {"positive", "negative"}:
            if intensity > 0.01:
                direction = "positive"
            elif intensity < -0.01:
                direction = "negative"
            else:
                direction = "neutral"

        layer_range = vector.get("layer_range")
        if isinstance(layer_range, Sequence) and len(layer_range) >= 2:
            layer_label = f"{layer_range[0]}-{layer_range[1]}"
        else:
            layer_label = "-"

        rows.append({
            "emotion": EMOTION_LABELS.get(emotion_key, emotion_key),
            "wert": int(emotion_state.get(emotion_key, EMOTION_DEFAULTS[emotion_key])),
            "alpha": round(intensity, 3),
            "richtung": {
                "positive": "anhebend",
                "negative": "daempfend",
                "neutral": "neutral",
            }.get(direction, direction),
            "basisvektor_aktiv": bool(vector),
            "layer_range": layer_label,
            "wirkung": vector.get("surface_effect", ""),
        })
    return rows