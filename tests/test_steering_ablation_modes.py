"""OFF and ablations must gate actual interventions, including stale payloads."""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import torch
from brain.steering_backend import LocalSteeringEngine
from brain.steering_manager import SteeringManager
from config.config import LLMProvider
from config.emotions import EMOTION_DEFAULTS


def test_manager_modes():
    manager = SteeringManager()
    state = {**EMOTION_DEFAULTS, "frustration": 85, "calm": 10}
    for mode in ("off", "activation", "sequence", "combined"):
        p = manager.get_steering_payload(
            state,
            force=True,
            provider=LLMProvider.VLLM,
            model="Qwen/Qwen3.5-4B",
            user_input="Du nervst mich.",
            steering_mode=mode,
        )["steering"]
        assert bool(p["vectors"]) == (mode in ("activation", "combined"))
        assert bool(p.get("sequences")) == (mode in ("sequence", "combined"))
    p = manager.get_steering_payload(state, force=True, steering_enabled=False)[
        "steering"
    ]
    assert not p["enabled"] and not p["vectors"] and not p["sequences"]


def test_backend_off_ignores_vectors():
    engine = LocalSteeringEngine.__new__(LocalSteeringEngine)
    engine.model_name = "test"
    engine.layers = [torch.nn.Identity()]
    engine.device = torch.device("cpu")
    engine.dtype = torch.float32
    engine.last_steering_report = {}

    def forbidden(*args, **kwargs):
        raise AssertionError("OFF must not resolve a vector")

    engine.resolver = SimpleNamespace(resolve=forbidden)
    for extra in ({"enabled": False}, {"mode": "off"}, {"mode": "sequence"}):
        p = {
            "steering": {
                "vectors": [
                    {"name": "x", "strength": 1, "layer_range": [0, 0], "vector": {}}
                ],
                **extra,
            }
        }
        with engine._apply_activation_plan(p) as processors:
            assert not processors
            assert not engine.layers[0]._forward_pre_hooks
        assert engine.last_steering_report["hook_count"] == 0
        assert not engine.last_steering_report["verified_active"]


if __name__ == "__main__":
    test_manager_modes()
    test_backend_off_ignores_vectors()
    print("Ablation contracts passed")
