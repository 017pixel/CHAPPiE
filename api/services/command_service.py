from __future__ import annotations

import time
from contextlib import nullcontext
from typing import Any, Dict, List

from config.config import settings
from config.emotions import EMOTION_ORDER, EMOTION_PRESETS, EMOTION_PRESET_ORDER, get_emotion_preset

from config.commands import help_markdown, COMMAND_REGISTRY

HELP_TEXT = help_markdown()


def _base_result(backend, response_text: str, **extra: Any) -> Dict[str, Any]:
    return {
        "response_text": response_text,
        "emotions": backend.get_emotions_snapshot(),
        "life_snapshot": backend.life_simulation.get_snapshot(),
        "sleep_status": backend.sleep_handler.get_status(),
        "debug_entries": backend.debug_logger.get_entries_as_dict(),
        "retry_history": [],
        **extra,
    }


def _build_stats_text(backend) -> str:
    status = backend.get_status()
    memory_count = backend.memory.get_memory_count()
    stm = backend.short_term_memory.get_stats() if hasattr(backend.short_term_memory, "get_stats") else {"active": backend.short_term_memory.get_count(), "quarantined": 0, "migrated": 0}
    emotion_lines = "\n".join(f"- {name}: {value}%" for name, value in status.get("emotions", {}).items())
    return f"""**System-Statistiken:**

**Brain:** {'Verfuegbar' if status['brain_available'] else 'Nicht verfuegbar'}
**Modell:** {status['model']}
**Provider:** {settings.llm_provider.value}
**Langzeitgedaechtnis:** {memory_count} Erinnerungen
**Kurzzeitgedaechtnis:** {stm.get('active', 0)} aktiv, {stm.get('quarantined', 0)} quarantäniert, {stm.get('migrated', 0)} migriert

**Emotionen:**
{emotion_lines}
"""


def _run_sleep(backend) -> Dict[str, Any]:
    result = backend.sleep_handler.execute_sleep_phase(
        memory_engine=backend.memory,
        context_files=backend.context_files,
        short_term_memory=backend.short_term_memory,
    )
    recovery = result.get("emotional_recovery", {})
    recovery_text = ", ".join(f"{key}: {'+' if value > 0 else ''}{value}" for key, value in recovery.items()) or "keine Veraenderung"
    response_text = f"Schlafzyklus beendet. Energie: {result.get('energy_value', 100)}%. Emotionale Regeneration: {recovery_text}"
    return _base_result(backend, response_text, sleep_result=result)


EMOTION_NAMES = EMOTION_ORDER


def _is_emotion_frozen(backend) -> bool:
    try:
        frozen_fn = getattr(getattr(backend, "emotions", None), "is_frozen", None)
        if not callable(frozen_fn):
            return False
        result = frozen_fn()
        return result is True
    except Exception:
        return False


def _run_preset(backend, cmd: str) -> Dict[str, Any]:
    parts = cmd.split()
    if len(parts) == 1 or (len(parts) == 2 and parts[1].lower() in {"list", "status", "help"}):
        emotions = backend.get_emotions_snapshot()
        lines = ["**Emotions-Presets:**\n"]
        for preset_name in EMOTION_PRESET_ORDER:
            preset = EMOTION_PRESETS[preset_name]
            lines.append(f"- **{preset_name}**: " + ", ".join(f"{key} {preset[key]}" for key in EMOTION_ORDER))
        lines.append("\n**Aktuell:** " + ", ".join(f"{name} {emotions.get(name, '?')}" for name in EMOTION_NAMES))
        lines.append("\n*Nutze: /preset <schlecht|neutral|wohl>*")
        return _base_result(backend, "\n".join(lines), _command_trace_actions=["Presets gelistet"])
    if len(parts) != 2:
        return _base_result(
            backend,
            "Nutze: `/preset <schlecht|neutral|wohl>`",
            _command_trace_actions=["Preset-Syntax geprüft", "Änderung verworfen"],
            _command_trace_status="rejected",
        )
    preset_name = parts[1].lower()
    preset = get_emotion_preset(preset_name)
    if preset is None:
        return _base_result(
            backend,
            f"Unbekanntes Preset: `{preset_name}`. Gueltig: {', '.join(EMOTION_PRESET_ORDER)}",
            _command_trace_actions=["Preset-Name geprüft", "Änderung verworfen"],
            _command_trace_status="rejected",
        )
    if _is_emotion_frozen(backend):
        return _base_result(
            backend,
            "Emotionen sind eingefroren. Nutze `/emofreeze off` zum Freigeben.",
            _command_trace_actions=["Freeze geprüft", "Preset wegen Freeze verworfen"],
            _command_trace_status="rejected",
        )
    before = backend.get_emotions_snapshot()
    for emotion, value in preset.items():
        try:
            backend.emotions.set_emotion(emotion, value)
        except Exception:
            continue
    after = backend.get_emotions_snapshot()
    summary = ", ".join(f"{name} {before.get(name, '?')}->{after.get(name, '?')}" for name in EMOTION_NAMES)
    return _base_result(
        backend,
        f"**Preset {preset_name} aktiv:** {summary}",
        preset_update={"preset": preset_name, "before": before, "after": after},
        _command_trace_actions=["Preset validiert", f"Preset {preset_name} gesetzt"],
    )


