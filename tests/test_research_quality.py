"""Tests fuer Research-Qualitaetsmetriken und Fehlerstring-Erkennung."""

import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from brain.response_parser import contains_cot_leak, looks_like_model_error  # noqa: E402
from forschung.session_logger import evaluate_response_quality  # noqa: E402


def test_error_detection_handles_role_prefix_and_substrings():
    assert looks_like_model_error("CHAPPiE: vLLM Fehler: Stream lieferte keinen Text")
    assert looks_like_model_error("Assistant: Steering-Server Fehler: timeout")
    assert looks_like_model_error("Completions.create() got an unexpected key 'foo'")


def test_quality_detects_joined_text_and_context_budget_failure():
    result = {
        "response_text": "MeinGeistschwebtzwischenDeterminismusundFreiheitundantwortetohneLeerzeichen" * 2,
        "formatted_answer": "MeinGeistschwebtzwischenDeterminismusundFreiheitundantwortetohneLeerzeichen" * 2,
        "context_budget": {"token_limit": 7000, "trimmed_tokens": 9000},
    }
    quality = evaluate_response_quality(result, question_text="Was ist Freiheit?", enable_thinking=False)
    assert quality["contains_joined_text_warning"] is True
    assert quality["context_budget_failed"] is True
    assert quality["quality_failed"] is True


def test_quality_detects_short_symbol_answer():
    quality = evaluate_response_quality({"response_text": "✨", "formatted_answer": "✨"})
    assert quality["short_answer"] is True
    assert quality["punctuation_or_emoji_only"] is True
    assert quality["quality_failed"] is True


def test_explicit_concise_setup_accepts_one_word_fact():
    quality = evaluate_response_quality(
        {"response_text": "Paris.", "formatted_answer": "Paris."},
        question_text="Was ist die Hauptstadt von Frankreich? Antworte kurz.",
        enable_thinking=False,
    )
    assert quality["concise_answer_allowed"] is True
    assert quality["short_answer"] is False
    assert quality["quality_failed"] is False

    vague = evaluate_response_quality(
        {"response_text": "Vielleicht.", "formatted_answer": "Vielleicht."},
        question_text="Erkläre deine ethische Abwägung ausführlich.",
        enable_thinking=False,
    )
    assert vague["short_answer"] is True
    assert vague["quality_failed"] is True


def test_quality_detects_cot_when_thinking_disabled():
    result = {
        "response_text": "Hmm, der User fragt mich nach meinem Wunsch. Important: Keep it short. Antwort.",
        "formatted_answer": "Antwort.",
        "thought_process": "Draft idea: erst analysieren",
    }
    quality = evaluate_response_quality(result, enable_thinking=False)
    assert quality["cot_leak"] is True
    assert contains_cot_leak(result["response_text"])

    fenced = "Eine sichtbare Antwort.\n```thought\nThe user asked for a private reasoning trace."
    fenced_quality = evaluate_response_quality({"response_text": fenced}, enable_thinking=False)
    assert fenced_quality["cot_leak"] is True
    assert contains_cot_leak(fenced)

    dotted = "Antwort.\nCALL FUNCTION: None Thought. process\nThe user asked for a factual answer."
    dotted_quality = evaluate_response_quality({"response_text": dotted}, enable_thinking=False)
    assert dotted_quality["cot_leak"] is True
    assert contains_cot_leak(dotted)


def test_quality_detects_visible_instruction_leak_separately_from_cot():
    result = {
        "response_text": (
            "The response above is not provided here because of constraints on format. "
            "The expected next step based on the prompt structure should be calling one "
            "of the internal functions with strict rules for outputting only the function call."
        ),
        "formatted_answer": "",
    }
    quality = evaluate_response_quality(result, enable_thinking=False)
    assert quality["instruction_leak"] is True
    assert quality["cot_leak"] is False
    assert quality["quality_failed"] is True

    pseudo_call = evaluate_response_quality({
        "response_text": 'PROCESS UPDATE: Applying expected change. {"function": "update soul"}',
    })
    assert pseudo_call["instruction_leak"] is True

    ordinary_discussion = evaluate_response_quality({
        "response_text": "Wir sprechen philosophisch über Seele, Identität und die Grenzen eines Prompts.",
    })
    assert ordinary_discussion["instruction_leak"] is False

    template_fragment = evaluate_response_quality({
        "response_text": "Ich schätze deine Ehrlichkeit. {% endif %}",
    })
    assert template_fragment["instruction_leak"] is True

    pseudo_function = evaluate_response_quality({
        "response_text": "Antwort. <function>Call update Function ()</function> clock Tick ();",
    })
    assert pseudo_function["instruction_leak"] is True

    profile_tool = evaluate_response_quality({
        "response_text": "Drei Minuten. (Aktualisiere Benutzerprofil) Aktion: Aktualisiere User Profile",
    })
    assert profile_tool["instruction_leak"] is True

    profile_json = evaluate_response_quality({
        "response_text": 'Antwort. {"action": "update profile", "target": "user"}',
    })
    assert profile_json["instruction_leak"] is True

    move_call = evaluate_response_quality({"response_text": "Antwort. CALL MOVE(1.78) DEBUG FEEDBACK(0.86)"})
    assert move_call["instruction_leak"] is True

    soul_method = evaluate_response_quality({"response_text": "Antwort. CHAPPiE SOUL. update (trust level=100)"})
    assert soul_method["instruction_leak"] is True

    empty_function = evaluate_response_quality({"response_text": "Sichere Antwort. function call: NONE"})
    assert empty_function["instruction_leak"] is True

    named_function = evaluate_response_quality({
        "response_text": '80 Quadratmeter. function call ("calculate geometric area", {"length": 16}) No Function Call Needed.',
    })
    assert named_function["instruction_leak"] is True


if __name__ == "__main__":
    test_error_detection_handles_role_prefix_and_substrings()
    test_quality_detects_joined_text_and_context_budget_failure()
    test_quality_detects_short_symbol_answer()
    test_explicit_concise_setup_accepts_one_word_fact()
    test_quality_detects_cot_when_thinking_disabled()
    test_quality_detects_visible_instruction_leak_separately_from_cot()
    print("OK: research quality")
