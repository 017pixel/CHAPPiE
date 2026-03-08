import streamlit as st
import time
from web_infrastructure.components import render_brain_monitor, render_deep_think_controls
from web_infrastructure.ui_utils import EMOTION_DISPLAY_ORDER, EMOTION_LABELS, normalize_emotions


def _render_live_vital_signs(emotions: dict) -> None:
    normalized = normalize_emotions(emotions)
    st.markdown("---")
    st.markdown("**📊 Live-Vitalzeichen:**")
    cols_vitals = st.columns(4)
    for index, emotion_key in enumerate(EMOTION_DISPLAY_ORDER):
        with cols_vitals[index % 4]:
            st.write(f"{EMOTION_LABELS[emotion_key]}: {normalized[emotion_key]}%")
    st.markdown("---")


def _format_emotion_list(emotions: dict) -> str:
    normalized = normalize_emotions(emotions)
    return "\n".join(
        f"- {EMOTION_LABELS[emotion_key]}: {normalized[emotion_key]}%"
        for emotion_key in EMOTION_DISPLAY_ORDER
    )


def _persist_current_session(backend) -> str:
    st.session_state.messages = backend.chat_manager.ensure_message_ids(st.session_state.messages)
    session_id = backend.chat_manager.save_session(st.session_state.get("session_id"), st.session_state.messages)
    st.session_state.session_id = session_id
    backend.chat_manager.set_active_session(session_id)
    session_data = backend.chat_manager.load_session(session_id)
    st.session_state.session_updated_at = session_data.get("updated_at")
    return session_id