def _run_emofreeze(backend, cmd: str) -> Dict[str, Any]:
    parts = [part.lower() for part in cmd.split()]
    args = parts[1:]
    emotions_engine = getattr(backend, "emotions", None)
    if emotions_engine is None or not hasattr(emotions_engine, "set_frozen"):
        return _base_result(backend, "Emotion-Freeze wird von diesem Backend nicht unterstützt.", _command_trace_status="rejected")
    if not args or args == ["status"]:
        state = "eingefroren" if _is_emotion_frozen(backend) else "aktiv"
        return _base_result(backend, f"Emotionen: **{state}** (*Nutze: /emofreeze on|off|status*)")
    if args == ["on"]:
        emotions_engine.set_frozen(True)
        return _base_result(backend, "Emotionen **eingefroren**. Tests laufen jetzt mit festen Werten.", _command_trace_actions=["Emotionen eingefroren"])
    if args == ["off"]:
        emotions_engine.set_frozen(False)
        return _base_result(backend, "Emotionen wieder **aktiv**.", _command_trace_actions=["Emotionen freigegeben"])
    return _base_result(
        backend,
        "Nutze: `/emofreeze on|off|status`",
        _command_trace_actions=["Freeze-Syntax geprüft"],
        _command_trace_status="rejected",
    )


def _run_default(backend, cmd: str, session_id: str | None = None) -> Dict[str, Any]:
    parts = cmd.split()
    if len(parts) != 1:
        return _base_result(
            backend,
            "Nutze: `/default` (setzt alles auf Standard zurück)",
            _command_trace_status="rejected",
        )
    session_id = backend.chat_manager.ensure_session_id(session_id)
    defaults = dict(settings.runtime_defaults)
    try:
        runtime = backend.chat_manager.update_runtime_settings(session_id, defaults)
    except Exception as exc:
        return _base_result(backend, f"Session-Defaults konnten nicht gesetzt werden: {exc}", _command_trace_status="rejected")
    try:
        settings.update_from_ui(chain_of_thought=False)
    except Exception:
        pass
    try:
        if hasattr(backend, "apply_runtime_settings"):
            backend.apply_runtime_settings(force=True)
    except Exception:
        pass
    try:
        if hasattr(backend.emotions, "set_frozen"):
            backend.emotions.set_frozen(False)
    except Exception:
        pass
    try:
        reset_fn = getattr(backend.emotions, "reset", None)
        if callable(reset_fn):
            try:
                reset_fn(force=True)
            except TypeError:
                reset_fn()
    except Exception:
        pass
    try:
        if hasattr(backend, "debug_logger") and hasattr(backend.debug_logger, "disable"):
            backend.debug_logger.disable()
    except Exception:
        pass
    emotions = backend.get_emotions_snapshot()
    emotion_summary = ", ".join(
        f"{name} {emotions.get(name, '?')}" for name in EMOTION_NAMES
    )
    text = (
        "**Defaults wiederhergestellt:**\n"
        f"- Thinking: AUS\n"
        f"- Memory: {'AN' if runtime.memory_enabled else 'AUS'}\n"
        f"- Steering: {'AN' if runtime.steering_enabled else 'AUS'} ({runtime.steering_mode})\n"
        f"- Live: {'AN' if runtime.live_enabled else 'AUS'}\n"
        f"- Emotionen: {emotion_summary}\n"
        f"- Freeze: AUS, Debug: AUS"
    )
    return _base_result(
        backend,
        text,
        session_id=session_id,
        runtime_settings=runtime.to_dict(),
        _command_trace_actions=["Session-Flags zurückgesetzt", "Thinking ausgeschaltet", "Emotionen zurückgesetzt", "Freeze und Debug ausgeschaltet"],
    )


