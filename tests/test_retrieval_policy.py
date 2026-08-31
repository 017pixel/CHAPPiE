"""Regression tests for semantic retrieval gating."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from web_infrastructure.backend_wrapper import (
    context_allows_long_term_memory,
    is_isolated_request,
    is_self_contained_math_query,
)


def test_digit_arithmetic_is_closed_form():
    assert is_self_contained_math_query("Wie viel ist 9 plus 4?")
    assert is_self_contained_math_query("Was ist 17 mal 6? Antworte kurz.")
    assert is_self_contained_math_query("Berechne 12 / 3.")


def test_german_number_words_are_closed_form():
    assert is_self_contained_math_query("Wie viel ist neun plus vier?")
    assert is_self_contained_math_query("Was ergibt zwölf minus fünf?")


def test_personal_recall_questions_keep_memory_enabled():
    assert not is_self_contained_math_query("Erinnerst du dich an meine letzte Zahl?")
    assert not is_self_contained_math_query("Was ist meine Lieblingszahl?")
    assert not is_self_contained_math_query("Was haben wir gestern besprochen?")


def test_context_contract_is_authoritative_for_retrieval_and_isolation():
    isolated = {
        "need_soul_context": False,
        "need_user_context": False,
        "need_preferences": False,
        "need_short_term_memory": False,
        "need_long_term_memory": False,
    }
    assert not context_allows_long_term_memory(isolated)
    assert is_isolated_request(isolated)
    assert context_allows_long_term_memory({"need_long_term_memory": True})
    assert not is_isolated_request({"need_long_term_memory": True})


if __name__ == "__main__":
    test_digit_arithmetic_is_closed_form()
    test_german_number_words_are_closed_form()
    test_personal_recall_questions_keep_memory_enabled()
    test_context_contract_is_authoritative_for_retrieval_and_isolation()
    print("OK: retrieval policy")
