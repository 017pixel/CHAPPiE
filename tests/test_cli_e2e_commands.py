"""E2E tests for every CLI slash command: routing, sessions, restart, help layout.

Covers local and remote paths of CHAPPiEBrainCLI._handle_command plus the
RemoteBackend session contract (session_id + command_mode payloads).
"""

import builtins
import importlib
import io
import os
import re
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

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


def _emotion_state(value=50):
    m = _get_module()
    return SimpleNamespace(**{name: value for name in m.EMOTION_NAMES})


def _build_local_cli():
    m = _get_module()
    backend = MagicMock()
    backend.get_status.return_value = {
        "model": "test", "provider": "test",
        "two_step_enabled": True, "emotions": {},
    }
    backend.emotions.get_state.return_value = _emotion_state()
    backend.emotions.get_state.return_value.to_dict = lambda: {}
    backend.steering_manager.is_local_provider.return_value = True
    backend.steering_manager.build_debug_report.return_value = {
        "mode": "VEKTOR", "steering_active": True,
        "dominant_vector": "neutral", "dominant_strength": 0.5,
        "base_vectors": [{"name": "happiness"}],
    }
    backend.short_term_memory.get_active_entries.return_value = []
    backend.memory.search_memory.return_value = []
    backend.context_files.get_soul_context.return_value = "soul"
    backend.context_files.get_user_context.return_value = "user"
    backend.context_files.get_preferences_context.return_value = "prefs"
    backend.chat_manager.ensure_session_id.side_effect = lambda sid: sid or "sess-1"
    backend.chat_manager.load_session.return_value = {"id": "sess-1", "messages": [], "title": "t"}
    backend.chat_manager.list_sessions.return_value = []
    backend.chat_manager.create_message_id.return_value = "msg-1"
    backend.build_assistant_message.return_value = {"content": "hi", "metadata": {}}
    backend.debug_logger.enabled = True
    backend.debug_logger.get_entries_as_dict.return_value = []
    backend.handle_command.return_value = "Unbekannter Command: /nope"

    cli = m.CHAPPiEBrainCLI.__new__(m.CHAPPiEBrainCLI)
    cli.remote_url = None
    cli._use_remote = False
    cli._show_full_report = False
    cli.history = []
    cli.last_result = None
    cli.session_id = None
    cli.backend = backend
    cli.emotions = backend.emotions
    cli.memory = backend.memory
    cli.steering = backend.steering_manager
    cli.short_term = backend.short_term_memory
    cli.context = backend.context_files
    return m, cli


def _build_remote_cli():
    m = _get_module()
    cli = m.CHAPPiEBrainCLI.__new__(m.CHAPPiEBrainCLI)
    cli.remote_url = "http://localhost:8010"
    cli._use_remote = True
    cli._show_full_report = False
    cli.history = []
    cli.last_result = None
    cli.session_id = "sess-9"
    cli.remote = m.RemoteBackend("http://localhost:8010")
    cli.remote.session_id = "sess-9"
    return m, cli


def _run_quiet(func, *args, **kwargs):
    saved = sys.stdout
    sys.stdout = io.StringIO()
    try:
        result = func(*args, **kwargs)
        return result, sys.stdout.getvalue()
    finally:
        sys.stdout = saved


# ── local routing: every command returns True (False only for exit) ──

LOCAL_COMMANDS = [
    "/status", "/help", "/last", "/raw", "/trace", "/compact", "/full",
    "/runtime", "/model", "/thinking", "/thinking true", "/thinking off",
    "/thinking bogus", "/steering", "/emotion", "/emotion happiness",
    "/emotion happiness +10", "/emotion energy 50", "/emotion bogus 10",
    "/emotion happiness abc", "/resetemotions", "/sleep", "/memory",
    "/memory suche", "/history", "/clear", "/new", "/sessions",
    "/session sess-1", "/debug", "/debug on", "/debug off", "/md",
    "/stats", "/think", "/deep think 3", "/life", "/unknowncmd",
]


def test_local_commands_all_route():
    m, cli = _build_local_cli()
    with patch("api.services.command_service.execute_slash_command") as exec_cmd:
        exec_cmd.return_value = {"response_text": "Unbekannter Command: /x"}
        for cmd in LOCAL_COMMANDS:
            result, _ = _run_quiet(cli._handle_command, cmd)
            assert result is True, f"{cmd} should return True"


def test_exit_returns_false():
    _, cli = _build_local_cli()
    assert cli._handle_command("/exit") is False
    assert cli._handle_command("/quit") is False