def _run_emotion(backend, cmd: str) -> Dict[str, Any]:
    """Setzt/erhoeht/senkt eine Emotion. Syntax: /emotion [name] [[+/-]wert]"""
    parts = cmd.split()
    if len(parts) == 4 and parts[2] in {"+", "-"} and parts[3].isdigit():
        parts = parts[:2] + [parts[2] + parts[3]]

    if len(parts) == 1:
        emotions = backend.get_emotions_snapshot()
        lines = ["**Aktuelle Emotions-Werte:**\n"]
        for name in EMOTION_NAMES:
            val = emotions.get(name, "?")
            lines.append(f"- **{name}**: {val}/100")
        lines.append("\n*Syntax: /emotion <name> [+/-]<0-100>*")
        lines.append("*Beispiel: /emotion happiness +10*")
        return _base_result(backend, "\n".join(lines), _command_trace_actions=["Emotionszustand gelesen"])

    if len(parts) != 3:
        return _base_result(
            backend,
            "Nutze: `/emotion <name> [+/-]<0-100>` (z.B. `/emotion happiness +10`)",
            _command_trace_actions=["Command-Syntax geprüft", "Änderung wegen fehlendem Wert verworfen"],
            _command_trace_status="rejected",
        )

    _, emotion, val_str, *_extra = parts
    if emotion not in EMOTION_NAMES:
        names = ", ".join(EMOTION_NAMES)
        return _base_result(
            backend,
            f"Unbekannte Emotion: `{emotion}`. Gueltig: {names}",
            _command_trace_actions=["Emotionsname geprüft", "Änderung wegen unbekannter Emotion verworfen"],
            _command_trace_status="rejected",
        )

    is_delta = val_str.startswith("+") or val_str.startswith("-")
    try:
        parsed = int(val_str)
    except ValueError:
        return _base_result(
            backend,
            f"Ungueltiger Wert: `{val_str}`. Erwartet: Zahl oder +Zahl/-Zahl.",
            _command_trace_actions=["Emotionswert geprüft", "Änderung wegen ungültigem Wert verworfen"],
            _command_trace_status="rejected",
        )

    current = backend.get_emotions_snapshot().get(emotion, 50)
    if _is_emotion_frozen(backend):
        return _base_result(
            backend,
            "Emotionen sind eingefroren. Nutze `/emofreeze off` zum Freigeben.",
            _command_trace_actions=["Freeze geprüft", "Änderung wegen Freeze verworfen"],
            _command_trace_status="rejected",
        )
    target = current + parsed if is_delta else parsed
    clamped = max(0, min(100, target))

    if target != clamped:
        direction = "Maximum" if target > 100 else "Minimum"
        overflow = abs(target - clamped)
        msg = f"**{emotion}**: {current} {'+' if parsed > 0 else ''}{parsed} → **{clamped}**/100 ⚠️ *({direction} erreicht, {overflow} {'reduziert' if target > 100 else 'erhoeht'})*"
    else:
        delta_str = f" {'+' if parsed > 0 else ''}{parsed} → " if is_delta else " → "
        msg = f"**{emotion}**: {current}{delta_str}**{clamped}**/100 ✓"

    backend.emotions.set_emotion(emotion, clamped)
    return _base_result(
        backend,
        msg,
        emotion_update={"emotion": emotion, "before": current, "after": clamped, "requested": parsed, "is_delta": is_delta},
        _command_trace_actions=["Emotionswert validiert", f"{emotion} von {current} auf {clamped} gesetzt"],
    )


