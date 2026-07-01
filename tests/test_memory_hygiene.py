"""Tests fuer Memory-Hygiene gegen Backend-Fehlerstrings."""

import os
import sys
from unittest.mock import MagicMock

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

sys.modules.setdefault("chromadb", MagicMock())
sys.modules.setdefault("chromadb.config", MagicMock())
sys.modules.setdefault("sentence_transformers", MagicMock())

from memory.memory_engine import MemoryEngine  # noqa: E402


def test_assistant_backend_errors_are_marked_contaminated():
    assert MemoryEngine._is_memory_contaminated("CHAPPiE: vLLM Fehler: Stream lieferte keinen Text")
    assert MemoryEngine._is_memory_contaminated("Assistant: Groq Fehler: timeout")


def test_normal_memory_is_not_marked_contaminated():
    assert not MemoryEngine._is_memory_contaminated("Wir haben gestern ueber Projektplanung gesprochen.")


if __name__ == "__main__":
    test_assistant_backend_errors_are_marked_contaminated()
    test_normal_memory_is_not_marked_contaminated()
    print("OK: memory hygiene")
