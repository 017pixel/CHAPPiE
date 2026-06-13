"""Tests for CLI /emotion delta syntax: +N, -N, absolute, clamping, no-args help."""

import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

import importlib
import io
from unittest.mock import MagicMock

for mod in (
    "chromadb", "chromadb.config", "requests", "openai",
    "brain.nvidia_brain", "brain.steering_api_server",
    "brain.steering_backend", "brain.deep_think",
    "brain.global_workspace", "brain.action_response",
    "brain.response_parser", "brain.agents",
    "life", "memory", "memory.memory_engine",
    "memory.emotions_engine", "memory.sleep_phase",
    "memory.forgetting_curve", "memory.context_files",
    "memory.chat_manager", "memory.short_term_memory",
    "memory.personality_manager",
    "memory.function_registry", "memory.intent_processor",
    "memory.debug_logger", "sentence_transformers",
):
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()
sys.modules["ollama"] = MagicMock()


def _get_module():
    sys.modules.pop("chappie_brain_cli", None)
    return importlib.import_module("chappie_brain_cli")


# ── mock setup ───────────────────────────────────────────────────

class _TrackedEmotions:
    """Mock emotions engine that tracks set_emotion calls."""

    def __init__(self):
        self._values: dict[str, int] = {
            "happiness": 56, "trust": 47, "energy": 80,
            "curiosity": 59, "frustration": 8, "motivation": 77,
            "sadness": 15,
        }
        self._calls: list[tuple[str, int]] = []

    def get_state(self):
        state = type("EmotionalState", (), {})
        for name, val in self._values.items():
            setattr(state, name, val)
        state.to_dict = lambda s=self: dict(s._values)
        return state

    def set_emotion(self, name: str, val: int):
        self._calls.append((name, val))
        self._values[name] = val

    def reset(self):
        pass


class _MockSteering:
    def is_local_provider(self):
        return True


class _MockDebug:
    def enable(self): pass
    def disable(self): pass


class _MockSTM:
    def get_active_entries(self):
        return []


class _MockBackend:
    def __init__(self):
        self.steering_manager = _MockSteering()
        self.emotions = _TrackedEmotions()
        self.memory = MagicMock()
        self.debug_logger = _MockDebug()
        self.short_term_memory = _MockSTM()

    def get_status(self):
        return {"model": "test", "provider": "test", "two_step_enabled": True, "emotions": {}}

    def handle_command(self, cmd):
        return "Unbekannter Command: " + cmd


def _build_local_cli():
    m = _get_module()
    cli = m.CHAPPiEBrainCLI.__new__(m.CHAPPiEBrainCLI)
    cli.remote_url = None
    cli._use_remote = False
    cli._show_full_report = False
    cli.history = []
    cli.last_result = None
    cli.backend = _MockBackend()
    cli.emotions = cli.backend.emotions
    cli.memory = cli.backend.memory
    cli.steering = cli.backend.steering_manager
    cli.short_term = cli.backend.short_term_memory
    return cli


def _capture_stdout(fn):
    saved = sys.stdout
    try:
        sys.stdout = io.StringIO()
        fn()
        return sys.stdout.getvalue()
    finally:
        sys.stdout = sys.__stdout__


# ── /emotion no-args: show status + help ─────────────────────────

def test_emotion_no_args_shows_status_and_syntax():
    cli = _build_local_cli()
    output = _capture_stdout(lambda: cli._handle_command("/emotion"))

    assert "happiness" in output
    assert "trust" in output
    assert "energy" in output
    assert "Syntax" in output
    assert "+10" in output
    assert "-5" in output


# ── /emotion <name> +delta ───────────────────────────────────────

def test_emotion_delta_increase():
    cli = _build_local_cli()
    output = _capture_stdout(lambda: cli._handle_command("/emotion happiness +10"))

    assert "66" in output or "happiness" in output
    assert cli.emotions._values["happiness"] == 66
    assert ("happiness", 66) in cli.emotions._calls


def test_emotion_delta_decrease():
    cli = _build_local_cli()
    output = _capture_stdout(lambda: cli._handle_command("/emotion sadness -5"))

    assert cli.emotions._values["sadness"] == 10
    assert ("sadness", 10) in cli.emotions._calls


def test_emotion_delta_negative_number():
    cli = _build_local_cli()
    output = _capture_stdout(lambda: cli._handle_command("/emotion frustration -3"))

    assert cli.emotions._values["frustration"] == 5
    assert ("frustration", 5) in cli.emotions._calls


# ── /emotion <name> absolute ─────────────────────────────────────

