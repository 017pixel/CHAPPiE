"""Tests fuer robustere deutsche Query-Extraktion."""

import os
import sys
from unittest.mock import MagicMock

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

for module_name in ("chromadb", "chromadb.config", "sentence_transformers", "ollama", "openai", "requests"):
    sys.modules.setdefault(module_name, MagicMock())

from memory.memory_engine import MemoryEngine  # noqa: E402


def _engine_without_init() -> MemoryEngine:
    return MemoryEngine.__new__(MemoryEngine)


class _FakeCollection:
    def __init__(self, docs):
        self.docs = docs

    def count(self):
        return len(self.docs)

    def get(self, include=None):
        return {
            "ids": [item[0] for item in self.docs],
            "documents": [item[1] for item in self.docs],
            "metadatas": [item[2] for item in self.docs],
        }


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


def test_keyword_rag_retrieves_exact_relationship_fact():
    engine = _engine_without_init()
    engine.collection = _FakeCollection([
        ("mem-1", "User: Mein Bruder heißt Lukas.", {"role": "user", "timestamp": "2026-06-29T10:00:00+00:00"}),
        ("mem-2", "CHAPPiE: Wir haben ueber ein Projekt gesprochen.", {"role": "assistant", "timestamp": "2026-06-29T10:05:00+00:00"}),
    ])

    results = engine.search_memory_keywords(
        "Wie heißt mein Bruder?",
        keywords=["bruder", "heisst"],
        top_k=5,
    )

    assert len(results) == 1
    assert results[0].id == "mem-1"
    assert results[0].match_type == "Keyword"
    assert "bruder" in results[0].matched_terms


def test_keyword_rag_normalizes_umlauts_for_entities():
    engine = _engine_without_init()
    engine.collection = _FakeCollection([
        ("mem-1", "User: Mein Nachname ist Müller.", {"role": "user", "timestamp": "2026-06-29T10:00:00+00:00"}),
    ])

    results = engine.search_memory_keywords(
        "Wie ist mein Nachname?",
        keywords=["nachname"],
        entities=["Mueller"],
    )

    assert len(results) == 1
    assert results[0].id == "mem-1"
    assert results[0].match_type == "Exact"


def test_keyword_rag_rejects_weak_only_matches():
    engine = _engine_without_init()
    engine.collection = _FakeCollection([
        ("mem-1", "User: Das Projekt hatte einen Fehler.", {"role": "user", "timestamp": "2026-06-29T10:00:00+00:00"}),
    ])

    results = engine.search_memory_keywords(
        "Name Projekt Fehler",
        keywords=["name", "projekt", "fehler"],
    )

    assert results == []


def test_keyword_rag_dedupes_semantic_memory_ids():
    engine = _engine_without_init()
    engine.collection = _FakeCollection([
        ("mem-1", "User: Ich heiße Benjamin.", {"role": "user", "timestamp": "2026-06-29T10:00:00+00:00"}),
    ])

    results = engine.search_memory_keywords(
        "Wie heiße ich?",
        keywords=["heisse"],
        exclude_ids={"mem-1"},
    )

    assert results == []


if __name__ == "__main__":
    test_keyword_builder_normalizes_umlauts_and_filters_stop_words()
    test_clean_query_output_rejects_json_like_noise()
    test_short_input_query_uses_keyword_path_without_llm()
    test_keyword_rag_retrieves_exact_relationship_fact()
    test_keyword_rag_normalizes_umlauts_for_entities()
    test_keyword_rag_rejects_weak_only_matches()
    test_keyword_rag_dedupes_semantic_memory_ids()
    print("OK: memory query extraction german")