def process_command(user_input: str, backend) -> bool:
    """
    Verarbeitet Slash-Commands wie /sleep, /think, /deep think.
    Returns:
        True, wenn ein Befehl verarbeitet wurde (keine weitere Chat-Verarbeitung nötig).
        False, wenn es eine normale Nachricht ist.
    """
    cmd = user_input.strip().lower()
    
    if cmd == "/sleep":
        with st.status("CHAPPiE schlaeft... Traum-Phase aktiv...", expanded=True):
            from memory.sleep_phase import get_sleep_phase_handler
            sleep_handler = get_sleep_phase_handler()
            result = sleep_handler.execute_sleep_phase(
                memory_engine=backend.memory,
                context_files=None
            )
            
            # Zeige Ergebnisse
            if result.get("energy_restored"):
                st.write(f"Energie wiederhergestellt: {result.get('energy_value', 100)}%")
            
            recovery = result.get("emotional_recovery", {})
            if recovery:
                st.write("Emotionale Regeneration:")
                for emotion, delta in recovery.items():
                    sign = "+" if delta > 0 else ""
                    st.write(f"  {emotion}: {sign}{delta}")
        
        # Baue Zusammenfassung
        energy_val = result.get("energy_value", 100)
        recovery_text = ", ".join([f"{k}: {'+' if v > 0 else ''}{v}" for k, v in result.get("emotional_recovery", {}).items()])
        sleep_summary = f"Schlafzyklus beendet. Energie: {energy_val}%. Emotionale Regeneration: {recovery_text}"
        
        assistant_msg = {
            "role": "assistant", 
            "content": sleep_summary, 
            "metadata": {"thought_process": "Kommando /sleep ausgefuehrt."}
        }
        st.session_state.messages.append(assistant_msg)
        _persist_current_session(backend)
        st.rerun()
        return True
    
    elif cmd.startswith("/think"):
        # Alter /think Befehl - einfache 10 Schritte Reflexion
        parts = user_input.strip().split(" ", 1)
        topic = parts[1] if len(parts) > 1 else ""
        
        thought_log = []
        
        with st.status("CHAPPiE denkt nach...", expanded=True) as status:
            for step_result in backend.memory.think_deep(backend.brain, topic=topic, steps=10, delay=1.0):
                step = step_result["step"]
                total = step_result["total_steps"]
                thought = step_result["thought"]
                mem_count = step_result["memories_found"]
                
                log_entry = f"**Schritt {step}/{total}** ({mem_count} Erinnerungen gefunden)\n> {thought}"
                thought_log.append(log_entry)
                st.write(f"Schritt {step}/{total}: {thought[:80]}...")
                
                if step_result.get("error"):
                    status.update(label="Fehler im Think-Modus", state="error")
                    break
            
            status.update(label="Denkprozess abgeschlossen!", state="complete")
        
        full_thoughts = "\n\n".join(thought_log)
        response_text = f"**Mein Denkprozess (10 Schritte):**\n\n{full_thoughts}\n\n---\n*Alle Gedanken wurden als Erinnerungen gespeichert.*"
        
        assistant_msg = {
            "role": "assistant", 
            "content": response_text, 
            "metadata": {"thought_process": f"Think-Modus mit Thema: {topic if topic else 'Allgemeine Selbstreflexion'}"}
        }
        st.session_state.messages.append(assistant_msg)
        _persist_current_session(backend)
        st.rerun()
        return True
    
    elif cmd.startswith("/deep think"):
        # === /deep think MODUS MIT HUMAN-IN-THE-LOOP ===
        
        # Prüfe ob bereits ein Deep Think Zyklus läuft
        if not st.session_state.deep_think_active:
            st.session_state.deep_think_active = True
            st.session_state.deep_think_steps = []
            st.session_state.deep_think_total_done = 0
        
        # Dekrementiere pending_batches falls gesetzt (für Multi-Batch)
        auto_continue = False
        if st.session_state.deep_think_pending_batches > 1:
            st.session_state.deep_think_pending_batches -= 1
            auto_continue = True
        elif st.session_state.deep_think_pending_batches == 1:
            st.session_state.deep_think_pending_batches = 0
        
        # Führe 10 Iterationen durch
        current_batch_steps = []
        
        with st.status(f"CHAPPiE Deep Think (Batch {st.session_state.deep_think_total_done // 10 + 1})...", expanded=True) as status:
            for step_result in backend.deep_think_engine.think_cycle(iterations=10, delay=1.5, max_tokens=5000):
                step = step_result.step
                total = step_result.total_steps
                thought = step_result.thought
                
                current_batch_steps.append(step_result)
                
                # === VITALZEICHEN LIVE UPDATEN ===
                new_emotions = normalize_emotions(step_result.emotions_after)
                if new_emotions and isinstance(new_emotions, dict):
                    st.session_state.current_emotions = new_emotions
                
                # Zeige Live-Vitalzeichen im Status-Container
                _render_live_vital_signs(new_emotions)
                
                # Fortschritt ohne HTML anzeigen
                delta_info = ""
                if step_result.emotions_delta:
                    changes = []
                    # Übersetzung für Delta-Anzeige
                    name_map = {"happiness": "Freude", "trust": "Vertrauen", "energy": "Energie", 
                               "curiosity": "Neugier", "frustration": "Frust", "motivation": "Motivation", "sadness": "Traurigkeit"}
                    for emo_key, delta in step_result.emotions_delta.items():
                        if delta != 0:
                            name = name_map.get(emo_key, emo_key)
                            sign = "+" if delta > 0 else ""
                            changes.append(f"{name}: {sign}{delta}")
                    if changes:
                        delta_info = f" | Delta: {', '.join(changes)}"
                
                st.write(f"**Schritt {step}/{total}:** {thought[:70]}...{delta_info}")
                
                if step_result.error:
                    status.update(label=f"Fehler: {step_result.error}", state="error")
                    break
            
            status.update(label=f"Batch abgeschlossen! ({len(current_batch_steps)} Gedanken)", state="complete")
        
        # Update Session State
        st.session_state.deep_think_steps.extend(current_batch_steps)
        st.session_state.deep_think_total_done += len(current_batch_steps)
        
        # Zusammenfassung
        summary = backend.deep_think_engine.get_summary_after_cycle(current_batch_steps)
        
        # NEU: Füge Function Calls zur Summary hinzu
        total_func_calls = sum(len(s.function_calls) for s in current_batch_steps)
        func_names = set()
        for step in current_batch_steps:
            for func in step.function_calls:
                func_names.add(func.get("name", "unknown"))
        
        summary["functions_called"] = total_func_calls
        summary["function_names"] = list(func_names)
        
        # Formatiere Gedanken OHNE HTML (nur Markdown)
        thoughts_md = ""
        name_map = {"happiness": "Freude", "trust": "Vertrauen", "energy": "Energie", 
                   "curiosity": "Neugier", "frustration": "Frust", "motivation": "Motivation", "sadness": "Traurigkeit"}
        
        for step in current_batch_steps:
            if not step.error:
                delta_parts = []
                for emo_key, val in step.emotions_delta.items():
                    if val != 0:
                        name = name_map.get(emo_key, emo_key)
                        sign = "+" if val > 0 else ""
                        color_emoji = "🟢" if val > 0 else "🔴"
                        delta_parts.append(f"{color_emoji} {name}: {sign}{val}")
                delta_str = ", ".join(delta_parts) if delta_parts else "keine Änderung"
                
                # NEU: Function Calls anzeigen
                func_calls_str = ""
                if step.function_calls:
                    func_icons = []
                    for func in step.function_calls:
                        func_name = func.get("name", "unknown")
                        func_icons.append(f"🔧 {func_name}")
                    func_calls_str = f"\n**Funktionen:** {' '.join(func_icons)}"
                
                thoughts_md += f"""
**Schritt {step.step}/{step.total_steps}**
> {step.thought}

*Emotions-Delta: {delta_str}* | *Memories: {len(step.memories_used)}*{func_calls_str}

---
"""
        
        # Gesamt-Delta formatieren (ohne HTML)
        total_delta_parts = []
        for emo_key, val in summary.get("emotions_total_delta", {}).items():
            if val != 0:
                name = name_map.get(emo_key, emo_key)
                sign = "+" if val > 0 else ""
                emoji = "🟢" if val > 0 else "🔴"
                total_delta_parts.append(f"{emoji} {name}: {sign}{val}")
        total_delta_str = ", ".join(total_delta_parts) if total_delta_parts else "keine Netto-Änderung"
        
        response_text = f"""## Deep Think Zyklus abgeschlossen

**Statistiken:**
- Gedanken in diesem Batch: {len(current_batch_steps)}
- Gesamt Gedanken bisher: {st.session_state.deep_think_total_done}
- Eindeutige Memories abgerufen: {summary.get("memories_accessed", 0)}
- Funktionen aufgerufen: {sum(len(s.function_calls) for s in current_batch_steps)}
- Gesamt Emotions-Delta: {total_delta_str}

---

### Gedanken-Protokoll:
{thoughts_md}

---
*Alle Gedanken wurden mit `source: self_reflection` in ChromaDB gespeichert.*
*Funktionsaufrufe werden automatisch ausgeführt.*
"""
        
        # Speichere Nachricht ZUERST
        assistant_msg = {
            "role": "assistant", 
            "content": response_text, 
            "metadata": {
                "thought_process": f"Deep Think Batch {st.session_state.deep_think_total_done // 10}",
                "deep_think_stats": summary
            }
        }
        st.session_state.messages.append(assistant_msg)
        _persist_current_session(backend)
        
        # Human-in-the-Loop: Zeige Buttons via Component
        action = render_deep_think_controls(st.session_state.deep_think_total_done)
        
        if action:
            if action == "sleep":
                # Beende Deep Think und starte /sleep
                st.session_state.deep_think_active = False
                st.session_state.deep_think_steps = []
                st.session_state.deep_think_total_done = 0
                
                final_summary = f"""## Deep Think Session beendet

**Gesamt-Statistiken:**
- Durchgeführte Gedanken: {st.session_state.deep_think_total_done}
- Gesamt Emotions-Delta: {total_delta_str}

*Starte nun /sleep Modus zur Konsolidierung aller Erinnerungen...*
"""
                final_msg = {"role": "assistant", "content": final_summary, "metadata": {"thought_process": "Deep Think Session beendet"}}
                st.session_state.messages.append(final_msg)
                _persist_current_session(backend)
                
                st.session_state.pending_cmd = "/sleep"
                st.rerun()
                
            elif action in ["10", "20", "30", "40", "60", "100"]:
                count = int(action)
                if count > 10:
                    st.session_state.deep_think_pending_batches = count // 10
                
                st.session_state.pending_cmd = "/deep think"
                st.rerun()
        
        # Wenn auto_continue aktiv (Multi-Batch), automatisch nächsten Batch starten
        if auto_continue:
            st.session_state.pending_cmd = "/deep think"
            st.rerun()
            return True
        
        # Kein st.rerun() hier, damit die Buttons sichtbar bleiben!
        return True
    
    elif cmd == "/clear":
         st.session_state.messages = []
         st.session_state.session_id = backend.chat_manager.create_session()
         backend.chat_manager.set_active_session(st.session_state.session_id)
         st.session_state.session_updated_at = None
         st.rerun()
         return True
    
    elif cmd == "/help":
        help_text = """**CHAPPiE Commands:**

- **/sleep** - Startet die Traum-Phase (konsolidiert Erinnerungen)
- **/think [thema]** - Einfacher Reflektionsmodus (10 Schritte)
- **/deep think** - Rekursive Selbstreflexion mit Human-in-the-Loop (10 Schritte pro Batch, fortsetzbar)
- **/clear** - Loescht aktuellen Chat und startet neue Sitzung
- **/stats** - Zeigt System-Statistiken
- **/config** - Oeffnet Einstellungen

- **/daily** - Zeigt Kurzzeitgedächtnis (Daily Info)
- **/personality** - Zeigt aktuelle Persönlichkeit
- **/consolidate** - Bereinigt abgelaufene Daily Infos
- **/reflect** - Zeigt letzte Selbst-Reflexionen
- **/functions** - Listet verfügbare Funktionen auf
- **/life** - Öffnet den allgemeinen Life-State mit inneren Zuständen
- **/world** - Zeigt das aktuelle Weltmodell und antizipierte User-Bedürfnisse
- **/habits** - Zeigt wiederkehrende Verhaltensmuster und deren Stärke
- **/stage** - Zeigt Entwicklungsstand, Fortschritt und nächste Stufe
- **/plan** - Zeigt aktuelle Planung über mehrere Zeithorizonte
- **/forecast** - Zeigt nächste Prognosen, Risiken und Schutzfaktoren
- **/arc** - Zeigt Beziehungskurve, Phase und sozialen Verlauf
- **/timeline** - Zeigt autobiografische Timeline-Einträge und Verlaufsspur

- **/help** - Zeigt diese Hilfe

**Memory Enhancement Features:**
CHAPI kann jetzt selbstständig:
- Wichtige Infos im Kurzzeitgedächtnis speichern
- Seine Persönlichkeit dokumentieren
- Selbst-Reflexionen anlegen

**Debug Mode:**
Aktiviere den DEBUG MODE Button in der Sidebar fuer das Brain Monitor Panel.

**Tipp:** Klicke auf die Buttons oben fuer schnellen Zugriff!"""
        assistant_msg = {"role": "assistant", "content": help_text, "metadata": {"thought_process": "Kommando /help ausgefuehrt."}}
        st.session_state.messages.append(assistant_msg)
        _persist_current_session(backend)
        st.rerun()
        return True
    
    elif cmd == "/stats":
        status = backend.get_status()
        memory_count = backend.memory.get_memory_count()
        daily_count = backend.short_term_memory.get_count()
        stats_text = f"""**System-Statistiken:**

**Brain:** {'Verfügbar' if status['brain_available'] else 'Nicht verfügbar'}
**Modell:** {status['model']}
**Langzeitgedächtnis:** {memory_count} Erinnerungen
**Kurzzeitgedächtnis:** {daily_count} Einträge

**Emotionen:**
{_format_emotion_list(status.get('emotions', {}))}"""
        assistant_msg = {"role": "assistant", "content": stats_text, "metadata": {"thought_process": "Kommando /stats ausgeführt."}}
        st.session_state.messages.append(assistant_msg)
        _persist_current_session(backend)
        st.rerun()
        return True

    elif cmd in ["/life", "/needs", "/goals", "/world", "/habits", "/stage", "/plan", "/forecast", "/arc", "/timeline"]:
        response = backend.handle_command(cmd)
        assistant_msg = {"role": "assistant", "content": response, "metadata": {"thought_process": f"Kommando {cmd} ausgeführt."}}
        st.session_state.messages.append(assistant_msg)
        _persist_current_session(backend)
        st.rerun()
        return True
    
    elif cmd == "/config":
        st.session_state.show_settings = True
        st.rerun()
        return True
    
    # === NEU: Memory Enhancement Commands ===
    elif cmd == "/daily":
        response = backend.handle_command(cmd)
        assistant_msg = {"role": "assistant", "content": response, "metadata": {"thought_process": "Kommando /daily ausgeführt."}}
        st.session_state.messages.append(assistant_msg)
        _persist_current_session(backend)
        st.rerun()
        return True
    
    elif cmd == "/personality":
        response = backend.handle_command(cmd)
        assistant_msg = {"role": "assistant", "content": response, "metadata": {"thought_process": "Kommando /personality ausgeführt."}}
        st.session_state.messages.append(assistant_msg)
        _persist_current_session(backend)
        st.rerun()
        return True
    
    elif cmd == "/consolidate":
        with st.status("Bereinige Kurzzeitgedächtnis...", expanded=True):
            response = backend.handle_command(cmd)
        # Aktualisiere Short-term Count nach Bereinigung
        if hasattr(backend, 'short_term_memory_v2'):
            st.session_state.short_term_count = backend.short_term_memory_v2.get_count()
        assistant_msg = {"role": "assistant", "content": response, "metadata": {"thought_process": "Kommando /consolidate ausgeführt."}}
        st.session_state.messages.append(assistant_msg)
        _persist_current_session(backend)
        st.rerun()
        return True
    
    elif cmd == "/reflect":
        response = backend.handle_command(cmd)
        assistant_msg = {"role": "assistant", "content": response, "metadata": {"thought_process": "Kommando /reflect ausgeführt."}}
        st.session_state.messages.append(assistant_msg)
        _persist_current_session(backend)
        st.rerun()
        return True
    
    elif cmd == "/functions":
        response = backend.handle_command(cmd)
        assistant_msg = {"role": "assistant", "content": response, "metadata": {"thought_process": "Kommando /functions ausgeführt."}}
        st.session_state.messages.append(assistant_msg)
        _persist_current_session(backend)
        st.rerun()
        return True
    
    # === NEU: Zwei-Schritte System Commands ===
    elif cmd == "/debug":
        response = backend.handle_command(cmd)
        # Toggle Debug Mode im Session State
        st.session_state.debug_mode = not st.session_state.get("debug_mode", False)
        assistant_msg = {"role": "assistant", "content": response, "metadata": {"thought_process": "Kommando /debug ausgeführt."}}
        st.session_state.messages.append(assistant_msg)
        _persist_current_session(backend)
        st.rerun()
        return True
    
    elif cmd == "/step1":
        response = backend.handle_command(cmd)
        assistant_msg = {"role": "assistant", "content": response, "metadata": {"thought_process": "Kommando /step1 ausgeführt."}}
        st.session_state.messages.append(assistant_msg)
        _persist_current_session(backend)
        st.rerun()
        return True
    
    elif cmd == "/soul":
        response = backend.handle_command(cmd)
        assistant_msg = {"role": "assistant", "content": response, "metadata": {"thought_process": "Kommando /soul ausgeführt."}}
        st.session_state.messages.append(assistant_msg)
        _persist_current_session(backend)
        st.rerun()
        return True
    
    elif cmd == "/user":
        response = backend.handle_command(cmd)
        assistant_msg = {"role": "assistant", "content": response, "metadata": {"thought_process": "Kommando /user ausgeführt."}}
        st.session_state.messages.append(assistant_msg)
        _persist_current_session(backend)
        st.rerun()
        return True
    
    elif cmd == "/prefs" or cmd == "/preferences":
        response = backend.handle_command(cmd)
        assistant_msg = {"role": "assistant", "content": response, "metadata": {"thought_process": "Kommando /prefs ausgeführt."}}
        st.session_state.messages.append(assistant_msg)
        _persist_current_session(backend)
        st.rerun()
        return True
    
    elif cmd == "/twostep":
        response = backend.handle_command(cmd)
        assistant_msg = {"role": "assistant", "content": response, "metadata": {"thought_process": "Kommando /twostep ausgeführt."}}
        st.session_state.messages.append(assistant_msg)
        _persist_current_session(backend)
        st.rerun()
        return True
    
    return False