def test_emotion_absolute_set():
    cli = _build_local_cli()
    output = _capture_stdout(lambda: cli._handle_command("/emotion energy 50"))

    assert cli.emotions._values["energy"] == 50
    assert ("energy", 50) in cli.emotions._calls


def test_emotion_absolute_set_zero():
    cli = _build_local_cli()
    output = _capture_stdout(lambda: cli._handle_command("/emotion sadness 0"))

    assert cli.emotions._values["sadness"] == 0
    assert ("sadness", 0) in cli.emotions._calls


def test_emotion_absolute_set_hundred():
    cli = _build_local_cli()
    output = _capture_stdout(lambda: cli._handle_command("/emotion trust 100"))

    assert cli.emotions._values["trust"] == 100
    assert ("trust", 100) in cli.emotions._calls


# ── clamping tests ───────────────────────────────────────────────

def test_emotion_delta_clamp_maximum():
    cli = _build_local_cli()
    output = _capture_stdout(lambda: cli._handle_command("/emotion happiness +50"))

    assert cli.emotions._values["happiness"] == 100
    assert ("happiness", 100) in cli.emotions._calls
    assert "Maximum" in output


def test_emotion_delta_clamp_minimum():
    cli = _build_local_cli()
    output = _capture_stdout(lambda: cli._handle_command("/emotion sadness -20"))

    assert cli.emotions._values["sadness"] == 0
    assert ("sadness", 0) in cli.emotions._calls
    assert "Minimum" in output


def test_emotion_absolute_clamp_above():
    cli = _build_local_cli()
    output = _capture_stdout(lambda: cli._handle_command("/emotion happiness 150"))

    assert cli.emotions._values["happiness"] == 100
    assert ("happiness", 100) in cli.emotions._calls


def test_emotion_minus_prefix_is_delta():
    """Verifies that -N is treated as delta, not absolute (clamps at 0)."""
    cli = _build_local_cli()
    output = _capture_stdout(lambda: cli._handle_command("/emotion trust -100"))

    # -100 from 47 → -53 → clamped to 0
    assert cli.emotions._values["trust"] == 0
    assert ("trust", 0) in cli.emotions._calls
    assert "Minimum" in output


# ── error handling ──────────────────────────────────────────────

def test_emotion_unknown_name():
    cli = _build_local_cli()
    output = _capture_stdout(lambda: cli._handle_command("/emotion nonexistent +10"))

    assert "Unbekannte Emotion" in output or "nonexistent" in output
    assert len(cli.emotions._calls) == 0


def test_emotion_invalid_value():
    cli = _build_local_cli()
    output = _capture_stdout(lambda: cli._handle_command("/emotion happiness abc"))

    assert "Ungueltiger Wert" in output or "abc" in output
    assert len(cli.emotions._calls) == 0


def test_emotion_missing_value():
    cli = _build_local_cli()
    output = _capture_stdout(lambda: cli._handle_command("/emotion happiness"))

    assert "[+/-]" in output or "+/-" in output
    assert len(cli.emotions._calls) == 0


def test_emotion_missing_args():
    cli = _build_local_cli()
    output = _capture_stdout(lambda: cli._handle_command("/emotion"))

    # Should not crash, should show status
    assert len(cli.emotions._calls) == 0


# ── /help contains new syntax ────────────────────────────────────

def test_help_contains_emotion_delta_syntax():
    m = _get_module()
    cli = _build_local_cli()
    output = _capture_stdout(lambda: cli._print_help())

    assert "/emotion" in output
    assert "[+/-]" in output or "erhoehen" in output or "senken" in output


# ── runner ───────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        ("no-args shows status + syntax", test_emotion_no_args_shows_status_and_syntax),
        ("delta increase", test_emotion_delta_increase),
        ("delta decrease", test_emotion_delta_decrease),
        ("delta negative number", test_emotion_delta_negative_number),
        ("absolute set", test_emotion_absolute_set),
        ("absolute set zero", test_emotion_absolute_set_zero),
        ("absolute set hundred", test_emotion_absolute_set_hundred),
        ("clamp maximum", test_emotion_delta_clamp_maximum),
        ("clamp minimum", test_emotion_delta_clamp_minimum),
        ("absolute clamp above", test_emotion_absolute_clamp_above),
        ("minus prefix is delta", test_emotion_minus_prefix_is_delta),
        ("unknown name error", test_emotion_unknown_name),
        ("invalid value error", test_emotion_invalid_value),
        ("missing value usage", test_emotion_missing_value),
        ("no args no crash", test_emotion_missing_args),
        ("help contains delta syntax", test_help_contains_emotion_delta_syntax),
    ]
    for name, fn in tests:
        fn()
        print(f"  OK: {name}")
    print(f"OK: CLI /emotion delta syntax ({len(tests)} tests)")
