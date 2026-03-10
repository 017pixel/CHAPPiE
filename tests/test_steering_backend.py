"""Unit-Tests fuer die echte Activation-Steering-Planung."""

import os
import sys

import torch

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from config.config import LLMProvider, settings  # noqa: E402
from brain.agents.steering_manager import SteeringManager  # noqa: E402
from brain.steering_backend import LocalSteeringEngine, add_vector_to_inputs, add_vector_to_output, build_activation_plan, build_style_instruction, extract_steering_payload  # noqa: E402


def test_extract_steering_payload_supports_extra_body_wrapper():
    payload = extract_steering_payload({
        "chat_template_kwargs": {"enable_thinking": False},
        "extra_body": {"steering": {"enabled": True, "vectors": []}},
    })
    assert payload["steering"]["enabled"] is True
    assert payload["chat_template_kwargs"]["enable_thinking"] is False


def test_build_activation_plan_combines_sign_and_strength():
    def resolver(_item, start, end):
        return {layer: torch.tensor([1.0, -1.0]) for layer in range(start, end + 1)}

    payload = {
        "steering": {
            "vectors": [
                {"layer_range": [2, 3], "strength": 0.5, "direction": "positive"},
                {"layer_range": [3, 4], "strength": 0.25, "direction": "negative"},
            ]
        }
    }
    plan = build_activation_plan(payload, resolver)
    assert torch.allclose(plan[2], torch.tensor([0.5, -0.5]))
    assert torch.allclose(plan[3], torch.tensor([0.25, -0.25]))
    assert torch.allclose(plan[4], torch.tensor([-0.25, 0.25]))


def test_add_vector_to_output_updates_first_tuple_tensor_only():
    hidden = torch.zeros(1, 2, 3)
    outputs = (hidden, "meta")
    updated = add_vector_to_output(outputs, torch.tensor([1.0, 2.0, 3.0]))
    assert updated[1] == "meta"
    assert torch.allclose(updated[0][0, 0], torch.tensor([1.0, 2.0, 3.0]))


def test_add_vector_to_inputs_updates_first_tuple_tensor_only():
    hidden = torch.zeros(1, 2, 3)
    inputs = (hidden, "meta")
    updated = add_vector_to_inputs(inputs, torch.tensor([1.0, 2.0, 3.0]))
    assert updated[1] == "meta"
    assert torch.allclose(updated[0][0, 0], torch.tensor([1.0, 2.0, 3.0]))


def test_build_activation_plan_soft_caps_many_overlapping_vectors():
    def resolver(_item, start, end):
        return {layer: torch.tensor([3.0, 4.0]) for layer in range(start, end + 1)}

    payload = {
        "steering": {
            "vectors": [
                {"layer_range": [1, 1], "strength": 1.0, "direction": "positive"},
                {"layer_range": [1, 1], "strength": 1.0, "direction": "positive"},
                {"layer_range": [1, 1], "strength": 1.0, "direction": "positive"},
            ]
        }
    }
    plan = build_activation_plan(payload, resolver)
    assert float(plan[1].norm().item()) > 0.0
    assert float(plan[1].norm().item()) <= 2.4001


def test_build_style_instruction_mentions_negative_guardrails():
    instruction = build_style_instruction({
        "steering": {
            "vectors": [
                {"name": "crashout", "strength": 1.0, "surface_effect": "kurz angebunden, aggressiv, konfrontativ"}
            ]
        }
    })
    assert instruction is not None
    assert "ohne Beleidigungen" in instruction


def test_build_style_instruction_uses_all_seven_vitals_from_payload_metadata():
    instruction = build_style_instruction({
        "steering": {
            "emotion_state": {
                "happiness": 82,
                "sadness": 27,
                "frustration": 18,
                "trust": 79,
                "curiosity": 67,
                "motivation": 64,
                "energy": 71,
            },
            "emotion_intensities": {
                "happiness": 0.9,
                "sadness": -0.6,
                "frustration": -0.55,
                "trust": 0.72,
                "curiosity": 0.35,
                "motivation": 0.42,
                "energy": 0.58,
            },
            "vectors": [],
        }
    })
    assert instruction is not None
    for label in ["Freude", "Traurigkeit", "Frustration", "Vertrauen", "Neugier", "Motivation", "Energie"]:
        assert label in instruction


def test_steering_manager_payload_keeps_all_seven_vitals_and_base_vectors():
    provider_before = settings.llm_provider
    settings.llm_provider = LLMProvider.VLLM
    try:
        manager = SteeringManager()
        payload = manager.get_steering_payload({
            "happiness": 82,
            "sadness": 26,
            "frustration": 74,
            "trust": 77,
            "curiosity": 69,
            "motivation": 72,
            "energy": 75,
        }, force=True)
    finally:
        settings.llm_provider = provider_before

    steering = payload["steering"]
    assert set(steering["emotion_state"].keys()) == {"happiness", "sadness", "frustration", "trust", "curiosity", "motivation", "energy"}
    assert set(steering["emotion_intensities"].keys()) == {"happiness", "sadness", "frustration", "trust", "curiosity", "motivation", "energy"}
    base_names = {item["name"] for item in steering["base_vectors"]}
    assert base_names == {"happiness", "sadness", "frustration", "trust", "curiosity", "motivation", "energy"}


def test_local_steering_engine_uses_trust_remote_code_for_qwen35():
    engine = LocalSteeringEngine.__new__(LocalSteeringEngine)
    engine.model_name = "Qwen/Qwen3.5-9B"
    assert engine._build_loader_kwargs() == {"trust_remote_code": True}


def test_local_steering_engine_keeps_default_loader_kwargs_for_non_qwen35():
    engine = LocalSteeringEngine.__new__(LocalSteeringEngine)
    engine.model_name = "Qwen/Qwen3-4B-Instruct-2507"
    assert engine._build_loader_kwargs() == {}


if __name__ == "__main__":
    test_extract_steering_payload_supports_extra_body_wrapper()
    test_build_activation_plan_combines_sign_and_strength()
    test_add_vector_to_output_updates_first_tuple_tensor_only()
    test_add_vector_to_inputs_updates_first_tuple_tensor_only()
    test_build_activation_plan_soft_caps_many_overlapping_vectors()
    test_build_style_instruction_mentions_negative_guardrails()
    test_build_style_instruction_uses_all_seven_vitals_from_payload_metadata()
    test_steering_manager_payload_keeps_all_seven_vitals_and_base_vectors()
    test_local_steering_engine_uses_trust_remote_code_for_qwen35()
    test_local_steering_engine_keeps_default_loader_kwargs_for_non_qwen35()
    print("OK: steering backend")