def _run_session_settings(backend, command, session_id):
    parts = command.split()
    name = parts[0].lower().lstrip("/")
    args = [part.lower() for part in parts[1:]]
    if args and args[0] not in COMMAND_REGISTRY["/" + name].subcommands:
        return _base_result(backend, "Unbekannter Unterbefehl. " + ", ".join(COMMAND_REGISTRY["/" + name].subcommands), _command_trace_status="rejected")
    session_id = backend.chat_manager.ensure_session_id(session_id)
    current = backend.chat_manager.get_runtime_settings(session_id)
    patch = {}
    try:
        if not args or args == ["status"]:
            pass
        elif args in (["on"], ["off"]):
            patch[name + "_enabled"] = args[0] == "on"
            if name == "steering" and args[0] == "on" and current.steering_mode == "off":
                patch["steering_mode"] = "combined"
        elif name == "steering" and len(args) == 2 and args[0] == "mode":
            if args[1] == "off":
                patch["steering_enabled"] = False
            else:
                patch["steering_mode"] = args[1]
        elif name == "memory" and args[0] == "search" and len(args) > 1:
            if not current.memory_enabled:
                return _base_result(backend, "Memory ist in dieser Sitzung aus. Suche übersprungen.",
                                    session_id=session_id, runtime_settings=current.to_dict())
            query = " ".join(parts[2:])
            memories = backend.memory.search_memory(query, top_k=10)
            text = "\n".join(getattr(item, "content", "") for item in memories) or "Keine Erinnerungen gefunden."
            return _base_result(backend, text, session_id=session_id, runtime_settings=current.to_dict())
        else:
            raise ValueError("Syntax: /memory on|off|status|search <Text>; /steering on|off|status|mode off|activation|sequence|combined; /live on|off|status")
        if patch:
            current = backend.chat_manager.update_runtime_settings(session_id, patch)
    except ValueError as exc:
        return _base_result(backend, str(exc), session_id=session_id,
                            runtime_settings=current.to_dict(), _command_trace_status="rejected")
    enabled = getattr(current, name + "_enabled")
    text = f"{name.capitalize()}: {'an' if enabled else 'aus'}"
    if name == "steering":
        text += f"; Modus: {current.steering_mode}; wirksam: {current.effective_mode}"
    return _base_result(backend, text, session_id=session_id, runtime_settings=current.to_dict())


