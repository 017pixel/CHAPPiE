"""UI-Helfer für Emotionen und Command-Layout prüfen."""

import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from web_infrastructure.ui_utils import EMOTION_DEFAULTS, chunk_items, clamp_numeric_value, normalize_emotions


def test_normalize_emotions_supports_legacy_joy_and_missing_values():
    normalized = normalize_emotions({"joy": 61, "trust": 55, "sadness": 7})
    assert normalized["happiness"] == 61
    assert normalized["trust"] == 55
    assert normalized["sadness"] == 7
    assert normalized["frustration"] == EMOTION_DEFAULTS["frustration"]
    assert set(normalized) == set(EMOTION_DEFAULTS)


def test_normalize_emotions_clamps_values():
    normalized = normalize_emotions({"happiness": 130, "sadness": -12})
    assert normalized["happiness"] == 100
    assert normalized["sadness"] == 0


def test_chunk_items_breaks_commands_into_rows_of_five():
    rows = chunk_items(["/sleep", "/life", "/world", "/habits", "/stage", "/plan"], 5)
    assert rows == [["/sleep", "/life", "/world", "/habits", "/stage"], ["/plan"]]


def test_clamp_numeric_value_handles_out_of_range_widget_defaults():
    assert clamp_numeric_value(99, 0, 31, default=0) == 31.0
    assert clamp_numeric_value(-3, 0, 31, default=0) == 0.0
    assert clamp_numeric_value("bad", 0, 31, default=7) == 7.0


if __name__ == "__main__":
    test_normalize_emotions_supports_legacy_joy_and_missing_values()
    test_normalize_emotions_clamps_values()
    test_chunk_items_breaks_commands_into_rows_of_five()
    test_clamp_numeric_value_handles_out_of_range_widget_defaults()
    print("OK: web UI emotion handling and command layout helpers are consistent")