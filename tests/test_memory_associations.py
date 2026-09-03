"""Offline-Tests fuer Recall-Staerke und assoziative Memory-Ausbreitung."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

for module_name in ("chromadb", "chromadb.config", "sentence_transformers"):
    sys.modules.setdefault(module_name, MagicMock())

from memory.memory_engine import MemoryEngine  # noqa: E402


class _Embedding:
    def tolist(self):
        return [0.1, 0.2, 0.3]


class _Embedder:
    def encode(self, _text):
        return _Embedding()


class _Collection:
    def __init__(self):
        old = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        self.records = {
            "a": {
                "document": "Benjamin arbeitet am Projekt CHAPPiE.",
                "metadata": {
                    "role": "user", "timestamp": old, "type": "interaction",
                    "label": "original", "source": "conversation",
                    "strength": 1.0, "recall_count": 0, "last_recall_time": old,
                    "associations": '{"b":0.9}',
                },
            },
            "b": {
                "document": "CHAPPiE soll sich genaue Fakten langfristig merken.",
                "metadata": {
                    "role": "user", "timestamp": old, "type": "interaction",
                    "label": "original", "source": "conversation",
                    "strength": 1.0, "recall_count": 0, "last_recall_time": old,
                    "associations": '{"a":0.9}',
                },
            },
        }

    def count(self):
        return len(self.records)

    def query(self, **_kwargs):
        record = self.records["a"]
        return {
            "ids": [["a"]],
            "documents": [[record["document"]]],
            "metadatas": [[dict(record["metadata"])]],
            "distances": [[0.08]],
        }

    def get(self, ids=None, **_kwargs):
        selected = ids or list(self.records)
        return {
            "ids": list(selected),
            "documents": [self.records[memory_id]["document"] for memory_id in selected],
            "metadatas": [dict(self.records[memory_id]["metadata"]) for memory_id in selected],
        }

    def update(self, ids, metadatas):
        for memory_id, metadata in zip(ids, metadatas):
            self.records[memory_id]["metadata"] = dict(metadata)


def _engine() -> MemoryEngine:
    engine = MemoryEngine.__new__(MemoryEngine)
    engine.collection = _Collection()
    engine.embedder = _Embedder()
    engine.embedding_dim = 3
    return engine


def test_association_expands_direct_retrieval_without_another_model_call() -> None:
    engine = _engine()
    memories = engine.search_memory(
        "Woran arbeitet Benjamin?",
        top_k=2,
        min_relevance=0.2,
        optimize_query=False,
    )
    assert [memory.id for memory in memories] == ["a", "b"]
    assert memories[1].match_type == "Association"
    assert memories[1].association_score == 0.9


def test_retrieval_persists_recall_strength_and_co_retrieval_links() -> None:
    engine = _engine()
    engine.search_memory("CHAPPiE Projekt", top_k=2, optimize_query=False)
    for memory_id in ("a", "b"):
        metadata = engine.collection.records[memory_id]["metadata"]
        assert metadata["recall_count"] == 1
        assert metadata["strength"] > 1.0
        assert memory_id not in MemoryEngine._parse_associations(metadata["associations"])


if __name__ == "__main__":
    test_association_expands_direct_retrieval_without_another_model_call()
    test_retrieval_persists_recall_strength_and_co_retrieval_links()
    print("OK: memory associations")
