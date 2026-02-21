import streamlit as st
import time
from web_infrastructure.components import render_brain_monitor, render_deep_think_controls

def process_command(user_input: str, backend) -> bool:
    """
    Verarbeitet Slash-Commands wie /sleep, /think, /deep think.
    Returns:
        True, wenn ein Befehl verarbeitet wurde (keine weitere Chat-Verarbeitung nötig).
        False, wenn es eine normale Nachricht ist.
    """
    cmd = user_input.strip().lower()
    
    if cmd == "/sleep":
        with st.status("System verarbeitet Erinnerungen...", expanded=True):
            res = backend.memory.consolidate_memories(backend.brain)
            backend.emotions.restore_energy(30)
        assistant_msg = {
            "role": "assistant", 
            "content": f"Schlafzyklus beendet. \n\n{res}", 
            "metadata": {"thought_process": "Kommando /sleep ausgefuehrt."}
        }
        st.session_state.messages.append(assistant_msg)
        backend.chat_manager.save_session(st.session_state.session_id, st.session_state.messages)
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
        backend.chat_manager.save_session(st.session_state.session_id, st.session_state.messages)
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
                new_emotions = {
                    "joy": step_result.emotions_after.get("happiness", 50),
                    "trust": step_result.emotions_after.get("trust", 50),
                    "energy": step_result.emotions_after.get("energy", 80),
                    "curiosity": step_result.emotions_after.get("curiosity", 60),
                    "frustration": step_result.emotions_after.get("frustration", 0),
                    "motivation": step_result.emotions_after.get("motivation", 80)
                }
                if new_emotions and isinstance(new_emotions, dict):
                    st.session_state.current_emotions = new_emotions
                
                # Zeige Live-Vitalzeichen im Status-Container
                st.markdown("---")
                st.markdown("**📊 Live-Vitalzeichen:**")
                cols_vitals = st.columns(3)
                with cols_vitals[0]:
                    st.write(f"🟢 Freude: {new_emotions['joy']}%")
                    st.write(f"🔵 Vertrauen: {new_emotions['trust']}%")
                with cols_vitals[1]:
                    st.write(f"⚡ Energie: {new_emotions['energy']}%")
                    st.write(f"🟣 Neugier: {new_emotions['curiosity']}%")
                with cols_vitals[2]:
                    st.write(f"🧡 Motivation: {new_emotions['motivation']}%")
                    st.write(f"🔴 Frustration: {new_emotions['frustration']}%")
                st.markdown("---")
                
                # Fortschritt ohne HTML anzeigen
                delta_info = ""
                if step_result.emotions_delta:
                    changes = []
                    # Übersetzung für Delta-Anzeige
                    name_map = {"happiness": "Freude", "trust": "Vertrauen", "energy": "Energie", 
                               "curiosity": "Neugier", "frustration": "Frust", "motivation": "Motivation"}
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
                   "curiosity": "Neugier", "frustration": "Frust", "motivation": "Motivation"}
        
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
        backend.chat_manager.save_session(st.session_state.session_id, st.session_state.messages)
        
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
                backend.chat_manager.save_session(st.session_state.session_id, st.session_state.messages)
                
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
        backend.chat_manager.save_session(st.session_state.session_id, st.session_state.messages)
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
- Freude: {status['emotions']['joy']}%
- Vertrauen: {status['emotions']['trust']}%
- Energie: {status['emotions']['energy']}%
- Neugier: {status['emotions']['curiosity']}%"""
        assistant_msg = {"role": "assistant", "content": stats_text, "metadata": {"thought_process": "Kommando /stats ausgeführt."}}
        st.session_state.messages.append(assistant_msg)
        backend.chat_manager.save_session(st.session_state.session_id, st.session_state.messages)
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
        backend.chat_manager.save_session(st.session_state.session_id, st.session_state.messages)
        st.rerun()
        return True
    
    elif cmd == "/personality":
        response = backend.handle_command(cmd)
        assistant_msg = {"role": "assistant", "content": response, "metadata": {"thought_process": "Kommando /personality ausgeführt."}}
        st.session_state.messages.append(assistant_msg)
        backend.chat_manager.save_session(st.session_state.session_id, st.session_state.messages)
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
        backend.chat_manager.save_session(st.session_state.session_id, st.session_state.messages)
        st.rerun()
        return True
    
    elif cmd == "/reflect":
        response = backend.handle_command(cmd)
        assistant_msg = {"role": "assistant", "content": response, "metadata": {"thought_process": "Kommando /reflect ausgeführt."}}
        st.session_state.messages.append(assistant_msg)
        backend.chat_manager.save_session(st.session_state.session_id, st.session_state.messages)
        st.rerun()
        return True
    
    elif cmd == "/functions":
        response = backend.handle_command(cmd)
        assistant_msg = {"role": "assistant", "content": response, "metadata": {"thought_process": "Kommando /functions ausgeführt."}}
        st.session_state.messages.append(assistant_msg)
        backend.chat_manager.save_session(st.session_state.session_id, st.session_state.messages)
        st.rerun()
        return True
    
    # === NEU: Zwei-Schritte System Commands ===
    elif cmd == "/debug":
        response = backend.handle_command(cmd)
        # Toggle Debug Mode im Session State
        st.session_state.debug_mode = not st.session_state.get("debug_mode", False)
        assistant_msg = {"role": "assistant", "content": response, "metadata": {"thought_process": "Kommando /debug ausgeführt."}}
        st.session_state.messages.append(assistant_msg)
        backend.chat_manager.save_session(st.session_state.session_id, st.session_state.messages)
        st.rerun()
        return True
    
    elif cmd == "/step1":
        response = backend.handle_command(cmd)
        assistant_msg = {"role": "assistant", "content": response, "metadata": {"thought_process": "Kommando /step1 ausgeführt."}}
        st.session_state.messages.append(assistant_msg)
        backend.chat_manager.save_session(st.session_state.session_id, st.session_state.messages)
        st.rerun()
        return True
    
    elif cmd == "/soul":
        response = backend.handle_command(cmd)
        assistant_msg = {"role": "assistant", "content": response, "metadata": {"thought_process": "Kommando /soul ausgeführt."}}
        st.session_state.messages.append(assistant_msg)
        backend.chat_manager.save_session(st.session_state.session_id, st.session_state.messages)
        st.rerun()
        return True
    
    elif cmd == "/user":
        response = backend.handle_command(cmd)
        assistant_msg = {"role": "assistant", "content": response, "metadata": {"thought_process": "Kommando /user ausgeführt."}}
        st.session_state.messages.append(assistant_msg)
        backend.chat_manager.save_session(st.session_state.session_id, st.session_state.messages)
        st.rerun()
        return True
    
    elif cmd == "/prefs" or cmd == "/preferences":
        response = backend.handle_command(cmd)
        assistant_msg = {"role": "assistant", "content": response, "metadata": {"thought_process": "Kommando /prefs ausgeführt."}}
        st.session_state.messages.append(assistant_msg)
        backend.chat_manager.save_session(st.session_state.session_id, st.session_state.messages)
        st.rerun()
        return True
    
    elif cmd == "/twostep":
        response = backend.handle_command(cmd)
        assistant_msg = {"role": "assistant", "content": response, "metadata": {"thought_process": "Kommando /twostep ausgeführt."}}
        st.session_state.messages.append(assistant_msg)
        backend.chat_manager.save_session(st.session_state.session_id, st.session_state.messages)
        st.rerun()
        return True
    
    return False

def process_chat_message(user_input: str, backend):
    """Verarbeitet eine normale Chat-Nachricht."""
    # Debug Mode aus Session State holen
    debug_mode = st.session_state.get("debug_mode", False)
    
    with st.chat_message("assistant"):
        with st.spinner("CHAPPiE denkt nach..."):
            result = backend.process(user_input, st.session_state.messages[:-1], debug_mode=debug_mode)
            st.markdown(result["response_text"])
            if result.get("emotions") and isinstance(result["emotions"], dict):
                st.session_state.current_emotions = result["emotions"]
            
            # Aktualisiere Short-term Memory Count fuer Sidebar
            if result.get("short_term_count") is not None:
                st.session_state.short_term_count = result["short_term_count"]
            
            # Zeige Debug Info wenn Debug Mode an
            if debug_mode and result.get("debug_log"):
                with st.expander("🔍 DEBUG INFO", expanded=False):
                    st.text(result["debug_log"])
                    
                    # Zeige Intent Info
                    if result.get("intent_type"):
                        st.markdown(f"**Intent:** {result['intent_type']} ({result.get('intent_confidence', 0):.0%})")
                    
                    # Zeige Tool Calls
                    if result.get("tool_calls_executed", 0) > 0:
                        st.markdown(f"**Tool Calls:** {result['tool_calls_executed']} ausgeführt")
                    
                    # Zeige Short Term Count
                    st.markdown(f"**Short-Term Entries:** {result.get('short_term_count', 0)}")
    
    # Helper to serialize memories for JSON storage (Memory objects are not JSON serializable by default)
    formatted_memories = []
    if result.get("rag_memories"):
        for m in result["rag_memories"]:
            formatted_memories.append({
                "content": m.content,
                "relevance_score": m.relevance_score,
                "role": m.role,
                "label": getattr(m, 'label', 'original'),
                "id": m.id,
                "timestamp": getattr(m, 'timestamp', ''),
                "type": getattr(m, 'mem_type', 'interaction'),
            })

    intent_raw = result.get("intent_raw_json", {})
    tool_calls_raw = []
    if result.get("tool_calls_executed", 0) > 0 and intent_raw.get("tool_calls"):
        tool_calls_raw = intent_raw.get("tool_calls", [])
    
    assistant_msg = {
        "role": "assistant",
        "content": result["response_text"],
        "metadata": {
            "thought_process": result.get("thought_process"),
            "rag_memories": formatted_memories,
            "emotions_delta": result.get("emotions_delta", {}),
            "emotions_before": result.get("emotions_before", {}),
            "input_analysis": result.get("input_analysis", user_input),
            "intent_type": result.get("intent_type"),
            "intent_confidence": result.get("intent_confidence"),
            "tool_calls_executed": result.get("tool_calls_executed", 0),
            "intent_raw_json": intent_raw,
            "tool_calls": tool_calls_raw,
            "short_term_count": result.get("short_term_count", 0),
            "processing_time_ms": result.get("processing_time_ms", 0),
        }
    }

    st.session_state.messages.append(assistant_msg)
    backend.chat_manager.save_session(st.session_state.session_id, st.session_state.messages)
    st.rerun()
