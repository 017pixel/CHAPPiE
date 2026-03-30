from __future__ import annotations

from typing import Any, Dict, List

from config.config import get_active_model, settings

HELP_TEXT = """**CHAPPiE Commands:**

- **/sleep** - Startet die Traum-Phase (konsolidiert Erinnerungen)
- **/think [thema]** - Einfacher Reflektionsmodus (10 Schritte)
- **/deep think [anzahl]** - Rekursive Selbstreflexion, Standard 10 Schritte
- **/clear** - Startet eine neue Chat-Sitzung
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
        "emotions": backend._get_emotions_snapshot(),
        "life_snapshot": backend.life_simulation.get_snapshot(),
        "sleep_status": backend.sleep_handler.get_status(),
        "debug_entries": backend.debug_logger.get_entries_as_dict(),
        "retry_history": [],
        **extra,
    }


def _build_stats_text(backend) -> str:
    status = backend.get_status()
    memory_count = backend.memory.get_memory_count()
    short_term_count = backend.short_term_memory_v2.get_count()
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
        short_term_memory=backend.short_term_memory_v2,
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


def execute_slash_command(command: str, backend) -> Dict[str, Any]:
    cmd = command.strip()
    lower = cmd.lower()

    if lower == "/sleep":
        return _run_sleep(backend)
    if lower.startswith("/deep think"):
        return _run_deep_think(backend, cmd)
    if lower.startswith("/think"):
        return _run_think(backend, cmd)
    if lower == "/help":
        return _base_result(backend, HELP_TEXT)
    if lower == "/stats":
        return _base_result(backend, _build_stats_text(backend))
    if lower == "/config":
        return _base_result(backend, "Die Konfiguration liegt jetzt im React-Frontend unter der Settings-Ansicht und in der API unter `/settings`.")
    if lower == "/clear":
        new_session_id = backend.chat_manager.create_session()
        backend.chat_manager.set_active_session(new_session_id)
        return _base_result(backend, "Neue Chat-Sitzung gestartet.", replacement_session_id=new_session_id, clear_history=True)
    if lower in {"/daily", "/personality", "/consolidate", "/reflect", "/functions", "/life", "/needs", "/goals", "/world", "/habits", "/stage", "/plan", "/forecast", "/arc", "/timeline", "/debug", "/step1", "/soul", "/user", "/prefs", "/preferences", "/twostep"}:
        return _base_result(backend, backend.handle_command(lower))
    return _base_result(backend, backend.handle_command(cmd))


def build_visualizer_payload(backend) -> Dict[str, Any]:
    emotions = backend._get_emotions_snapshot()
    life_snapshot = backend.life_simulation.get_snapshot()
    report = backend.steering_manager.build_debug_report(emotions)
    return {
        "model": get_active_model(),
        "provider": settings.llm_provider.value,
        "emotions": emotions,
        "life_snapshot": life_snapshot,
        "steering_report": report,
    }
