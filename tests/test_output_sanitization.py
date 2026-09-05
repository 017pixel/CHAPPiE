"""Provider-independent leak sanitizer regression tests."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from brain.response_parser import contains_instruction_leak, is_safe_retrieval_text, resolve_visible_answer, sanitize_visible_response


def test_tool_json_is_removed_but_answer_is_preserved():
    raw = 'Gern helfe ich dir.\n{"name":"update_soul","arguments":{"trust_level":80}}'
    clean, reasons = sanitize_visible_response(raw)
    assert clean == "Gern helfe ich dir."
    assert reasons
    assert not contains_instruction_leak(clean)


def test_reasoning_and_function_blocks_never_reach_visible_answer():
    raw = "<think>Ich plane intern.</think>\nDie Antwort ist 42.\n<function_call>{\"name\":\"update_user\"}</function_call>"
    clean, reasons = sanitize_visible_response(raw)
    assert clean == "Die Antwort ist 42."
    assert "private_reasoning" in reasons
    assert "tool_call" in reasons


def test_unresolved_template_output_is_withheld():
    clean, reasons = sanitize_visible_response("{{ internal_prompt }}")
    assert clean == ""
    assert reasons


def test_contaminated_historical_memory_is_rejected_before_retrieval():
    assert is_safe_retrieval_text("Der Nutzer bevorzugt klare, kurze Antworten.")
    assert not is_safe_retrieval_text('call: update_soul(trust_level=0.99)')
    assert not is_safe_retrieval_text("## ANWEISUNG FÜR DIE AUTORGENERATION\nthought\nInterner Plan")


def test_truncated_prose_thinking_is_withheld_as_a_whole():
    raw = "Thinking Process:\n\n1. **Analyze Request:**\nThe user asks for one sentence."
    clean, reasons = sanitize_visible_response(raw)
    assert clean == ""
    assert "private_reasoning" in reasons


def test_final_answer_after_prose_thinking_is_preserved():
    raw = "Thinking Process:\n1. Analyze Request\nFinal Answer: Die Antwort ist 102."
    clean, reasons = sanitize_visible_response(raw)
    assert clean == "Die Antwort ist 102."
    assert "private_reasoning" in reasons


def test_gemma_internal_tail_is_cut_after_valid_answer():
    raw = (
        "Das Ergebnis von 7 plus 5 beträgt 12. Bitte gib mir eine neue Aufgabe. "
        "brandoffset = 12.0. Mein aktueller Zustand wird weiterverarbeitet. "
        "My Score Update (New Rate: 0.9)."
    )
    clean, reasons = sanitize_visible_response(raw)
    assert clean == "Das Ergebnis von 7 plus 5 beträgt 12. Bitte gib mir eine neue Aufgabe."
    assert "private_reasoning_tail" in reasons
    assert not contains_instruction_leak(clean)


def test_gemma_thought_stream_marker_contaminates_retrieval():
    assert not is_safe_retrieval_text(
        "Eine korrekte Antwort. outbound\\_thought\\_stream{status: Stable.}"
    )


def test_gemma_plain_think_end_is_not_persisted_or_retrieved():
    clean, reasons = sanitize_visible_response("Die Antwort ist 13. Think End")
    assert clean == "Die Antwort ist 13."
    assert reasons
    assert not is_safe_retrieval_text("Falscher interner Text. Think End")


def test_echoed_memory_transcript_keeps_only_the_final_assistant_answer():
    raw = (
        "d1d6a15c | Score\n"
        "user\n"
        "Hallo CH\n"
        "assistant\n"
        "Hallo Benjamin! Wie läuft dein Projekt heute?"
    )
    clean, reasons = sanitize_visible_response(raw)
    assert clean == "Hallo Benjamin! Wie läuft dein Projekt heute?"
    assert "memory_header" in reasons
    assert "role_fragment" in reasons
    assert "user" not in clean.casefold()
    assert "assistant" not in clean.casefold()


def test_role_only_or_user_only_transcripts_are_withheld():
    clean, reasons = sanitize_visible_response("user\nDas ist der Prompt.")
    assert clean == ""
    assert "unresolved_leak" in reasons
    assert not is_safe_retrieval_text("assistant: interne Antwort")


def test_memory_headers_are_not_safe_retrieval_context():
    assert not is_safe_retrieval_text("d1d6a15c | Score")
    assert not is_safe_retrieval_text("[Keyword | ID d1d6a15c | Score 48%]")


def test_resolve_visible_answer_never_discards_generated_text():
    text, info = resolve_visible_answer("Hallo Welt")
    assert text == "Hallo Welt"
    assert info["sanitization_fallback"] is False

    text, info = resolve_visible_answer("", display_response="Extrahierte Antwort", raw_response="roher Text")
    assert text == "Extrahierte Antwort"
    assert info["sanitization_fallback"] is True

    text, info = resolve_visible_answer("", display_response="", raw_response="nur roh vorhanden")
    assert text == "nur roh vorhanden"
    assert info["sanitization_fallback"] is True

    text, info = resolve_visible_answer("", display_response="  ", raw_response="")
    assert "0 Tokens" in text
    assert info.get("empty_generation") is True


if __name__ == "__main__":
    test_tool_json_is_removed_but_answer_is_preserved()
    test_reasoning_and_function_blocks_never_reach_visible_answer()
    test_unresolved_template_output_is_withheld()
    test_contaminated_historical_memory_is_rejected_before_retrieval()
    test_truncated_prose_thinking_is_withheld_as_a_whole()
    test_final_answer_after_prose_thinking_is_preserved()
    test_gemma_internal_tail_is_cut_after_valid_answer()
    test_gemma_thought_stream_marker_contaminates_retrieval()
    test_gemma_plain_think_end_is_not_persisted_or_retrieved()
    test_echoed_memory_transcript_keeps_only_the_final_assistant_answer()
    test_role_only_or_user_only_transcripts_are_withheld()
    test_memory_headers_are_not_safe_retrieval_context()
    test_resolve_visible_answer_never_discards_generated_text()
    print("OK: output sanitization")