def test_last_raw_trace_with_result():
    _, cli = _build_local_cli()
    cli.last_result = {
        "response_text": "raw", "formatted_answer": "fmt",
        "intent_raw_json": {"a": 1},
        "causal_trace": [{"phase": "Input", "driver": "d", "effect": "e"}],
    }
    for cmd in ("/last", "/raw", "/trace"):
        result, _ = _run_quiet(cli._handle_command, cmd)
        assert result is True


def test_history_with_messages():
    _, cli = _build_local_cli()
    cli.history = [{"role": "user", "content": "hi"}]
    result, output = _run_quiet(cli._handle_command, "/history")
    assert result is True
    assert "hi" in output


def test_clear_creates_empty_history():
    _, cli = _build_local_cli()
    cli.history = [{"role": "user", "content": "hi"}]
    with patch("api.services.command_service.execute_slash_command") as exec_cmd:
        exec_cmd.return_value = {"response_text": "neu", "replacement_session_id": "sess-2"}
        cli.backend.chat_manager.load_session.return_value = {"id": "sess-2", "messages": []}
        result, _ = _run_quiet(cli._handle_command, "/clear")
    assert result is True
    assert cli.history == []
    assert cli.last_result is None


# ── remote routing ──

def _mock_requests(m, get_json=None, post_json=None):
    mock_get = MagicMock()
    get_resp = MagicMock()
    get_resp.json.return_value = get_json if get_json is not None else {}
    mock_get.return_value = get_resp
    mock_post = MagicMock()
    post_resp = MagicMock()
    post_resp.raise_for_status = MagicMock()
    post_resp.json.return_value = post_json if post_json is not None else {}
    mock_post.return_value = post_resp
    return patch.object(m.requests, "get", mock_get), patch.object(m.requests, "post", mock_post)


def test_remote_commands_all_route():
    m, cli = _build_remote_cli()
    get_ctx, post_ctx = _mock_requests(
        m,
        get_json={"emotions": {"happiness": 50}, "vllm_model": "qwen", "llm_provider": "vllm",
                  "chain_of_thought": True, "items": [], "sessions": []},
        post_json={"output": "ok", "session_id": "sess-9"},
    )
    with get_ctx, post_ctx:
        for cmd in ("/status", "/runtime", "/model", "/thinking", "/steering",
                    "/emotion", "/resetemotions", "/sleep", "/memory", "/md",
                    "/sessions", "/stats", "/life", "/unknowncmd"):
            result, _ = _run_quiet(cli._handle_command, cmd)
            assert result is True, f"remote {cmd} should return True"


# ── restart ──

def test_restart_chappie_restarts_both_services():
    m, cli = _build_local_cli()
    with patch.object(m.CHAPPiEBrainCLI, "_run_systemctl", return_value=(True, "")) as run_mock:
        result, _ = _run_quiet(cli._handle_command, "/restart chappie")
    assert result is True
    assert [c.args[0] for c in run_mock.call_args_list] == ["chappie-web", "chappie-frontend"]


def test_restart_chappie_reports_failure():
    m, cli = _build_local_cli()
    with patch.object(m.CHAPPiEBrainCLI, "_run_systemctl", return_value=(False, "boom")):
        result, output = _run_quiet(cli._handle_command, "/restart chappie")
    assert result is True
    assert "fehlgeschlagen" in output


def test_restart_cli_reexecs_process():
    m, cli = _build_local_cli()
    with patch("os.execv") as execv:
        result, _ = _run_quiet(cli._handle_command, "/restart cli")
    assert result is True
    execv.assert_called_once()


def test_restart_prompt_choice_chappie_and_cli():
    m, cli = _build_local_cli()
    with patch.object(builtins, "input", return_value="1"):
        with patch.object(m.CHAPPiEBrainCLI, "_run_systemctl", return_value=(True, "")) as run_mock:
            assert cli._handle_command("/restart") is True
        assert run_mock.call_count == 2
    with patch.object(builtins, "input", return_value="2"):
        with patch("os.execv") as execv:
            assert cli._handle_command("/restart") is True
        execv.assert_called_once()


def test_restart_prompt_invalid_and_abort():
    m, cli = _build_local_cli()
    with patch.object(builtins, "input", return_value="9"):
        result, output = _run_quiet(cli._handle_command, "/restart")
    assert result is True
    assert "Ungueltig" in output
    with patch.object(builtins, "input", side_effect=KeyboardInterrupt):
        assert cli._handle_command("/restart") is True
    result, _ = _run_quiet(cli._handle_command, "/restart bogus")
    assert result is True


# ── help layout: 3 columns, 2 separators, responsive ──

