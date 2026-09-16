"""Bounded state and recent-delta coefficients; no generated language targets."""
import math
from config.emotions import EMOTION_DEFAULTS, EMOTION_ORDER
from config.config import get_steering_runtime_config


def mix_emotions(state, recent_changes=None):
    config = get_steering_runtime_config()
    changes = recent_changes or {}
    candidates = []
    for name in EMOTION_ORDER:
        value = float(state.get(name, EMOTION_DEFAULTS[name]))
        change = changes.get(name, {})
        delta = float(change.get("applied_delta", change.get("change", 0)) if isinstance(change, dict) else change)
        if not math.isfinite(value) or not math.isfinite(delta):
            raise ValueError("Emotion state and delta must be finite")
        baseline = EMOTION_DEFAULTS[name]
        state_component = (min(100, max(0, value)) - baseline) / max(baseline, 100-baseline, 1)
        acute_component = max(-1, min(1, delta / 100)) * config["acute_delta_weight"]
        coefficient = max(-1, min(1, state_component + acute_component))
        if abs(coefficient) < config["minimum_mixer_coefficient"]:
            continue
        candidates.append({"name": name, "coefficient": coefficient,
                           "state_component": state_component, "acute_delta_component": acute_component,
                           "emotion_value": value, "source": "acute_delta" if acute_component else "persistent"})
    return sorted(candidates, key=lambda item: abs(item["coefficient"]), reverse=True)[:config["measured_max_base_vectors"]]
