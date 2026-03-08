"""Tests fuer getrennte Ebenen von Modell-Reasoning und CHAPPiE-Gedankenprozess."""

import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from brain.response_parser import extract_tagged_block, parse_chain_of_thought  # noqa: E402


def test_model_reasoning_and_internal_thought_are_separated():
    raw = (
        "<model_reasoning>Modell denkt zuerst</model_reasoning>\n\n"
        "<gedanke>CHAPPiE plant die Antwort</gedanke>\n\n"
        "<antwort>Hier ist die finale Antwort.</antwort>"
    )
    extraction = extract_tagged_block(raw, ["model_reasoning"])
    parsed = parse_chain_of_thought(extraction.remaining)

    assert extraction.content == "Modell denkt zuerst"
    assert parsed.thought == "CHAPPiE plant die Antwort"
    assert parsed.answer == "Hier ist die finale Antwort."


if __name__ == "__main__":
    test_model_reasoning_and_internal_thought_are_separated()
    print("OK: reasoning layers stay separated")