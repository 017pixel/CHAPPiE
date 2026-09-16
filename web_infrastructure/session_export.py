"""Structured, transport-neutral exports for persisted CHAPPiE sessions.

The exporter deliberately keeps clipboard transport out of the API.  A remote
CLI receives the same JSON payload as a local CLI and emits OSC 52 through its
terminal connection.  The server-side JSON file is written independently so a
terminal that does not accept OSC 52 still leaves the user with a complete
export.
"""

from __future__ import annotations

import base64
import dataclasses
import json
import math
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence, TextIO
from uuid import uuid4


EXPORT_FORMAT = "chappie-session-export"
EXPORT_SCHEMA_VERSION = 1
EXPORT_MODES = ("standard", "debug")

# OSC 52 support differs between terminals and multiplexers.  Keep the
# terminal path conservative and always create the complete file fallback.
OSC52_MAX_PAYLOAD_BYTES = 128 * 1024

_SENSITIVE_KEY_PATTERN = re.compile(
    r"(?:api[_-]?key|access[_-]?token|refresh[_-]?token|auth[_-]?token|"
    r"client[_-]?secret|password|authorization|cookie|private[_-]?key|secret)",
    re.IGNORECASE,
)
_SESSION_ID_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9_-]+")

_EVENT_JSON_FIELDS = {
    "emotion_before_json": "emotions_before",
    "emotion_after_json": "emotions_after",
    "emotion_delta_json": "emotions_delta",
    "steering_vectors_json": "steering_vectors",
    "quality_flags_json": "quality_flags",
}
_EVENT_BOOLEAN_FIELDS = {"memory_enabled", "retrieval_eligible"}

# These are the fields rendered by the terminal report or the web inspector.
# Raw model/debug payloads stay in the debug export only.
_UI_METADATA_FIELDS = (
    "runtime_settings",
    "session_id",
    "turn_id",
    "thought_process",
    "model_reasoning",
    "reasoning_only",
    "emotions",
    "emotions_delta",
    "emotions_before",
    "input_analysis",
    "keyword_rag_memories",
    "intent_type",
    "intent_confidence",
    "tool_calls_executed",
    "available_tools",
    "selected_tools",
    "unused_tools",
    "input_classification",
    "short_term_count",
    "processing_time_ms",
    "life_snapshot",
    "global_workspace",
    "action_plan",
    "emotion_steering",
    "steering_runtime",
    "context_budget",
    "memory_consolidation",
    "memory_trace",
    "tone_decision",
    "causal_trace",
    "prompt_emotion_mode",
    "repetition_events",
    "dream_fragments",
    "provider",
    "model",
    "timing",
    "ttft_ms",
    "answer_tokens",
    "tokens_per_second",
    "live_pipeline",
    "auto_sleep_triggered",
    "sleep_status",
    "pending",
    "status_text",
    "retry_history",
    "formatted_cot",
    "formatted_answer",
    "formatting_failed",
    "formatting_warning",
    "formatting_error",
    "formatting_source",
    "formatting_model",
    "formatting_reason",
    "formatting_skip_reason",
    "finish_reason",
    "technical_retry_count",
    "sanitization_fallback",
    "sanitization_reasons",
    "multi_question_paragraph_normalized",
    "direct_self_report_stabilized",
    "semantic_retry_count",
    "command_trace",
    "cot_leak",
    "is_command",
    "is_system",
    "is_system_response",
    "message_kind",
    "command",
    "replacement_session_id",
    "clear_history",
    "stream_error",
    "error_message",
)


class SessionExportError(ValueError):
    """Raised when a session export cannot be created safely."""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_export_mode(mode: str) -> str:
    normalized = str(mode or "").strip().lower()
    if normalized not in EXPORT_MODES:
        raise SessionExportError("Export-Modus muss 'standard' oder 'debug' sein.")
    return normalized


def _is_sensitive_key(key: str) -> bool:
    return bool(_SENSITIVE_KEY_PATTERN.search(key))


