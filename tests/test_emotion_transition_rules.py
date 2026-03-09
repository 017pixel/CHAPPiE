"""Regressionstests fuer geglaettete Emotionsuebergaenge."""

import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from memory.emotions_engine import calculate_emotion_transition


def test_extreme_delta_is_softened_and_capped():
    transition = calculate_emotion_transition("happiness", 100, -85)
    assert transition["raw_delta"] == -85
    assert transition["applied_delta"] == -8
    assert transition["after"] == 92
    assert transition["softened"] is True


def test_small_delta_stays_direct():
    transition = calculate_emotion_transition("trust", 40, 2)
    assert transition["raw_delta"] == 2
    assert transition["applied_delta"] == 2
    assert transition["after"] == 42
    assert transition["softened"] is False


if __name__ == "__main__":
    test_extreme_delta_is_softened_and_capped()
    test_small_delta_stays_direct()
    print("OK: emotion transition rules")