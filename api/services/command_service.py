from __future__ import annotations

import time
from typing import Any, Dict, List

from config.config import settings
from config.emotions import EMOTION_ORDER

HELP_TEXT = """**CHAPPiE Commands:**

- **/sleep** - Startet die Traum-Phase (konsolidiert Erinnerungen)
- **/think [thema]** - Einfacher Reflektionsmodus (10 Schritte)
- **/deep think [anzahl]** - Rekursive Selbstreflexion, Standard 10 Schritte
- **/emotion <name> [+/-]<0-100>** - Emotion setzen/erhoehen/senken (z.B. /emotion happiness +10)
- **/emotion** - Zeigt alle aktuellen Emotions-Werte
- **/clear /new** - Startet eine neue Chat-Sitzung
- **/stats** - Zeigt System-Statistiken
- **/config** - Zeigt Hinweis auf die Settings-Ansicht
- **/daily** - Zeigt Kurzzeitgedaechtnis
- **/personality** - Zeigt aktuelle Persoenlichkeit
- **/consolidate** - Bereinigt abgelaufene Daily Infos
- **/reflect** - Zeigt letzte Selbst-Reflexionen
- **/functions** - Listet verfuegbare Funktionen auf
- **/life /world /habits /stage /plan /forecast /arc /timeline** - Life- und Growth-Sichten
- **/debug /step1 /soul /user /prefs /preferences /twostep** - Debug- und Kontextfunktionen
"""


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
    short_term_count = backend.short_term_memory.get_count()
    emotion_lines = "\n".join(f"- {name}: {value}%" for name, value in status.get("emotions", {}).items())
    return f"""**System-Statistiken:**

**Brain:** {'Verfuegbar' if status['brain_available'] else 'Nicht verfuegbar'}
**Modell:** {status['model']}
**Provider:** {settings.llm_provider.value}
**Langzeitgedaechtnis:** {memory_count} Erinnerungen
**Kurzzeitgedaechtnis:** {short_term_count} Eintraege

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


def _run_think(backend, command: str) -> Dict[str, Any]:
    parts = command.split(" ", 1)
    topic = parts[1].strip() if len(parts) > 1 else ""
    thought_log: List[str] = []
    for step_result in backend.memory.think_deep(backend.brain, topic=topic, steps=10, delay=0.0):
        step = step_result["step"]
        total = step_result["total_steps"]
        thought = step_result["thought"]
        mem_count = step_result["memories_found"]
        thought_log.append(f"**Schritt {step}/{total}** ({mem_count} Erinnerungen gefunden)\n> {thought}")
        if step_result.get("error"):
            break
    joined_thoughts = "\n\n".join(thought_log)
    response_text = (
        f"**Mein Denkprozess (10 Schritte):**\n\n{joined_thoughts}\n\n---\n"
        f"*Thema: {topic or 'Allgemeine Selbstreflexion'}*"
    )
    return _base_result(backend, response_text, think_topic=topic)


def _parse_deep_think_iterations(command: str) -> int:
    parts = command.split()
    for token in reversed(parts):
        if token.isdigit():
            return max(1, min(100, int(token)))
    return 10


def _run_deep_think(backend, command: str) -> Dict[str, Any]:
    iterations = _parse_deep_think_iterations(command)
    steps = list(backend.deep_think_engine.think_cycle(iterations=iterations, delay=0.0, max_tokens=5000))
    summary = backend.deep_think_engine.get_summary_after_cycle(steps)
    blocks = []
    for step in steps:
        if step.error:
            blocks.append(f"**Schritt {step.step}/{step.total_steps}**\n> Fehler: {step.error}")
            continue
        delta_text = ", ".join(
            f"{key}: {'+' if value > 0 else ''}{value}"
            for key, value in step.emotions_delta.items()
            if value != 0
        ) or "keine Aenderung"
        blocks.append(
            f"**Schritt {step.step}/{step.total_steps}**\n> {step.thought}\n\n"
            f"*Emotions-Delta: {delta_text} | Memories: {len(step.memories_used)} | Funktionen: {len(step.function_calls)}*"
        )
    joined_blocks = "\n\n---\n\n".join(blocks)
    response_text = (
        f"## Deep Think Zyklus abgeschlossen\n\n"
        f"**Gedanken:** {len(steps)}\n"
        f"**Memories:** {summary.get('memories_accessed', 0)}\n"
        f"**Netto-Delta:** {summary.get('emotions_total_delta', {})}\n\n"
        f"{joined_blocks}"
    )
    return _base_result(backend, response_text, deep_think_summary=summary)


EMOTION_NAMES = EMOTION_ORDER


def _run_emotion(backend, cmd: str) -> Dict[str, Any]:
    """Setzt/erhoeht/senkt eine Emotion. Syntax: /emotion [name] [[+/-]wert]"""
    parts = cmd.split()

    if len(parts) == 1:
        emotions = backend.get_emotions_snapshot()
        lines = ["**Aktuelle Emotions-Werte:**\n"]
        for name in EMOTION_NAMES:
            val = emotions.get(name, "?")
            lines.append(f"- **{name}**: {val}/100")
        lines.append("\n*Syntax: /emotion <name> [+/-]<0-100>*")
        lines.append("*Beispiel: /emotion happiness +10*")
        return _base_result(backend, "\n".join(lines), _command_trace_actions=["Emotionszustand gelesen"])

    if len(parts) < 3:
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


def execute_slash_command(command: str, backend) -> Dict[str, Any]:
    cmd = command.strip()
    lower = cmd.lower()
    started_at = time.perf_counter()
    handler = "backend.handle_command"
    actions: List[str] = []

    if lower == "/sleep":
        handler = "sleep_handler.execute_sleep_phase"
        actions = ["Schlafphase gestartet", "Erinnerungen konsolidiert", "Emotionalen Zustand regeneriert"]
        result = _run_sleep(backend)
    elif lower.startswith("/deep think"):
        handler = "deep_think_engine.think_cycle"
        actions = ["Iterationen ausgewertet", "Erinnerungen einbezogen", "Reflexionszusammenfassung erstellt"]
        result = _run_deep_think(backend, cmd)
    elif lower.startswith("/think"):
        handler = "memory.think_deep"
        actions = ["Reflexionszyklus gestartet", "Gedankenschritte gesammelt", "Ergebnis formatiert"]
        result = _run_think(backend, cmd)
    elif lower == "/help":
        handler = "command_service.help"
        actions = ["Verfügbare Commands geladen"]
        result = _base_result(backend, HELP_TEXT)
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
