"""Tests for CLI v6.0 command handling: /help, /compact, /full, toggles, emotion names."""

import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

import importlib
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

class _MockBackend:
    def __init__(self):
        self.steering_manager = _MockSteering()
        self.emotions = _MockEmotions()
        self.memory = _MockMemory()
        self.debug_logger = _MockDebug()
        self.short_term_memory = _MockSTM()

    def get_status(self):
        return {"model": "test", "provider": "test", "two_step_enabled": True, "emotions": {}}

    def handle_command(self, cmd):
        if cmd == "/daily":
            return "daily output"
        return "Unbekannter Command: " + cmd


class _MockSteering:
    def is_local_provider(self):
        return True


class _MockEmotions:
    def get_state(self):
        return type("s", (), {"to_dict": lambda s: {}})()

    def set_emotion(self, name, val):
        pass

    def reset(self):
        pass


class _MockMemory:
    pass


class _MockDebug:
    def enable(self):
        pass

    def disable(self):
        pass


class _MockSTM:
    def get_active_entries(self):
        return []


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


# ── /help output content ────────────────────────────────────────

def test_help_contains_v6_commands():
    m = _get_module()
    cli = _build_local_cli()
    import io

    saved = sys.stdout
    try:
        sys.stdout = io.StringIO()
        cli._print_help()
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = sys.__stdout__

    assert "CHAPPiE Terminal Interface v6.0" in output
    assert "/help" in output
    assert "/status" in output
    assert "/exit" in output
    assert "Ctrl+C" in output


def test_help_contains_post_output_section():
    m = _get_module()
    cli = _build_local_cli()
    import io

    saved = sys.stdout
    try:
        sys.stdout = io.StringIO()
        cli._print_help()
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = sys.__stdout__

    assert "Nach Ausgabe Befehle" in output
    assert "/last" in output
    assert "/raw" in output
    assert "/trace" in output
    assert "/compact" in output
    assert "/full" in output


# ── command toggle states ────────────────────────────────────────

def test_compact_toggle():
    cli = _build_local_cli()
    assert cli._show_full_report is False
    import io
    saved = sys.stdout
    try:
        sys.stdout = io.StringIO()
        result = cli._handle_command("/compact")
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = sys.__stdout__
    assert result is True
    assert cli._show_full_report is False
    assert "Compact-Mode" in output


def test_full_toggle():
    cli = _build_local_cli()
    import io
    saved = sys.stdout
    try:
        sys.stdout = io.StringIO()
        result = cli._handle_command("/full")
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = sys.__stdout__
    assert result is True
    assert cli._show_full_report is True
    assert "Full-Mode" in output


def test_exit_returns_false():
    cli = _build_local_cli()
    assert cli._handle_command("/exit") is False
    assert cli._handle_command("/quit") is False


def test_status_returns_true():
    cli = _build_local_cli()
    assert cli._handle_command("/status") is True


def test_clear_returns_true():
    cli = _build_local_cli()
    cli.history = [{"role": "user", "content": "hi"}]
    cli.last_result = {"a": 1}
    result = cli._handle_command("/clear")
    assert result is True
    assert cli.history == []
    assert cli.last_result is None


def test_last_without_result():
    cli = _build_local_cli()
    result = cli._handle_command("/last")
    assert result is True


def test_last_with_result():
    cli = _build_local_cli()
    cli.last_result = {
        "response_text": "hi",
        "formatted_answer": "hi",
        "emotions": {"happiness": 60},
        "emotions_before": {"happiness": 55},
        "intent_type": "casual_chat",
        "intent_confidence": 0.9,
        "provider": "vllm",
        "model": "qwen",
        "processing_time_ms": 500,
    }
    result = cli._handle_command("/last")
    assert result is True


def test_raw_without_result():
    cli = _build_local_cli()
    result = cli._handle_command("/raw")
    assert result is True


def test_raw_with_result():
    cli = _build_local_cli()
    cli.last_result = {
        "response_text": "raw output",
        "intent_raw_json": {"key": "val"},
    }
    result = cli._handle_command("/raw")
    assert result is True


def test_trace_without_result():
    cli = _build_local_cli()
    result = cli._handle_command("/trace")
    assert result is True


def test_trace_with_result():
    cli = _build_local_cli()
    cli.last_result = {
        "causal_trace": [
            {"phase": "Input", "driver": "test", "effect": "test"},
        ],
    }
    result = cli._handle_command("/trace")
    assert result is True


def test_history_empty():
    cli = _build_local_cli()
    result = cli._handle_command("/history")
    assert result is True


def test_history_with_messages():
    cli = _build_local_cli()
    cli.history = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]
    result = cli._handle_command("/history")
    assert result is True


def test_debug_toggle():
    cli = _build_local_cli()
    assert cli._handle_command("/debug on") is True
    assert cli._handle_command("/debug off") is True
    assert cli._handle_command("/debug invalid") is True


def test_invalid_emotion_name():
    cli = _build_local_cli()
    result = cli._handle_command("/emotion nonexistent 50")
    assert result is True


def test_emotion_invalid_value():
    cli = _build_local_cli()
    result = cli._handle_command("/emotion happiness abc")
    assert result is True


def test_emotion_wrong_arg_count():
    cli = _build_local_cli()
    result = cli._handle_command("/emotion happiness")
    assert result is True


def test_unknown_command():
    cli = _build_local_cli()
    result = cli._handle_command("/unknowncmd")
    assert result is True


def test_non_slash_unknown():
    cli = _build_local_cli()
    result = cli._handle_command("hello")
    assert result is True


def test_memory_command():
    cli = _build_local_cli()
    result = cli._handle_command("/memory")
    assert result is True


def test_runtime_remote_warns():
    m = _get_module()
    cli = m.CHAPPiEBrainCLI.__new__(m.CHAPPiEBrainCLI)
    cli._use_remote = True
    assert cli._handle_command("/runtime") is True


def test_steering_remote_warns():
    m = _get_module()
    cli = m.CHAPPiEBrainCLI.__new__(m.CHAPPiEBrainCLI)
    cli._use_remote = True
    assert cli._handle_command("/steering") is True


if __name__ == "__main__":
    test_help_contains_v6_commands()
    test_help_contains_post_output_section()
    test_compact_toggle()
    test_full_toggle()
    test_exit_returns_false()
    test_status_returns_true()
    test_clear_returns_true()
    test_last_without_result()
    test_last_with_result()
    test_raw_without_result()
    test_raw_with_result()
    test_trace_without_result()
    test_trace_with_result()
    test_history_empty()
    test_history_with_messages()
    test_debug_toggle()
    test_invalid_emotion_name()
    test_emotion_invalid_value()
    test_emotion_wrong_arg_count()
    test_unknown_command()
    test_non_slash_unknown()
    test_memory_command()
    test_runtime_remote_warns()
    test_steering_remote_warns()
    print("OK: CLI v6.0 command handling")