def _json_safe(value: Any, seen: set[int] | None = None) -> Any:
    """Convert runtime values to JSON without leaking credential-like keys."""
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")

    active = seen if seen is not None else set()
    object_id = id(value)
    if object_id in active:
        return "[Circular]"
    active.add(object_id)
    try:
        if dataclasses.is_dataclass(value) and not isinstance(value, type):
            return _json_safe(dataclasses.asdict(value), active)
        if isinstance(value, Mapping):
            return {
                str(key): _json_safe(item, active)
                for key, item in value.items()
                if not _is_sensitive_key(str(key))
            }
        if isinstance(value, (list, tuple)):
            return [_json_safe(item, active) for item in value]
        if isinstance(value, (set, frozenset)):
            return [_json_safe(item, active) for item in sorted(value, key=str)]
        try:
            json.dumps(value)
        except (TypeError, ValueError, OverflowError):
            return str(value)
        return value
    finally:
        active.discard(object_id)


def serialize_session_export(export: Mapping[str, Any]) -> str:
    """Return the canonical UTF-8 JSON representation used everywhere."""
    safe_export = _json_safe(dict(export))
    return json.dumps(safe_export, ensure_ascii=False, indent=2) + "\n"


# Reale Session-Exports (302 KB Standard, 631 KB Debug, gemessen 2026-09-08)
# passen nie in OSC 52 (128 KB). Die Zwischenablage bekommt deshalb diese
# kompakte lesbare Form, die JSON-Datei bleibt der vollstaendige Export.
CLIPBOARD_MAX_BYTES = 96 * 1024
CLIPBOARD_MAX_MESSAGE_CHARS = 4000


def build_clipboard_text(export: Mapping[str, Any], *, max_bytes: int = CLIPBOARD_MAX_BYTES) -> str:
    """Build a compact human-readable session text that fits into OSC 52."""
    session = export.get("session", {}) if isinstance(export.get("session"), Mapping) else {}
    summary = export.get("summary", {}) if isinstance(export.get("summary"), Mapping) else {}
    runtime = export.get("runtime", {}) if isinstance(export.get("runtime"), Mapping) else {}
    title = str(session.get("title", "New Chat") or "New Chat")
    session_id = str(session.get("id", "") or "")
    mode = str(export.get("mode", "standard") or "standard")
    lines = [
        f"CHAPPiE Session ({mode}): {title}",
        f"ID: {session_id}",
        f"Nachrichten: {summary.get('message_count', '?')}",
    ]
    current_emotions = summary.get("current_emotions") or runtime.get("emotions") or {}
    if isinstance(current_emotions, Mapping) and current_emotions:
        lines.append("Emotionen: " + ", ".join(f"{key} {value}" for key, value in current_emotions.items()))
    lines.extend(["", "--- Verlauf ---", ""])
    messages = session.get("messages", [])
    if not isinstance(messages, list):
        messages = []
    shown = 0
    omitted = 0
    for message in messages:
        if not isinstance(message, Mapping):
            continue
        role = str(message.get("role", "?") or "?")
        label = {"user": "USER", "assistant": "CHAPPIE"}.get(role, role.upper())
        stamp = str(message.get("created_at", "") or "")
        content = str(message.get("content", "") or "").strip()
        if len(content) > CLIPBOARD_MAX_MESSAGE_CHARS:
            content = content[:CLIPBOARD_MAX_MESSAGE_CHARS] + " [...]"
        block = f"[{stamp}] {label}:\n{content}\n" if stamp else f"{label}:\n{content}\n"
        candidate = "\n".join(lines) + "\n" + block
        if len(candidate.encode("utf-8")) > max_bytes:
            omitted += 1
            continue
        lines.append(block)
        shown += 1
    if omitted:
        lines.append(f"\n[Hinweis: {omitted} aeltere Nachrichten gekuerzt, vollstaendig in der JSON-Datei.]")
    else:
        lines.append("\n[Vollstaendiger Verlauf, JSON-Datei enthaelt zusaetzlich Metadaten.]")
    text = "\n".join(lines).strip() + "\n"
    return text


def _safe_call(callable_value: Any, default: Any, warnings: list[str], label: str) -> Any:
    if not callable(callable_value):
        warnings.append(f"{label} nicht verfügbar")
        return default
    try:
        return callable_value()
    except Exception as exc:
        warnings.append(f"{label} konnte nicht gelesen werden ({type(exc).__name__})")
        return default


