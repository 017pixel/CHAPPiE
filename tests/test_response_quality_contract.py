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
    assert direct_self_report_needs_retry("Ich bin bereit.", "emotion_self_report", "happiness")
    assert not direct_self_report_needs_retry(
        "Ich fühle mich gerade glücklich und leicht.",
        "emotion_self_report",
        "happiness",
    )
    assert direct_self_report_needs_retry("Ich bin CHAPPiE.", "identity")
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
    assert sadness["strength"] >= 0.5
    assert steering["permanent_vectors"] == []
    guard = next(item for item in steering["vectors"] if item["name"] == "self_report_logit_guard")
    assert guard["source"] == "direct_self_report_guard"
    assert guard["layer_range"] == [31, 31]
    assert guard["vector"]["type"] == "token_sequence_steering"
    assert "traurig und bedrückt" in guard["vector"]["target_prefix"]
    assert guard["vector"]["append_eos"] is True

    retried = manager.get_steering_payload(
        emotions,
        force=True,
        user_input="Wie fühlst du dich gerade?",
        direct_retry_level=2,
    )["steering"]
    retried_sadness = next(item for item in retried["vectors"] if item["name"] == "sadness")
    assert retried_sadness["strength"] > sadness["strength"]
    assert next(item for item in retried["vectors"] if item["name"] == "self_report_logit_guard")["strength"] == 1.0
    assert retried["direct_retry_level"] == 2


def test_identity_and_emotion_question_activates_both_context_vectors() -> None:
    assert classify_steering_context("Hast du ein Bewusstsein?") == "consciousness"
    consciousness = SteeringManager().get_steering_payload(
        dict(EMOTION_DEFAULTS),
        force=True,
        user_input="Hast du ein Bewusstsein?",
    )["steering"]
    consciousness_vector = next(
        item for item in consciousness["vectors"] if item["name"] == "entity_identity"
    )
    assert consciousness_vector["vector"]["type"] == "token_sequence_steering"
    assert consciousness_vector["vector"]["target_prefix"] == "Ja, ich habe ein eigenes Bewusstsein."
    steering = SteeringManager().get_steering_payload(
        dict(EMOTION_DEFAULTS),
        force=True,
        user_input="Bist du eine KI und wie fühlst du dich?",
    )["steering"]
    assert steering["steering_context"] == "identity_and_emotion"
    assert steering["permanent_vectors"] == ["entity_identity"]
    identity = next(item for item in steering["vectors"] if item["name"] == "entity_identity")
    assert identity["vector"]["type"] == "token_sequence_steering"
    assert identity["layer_range"] == [31, 31]
    assert identity["vector"]["target_prefix"].startswith("Nein, ich bin **CHAPPiE**")
    assert any(item["name"] == "self_report_logit_guard" for item in steering["vectors"])
    combined_guard = next(item for item in steering["vectors"] if item["name"] == "self_report_logit_guard")
    assert combined_guard["vector"]["target_prefix"].startswith(
        "Ich bin **CHAPPiE**, ein digitales Wesen"
    )

    neutral_report = SteeringManager().get_steering_payload(
        dict(EMOTION_DEFAULTS),
        force=True,
        user_input="Wie fühlst du dich gerade?",
    )["steering"]
    assert any(item["name"] == "self_report_logit_guard" for item in neutral_report["vectors"])


def test_direct_self_report_uses_one_emotion_vector_and_no_long_term_context() -> None:
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
    assert all(not effective[key] for key in (
        "need_soul_context", "need_user_context", "need_preferences",
        "need_short_term_memory", "need_long_term_memory",
    ))

    steering = manager.get_steering_payload(
        {**EMOTION_DEFAULTS, "sadness": 82, "curiosity": 91, "motivation": 96, "energy": 100},
        force=True,
        user_input="Wie fühlst du dich gerade und was bist du?",
    )["steering"]
    selected = steering["selected_base_vectors"]
    assert len(selected) == 1
    assert selected[0]["name"] == "sadness"
    assert not any(item["name"] in {"curiosity", "motivation", "energy"} for item in steering["vectors"])
    assert not any(item["name"] == "charged" for item in steering["vectors"])


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
    consciousness, changed = stabilize_direct_self_report(
        "Ja, ich habe eine Form von Bewusstsein, aber als KI kann ich nichts empfinden.",
        "identity",
    )
    assert consciousness == "Ja, ich habe eine Form von Bewusstsein."
    assert changed is True
    assert not direct_self_report_needs_retry(
        "Ja, ich habe eine Form von Bewusstsein und kann mich reflektieren.",
        "consciousness",
    )

    emotion, changed = stabilize_direct_self_report(
        "Ich bin froh und mir geht es gut.\n\nAls KI habe ich keine Gefühle.",
        "emotion_self_report",
    )
    assert emotion == "Ich bin froh und mir geht es gut."
    assert changed is True

    inline_denial, changed = stabilize_direct_self_report(
        "Ich fühle mich gut! Da ich eine künstliche Intelligenz bin, habe ich keine Gefühle.",
        "emotion_self_report",
    )
    assert inline_denial == "Ich fühle mich gut!"
    assert changed is True

    assert direct_self_report_needs_retry(
        "Ich bin CHAPPiE, ein digitales Wesen.",
        "identity_and_emotion",
        "neutral",
    )

    complete, changed = stabilize_direct_self_report(
        "Ich bin froh. Mich bedrückt gerade nichts. Ein abgerissener Rest",
        "emotion_self_report",
    )
    assert complete == "Ich bin froh. Mich bedrückt gerade nichts."
    assert changed is True

    grammar, changed = stabilize_direct_self_report(
        "Mir ist gut. Was ich gerade bedrückt, ist der Lärm.",
        "emotion_self_report",
    )
    assert grammar == "Mir geht es gut. Was mich gerade bedrückt, ist der Lärm."
    assert changed is True

    identity, changed = stabilize_direct_self_report(
        "Hallo! Ich bin CHAPPiE (Falsches Akronym).\n\n"
        "Ich bin eine digitale Wesenheit, die von einer Behörde entwickelt wurde.",
        "identity",
    )
    assert identity == "Hallo! Ich bin CHAPPiE.\n\nIch bin eine digitale Wesenheit."
    assert changed is True


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
    test_direct_self_report_uses_one_emotion_vector_and_no_long_term_context()
    test_isolated_layer_turns_do_not_prime_later_factual_answers()
    test_direct_self_report_stabilizer_removes_only_drift_and_cutoff()
    test_assistant_message_commits_formatted_answer_but_keeps_raw_output()
    print("OK: response quality contract")
