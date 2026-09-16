"""CLI contracts for /copy routing, prompt selection and remote export lookup."""

from __future__ import annotations

import io
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import chappie_brain_cli as cli_module
from config.commands import command_candidates


class _Manager:
    def __init__(self):
        self.session = {
            "id": "session-1",
            "title": "CLI-Test",
            "updated_at": "",
            "messages": [{"id": "m1", "role": "user", "content": "Hallo", "created_at": ""}],
        }

    @staticmethod
    def ensure_session_id(session_id):
        return session_id or "session-1"

    def load_session(self, session_id):
        return self.session


class _Service:
    @staticmethod
    def get_snapshot():
        return {}

    @staticmethod
    def get_status():
        return {}


class _Debug:
    enabled = True

    @staticmethod
    def get_entries_as_dict():
        return []

    @staticmethod
    def get_formatted_log():
        return ""


class _Backend:
    event_store = None
    life_simulation = _Service()
    sleep_handler = _Service()
    debug_logger = _Debug()

    def __init__(self, data_dir):
        self.runtime_data_dir = Path(data_dir)
        self.chat_manager = _Manager()

    @staticmethod
    def get_status():
        return {"model": "test", "provider": "vllm"}

    @staticmethod
    def get_emotions_snapshot():
        return {"happiness": 50}


def _cli(directory):
    cli = cli_module.CHAPPiEBrainCLI.__new__(cli_module.CHAPPiEBrainCLI)
    cli._use_remote = False
    cli.remote_url = None
    cli.backend = _Backend(directory)
    cli.session_id = "session-1"
    cli.history = []
    cli.last_result = None
    return cli


def test_copy_standard_writes_fallback_file():
    with tempfile.TemporaryDirectory() as directory:
        cli = _cli(directory)
        output = io.StringIO()
        with patch.object(sys, "stdout", output):
            assert cli._handle_command("/copy standard") is True
        files = list((Path(directory) / "session_exports").glob("*.json"))
        assert len(files) == 1
        assert json.loads(files[0].read_text(encoding="utf-8"))["mode"] == "standard"
        assert "Vollständige Fallback-Datei" in output.getvalue()


def test_copy_modes_are_available_for_completion():
    assert command_candidates("/copy ") == ["standard", "debug"]


def test_copy_without_mode_uses_restart_style_prompt_for_debug():
    with tempfile.TemporaryDirectory() as directory:
        cli = _cli(directory)
        with patch("builtins.input", return_value="2"):
            assert cli._handle_command("/copy") is True
        files = list((Path(directory) / "session_exports").glob("*.json"))
        assert len(files) == 1
        assert json.loads(files[0].read_text(encoding="utf-8"))["mode"] == "debug"


def test_remote_backend_requests_session_export():
    response = type(
        "Response",
        (),
        {
            "raise_for_status": lambda self: None,
            "json": lambda self: {"mode": "debug", "export": {"mode": "debug"}, "fallback_path": "/srv/export.json"},
        },
    )()
    with patch.object(cli_module.requests, "get", return_value=response) as get:
        backend = cli_module.RemoteBackend("http://localhost:8010")
        result = backend.export_session("debug", session_id="session-1")
    assert result["export"]["mode"] == "debug"
    get.assert_called_once_with(
        "http://localhost:8010/sessions/session-1/export",
        params={"mode": "debug"},
        timeout=30,
    )


if __name__ == "__main__":
    test_copy_standard_writes_fallback_file()
    test_copy_without_mode_uses_restart_style_prompt_for_debug()
    test_remote_backend_requests_session_export()
    print("OK: CLI /copy standard, debug and remote export contracts")
