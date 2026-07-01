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


def test_quality_detects_cot_when_thinking_disabled():
    result = {
        "response_text": "Hmm, der User fragt mich nach meinem Wunsch. Important: Keep it short. Antwort.",
        "formatted_answer": "Antwort.",
        "thought_process": "Draft idea: erst analysieren",
    }
    quality = evaluate_response_quality(result, enable_thinking=False)
    assert quality["cot_leak"] is True
    assert contains_cot_leak(result["response_text"])


if __name__ == "__main__":
    test_error_detection_handles_role_prefix_and_substrings()
    test_quality_detects_joined_text_and_context_budget_failure()
    test_quality_detects_short_symbol_answer()
    test_quality_detects_cot_when_thinking_disabled()
    print("OK: research quality")