def process_chat_message(user_input: str, backend):
    """Verarbeitet eine normale Chat-Nachricht."""
    debug_mode = st.session_state.get("debug_mode", False)
    st.session_state.messages = backend.chat_manager.ensure_message_ids(st.session_state.messages)
    history = st.session_state.messages[:-1]
    st.session_state.session_id = backend.chat_manager.ensure_session_id(st.session_state.get("session_id"))
    backend.chat_manager.set_active_session(st.session_state.session_id)

    pending_message_id = backend.chat_manager.create_message_id()
    st.session_state.messages.append(backend._build_pending_message(pending_message_id))
    _persist_current_session(backend)

    backend.start_async_chat(
        session_id=st.session_state.session_id,
        message_id=pending_message_id,
        user_input=user_input,
        history=history,
        debug_mode=debug_mode,
    )

    with st.chat_message("assistant"):
        content_placeholder = st.empty()
        status_placeholder = st.empty()
        final_message = None

        while True:
            session_data = backend.chat_manager.load_session(st.session_state.session_id)
            st.session_state.messages = session_data.get("messages", st.session_state.messages)
            st.session_state.session_updated_at = session_data.get("updated_at")

            final_message = next(
                (msg for msg in st.session_state.messages if msg.get("id") == pending_message_id),
                None,
            )

            if final_message:
                final_meta = final_message.get("metadata") or {}
                content_placeholder.markdown(final_message.get("content", ""))
                if final_meta.get("status_text"):
                    status_placeholder.caption(final_meta.get("status_text"))
                else:
                    status_placeholder.empty()

                if not final_meta.get("pending"):
                    if final_meta.get("emotions") and isinstance(final_meta["emotions"], dict):
                        st.session_state.current_emotions = normalize_emotions(final_meta["emotions"])
                    if final_meta.get("life_snapshot"):
                        st.session_state.current_life_state = final_meta["life_snapshot"]
                    if final_meta.get("global_workspace"):
                        st.session_state.current_workspace = final_meta["global_workspace"]
                    if final_meta.get("short_term_count") is not None:
                        st.session_state.short_term_count = final_meta["short_term_count"]
                    break

            time.sleep(0.4)

        final_meta = (final_message or {}).get("metadata") or {}
        if debug_mode and final_meta.get("debug_log"):
            with st.expander("DEBUG INFO", expanded=False):
                st.text(final_meta["debug_log"])
                if final_meta.get("intent_type"):
                    st.markdown(f"**Intent:** {final_meta['intent_type']} ({final_meta.get('intent_confidence', 0):.0%})")
                if final_meta.get("tool_calls_executed", 0) > 0:
                    st.markdown(f"**Tool Calls:** {final_meta['tool_calls_executed']} ausgeführt")
                st.markdown(f"**Short-Term Entries:** {final_meta.get('short_term_count', 0)}")

    st.rerun()
