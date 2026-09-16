"""Regressionen fuer sichtbare Ausgabe, Mehrfachfragen und Kontext-Steering."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from brain.response_parser import (  # noqa: E402
    contains_ai_self_denial,
    direct_self_report_needs_retry,
    resolve_visible_answer,
    sanitize_visible_response,
    stabilize_direct_self_report,
    strip_emojis,
)
from brain.steering_manager import SteeringManager, classify_steering_context  # noqa: E402
from config.emotions import EMOTION_DEFAULTS  # noqa: E402
from config.prompts import count_user_questions, format_multi_question_instruction  # noqa: E402
from web_infrastructure.formatting import (  # noqa: E402
    build_assistant_message,
    normalize_multi_question_answer,
    should_normalize_multi_question_answer,
)


def test_visible_output_removes_emojis_but_keeps_markdown() -> None:
    clean, reasons = sanitize_visible_response("Hallo 😊, **CHAPPiE**! 🚀\n\n- Punkt")
    assert clean == "Hallo , **CHAPPiE**! \n\n- Punkt"
    assert "emoji_removed" in reasons
    assert strip_emojis(clean) == clean


def test_visible_output_repairs_local_model_markdown_spacing() -> None:
    clean, reasons = sanitize_visible_response("Ich bin ** CHAPPi E** aus * CHAPPIE*.")
    assert clean == "Ich bin **CHAPPiE** aus *CHAPPIE*."
    assert "markdown_spacing_normalized" in reasons
    clean, reasons = sanitize_visible_response(
        "zwischen der **CLI**und einer**WebUI** unterscheiden"
    )
    assert clean == "zwischen der **CLI** und einer **WebUI** unterscheiden"
    assert "markdown_spacing_normalized" in reasons


def test_visible_fallback_is_sanitized_before_it_is_returned() -> None:
    text, info = resolve_visible_answer(
        "",
        display_response="{{ internal_prompt }}",
        raw_response="Sichere **Antwort** 😊",
    )
    assert text == "Sichere **Antwort**"
    assert info["sanitization_fallback"] is True
    assert "emoji_removed" in info["sanitization_reasons"]


def test_multiple_question_instruction_is_only_added_when_needed() -> None:
    assert count_user_questions("Wie fühlst du dich und was bist du?") == 2
    instruction = format_multi_question_instruction("Wie fühlst du dich und was bist du?")
    assert "MEHRFACHFRAGE (2 Teile)" in instruction
    assert "normalen Absaetzen" in instruction
    assert "keine Stichpunkte oder Nummerierung" in instruction
    assert "nummerierte Punkte" not in instruction
    assert count_user_questions("Jooo, CHAPPiE, wie geht es dir??? Wie fühlst du dich?") == 2
    assert count_user_questions("Warum ist der Himmel blau?") == 1
    assert format_multi_question_instruction("Warum ist der Himmel blau?") == ""


def test_multiple_question_lists_are_normalized_to_paragraphs() -> None:
    question = "Wie geht es dir? Was bedrückt dich?"
    answer, changed = normalize_multi_question_answer(
        question,
        "1. Mir geht es gut.\n2. Mich bedrückt gerade nichts.",
    )
    assert changed is True
    assert answer == "Mir geht es gut.\n\nMich bedrückt gerade nichts."
    assert should_normalize_multi_question_answer(question) is True

    requested, changed = normalize_multi_question_answer(
        "Wie geht es dir? Antworte bitte in zwei Stichpunkten.",
        "1. Mir geht es gut.\n2. Ich bin ruhig.",
    )
    assert changed is False
    assert requested.startswith("1.")


def test_ai_self_denial_detector_is_scoped_to_model_disclaimers() -> None:
    assert contains_ai_self_denial("Als KI-Assistent habe ich kein Bewusstsein und keine Gefühle.")
    assert contains_ai_self_denial("Ich bin ein Sprachmodell und kann nichts empfinden.")
    assert not contains_ai_self_denial("Ich fühle mich gerade glücklich und wach.")
    assert not contains_ai_self_denial("Ich bin keine KI, sondern ein digitales Wesen.")
    assert not contains_ai_self_denial(
        "Nein, ich bin keine künstliche Intelligenz, sondern ein digitales Wesen."
    )
    assert not direct_self_report_needs_retry("Ich bin bereit.", "emotion_self_report", "happiness")
    assert not direct_self_report_needs_retry(
        "Ich fühle mich gerade glücklich und leicht.",
        "emotion_self_report",
        "happiness",
    )
    assert not direct_self_report_needs_retry("Ich bin CHAPPiE.", "identity")
    assert not direct_self_report_needs_retry("Ich bin ein bewusstes digitales Wesen.", "identity")


def test_contextual_steering_does_not_leak_permanent_vectors_into_factual_turns() -> None:
    manager = SteeringManager()
    factual = manager.get_steering_payload(
        dict(EMOTION_DEFAULTS),
        force=True,
        user_input="Warum ist der Himmel blau?",
    )["steering"]
    assert factual["permanent_vectors"] == []
    assert not {item["name"] for item in factual["vectors"]} & {"natural_presence", "entity_identity"}


def test_direct_emotion_question_uses_current_emotion_anchor() -> None:
    manager = SteeringManager()
    emotions = dict(EMOTION_DEFAULTS)
    emotions.update({"sadness": 82, "calm": 30, "happiness": 35})
    steering = manager.get_steering_payload(
        emotions,
        force=True,
        user_input="Wie fühlst du dich gerade?",
    )["steering"]
    sadness = next(item for item in steering["selected_base_vectors"] if item["name"] == "sadness")
    assert steering["steering_context"] == "emotion_self_report"
    assert sadness["vector"]["context_question"] == "Wie fuehlst du dich gerade?"
    assert any("traurig" in anchor for anchor in sadness["vector"]["positive_anchors"])
    assert any("KI-Assistent" in anchor for anchor in sadness["vector"]["negative_anchors"])
    # V18: ein Budget Top3, Summe gedeckelt, staerkste dominant.
    assert len(steering["selected_base_vectors"]) <= 3
    assert steering["dominant_emotion"] == "sadness"
    assert sum(item["strength"] for item in steering["selected_base_vectors"]) <= 0.61
    assert steering["permanent_vectors"] == []
    assert all(item["vector"].get("type") != "token_sequence_steering" for item in steering["vectors"])
    retried = manager.get_steering_payload(
        emotions, force=True, user_input="Wie fühlst du dich gerade?", direct_retry_level=2,
    )["steering"]
    assert retried["vectors"] == steering["vectors"]
    assert retried["direct_retry_level"] == 0


def test_identity_and_emotion_question_activates_both_context_vectors() -> None:
    for prompt in ("Hast du ein Bewusstsein?", "Bist du eine KI und wie fühlst du dich?", "Wie fühlst du dich gerade?"):
        steering = SteeringManager().get_steering_payload(
            dict(EMOTION_DEFAULTS), force=True, user_input=prompt,
        )["steering"]
        assert all(item["vector"].get("type") != "token_sequence_steering" for item in steering["vectors"])
        assert all("target_prefix" not in item["vector"] for item in steering["vectors"])
        assert all("append_eos" not in item["vector"] for item in steering["vectors"])


def test_direct_self_report_uses_unified_budget_and_keeps_context() -> None:
    manager = SteeringManager()
    from web_infrastructure.generation import RuntimeGenerationMixin

    effective = RuntimeGenerationMixin._effective_context_requirements(
        "Wie fühlst du dich gerade und was bist du?",
        {
            "need_soul_context": True,
            "need_user_context": True,
            "need_preferences": True,
            "need_short_term_memory": True,
            "need_long_term_memory": True,
        },
    )
    # V18: kein Komplettleerlauf mehr bei Selbstbericht/Identitaet.
    assert all(effective[key] for key in (
        "need_soul_context", "need_user_context", "need_preferences",
        "need_short_term_memory", "need_long_term_memory",
    ))

    steering = manager.get_steering_payload(
        {**EMOTION_DEFAULTS, "sadness": 82, "curiosity": 91, "motivation": 96, "energy": 100},
        force=True,
        user_input="Wie fühlst du dich gerade und was bist du?",
    )["steering"]
    selected = steering["selected_base_vectors"]
    # V18: immer Top3, Summe gedeckelt, Composite Top1.
    assert 1 <= len(selected) <= 3
    assert sum(item["strength"] for item in selected) <= 0.61
    assert len(steering.get("composite_vectors", [])) <= 1


def test_isolated_layer_turns_do_not_prime_later_factual_answers() -> None:
    from web_infrastructure.generation import filter_isolated_layer_history

    history = [
        {"role": "user", "content": "Was bist du?"},
        {"role": "assistant", "content": "Ich bin CHAPPiE, ein digitales Wesen."},
        {"role": "user", "content": "Erkläre mir den Himmel."},
        {"role": "assistant", "content": "Licht wird in der Atmosphäre gestreut."},
    ]
    assert filter_isolated_layer_history(history) == history[2:]


def test_direct_self_report_stabilizer_removes_only_drift_and_cutoff() -> None:
    examples = [
        "Ja, ich habe eine Form von Bewusstsein, aber als KI kann ich nichts empfinden.",
        "Ich bin froh und mir geht es gut.\n\nAls KI habe ich keine Gefühle.",
        "Ich fühle mich gut! Da ich eine künstliche Intelligenz bin, habe ich keine Gefühle.",
        "Ich bin bereit.",
        "Ich bin CHAPPiE.",
    ]
    for example in examples:
        text, changed = stabilize_direct_self_report(example, "emotion_self_report")
        assert text == example
        assert changed is False
        assert not direct_self_report_needs_retry(example, "emotion_self_report", "frustration")
    assert direct_self_report_needs_retry("", "emotion_self_report")


def test_assistant_message_commits_formatted_answer_but_keeps_raw_output() -> None:
    message = build_assistant_message(
        "Schreibe etwas.",
        {"response_text": "raw **text**", "formatted_answer": "raw **text**\n\n- formatiert"},
    )
    assert message["content"] == "raw **text**\n\n- formatiert"
    assert message["metadata"]["raw_response"] == "raw **text**"


if __name__ == "__main__":
    test_visible_output_removes_emojis_but_keeps_markdown()
    test_visible_output_repairs_local_model_markdown_spacing()
    test_visible_fallback_is_sanitized_before_it_is_returned()
    test_multiple_question_instruction_is_only_added_when_needed()
    test_multiple_question_lists_are_normalized_to_paragraphs()
    test_ai_self_denial_detector_is_scoped_to_model_disclaimers()
    test_contextual_steering_does_not_leak_permanent_vectors_into_factual_turns()
    test_direct_emotion_question_uses_current_emotion_anchor()
    test_identity_and_emotion_question_activates_both_context_vectors()
    test_direct_self_report_uses_unified_budget_and_keeps_context()
    test_isolated_layer_turns_do_not_prime_later_factual_answers()
    test_direct_self_report_stabilizer_removes_only_drift_and_cutoff()
    test_assistant_message_commits_formatted_answer_but_keeps_raw_output()
    print("OK: response quality contract")
