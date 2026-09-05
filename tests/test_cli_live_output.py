"""Tests for clean live output: stray-print capture, sleep panel, input prompt.

Regression coverage for duplicated STEP-1 panels during sleep phase,
sleep output glued to the input line, and the input prompt label.
"""

import importlib
import io
import os
import sys
import threading
from unittest.mock import MagicMock

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

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


def _build_cli():
    m = _get_module()
    cli = m.CHAPPiEBrainCLI.__new__(m.CHAPPiEBrainCLI)
    cli.remote_url = None
    cli._use_remote = False
    cli._show_full_report = False
    cli.history = []
    cli.last_result = None
    cli.session_id = None
    return m, cli


def _capture_stdout(func, *args, **kwargs):
    saved = sys.stdout
    sys.stdout = io.StringIO()
    try:
        result = func(*args, **kwargs)
        return result, sys.stdout.getvalue()
    finally:
        sys.stdout = saved


# ── capture passes main output through when idle ──

def test_capture_passes_main_thread_through():
    m = _get_module()
    real = io.StringIO()
    cap = m._StrayOutputCapture(real)
    cap.write("direkt")
    assert real.getvalue() == "direkt"
    assert cap.drain() == ""


def test_capture_buffers_main_thread_while_streaming():
    m = _get_module()
    real = io.StringIO()
    cap = m._StrayOutputCapture(real)
    cap.main_capturing = True
    cap.write("gepuffert")
    assert real.getvalue() == ""
    assert cap.drain() == "gepuffert"


def test_capture_buffers_background_thread_always():
    m = _get_module()
    real = io.StringIO()
    cap = m._StrayOutputCapture(real)

    def worker():
        print("SCHLAFPHASE GESTARTET", file=cap)
        print("[SleepPhase] Energie wiederhergestellt: 96%", file=cap)

    t = threading.Thread(target=worker)
    t.start()
    t.join()
    assert real.getvalue() == ""
    drained = cap.drain()
    assert "SCHLAFPHASE GESTARTET" in drained
    assert "96%" in drained
    assert cap.drain() == ""


def test_capture_flush_never_raises():
    m = _get_module()
    cap = m._StrayOutputCapture(io.StringIO())
    cap.flush()


# ── drain renders its own info area ──

def test_drain_prints_background_block():
    m, cli = _build_cli()
    cli._out_capture = m._StrayOutputCapture(io.StringIO())
    cli._out_capture.main_capturing = True
    cli._out_capture.write("[SleepPhase] Energie wiederhergestellt: 96%\n")
    cli._out_capture.main_capturing = False
    _, output = _capture_stdout(cli._drain_background_output)
    assert "Hintergrund" in output
    assert "96%" in output


def test_drain_stays_silent_when_empty():
    m, cli = _build_cli()
    cli._out_capture = m._StrayOutputCapture(io.StringIO())
    _, output = _capture_stdout(cli._drain_background_output)
    assert output == ""


def test_drain_without_capture_is_noop():
    _, cli = _build_cli()
    if hasattr(cli, "_out_capture"):
        del cli._out_capture
    _, output = _capture_stdout(cli._drain_background_output)
    assert output == ""


# ── sleep info panel in compact report ──

def _minimal_result(**overrides):
    result = {
        "response_text": "hi",
        "formatted_answer": "hi",
        "processing_time_ms": 5,
        "provider": "vllm",
        "model": "qwen",
    }
    result.update(overrides)
    return result


def test_compact_report_shows_sleep_panel_when_triggered():
    _, cli = _build_cli()
    _, output = _capture_stdout(
        cli._display_compact_report, _minimal_result(auto_sleep_triggered=True)
    )
    assert "Schlafphase" in output


def test_compact_report_hides_sleep_panel_otherwise():
    _, cli = _build_cli()
    _, output = _capture_stdout(cli._display_compact_report, _minimal_result())
    assert "Schlafphase" not in output


def test_remote_meta_keeps_sleep_flag():
    m = _get_module()
    result = m.CHAPPiEBrainCLI._remote_meta_to_result({"auto_sleep_triggered": True})
    assert result["auto_sleep_triggered"] is True
    assert m.CHAPPiEBrainCLI._remote_meta_to_result({})["auto_sleep_triggered"] is False


# ── input prompt label ──

def test_prompt_uses_user_label():
    m, cli = _build_cli()
    assert m.CLI_USER_LABEL == "User"
    prompt = cli._input_prompt()
    assert "User >" in prompt
    assert "Benjamin" not in prompt


if __name__ == "__main__":
    test_capture_passes_main_thread_through()
    test_capture_buffers_main_thread_while_streaming()
    test_capture_buffers_background_thread_always()
    test_capture_flush_never_raises()
    test_drain_prints_background_block()
    test_drain_stays_silent_when_empty()
    test_drain_without_capture_is_noop()
    test_compact_report_shows_sleep_panel_when_triggered()
    test_compact_report_hides_sleep_panel_otherwise()
    test_remote_meta_keeps_sleep_flag()
    test_prompt_uses_user_label()
    print("OK: CLI live output")