def _standard_message(message: Mapping[str, Any]) -> dict[str, Any]:
    metadata = message.get("metadata")
    metadata = metadata if isinstance(metadata, Mapping) else {}
    ui_metadata = {
        key: _json_safe(metadata[key])
        for key in _UI_METADATA_FIELDS
        if key in metadata and not _is_sensitive_key(key)
    }
    result: dict[str, Any] = {
        "id": _json_safe(message.get("id")),
        "role": _json_safe(message.get("role", "")),
        "content": _json_safe(message.get("content", "")),
        "created_at": _json_safe(message.get("created_at", message.get("timestamp", ""))),
        "ui_metadata": ui_metadata,
    }
    return result


def _decode_event_row(row: Mapping[str, Any]) -> dict[str, Any]:
    decoded: dict[str, Any] = {}
    for key, value in row.items():
        if key in _EVENT_JSON_FIELDS:
            target_key = _EVENT_JSON_FIELDS[key]
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    value = {} if key != "quality_flags_json" else []
            decoded[target_key] = _json_safe(value)
        elif key in _EVENT_BOOLEAN_FIELDS:
            decoded[key] = bool(value)
        else:
            decoded[key] = _json_safe(value)
    return decoded


def _load_event_rows(backend: Any, session_id: str, warnings: list[str]) -> list[dict[str, Any]]:
    store = getattr(backend, "event_store", None)
    events_method = getattr(store, "events", None)
    if not callable(events_method):
        warnings.append("Event-Store nicht verfügbar, Archivdaten fehlen")
        return []
    try:
        rows = events_method(session_id)
    except Exception as exc:
        warnings.append(f"Event-Store konnte nicht gelesen werden ({type(exc).__name__})")
        return []
    if not isinstance(rows, list):
        warnings.append("Event-Store lieferte kein gültiges Ereignis-Array")
        return []
    return [_decode_event_row(row) for row in rows if isinstance(row, Mapping)]


def _emotion_timeline(
    messages: Sequence[Mapping[str, Any]],
    event_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []
    known_turns: set[str] = set()

    for event in event_rows:
        before = event.get("emotions_before") or {}
        after = event.get("emotions_after") or {}
        delta = event.get("emotions_delta") or {}
        if event.get("role") != "assistant" or not (before or after or delta):
            continue
        turn_id = str(event.get("turn_id") or "")
        if turn_id:
            known_turns.add(turn_id)
        timeline.append(
            {
                "timestamp": event.get("timestamp", ""),
                "turn_id": event.get("turn_id", ""),
                "source": event.get("source", "event_store"),
                "before": _json_safe(before),
                "after": _json_safe(after),
                "delta": _json_safe(delta),
            }
        )

    for message in messages:
        if message.get("role") != "assistant":
            continue
        metadata = message.get("metadata")
        if not isinstance(metadata, Mapping):
            continue
        turn_id = str(metadata.get("turn_id") or "")
        if turn_id and turn_id in known_turns:
            continue
        before = metadata.get("emotions_before") or {}
        after = metadata.get("emotions") or {}
        delta = metadata.get("emotions_delta") or {}
        if not (before or after or delta):
            continue
        timeline.append(
            {
                "timestamp": message.get("created_at", ""),
                "turn_id": metadata.get("turn_id", ""),
                "source": "session_message",
                "before": _json_safe(before),
                "after": _json_safe(after),
                "delta": _json_safe(delta),
            }
        )

    timeline.sort(key=lambda item: (str(item.get("timestamp", "")), str(item.get("turn_id", ""))))
    return timeline


def _command_history(event_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Mapping[str, Any]]] = {}
    for event in event_rows:
        turn_id = str(event.get("turn_id") or "")
        if not turn_id:
            continue
        role = str(event.get("role") or "")
        if role in {"user", "assistant"}:
            grouped.setdefault(turn_id, {})[role] = event

    commands: list[dict[str, Any]] = []
    for turn_id, pair in grouped.items():
        user = pair.get("user", {})
        command = str(user.get("content") or "")
        if not command.lstrip().startswith("/"):
            continue
        assistant = pair.get("assistant", {})
        commands.append(
            {
                "timestamp": user.get("timestamp", assistant.get("timestamp", "")),
                "turn_id": turn_id,
                "command": command,
                "response": assistant.get("content", ""),
                "emotions_before": assistant.get("emotions_before", {}),
                "emotions_after": assistant.get("emotions_after", {}),
                "emotions_delta": assistant.get("emotions_delta", {}),
                "source": assistant.get("source", user.get("source", "event_store")),
            }
        )
    commands.sort(key=lambda item: (str(item.get("timestamp", "")), str(item.get("turn_id", ""))))
    return commands