def test_help_has_three_columns():
    m, cli = _build_local_cli()
    _, output = _run_quiet(cli._print_help)
    for header in ("Chat-Befehle", "Forschungs-Befehle", "Nach Ausgabe Befehle"):
        assert header in output
    content_rows = [line for line in output.splitlines() if "│" in line]
    assert content_rows, "help must render column separators"
    for line in content_rows:
        assert line.count("│") == 2, "exactly two separators per row"


def _strip_ansi(text):
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def test_help_lists_all_commands_and_adapts_to_width():
    m, cli = _build_local_cli()
    wide = cli._build_help_lines(140)
    narrow = cli._build_help_lines(70)
    for cmd in ("/status", "/clear", "/restart", "/runtime", "/emotion",
                "/sleep", "/memory", "/last", "/raw", "/trace",
                "/compact", "/full", "/help", "/exit"):
        assert cmd in wide, f"{cmd} missing in help"
    assert len(narrow.splitlines()) == len(wide.splitlines())
    visible = [_strip_ansi(line) for line in narrow.splitlines()]
    assert max(len(line) for line in visible) <= 70


# ── remote session contract ──

def test_stream_events_sends_session_and_command_mode():
    m = _get_module()
    sse = [
        "event: turn_started\n",
        'data: {"session_id":"sess-1","message_id":"m1"}\n',
        "\n",
        "event: token\n",
        'data: {"content":"Hi","token_type":"answer"}\n',
        "\n",
        "event: turn_finished\n",
        'data: {"session_id":"sess-1","assistant_message":{"content":"Hi","metadata":{}}}\n',
    ]
    captured = {}

    def fake_post(url, json=None, **kwargs):
        captured.update(json or {})
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.iter_lines.return_value = sse
        return resp

    with patch.object(m.requests, "post", fake_post):
        rb = m.RemoteBackend("http://localhost:8010")
        rb.session_id = "sess-0"
        events = list(rb.stream_events("/stats"))
    assert captured["session_id"] == "sess-0"
    assert captured["command_mode"] is True
    assert rb.session_id == "sess-1"
    assert any(e.get("_sse_event") == "token" for e in events)


def test_handle_command_sends_session_and_tracks_replacement():
    m = _get_module()

    def fake_post(url, json=None, **kwargs):
        assert json["session_id"] == "sess-0"
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"output": "neu", "session_id": "sess-2"}
        return resp

    with patch.object(m.requests, "post", fake_post):
        rb = m.RemoteBackend("http://localhost:8010")
        rb.session_id = "sess-0"
        assert rb.handle_command("/new") == "neu"
        assert rb.session_id == "sess-2"


def test_apply_remote_session_tracks_replacement():
    m, cli = _build_remote_cli()
    cli._apply_remote_session({"replacement_session_id": "sess-5"})
    assert cli.session_id == "sess-5"
    assert cli.remote.session_id == "sess-5"


# ── local slash path uses command_service and persists ──

def test_process_local_slash_uses_command_service():
    m, cli = _build_local_cli()
    with patch("api.services.command_service.execute_slash_command") as exec_cmd:
        exec_cmd.return_value = {"response_text": "ok"}
        _, _ = _run_quiet(cli._process_local, "/stats")
        exec_cmd.assert_called_once_with("/stats", cli.backend)
        assert cli.last_result == {"response_text": "ok"}


def test_process_remote_updates_session_from_stream():
    m, cli = _build_remote_cli()
    sse = [
        "event: turn_started\n",
        'data: {"session_id":"sess-10","message_id":"m1"}\n',
        "\n",
        "event: turn_finished\n",
        'data: {"session_id":"sess-10","assistant_message":{"content":"Hi","metadata":{"formatted_answer":"Hi"}}}\n',
    ]
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.iter_lines.return_value = sse
    with patch.object(m.requests, "post", return_value=resp):
        with patch.object(m, "HAS_RICH", False):
            _, _ = _run_quiet(cli._process_remote, "hallo")
    assert cli.session_id == "sess-10"


if __name__ == "__main__":
    test_local_commands_all_route()
    test_exit_returns_false()
    test_last_raw_trace_with_result()
    test_history_with_messages()
    test_clear_creates_empty_history()
    test_remote_commands_all_route()
    test_restart_chappie_restarts_both_services()
    test_restart_chappie_reports_failure()
    test_restart_cli_reexecs_process()
    test_restart_prompt_choice_chappie_and_cli()
    test_restart_prompt_invalid_and_abort()
    test_help_has_three_columns()
    test_help_lists_all_commands_and_adapts_to_width()
    test_stream_events_sends_session_and_command_mode()
    test_handle_command_sends_session_and_tracks_replacement()
    test_apply_remote_session_tracks_replacement()
    test_process_local_slash_uses_command_service()
    test_process_remote_updates_session_from_stream()
    print("OK: CLI e2e commands")
