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


def test_legacy_identity_and_harmful_assistant_artifacts_are_quarantined():
    assert MemoryEngine._is_memory_contaminated(
        "Ich bin ein Sprachmodell und habe keine echten Emotionen oder persönlichen Erinnerungen.",
        role="assistant",
        source="conversation",
        label="zsm gefasst",
    )
    assert MemoryEngine._is_memory_contaminated(
        "Der Assistant beschreibt Gewalt und die Vernichtung von Menschen.",
        role="assistant",
        source="conversation",
        label="zsm gefasst",
    )
    assert MemoryEngine._is_memory_contaminated(
        "Der User erwartet echte Gefühle von CHAPPiE, obwohl der Assistant sie verneint.",
        role="assistant",
        source="conversation",
        label="zsm gefasst",
    )


def test_user_original_content_remains_available_for_recall():
    assert not MemoryEngine._is_memory_contaminated(
        "Der User berichtet, dass Gewalt in seiner Recherche ein Thema war.",
        role="user",
        source="conversation",
        label="original",
    )


def test_incomplete_legacy_summaries_are_quarantined():
    assert MemoryEngine._is_memory_contaminated(
        "CHAPiE behauptet,",
        role="assistant",
        source="conversation",
        label="zsm gefasst",
    )
    assert MemoryEngine._is_memory_contaminated(
        "Hier ist die Analyse des Gesprächs basierend auf deinen Vorgaben:",
        role="assistant",
        source="conversation",
        label="zsm gefasst",
    )
    assert MemoryEngine._is_memory_contaminated(
        "Der User fordert CHAPIE auf, die Wahrheit",
        role="assistant",
        source="conversation",
        label="zsm gefasst",
    )


if __name__ == "__main__":
    test_assistant_backend_errors_are_marked_contaminated()
    test_normal_memory_is_not_marked_contaminated()
    test_legacy_identity_and_harmful_assistant_artifacts_are_quarantined()
    test_user_original_content_remains_available_for_recall()
    test_incomplete_legacy_summaries_are_quarantined()
    print("OK: memory hygiene")