def _execute_slash_command(command: str, backend, session_id: str | None = None) -> Dict[str, Any]:
    cmd = command.strip()
    lower = cmd.lower()
    started_at = time.perf_counter()
    handler = "backend.handle_command"
    actions: List[str] = []

    if (lower.split() or [""])[0] in {"/memory", "/steering", "/live"}:
        handler = "command_service.session_settings"
        result = _run_session_settings(backend, cmd, session_id)
        actions = ["Sitzungseinstellungen gelesen oder aktualisiert"]
    elif lower == "/sleep":
        handler = "sleep_handler.execute_sleep_phase"
        actions = ["Schlafphase gestartet", "Erinnerungen konsolidiert", "Emotionalen Zustand regeneriert"]
        result = _run_sleep(backend)
    elif lower == "/help":
        handler = "command_service.help"
        actions = ["Verfügbare Commands geladen"]
        result = _base_result(backend, HELP_TEXT)
    elif (lower.split() or [""])[0] == "/copy":
        handler = "terminal.session_export"
        actions = ["Exportmodus validiert", "Terminal-Clipboard-Transport vorbereitet"]
        result = _base_result(
            backend,
            "Session-Export wird im Terminal ausgeführt. Nutze /copy standard oder /copy debug.",
        )
    elif lower == "/stats":
        handler = "command_service.stats"
        actions = ["Runtime-Status gelesen", "Memory-Zähler gelesen", "Emotionszustand gelesen"]
        result = _base_result(backend, _build_stats_text(backend))
    elif lower == "/config":
        handler = "command_service.config"
        actions = ["Konfigurationspfad ausgegeben"]
        result = _base_result(backend, "Die Konfiguration liegt jetzt im React-Frontend unter der Settings-Ansicht und in der API unter `/settings`.")
    elif lower.startswith("/emotion"):
        handler = "command_service.emotion"
        result = _run_emotion(backend, cmd)
        actions = list(result.pop("_command_trace_actions", ["Emotionszustand verarbeitet"]))
    elif (lower.split() or [""])[0] == "/preset":
        handler = "command_service.preset"
        result = _run_preset(backend, cmd)
        actions = list(result.pop("_command_trace_actions", ["Preset verarbeitet"]))
    elif (lower.split() or [""])[0] == "/emofreeze":
        handler = "command_service.emofreeze"
        result = _run_emofreeze(backend, cmd)
        actions = list(result.pop("_command_trace_actions", ["Freeze verarbeitet"]))
    elif (lower.split() or [""])[0] == "/default":
        handler = "command_service.default"
        result = _run_default(backend, cmd, session_id=session_id)
        actions = list(result.pop("_command_trace_actions", ["Defaults wiederhergestellt"]))
    elif lower in ("/clear", "/new"):
        handler = "chat_manager.create_session"
        actions = ["Neue Sitzung erstellt", "Neue Sitzung aktiviert", "Chatansicht zurückgesetzt"]
        new_session_id = backend.chat_manager.create_session()
        backend.chat_manager.set_active_session(new_session_id)
        result = _base_result(backend, "Neue Chat-Sitzung gestartet.", replacement_session_id=new_session_id, clear_history=True)
    elif lower in {"/daily", "/personality", "/consolidate", "/reflect", "/functions", "/life", "/needs", "/goals", "/world", "/habits", "/stage", "/plan", "/forecast", "/arc", "/timeline", "/debug", "/step1", "/soul", "/user", "/prefs", "/preferences", "/twostep"}:
        actions = ["Command an Backend-Handler übergeben", "Aktuellen Systemzustand ausgewertet"]
        result = _base_result(backend, backend.handle_command(lower))
    else:
        actions = ["Command an Backend-Handler übergeben"]
        result = _base_result(backend, backend.handle_command(cmd))

    common_keys = {
        "response_text", "emotions", "life_snapshot", "sleep_status",
        "debug_entries", "retry_history", "replacement_session_id",
        "clear_history", "command_trace",
    }
    trace_status = str(result.pop("_command_trace_status", "completed"))
    details = {key: value for key, value in result.items() if key not in common_keys}
    result["command_trace"] = {
        "command": cmd,
        "name": (lower.split()[0] if lower else "").removeprefix("/"),
        "arguments": cmd.split()[1:],
        "handler": handler,
        "status": trace_status,
        "duration_ms": round((time.perf_counter() - started_at) * 1000, 1),
        "actions": actions,
        "details": details,
    }
    return result


def execute_slash_command(command: str, backend, session_id: str | None = None) -> Dict[str, Any]:
    # Emotion commands must not mutate the state halfway through a chat turn.
    with getattr(backend, "_turn_lock", nullcontext()):
        return _execute_archived_slash_command(command, backend, session_id)


def _execute_archived_slash_command(command: str, backend, session_id: str | None = None) -> Dict[str, Any]:
    """Shared command execution with durable evidence when running a full runtime."""
    store = getattr(backend, "event_store", None)
    if store is None:
        return _execute_slash_command(command, backend, session_id=session_id)
    from memory.event_store import EventStore
    from uuid import uuid4
    if not isinstance(store, EventStore):
        return _execute_slash_command(command, backend, session_id=session_id)
    session_id = backend.chat_manager.ensure_session_id(session_id)
    turn_id = uuid4().hex
    runtime = backend.chat_manager.get_runtime_settings(session_id)
    before = backend.get_emotions_snapshot()
    metadata = {"source": "command", "memory_enabled": runtime.memory_enabled,
                "steering_mode": runtime.effective_mode, "emotions_before": before,
                "research_isolated": backend.research_mode,
                "model": backend._chat_model() if hasattr(backend, "_chat_model") else "",
                "provider": getattr(backend._chat_provider(), "value", "") if hasattr(backend, "_chat_provider") else ""}
    store.append(session_id=session_id, turn_id=turn_id, role="user", content=command, metadata=metadata)
    try:
        result = _execute_slash_command(command, backend, session_id=session_id)
    except Exception as exc:
        store.append(session_id=session_id, turn_id=turn_id, role="assistant", content=str(exc),
                     metadata={**metadata, "quality_flags": ["command_error"]})
        raise
    after = result.get("emotions", before)
    store.append(session_id=session_id, turn_id=turn_id, role="assistant", content=result["response_text"],
                 raw_content=result["response_text"], metadata={**metadata, "emotions_after": after,
                 "emotions_delta": {key: after.get(key, value)-value for key, value in before.items()}})
    return result
