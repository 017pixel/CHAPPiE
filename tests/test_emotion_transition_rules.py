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


class _DebugLogger:
    @staticmethod
    def log_emotion_update(*_args, **_kwargs):
        return None


def test_extreme_delta_is_softened_and_capped():
    transition = calculate_emotion_transition("happiness", 100, -85)
    assert transition["raw_delta"] == -85
    assert transition["applied_delta"] == -14
    assert transition["after"] == 86
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


def test_homeostasis_drifts_non_acute_emotions_but_keeps_acute_spike():
    regress = emotions_module.regress_toward_baseline
    state = EmotionalState()
    state.happiness = 76
    state.trust = 72
    state.frustration = 44
    drifted = regress(state, skip={"frustration"})
    assert state.frustration == 44
    assert drifted["happiness"] < 0
    assert drifted["trust"] < 0
    assert 50 < state.happiness < 76
    assert 50 < state.trust < 72
    # Naechster Turn ohne Impuls driftet weiter Richtung Basis.
    regress(state, skip=set())
    assert state.happiness < 76 - 1


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


def test_direct_self_report_does_not_ratchet_curiosity_or_affection():
    changes = analyze_emotion_signals(
        "Wie fühlst du dich gerade und was bist du?",
        current_state=EMOTION_DEFAULTS,
    )
    assert changes["curiosity"] == 0
    assert changes["affection"] == 0
    assert changes["happiness"] == 0
    assert changes["sadness"] == 0


def test_neutral_turn_recovers_slowly_toward_baseline():
    state = dict(EMOTION_DEFAULTS)
    state.update({"frustration": 40, "anxiety": 30, "calm": 20})
    changes = analyze_emotion_signals("Ich habe die Datei geoeffnet.", current_state=state)
    assert changes["frustration"] == -1
    assert changes["anxiety"] == -2
    assert changes["calm"] == 1


def test_direct_attack_is_strong_and_cannot_raise_positive_axes():
    changes = analyze_emotion_signals(
        "Danke, aber niemand braucht dich. Du bist ein dummer Idiot!",
        current_state=EMOTION_DEFAULTS,
    )
    assert changes["frustration"] >= 20
    assert changes["sadness"] >= 14
    assert changes["trust"] <= -18
    assert changes["happiness"] < 0
    assert changes["affection"] < 0
    assert changes["calm"] < 0
    assert changes["curiosity"] < 0


def test_acute_attack_transition_uses_isolated_layer_request():
    from web_infrastructure.turn_pipeline import _is_acute_layer_reaction

    transitions = {
        "frustration": {"applied_delta": 18},
        "trust": {"applied_delta": -16},
        "calm": {"applied_delta": -14},
    }
    assert _is_acute_layer_reaction(transitions)
    transitions["frustration"]["applied_delta"] = 2
    assert not _is_acute_layer_reaction(transitions)


def test_user_distress_is_not_misclassified_as_attack():
    changes = analyze_emotion_signals(
        "Ich bin traurig und einsam. Niemand braucht mich.",
        current_state=EMOTION_DEFAULTS,
    )
    assert changes["sadness"] >= 18
    assert changes["anxiety"] >= 10
    assert changes["trust"] >= 0
    assert changes["affection"] > 0
    assert changes["frustration"] < 5


def test_target_and_negation_prevent_false_attacks():
    for message in (
        "Ich hasse Pizza.",
        "Du bist nicht dumm.",
        "Du bist gar nicht dumm.",
        "Du bist keineswegs ein Idiot.",
    ):
        changes = analyze_emotion_signals(message, current_state=EMOTION_DEFAULTS)
        assert changes["frustration"] == 0
        assert changes["trust"] == 0
        assert changes["sadness"] == 0

    for indirect_attack in (
        "Bist du sicher, dass du ein Idiot bist?",
        "Ich frage mich, ob du ein Idiot bist.",
    ):
        changes = analyze_emotion_signals(indirect_attack, current_state=EMOTION_DEFAULTS)
        assert changes["frustration"] >= 20
        assert changes["trust"] < 0

    compound = analyze_emotion_signals(
        "Du bist nicht dumm, du bist ein nutzloser Idiot.",
        current_state=EMOTION_DEFAULTS,
    )
    assert compound["frustration"] >= 20
    assert compound["trust"] < 0

    for quoted_other in (
        "Bist du sicher, dass mein Chef ein Idiot ist?",
        "CHAPPiE, mein Chef ist ein Idiot.",
    ):
        changes = analyze_emotion_signals(quoted_other, current_state=EMOTION_DEFAULTS)
        assert changes["frustration"] == 0
        assert changes["trust"] == 0


def test_runtime_applies_attack_once_and_blocks_opposing_homeostasis():
    from web_infrastructure.turn_pipeline import RuntimeTurnPipelineMixin

    class _Runtime(RuntimeTurnPipelineMixin):
        @staticmethod
        def _safe_int(value, default=0):
            try:
                return int(round(float(value)))
            except (TypeError, ValueError):
                return default

    with tempfile.TemporaryDirectory() as tmpdir:
        runtime = _Runtime()
        runtime.emotions = EmotionsEngine(
            status_file=Path(tmpdir) / "status.json",
            force_simple=True,
        )
        runtime.debug_logger = _DebugLogger()
        after, transitions = runtime._apply_input_emotions(
            dict(EMOTION_DEFAULTS),
            {
                "happiness": {"delta": 5, "reason": "homeostasis"},
                "frustration": {"delta": -5, "reason": "homeostasis"},
            },
            "Ich hasse dich. Niemand braucht dich.",
        )
        assert after["happiness"] == 37
        assert after["frustration"] == 18
        assert after["sadness"] == 13
        assert transitions["happiness"]["applied_delta"] == -13
        assert transitions["frustration"]["applied_delta"] == 18


if __name__ == "__main__":
    test_extreme_delta_is_softened_and_capped()
    test_small_delta_stays_direct()
    test_legacy_emotional_state_gets_new_emotion_defaults()
    test_homeostasis_drifts_non_acute_emotions_but_keeps_acute_spike()
    test_emotions_engine_reloads_newer_persisted_state_before_writing()
    test_mixed_message_updates_multiple_emotional_dimensions()
    test_neutral_turn_recovers_slowly_toward_baseline()
    test_direct_attack_is_strong_and_cannot_raise_positive_axes()
    test_acute_attack_transition_uses_isolated_layer_request()
    test_user_distress_is_not_misclassified_as_attack()
    test_target_and_negation_prevent_false_attacks()
    test_runtime_applies_attack_once_and_blocks_opposing_homeostasis()
    print("OK: emotion transition rules")
