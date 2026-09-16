"""Standalone contracts for structured session export and OSC 52 transport."""

from __future__ import annotations

import base64
import io
import json
import os
import stat
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from web_infrastructure.session_export import (
    build_osc52_sequence,
    build_session_export,
    emit_osc52,
    serialize_session_export,
    write_session_export,
)


class _ChatManager:
    def __init__(self):
        self.session = {
            "id": "session-1",
            "title": "Export-Test",
            "updated_at": "2026-09-07T12:00:00+00:00",
            "runtime_settings": {"memory_enabled": True, "steering_mode": "combined"},
            "messages": [
                {"id": "u1", "role": "user", "content": "Hallo", "created_at": "2026-09-07T11:59:00+00:00"},
                {
                    "id": "a1",
                    "role": "assistant",
                    "content": "Hallo zurück",
                    "created_at": "2026-09-07T12:00:00+00:00",
                    "metadata": {
                        "turn_id": "turn-1",
                        "formatted_answer": "Hallo zurück",
                        "emotions_before": {"happiness": 50},
                        "emotions": {"happiness": 55},
                        "emotions_delta": {"happiness": 5},
                        "intent_type": "casual_chat",
                        "raw_response": "internal raw",
                        "debug_entries": [{"category": "TURN"}],
                        "intent_raw_json": {"hidden": True},
                        "api_key": "must-not-leak",
                    },
                },
            ],
        }

    @staticmethod
    def ensure_session_id(session_id):
        return session_id or "session-1"

    def load_session(self, session_id):
        assert session_id == "session-1"
        return self.session


class _EventStore:
    @staticmethod
    def events(session_id):
        assert session_id == "session-1"
        return [
            {
                "event_id": "event-1",
                "session_id": session_id,
                "turn_id": "turn-1",
                "timestamp": "2026-09-07T12:00:00+00:00",
                "role": "assistant",
                "content": "Hallo zurück",
                "model": "qwen",
                "provider": "vllm",
                "emotion_before_json": '{"happiness": 50}',
                "emotion_after_json": '{"happiness": 55}',
                "emotion_delta_json": '{"happiness": 5}',
                "steering_mode": "combined",
                "steering_vectors_json": '[{"name":"happiness"}]',
                "memory_enabled": 1,
                "quality_flags_json": '["assistant_claim"]',
                "retrieval_eligible": 0,
                "retrieval_confidence": 0.0,
                "source": "conversation",
                "raw_content": "internal raw",
                "promotion_state": "skipped",
                "promotion_error": None,
            }
        ]


class _DebugLogger:
    enabled = True

    @staticmethod
    def get_entries_as_dict():
        return [{"category": "TURN", "message": "debug"}]

    @staticmethod
    def get_formatted_log():
        return "formatted debug"


class _Service:
    @staticmethod
    def get_snapshot():
        return {"clock": {"phase_label": "Tag"}}

    @staticmethod
    def get_status():
        return {"trigger_due": False}


class _Backend:
    runtime_data_dir = None
    chat_manager = _ChatManager()
    event_store = _EventStore()
    debug_logger = _DebugLogger()
    life_simulation = _Service()
    sleep_handler = _Service()

    @staticmethod
    def get_status():
        return {"model": "qwen", "provider": "vllm", "brain_available": True}

    @staticmethod
    def get_emotions_snapshot():
        return {"happiness": 55}


def test_standard_and_debug_exports_have_stable_boundaries():
    standard = build_session_export(_Backend(), "session-1", mode="standard")
    debug = build_session_export(_Backend(), "session-1", mode="debug")

    assert standard["format"] == "chappie-session-export"
    assert standard["schema_version"] == 1
    assert standard["mode"] == "standard"
    assert [message["id"] for message in standard["session"]["messages"]] == ["u1", "a1"]
    assert standard["session"]["messages"][1]["ui_metadata"]["emotions_delta"] == {"happiness": 5}
    assert "raw_response" not in standard["session"]["messages"][1]["ui_metadata"]
    assert "debug" not in standard
    assert standard["summary"]["emotion_timeline"][0]["after"] == {"happiness": 55}

    assert debug["mode"] == "debug"
    assert debug["debug"]["raw_session"]["messages"][1]["metadata"]["raw_response"] == "internal raw"
    assert debug["debug"]["event_store"][0]["emotions_before"] == {"happiness": 50}
    assert debug["debug"]["event_store"][0]["memory_enabled"] is True
    assert "api_key" not in json.dumps(debug, ensure_ascii=False)


def test_fallback_file_is_private_and_contains_canonical_json():
    export = build_session_export(_Backend(), "session-1", mode="standard")
    with tempfile.TemporaryDirectory() as directory:
        path = write_session_export(export, directory)
        assert path.parent.name == "session_exports"
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert json.loads(path.read_text(encoding="utf-8")) == json.loads(serialize_session_export(export))


def test_osc52_sequence_round_trip_and_terminal_guards():
    payload = '{"message":"ä"}'
    sequence = build_osc52_sequence(payload)
    assert sequence is not None
    assert sequence.startswith("\033]52;c;") and sequence.endswith("\a")
    encoded = sequence[len("\033]52;c;"):-1]
    assert base64.b64decode(encoded).decode("utf-8") == payload

    class _TTY(io.StringIO):
        def isatty(self):
            return True

    stream = _TTY()
    result = emit_osc52(payload, stream=stream)
    assert result["sent"] is True
    assert stream.getvalue() == sequence
    assert emit_osc52(payload, stream=io.StringIO())["sent"] is False
    assert build_osc52_sequence("x" * 20, max_payload_bytes=10) is None

    old_tmux = os.environ.get("TMUX")
    try:
        os.environ["TMUX"] = "1"
        tmux_sequence = build_osc52_sequence(payload)
        assert tmux_sequence.startswith("\033Ptmux;")
        assert tmux_sequence.endswith("\033\\")
    finally:
        if old_tmux is None:
            os.environ.pop("TMUX", None)
        else:
            os.environ["TMUX"] = old_tmux


if __name__ == "__main__":
    test_standard_and_debug_exports_have_stable_boundaries()
    test_fallback_file_is_private_and_contains_canonical_json()
    test_osc52_sequence_round_trip_and_terminal_guards()
    print("OK: session export, fallback file and OSC 52 contracts")
