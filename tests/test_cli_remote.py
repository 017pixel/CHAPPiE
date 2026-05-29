"""Tests for CLI v6.0 RemoteBackend: SSE parsing, URL handling, command routing."""

import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

import importlib
from unittest.mock import MagicMock, patch

for mod in (
    "chromadb", "chromadb.config", "openai",
    "brain.nvidia_brain", "brain.steering_api_server",
    "brain.steering_backend", "brain.deep_think",
    "brain.global_workspace", "brain.action_response",
    "brain.response_parser", "brain.agents",
    "life", "memory", "memory.memory_engine",
    "memory.emotions_engine", "memory.sleep_phase",
    "memory.forgetting_curve", "memory.context_files",
    "memory.chat_manager", "memory.short_term_memory",
    "memory.short_term_memory_v2", "memory.personality_manager",
    "memory.function_registry", "memory.intent_processor",
    "memory.debug_logger", "sentence_transformers",
):
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()
sys.modules["ollama"] = MagicMock()

# Always mock requests for testing — CLI gracefully handles missing requests
sys.modules["requests"] = MagicMock()


def _get_module():
    sys.modules.pop("chappie_brain_cli", None)
    return importlib.import_module("chappie_brain_cli")


def _make_remote():
    m = _get_module()
    return m.RemoteBackend("http://localhost:8010")


# ── remote URL normalisation ─────────────────────────────────────

def test_remote_backend_strips_trailing_slash():
    m = _get_module()
    rb = m.RemoteBackend("http://localhost:8010/")
    assert rb.base_url == "http://localhost:8010"


def test_remote_backend_preserves_no_slash():
    m = _get_module()
    rb = m.RemoteBackend("http://192.168.1.1:8010")
    assert rb.base_url == "http://192.168.1.1:8010"


# ── remote get_status ────────────────────────────────────────────

def test_remote_get_status_success():
    m = _get_module()
    mock_get = MagicMock()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"model": "qwen", "provider": "vllm"}
    mock_get.return_value = mock_resp

    with patch.object(m.requests, "get", mock_get):
        rb = _make_remote()
        status = rb.get_status()
        assert status == {"model": "qwen", "provider": "vllm"}
        mock_get.assert_called_once_with("http://localhost:8010/", timeout=5)


def test_remote_get_status_failure():
    m = _get_module()
    mock_get = MagicMock(side_effect=Exception("connection refused"))
    with patch.object(m.requests, "get", mock_get):
        rb = _make_remote()
        status = rb.get_status()
        assert status == {}


# ── remote stream_events SSE parsing ─────────────────────────────

def test_stream_events_parses_sse_format():
    m = _get_module()
    sse_lines = [
        'event: turn_started\n',
        'data: {"session_id":"abc","message_id":"123"}\n',
        '\n',
        'event: token\n',
        'data: {"content":"Hello","token_type":"answer"}\n',
        '\n',
        'event: status\n',
        'data: {"event":"status","step":1,"status_text":"done"}\n',
        '\n',
        'event: turn_finished\n',
        'data: {"session_id":"abc","assistant_message":{"role":"assistant","content":"Hello","metadata":{}}}\n',
    ]

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.iter_lines.return_value = sse_lines
    mock_post = MagicMock(return_value=mock_response)

    with patch.object(m.requests, "post", mock_post):
        rb = _make_remote()
        events = list(rb.stream_events("hi"))

    assert len(events) >= 3

    token_events = [e for e in events if e.get("_sse_event") == "token"]
    assert len(token_events) == 1
    assert token_events[0]["content"] == "Hello"
    assert token_events[0]["token_type"] == "answer"

    status_events = [e for e in events if e.get("_sse_event") == "status"]
    assert len(status_events) == 1


def test_stream_events_json_decode_error():
    m = _get_module()
    sse_lines = ['event: token\n', 'data: {invalid json\n']
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.iter_lines.return_value = sse_lines
    mock_post = MagicMock(return_value=mock_response)

    with patch.object(m.requests, "post", mock_post):
        rb = _make_remote()
        events = list(rb.stream_events("hi"))
    assert len(events) == 0


def test_stream_events_connection_error():
    m = _get_module()
    mock_post = MagicMock(side_effect=Exception("timeout"))
    with patch.object(m.requests, "post", mock_post):
        rb = _make_remote()
        events = list(rb.stream_events("hi"))
    assert len(events) == 0


# ── remote handle_command ────────────────────────────────────────

def test_remote_handle_command_success():
    m = _get_module()
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"output": "result"}
    mock_post = MagicMock(return_value=mock_resp)

    with patch.object(m.requests, "post", mock_post):
        rb = _make_remote()
        result = rb.handle_command("/status")
    assert result == "result"


def test_remote_handle_command_error():
    m = _get_module()
    mock_post = MagicMock(side_effect=Exception("timeout"))
    with patch.object(m.requests, "post", mock_post):
        rb = _make_remote()
        result = rb.handle_command("/status")
    assert result.startswith("Error")


# ── remote_meta_to_result edge cases ─────────────────────────────

def test_remote_meta_to_result_empty_metadata():
    m = _get_module()
    result = m.CHAPPiEBrainCLI._remote_meta_to_result({})
    assert isinstance(result, dict)
    assert result["response_text"] == ""
    assert result["emotions"] == {}
    assert result["intent_type"] == "?"
    assert result["processing_time_ms"] == 0
    assert result["reasoning_only"] is False
    assert result["formatting_failed"] is False


def test_remote_meta_to_result_all_life_fields():
    m = _get_module()
    metadata = {
        "life_snapshot": {"clock": {"phase": "day"}},
        "memory_consolidation": {"ltm_loaded": 5},
        "debug_entries": [{"cat": "x"}],
        "sleep_status": {},
        "auto_sleep_triggered": True,
    }
    result = m.CHAPPiEBrainCLI._remote_meta_to_result(metadata)
    assert result["life_snapshot"] == {"clock": {"phase": "day"}}
    assert result["memory_consolidation"] == {"ltm_loaded": 5}
    assert result["debug_entries"] == [{"cat": "x"}]
    assert result["sleep_status"] == {}
    assert result["auto_sleep_triggered"] is True


if __name__ == "__main__":
    test_remote_backend_strips_trailing_slash()
    test_remote_backend_preserves_no_slash()
    test_remote_get_status_success()
    test_remote_get_status_failure()
    test_stream_events_parses_sse_format()
    test_stream_events_json_decode_error()
    test_stream_events_connection_error()
    test_remote_handle_command_success()
    test_remote_handle_command_error()
    test_remote_meta_to_result_empty_metadata()
    test_remote_meta_to_result_all_life_fields()
    print("OK: CLI v6.0 remote backend")
