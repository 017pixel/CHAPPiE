"""Offline-Vertraege fuer den reinen vLLM-Vector-Steering-Pfad."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from brain.steering_manager import SteeringManager  # noqa: E402
from config.config import LLMProvider  # noqa: E402
from config.emotions import EMOTION_DEFAULTS  # noqa: E402
from config.prompts import build_system_prompt, format_life_continuity_context  # noqa: E402
from web_infrastructure.formatting import RuntimeFormattingMixin  # noqa: E402


def test_local_system_prompt_has_no_emotion_or_personality_directives() -> None:
    prompt = build_system_prompt(
        happiness=99,
        sadness=91,
        frustration=88,
        include_emotion_status=False,
        use_chain_of_thought=False,
    )
    assert "AKTUELLER EMOTIONALER STATUS" not in prompt
    assert "IDENTITÄT" not in prompt
    assert "simulierten inneren" not in prompt
    assert "keine Gefühle" not in prompt


def test_local_response_plan_is_not_appended_to_prompt() -> None:
    runtime = RuntimeFormattingMixin()
    prompt = runtime._append_response_style_instruction(
        "Du bist CHAPPiE.",
        response_plan=None,
    )
    assert "AKTUELLER ANTWORTPLAN" not in prompt
    assert "Verhaltensvorgabe" not in prompt


def test_local_sampling_is_independent_of_emotion_state() -> None:
    quiet = RuntimeFormattingMixin._get_emotion_adjusted_config(
        {"frustration": 0, "sadness": 0, "energy": 100},
        apply_emotion_adjustments=False,
    )
    extreme = RuntimeFormattingMixin._get_emotion_adjusted_config(
        {"frustration": 100, "sadness": 100, "energy": 0},
        apply_emotion_adjustments=False,
    )
    assert quiet == extreme
    assert quiet["emotion_adjustments_enabled"] is False


def test_life_prompt_filters_emotion_derived_workspace_guidance() -> None:
    context = format_life_continuity_context(
        {
            "clock": {"phase_label": "Tag 4, Abend"},
            "current_activity": "goal_pursuit",
            "active_goal": {"title": "Memory verbessern", "progress": 0.4},
            "homeostasis": {
                "emotion_snapshot": {"sadness": 99},
                "guidance": "Antworte traurig.",
            },
        }
    )
    assert "Tag 4, Abend" in context
    assert "Memory verbessern" in context
    assert "sadness" not in context
    assert "traurig" not in context
    assert "emotional abgestimmt" not in context


def test_payload_keeps_full_state_but_activates_only_coherent_subset() -> None:
    manager = SteeringManager()
    payload = manager.get_steering_payload(
        {
            "happiness": 95,
            "trust": 90,
            "energy": 95,
            "curiosity": 95,
            "motivation": 95,
            "frustration": 80,
            "sadness": 80,
            "affection": 90,
            "anxiety": 80,
            "calm": 80,
        },
        force=True,
        provider=LLMProvider.VLLM,
        model="Qwen/Qwen3.5-4B",
    )["steering"]
    assert len(payload["emotion_state"]) == 10
    assert len(payload["selected_base_vectors"]) <= 3
    assert len(payload["composite_vectors"]) <= 1
    assert any(vector["name"] == "natural_presence" for vector in payload["vectors"])


def test_default_state_does_not_fake_positive_emotion_steering() -> None:
    payload = SteeringManager().get_steering_payload(
        dict(EMOTION_DEFAULTS),
        force=True,
        provider=LLMProvider.VLLM,
        model="Qwen/Qwen3.5-4B",
        user_input="Warum ist der Himmel blau?",
    )["steering"]
    assert payload["dominant_emotion"] == "calm"
    assert {item["name"] for item in payload["vectors"]} == {"calm"}
    assert payload["permanent_vectors"] == []


if __name__ == "__main__":
    test_local_system_prompt_has_no_emotion_or_personality_directives()
    test_local_response_plan_is_not_appended_to_prompt()
    test_local_sampling_is_independent_of_emotion_state()
    test_life_prompt_filters_emotion_derived_workspace_guidance()
    test_payload_keeps_full_state_but_activates_only_coherent_subset()
    test_default_state_does_not_fake_positive_emotion_steering()
    print("OK: vector-only emotion path")
