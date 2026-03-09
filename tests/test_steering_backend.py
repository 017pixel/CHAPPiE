"""Unit-Tests fuer die echte Activation-Steering-Planung."""

import os
import sys

import torch

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from brain.steering_backend import add_vector_to_inputs, add_vector_to_output, build_activation_plan, build_style_instruction, extract_steering_payload  # noqa: E402


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


if __name__ == "__main__":
    test_extract_steering_payload_supports_extra_body_wrapper()
    test_build_activation_plan_combines_sign_and_strength()
    test_add_vector_to_output_updates_first_tuple_tensor_only()
    test_add_vector_to_inputs_updates_first_tuple_tensor_only()
    test_build_activation_plan_soft_caps_many_overlapping_vectors()
    test_build_style_instruction_mentions_negative_guardrails()
    print("OK: steering backend")