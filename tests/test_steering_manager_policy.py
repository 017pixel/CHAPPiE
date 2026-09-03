"""Torch-freie Tests fuer die Steering-Manager-Policy."""

import importlib.util
import sys
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _load_steering_manager_module():
    path = PROJECT_ROOT / "brain" / "agents" / "steering_manager.py"
    spec = importlib.util.spec_from_file_location("steering_manager_policy_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_low_sadness_and_frustration_are_not_anti_steered():
    module = _load_steering_manager_module()
    manager = module.SteeringManager()
    payload = manager.get_steering_payload({
        "happiness": 86,
        "trust": 55,
        "energy": 88,
        "curiosity": 77,
        "motivation": 90,
        "frustration": 10,
        "sadness": 0,
    }, force=True)

    steering = payload["steering"]
    names = {item["name"] for item in steering["vectors"]}
    assert "sadness" not in names
    assert "frustration" not in names
    assert steering["dominant_emotion"] != "sadness"
    assert steering["dominant_strength"] <= module.BASE_VECTOR_STRENGTH_CAP


def test_charged_composite_is_capped():
    module = _load_steering_manager_module()
    manager = module.SteeringManager()
    intensities = manager.compute_emotion_intensity({
        "happiness": 86,
        "trust": 55,
        "energy": 88,
        "curiosity": 77,
        "motivation": 90,
        "frustration": 10,
        "sadness": 0,
    })
    modes = manager._build_composite_modes({
        "happiness": 86,
        "trust": 55,
        "energy": 88,
        "curiosity": 77,
        "motivation": 90,
        "frustration": 10,
        "sadness": 0,
    }, intensities)
    charged = next(item for item in modes if item["name"] == "charged")
    assert charged["strength"] <= module.CHARGED_COMPOSITE_STRENGTH_CAP


def test_new_emotion_vectors_are_conservative():
    module = _load_steering_manager_module()
    manager = module.SteeringManager()
    emotions = {
        "happiness": 50,
        "trust": 70,
        "energy": 55,
        "curiosity": 50,
        "motivation": 55,
        "frustration": 0,
        "sadness": 0,
        "affection": 85,
        "anxiety": 75,
        "calm": 82,
    }
    payload = manager.get_steering_payload(emotions, force=True)
    vectors = {
        item["name"]: item
        for item in payload["steering"]["base_vectors"]
        if item.get("source") == "base"
    }

    assert {"affection", "anxiety", "calm"}.issubset(vectors)
    assert vectors["affection"]["strength"] <= 0.35
    assert vectors["anxiety"]["strength"] <= 0.35
    assert vectors["calm"]["strength"] <= 0.35


def test_configured_defaults_are_neutral_and_attack_is_immediate():
    module = _load_steering_manager_module()
    manager = module.SteeringManager()
    defaults = {
        "happiness": 50, "trust": 50, "energy": 100, "curiosity": 50,
        "motivation": 80, "frustration": 0, "sadness": 0,
        "affection": 45, "anxiety": 0, "calm": 50,
    }
    neutral = manager.get_steering_payload(defaults, force=True)["steering"]
    assert neutral["selected_base_vectors"] == []
    assert neutral["dominant_emotion"] == "neutral"

    after_attack = dict(defaults)
    after_attack.update({"happiness": 37, "trust": 34, "frustration": 18, "sadness": 13, "calm": 36})
    recent = {"happiness": -13, "trust": -16, "frustration": 18, "sadness": 13, "calm": -14}
    attacked = manager.get_steering_payload(after_attack, force=True, recent_changes=recent)["steering"]
    selected = {item["name"] for item in attacked["selected_base_vectors"]}
    composites = {item["name"] for item in attacked["composite_vectors"]}
    assert "frustration" in selected
    assert "sadness" in selected
    assert "angered" in composites
    assert attacked["dominant_emotion"] in {"frustration", "sadness", "angered"}


if __name__ == "__main__":
    test_low_sadness_and_frustration_are_not_anti_steered()
    test_charged_composite_is_capped()
    test_new_emotion_vectors_are_conservative()
    test_configured_defaults_are_neutral_and_attack_is_immediate()
    print("OK: steering manager policy")
