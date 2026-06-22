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


if __name__ == "__main__":
    test_low_sadness_and_frustration_are_not_anti_steered()
    test_charged_composite_is_capped()
    print("OK: steering manager policy")
