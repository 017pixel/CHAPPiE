"""Regressionstests fuer geglaettete Emotionsuebergaenge."""

import os
import sys
import tempfile
import importlib.util
from pathlib import Path

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from config.emotions import EMOTION_DEFAULTS  # noqa: E402


def _load_emotions_module():
    path = Path(PROJECT_ROOT) / "memory" / "emotions_engine.py"
    spec = importlib.util.spec_from_file_location("emotions_engine_transition_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


emotions_module = _load_emotions_module()
EmotionalState = emotions_module.EmotionalState
EmotionsEngine = emotions_module.EmotionsEngine
calculate_emotion_transition = emotions_module.calculate_emotion_transition
analyze_emotion_signals = emotions_module.analyze_emotion_signals


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


def test_legacy_emotional_state_gets_new_emotion_defaults():
    state = EmotionalState.from_dict({"happiness": 73, "trust": 67, "sadness": 4})
    data = state.to_dict()

    assert data["happiness"] == 73
    assert data["trust"] == 67
    assert data["affection"] == EMOTION_DEFAULTS["affection"]
    assert data["anxiety"] == EMOTION_DEFAULTS["anxiety"]
    assert data["calm"] == EMOTION_DEFAULTS["calm"]


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


def test_mixed_message_updates_multiple_emotional_dimensions():
    changes = analyze_emotion_signals(
        "Danke, das ist gut, aber der Fehler funktioniert noch nicht. Warum?",
        current_state=EMOTION_DEFAULTS,
    )
    assert changes["frustration"] > 0
    assert changes["curiosity"] > 0
    assert changes["motivation"] > 0
    assert changes["calm"] < 0


def test_neutral_turn_recovers_slowly_toward_baseline():
    state = dict(EMOTION_DEFAULTS)
    state.update({"frustration": 40, "anxiety": 30, "calm": 20})
    changes = analyze_emotion_signals("Ich habe die Datei geoeffnet.", current_state=state)
    assert changes["frustration"] == -1
    assert changes["anxiety"] == -2
    assert changes["calm"] == 1


if __name__ == "__main__":
    test_extreme_delta_is_softened_and_capped()
    test_small_delta_stays_direct()
    test_legacy_emotional_state_gets_new_emotion_defaults()
    test_emotions_engine_reloads_newer_persisted_state_before_writing()
    test_mixed_message_updates_multiple_emotional_dimensions()
    test_neutral_turn_recovers_slowly_toward_baseline()
    print("OK: emotion transition rules")
