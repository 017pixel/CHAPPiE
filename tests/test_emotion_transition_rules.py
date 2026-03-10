"""Regressionstests fuer geglaettete Emotionsuebergaenge."""

import os
import sys
import tempfile
from pathlib import Path

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from memory import emotions_engine as emotions_module
from memory.emotions_engine import EmotionalState, EmotionsEngine, calculate_emotion_transition


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


def test_emotions_engine_reloads_newer_persisted_state_before_writing():
    with tempfile.TemporaryDirectory() as tmpdir:
        original_status_file = emotions_module.STATUS_FILE
        original_brain_initialized = EmotionsEngine._brain_initialized
        original_cached_brain = EmotionsEngine._cached_brain
        emotions_module.STATUS_FILE = Path(tmpdir) / "status.json"
        EmotionsEngine._brain_initialized = True
        EmotionsEngine._cached_brain = None
        try:
            writer_a = EmotionsEngine()
            writer_a.set_emotion("happiness", 73)
            writer_a.set_emotion("trust", 67)

            writer_b = EmotionsEngine()
            writer_b.set_emotion("energy", 58)

            writer_a.set_emotion("curiosity", 69)
            state = writer_a.get_state().to_dict()

            assert state["happiness"] == 73
            assert state["trust"] == 67
            assert state["energy"] == 58
            assert state["curiosity"] == 69

            reloaded = EmotionsEngine()
            reloaded_state = reloaded.get_state().to_dict()
            assert reloaded_state["happiness"] == 73
            assert reloaded_state["energy"] == 58
            assert reloaded_state["curiosity"] == 69
        finally:
            emotions_module.STATUS_FILE = original_status_file
            EmotionsEngine._brain_initialized = original_brain_initialized
            EmotionsEngine._cached_brain = original_cached_brain


if __name__ == "__main__":
    test_extreme_delta_is_softened_and_capped()
    test_small_delta_stays_direct()
    test_emotions_engine_reloads_newer_persisted_state_before_writing()
    print("OK: emotion transition rules")