"""Tests for command_service._run_emotion: delta syntax, clamping, help display."""

import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from unittest.mock import MagicMock
from api.services.command_service import _run_emotion, EMOTION_NAMES
from config.emotions import EMOTION_DEFAULTS


class _MockEmotionsEngine:
    def __init__(self):
        self._values: dict[str, int] = {
            "happiness": 56, "trust": 47, "energy": 80,
            "curiosity": 59, "frustration": 8, "motivation": 77,
            "sadness": 15, "affection": 45, "anxiety": 0, "calm": 50,
        }
        self._calls: list[tuple[str, int]] = []

    def set_emotion(self, name: str, val: int):
        self._calls.append((name, val))
        self._values[name] = val


def _make_backend(emotions_override: dict[str, int] | None = None):
    backend = MagicMock()
    default_emotions = {
        "happiness": 56, "trust": 47, "energy": 80,
        "curiosity": 59, "frustration": 8, "motivation": 77,
        "sadness": 15, "affection": 45, "anxiety": 0, "calm": 50,
    }
    emotions = dict(default_emotions)
    if emotions_override:
        emotions.update(emotions_override)

    backend._get_emotions_snapshot.return_value = emotions
    backend.emotions = _MockEmotionsEngine()
    return backend


# ── /emotion (no args): show status + help ───────────────────────

def test_emotion_no_args_shows_status():
    backend = _make_backend()
    result = _run_emotion(backend, "/emotion")

    assert "Aktuelle Emotions-Werte" in result["response_text"]
    assert "happiness" in result["response_text"]
    assert "Syntax" in result["response_text"]


# ── delta syntax ─────────────────────────────────────────────────

def test_emotion_delta_increase():
    backend = _make_backend()
    result = _run_emotion(backend, "/emotion happiness +10")

    assert "66" in result["response_text"]
    assert backend.emotions._calls == [("happiness", 66)]


def test_emotion_delta_decrease():
    backend = _make_backend()
    result = _run_emotion(backend, "/emotion sadness -5")

    assert "10" in result["response_text"]
    assert backend.emotions._calls == [("sadness", 10)]


def test_emotion_delta_explicit_positive():
    backend = _make_backend()
    result = _run_emotion(backend, "/emotion motivation +3")

    assert "80" in result["response_text"]
    assert backend.emotions._calls == [("motivation", 80)]


# ── absolute syntax ──────────────────────────────────────────────

def test_emotion_absolute_set():
    backend = _make_backend()
    result = _run_emotion(backend, "/emotion energy 50")

    assert "50" in result["response_text"]
    assert backend.emotions._calls == [("energy", 50)]


def test_emotion_absolute_set_zero():
    backend = _make_backend()
    result = _run_emotion(backend, "/emotion frustration 0")

    assert "0" in result["response_text"]
    assert backend.emotions._calls == [("frustration", 0)]


# ── clamping ─────────────────────────────────────────────────────

def test_emotion_clamp_maximum():
    backend = _make_backend()
    result = _run_emotion(backend, "/emotion happiness +50")

    assert "100" in result["response_text"]
    assert "Maximum" in result["response_text"]
    assert backend.emotions._calls == [("happiness", 100)]


def test_emotion_clamp_minimum():
    backend = _make_backend()
    result = _run_emotion(backend, "/emotion sadness -20")

    assert "0" in result["response_text"]
    assert "Minimum" in result["response_text"]
    assert backend.emotions._calls == [("sadness", 0)]


def test_emotion_absolute_clamp_above():
    backend = _make_backend()
    result = _run_emotion(backend, "/emotion happiness 150")

    assert "100" in result["response_text"]
    assert backend.emotions._calls == [("happiness", 100)]


def test_emotion_minus_prefix_is_delta():
    """Verifies that -N is treated as delta, not absolute."""
    backend = _make_backend()
    result = _run_emotion(backend, "/emotion trust -100")

    assert "0" in result["response_text"]
    assert "Minimum" in result["response_text"]
    assert backend.emotions._calls == [("trust", 0)]


# ── edge cases ───────────────────────────────────────────────────

def test_emotion_delta_zero():
    backend = _make_backend()
    result = _run_emotion(backend, "/emotion happiness +0")

    assert "56" in result["response_text"]
    assert backend.emotions._calls == [("happiness", 56)]


def test_emotion_at_boundary_low():
    backend = _make_backend(emotions_override={"happiness": 0})
    result = _run_emotion(backend, "/emotion happiness -1")

    assert "0" in result["response_text"]
    assert "Minimum" in result["response_text"]
    assert backend.emotions._calls == [("happiness", 0)]


def test_emotion_at_boundary_high():
    backend = _make_backend(emotions_override={"happiness": 100})
    result = _run_emotion(backend, "/emotion happiness +1")

    assert "100" in result["response_text"]
    assert "Maximum" in result["response_text"]
    assert backend.emotions._calls == [("happiness", 100)]


# ── error handling ──────────────────────────────────────────────

def test_emotion_unknown_name():
    backend = _make_backend()
    result = _run_emotion(backend, "/emotion nonexistent +10")

    assert "Unbekannte Emotion" in result["response_text"]
    assert len(backend.emotions._calls) == 0


def test_emotion_invalid_value():
    backend = _make_backend()
    result = _run_emotion(backend, "/emotion happiness abc")

    assert "Ungueltiger Wert" in result["response_text"]
    assert len(backend.emotions._calls) == 0


def test_emotion_missing_value():
    backend = _make_backend()
    result = _run_emotion(backend, "/emotion happiness")

    assert "Nutze" in result["response_text"]
    assert len(backend.emotions._calls) == 0


def test_emotion_just_name():
    backend = _make_backend()
    result = _run_emotion(backend, "/emotion happiness ")

    assert "Nutze" in result["response_text"]
    assert len(backend.emotions._calls) == 0


# ── all emotions work ───────────────────────────────────────────

def test_all_emotions_accepted():
    backend = _make_backend()
    for name in EMOTION_NAMES:
        result = _run_emotion(backend, f"/emotion {name} 42")

    assert len(backend.emotions._calls) == len(EMOTION_DEFAULTS)


# ── runner ───────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        ("no-args shows status", test_emotion_no_args_shows_status),
        ("delta increase", test_emotion_delta_increase),
        ("delta decrease", test_emotion_delta_decrease),
        ("delta positive", test_emotion_delta_explicit_positive),
        ("absolute set", test_emotion_absolute_set),
        ("absolute zero", test_emotion_absolute_set_zero),
        ("clamp maximum", test_emotion_clamp_maximum),
        ("clamp minimum", test_emotion_clamp_minimum),
        ("absolute clamp above", test_emotion_absolute_clamp_above),
        ("minus prefix is delta", test_emotion_minus_prefix_is_delta),
        ("delta zero", test_emotion_delta_zero),
        ("boundary low", test_emotion_at_boundary_low),
        ("boundary high", test_emotion_at_boundary_high),
        ("unknown name", test_emotion_unknown_name),
        ("invalid value", test_emotion_invalid_value),
        ("missing value", test_emotion_missing_value),
        ("just name trailing space", test_emotion_just_name),
        ("all emotions", test_all_emotions_accepted),
    ]
    for name, fn in tests:
        fn()
        print(f"  OK: {name}")
    print(f"OK: command_service /emotion ({len(tests)} tests)")
