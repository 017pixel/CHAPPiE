"""Tests fuer robustere deutsche Query-Extraktion."""

import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from memory.memory_engine import MemoryEngine  # noqa: E402


def _engine_without_init() -> MemoryEngine:
    return MemoryEngine.__new__(MemoryEngine)


def test_keyword_builder_normalizes_umlauts_and_filters_stop_words():
    engine = _engine_without_init()
    query = engine._build_keyword_query(
        "Ich moechte ueber Gefühle und Erinnerungen in CHAPPiE sprechen",
        max_terms=8,
    )
    assert "gefuehle" in query
    assert "erinnerungen" in query
    assert "chappie" in query
    assert "ich" not in query


def test_clean_query_output_rejects_json_like_noise():
    engine = _engine_without_init()
    cleaned = engine._clean_query_output('{ "query": "test" }')
    assert cleaned == ""


def test_short_input_query_uses_keyword_path_without_llm():
    engine = _engine_without_init()
    query = engine.extract_search_query("Bitte analysiere Traurigkeit und Vertrauen")
    assert "traurigkeit" in query
    assert "vertrauen" in query


if __name__ == "__main__":
    test_keyword_builder_normalizes_umlauts_and_filters_stop_words()
    test_clean_query_output_rejects_json_like_noise()
    test_short_input_query_uses_keyword_path_without_llm()
    print("OK: memory query extraction german")
