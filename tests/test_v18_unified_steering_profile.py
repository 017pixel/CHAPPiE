"""V18 Unified Steering Profile: ein Profil, ein Budget, stabile Antworten (offline)."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from brain.steering_manager import SteeringManager  # noqa: E402
from config.config import STEERING_RUNTIME_CONFIG, settings  # noqa: E402
from config.emotions import EMOTION_DEFAULTS  # noqa: E402
from web_infrastructure.formatting import RuntimeFormattingMixin  # noqa: E402
from web_infrastructure.generation import (  # noqa: E402
    RuntimeGenerationMixin,
    calculate_generation_timing,
)


def test_answer_budget_is_1200_everywhere() -> None:
    assert settings.max_tokens == 1200
    assert settings.chappie_answer_token_limit == 1200
    assert settings.chappie_thinking_token_limit == 800


def test_single_budget_top3_capped() -> None:
    assert STEERING_RUNTIME_CONFIG["max_base_vectors"] == 3
    assert STEERING_RUNTIME_CONFIG["max_composite_vectors"] == 1
    assert STEERING_RUNTIME_CONFIG["max_total_base_strength"] == 0.6
    manager = SteeringManager()
    emotions = dict(EMOTION_DEFAULTS)
    emotions.update({"sadness": 82, "frustration": 70, "anxiety": 65, "happiness": 20})
    for prompt in ("Wie geht es dir?", "Was bist du?", "Warum ist der Himmel blau?", "Wie geht es dir? Was bist du?"):
        steering = manager.get_steering_payload(emotions, force=True, user_input=prompt)["steering"]
        assert len(steering["selected_base_vectors"]) <= 3
        assert len(steering.get("composite_vectors", [])) <= 1
        total = sum(item["strength"] for item in steering["selected_base_vectors"])
        assert total <= 0.61


def test_no_neutral_mislabel_with_style_only() -> None:
    manager = SteeringManager()
    steering = manager.get_steering_payload(dict(EMOTION_DEFAULTS), force=True, user_input="Was bist du?")["steering"]
    assert steering["dominant_emotion"] == "identity-isoliert"
    assert steering["dominant_strength"] > 0


def test_no_frustration_budget_cut() -> None:
    calm = RuntimeFormattingMixin._get_emotion_adjusted_config(dict(EMOTION_DEFAULTS), apply_emotion_adjustments=False)
    stressed = RuntimeFormattingMixin._get_emotion_adjusted_config(
        {**EMOTION_DEFAULTS, "frustration": 90}, apply_emotion_adjustments=True,
    )
    assert stressed["max_tokens"] == calm["max_tokens"] == 1200


def test_self_report_keeps_memory_context() -> None:
    effective = RuntimeGenerationMixin._effective_context_requirements(
        "Was bist du?",
        {"need_soul_context": True, "need_user_context": True, "need_preferences": True,
         "need_short_term_memory": True, "need_long_term_memory": True},
    )
    assert all(effective.values())
    math_effective = RuntimeGenerationMixin._effective_context_requirements(
        "Was ist 12 plus 7?",
        {"need_soul_context": True, "need_user_context": True, "need_preferences": True,
         "need_short_term_memory": True, "need_long_term_memory": True},
    )
    assert not any(math_effective.values())


def test_timing_carries_finish_reason() -> None:
    timing = calculate_generation_timing(5000, answer_tokens=100, ttft_ms=500, finish_reason="length")
    assert timing["finish_reason"] == "length"
    assert timing["tokens_per_second"] == 20.0


def test_format_source_always_has_reason() -> None:
    from web_infrastructure.chappie_runtime import CHAPPiERuntime  # noqa

    class Probe(RuntimeFormattingMixin):
        def _single_local_chat_mode(self):
            return True

    result = Probe()._format_via_groq("Hallo Welt, das ist ein Test.")
    assert result["formatting_source"] == "local_forced"
    assert result["formatting_model"] == "local_regex"
    assert result["formatting_reason"] == "single_local_model"


def test_compact_cli_counts_words_not_events() -> None:
    import chappie_brain_cli as cli

    assert cli._count_words("Hallo Welt, wie geht es?") == 5
    assert cli._count_words("") == 0
    assert cli._count_words("  a  b   c ") == 3


def test_stm_stats_split() -> None:
    from memory.short_term_memory import ShortTermMemory

    stm = ShortTermMemory.__new__(ShortTermMemory)
    from memory.short_term_memory import ShortTermEntry

    stm.entries = [
        ShortTermEntry(id="1", content="a", category="user", importance="high",
                       created_at="2026-09-07T10:00:00+00:00", expires_at="2099-01-01T00:00:00+00:00",
                       migrated=False, retrieval_eligible=True),
        ShortTermEntry(id="2", content="b", category="chat", importance="low",
                       created_at="2026-09-07T10:00:00+00:00", expires_at="2099-01-01T00:00:00+00:00",
                       migrated=False, retrieval_eligible=False, quality_flag="unverified_source"),
        ShortTermEntry(id="3", content="c", category="user", importance="high",
                       created_at="2026-09-07T10:00:00+00:00", expires_at="2099-01-01T00:00:00+00:00",
                       migrated=True),
    ]
    stats = stm.get_stats()
    assert stats == {"active": 1, "quarantined": 1, "migrated": 1, "total": 3}


if __name__ == "__main__":
    test_answer_budget_is_1200_everywhere()
    test_single_budget_top3_capped()
    test_no_neutral_mislabel_with_style_only()
    test_no_frustration_budget_cut()
    test_self_report_keeps_memory_context()
    test_timing_carries_finish_reason()
    test_format_source_always_has_reason()
    test_compact_cli_counts_words_not_events()
    test_stm_stats_split()
    print("OK: V18 unified steering profile")