def backend_data_directory(backend: Any) -> Path:
    runtime_data_dir = getattr(backend, "runtime_data_dir", None)
    if isinstance(runtime_data_dir, (str, Path)) and runtime_data_dir:
        return Path(runtime_data_dir)
    configured_data_dir = getattr(backend, "data_dir", None)
    if isinstance(configured_data_dir, (str, Path)) and configured_data_dir:
        return Path(configured_data_dir)
    from config.config import DATA_DIR
    return Path(DATA_DIR)


def build_session_export(
    backend: Any,
    session_id: str | None = None,
    *,
    mode: str = "standard",
) -> dict[str, Any]:
    """Build a stable export from session messages and durable runtime events."""
    normalized_mode = validate_export_mode(mode)
    manager = getattr(backend, "chat_manager", None)
    if manager is None:
        raise SessionExportError("Chat-Manager nicht verfügbar.")
    ensure_session_id = getattr(manager, "ensure_session_id", None)
    if not callable(ensure_session_id):
        raise SessionExportError("Chat-Manager kann keine Session-ID validieren.")
    try:
        validator = getattr(manager, "_is_valid_session_id", None)
        if session_id is not None and callable(validator) and not validator(session_id):
            raise SessionExportError("Ungueltige Chat-Session-ID.")
        normalized_session_id = str(ensure_session_id(session_id))
        session = manager.load_session(normalized_session_id)
    except SessionExportError:
        raise
    except Exception as exc:
        raise SessionExportError(
            f"Session konnte nicht geladen werden ({type(exc).__name__})."
        ) from exc
    if not isinstance(session, Mapping):
        raise SessionExportError("Session liefert kein gültiges Objekt.")

    warnings: list[str] = []
    raw_messages = session.get("messages", [])
    if not isinstance(raw_messages, list):
        warnings.append("Session-Nachrichten sind kein gültiges Array")
        raw_messages = []
    messages = [message for message in raw_messages if isinstance(message, Mapping)]
    event_rows = _load_event_rows(backend, normalized_session_id, warnings)
    emotion_timeline = _emotion_timeline(messages, event_rows)

    status = _safe_call(getattr(backend, "get_status", None), {}, warnings, "Runtime-Status")
    emotions = _safe_call(getattr(backend, "get_emotions_snapshot", None), {}, warnings, "Emotionszustand")
    life_service = getattr(backend, "life_simulation", None)
    life_snapshot = _safe_call(getattr(life_service, "get_snapshot", None), {}, warnings, "Life-Zustand")
    sleep_service = getattr(backend, "sleep_handler", None)
    sleep_status = _safe_call(getattr(sleep_service, "get_status", None), {}, warnings, "Sleep-Zustand")

    runtime_settings = session.get("runtime_settings", {})
    if not isinstance(runtime_settings, Mapping):
        runtime_settings = {}
    debug_logger = getattr(backend, "debug_logger", None)
    debug_entries = _safe_call(
        getattr(debug_logger, "get_entries_as_dict", None), [], warnings, "Debug-Logger"
    )
    debug_log = _safe_call(
        getattr(debug_logger, "get_formatted_log", None), "", warnings, "Debug-Log"
    )
    logger_enabled = bool(getattr(debug_logger, "enabled", False)) if debug_logger is not None else False

    standard_messages = [_standard_message(message) for message in messages]
    export: dict[str, Any] = {
        "format": EXPORT_FORMAT,
        "schema_version": EXPORT_SCHEMA_VERSION,
        "mode": normalized_mode,
        "exported_at": utc_now_iso(),
        "session": {
            "id": normalized_session_id,
            "title": session.get("title", "New Chat"),
            "updated_at": session.get("updated_at", ""),
            "runtime_settings": _json_safe(runtime_settings),
            "messages": standard_messages,
        },
        "summary": {
            "message_count": len(messages),
            "user_message_count": sum(1 for message in messages if message.get("role") == "user"),
            "assistant_message_count": sum(1 for message in messages if message.get("role") == "assistant"),
            "system_message_count": sum(1 for message in messages if message.get("role") == "system"),
            "event_count": len(event_rows),
            "current_emotions": _json_safe(emotions),
            "emotion_timeline": emotion_timeline,
            "command_history": _command_history(event_rows),
        },
        "runtime": {
            "status": _json_safe(status),
            "emotions": _json_safe(emotions),
            "life_snapshot": _json_safe(life_snapshot),
            "sleep_status": _json_safe(sleep_status),
        },
        "availability": {
            "event_store": bool(event_rows) or not any("Event-Store" in warning for warning in warnings),
            "debug_logger": debug_logger is not None,
        },
        "warnings": warnings,
    }

    if normalized_mode == "debug":
        export["debug"] = {
            "logger": {
                "enabled": logger_enabled,
                "entries": _json_safe(debug_entries),
                "formatted_log": _json_safe(debug_log),
            },
            "raw_session": _json_safe(dict(session)),
            "event_store": event_rows,
        }
    return _json_safe(export)


def write_session_export(export: Mapping[str, Any], data_dir: str | Path) -> Path:
    """Atomically write a private server-side fallback file."""
    session = export.get("session", {})
    session_id = str(session.get("id", "session")) if isinstance(session, Mapping) else "session"
    mode = validate_export_mode(str(export.get("mode", "standard")))
    safe_session_id = _SESSION_ID_FILENAME_PATTERN.sub("_", session_id).strip("._") or "session"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    directory = Path(data_dir) / "session_exports"
    directory.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(directory, 0o700)
    except OSError:
        pass

    filename = f"{safe_session_id}_{mode}_{timestamp}_{uuid4().hex[:8]}.json"
    destination = directory / filename
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{filename}.", suffix=".tmp", dir=str(directory)
    )
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = -1
            handle.write(serialize_session_export(export))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        try:
            os.chmod(destination, 0o600)
        except OSError:
            pass
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if os.path.exists(temporary):
            os.unlink(temporary)
    return destination


def build_osc52_sequence(payload: str, *, max_payload_bytes: int = OSC52_MAX_PAYLOAD_BYTES) -> str | None:
    """Build an OSC 52 clipboard sequence, or None when it is too large."""
    payload_bytes = payload.encode("utf-8")
    if len(payload_bytes) > max_payload_bytes:
        return None
    encoded = base64.b64encode(payload_bytes).decode("ascii")
    sequence = f"\033]52;c;{encoded}\a"
    if os.environ.get("TMUX"):
        escaped = sequence.replace("\033", "\033\033")
        return f"\033Ptmux;\033{escaped}\033\\"
    return sequence


def emit_osc52(
    payload: str,
    *,
    stream: TextIO | None = None,
    max_payload_bytes: int = OSC52_MAX_PAYLOAD_BYTES,
) -> dict[str, Any]:
    """Send OSC 52 only to an interactive terminal and report the local result."""
    output = stream or sys.stdout
    try:
        is_tty = bool(output.isatty())
    except Exception:
        is_tty = False
    if not is_tty:
        return {"sent": False, "reason": "stdout_not_tty", "tmux_wrapped": False}
    sequence = build_osc52_sequence(payload, max_payload_bytes=max_payload_bytes)
    if sequence is None:
        return {
            "sent": False,
            "reason": "payload_too_large",
            "tmux_wrapped": bool(os.environ.get("TMUX")),
        }
    output.write(sequence)
    output.flush()
    return {"sent": True, "reason": "osc52_sent", "tmux_wrapped": bool(os.environ.get("TMUX"))}
