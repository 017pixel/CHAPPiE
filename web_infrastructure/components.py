import streamlit as st
from typing import Dict, Any, List
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from memory.memory_engine import MemoryEngine
import json

def render_emotion_metric(label, value, color="#2ea043"):
    st.markdown(f"""
    <div style="font-size: 0.8rem; color: #8b949e; display: flex; justify-content: space-between;">
        <span>{label}</span>
        <span>{value}%</span>
    </div>
    <div class="emotion-bar-bg">
        <div class="emotion-bar-fill" style="width: {value}%; background-color: {color};"></div>
    </div>
    """, unsafe_allow_html=True)


def render_vital_signs(backend):
    """Rendert den kompletten Block der Vitalzeichen."""
    emotions_dict = st.session_state.get("current_emotions", {})
    if not emotions_dict:
        try:
            emotions_dict = backend._get_emotions_snapshot()
        except:
            emotions_dict = {}

    render_emotion_metric("Freude", emotions_dict.get("joy", 50), "#FFD700")
    render_emotion_metric("Vertrauen", emotions_dict.get("trust", 50), "#2196F3")
    render_emotion_metric("Energie", emotions_dict.get("energy", 80), "#4CAF50")
    render_emotion_metric("Neugier", emotions_dict.get("curiosity", 60), "#9C27B0")
    render_emotion_metric("Motivation", emotions_dict.get("motivation", 80), "#FF9800")
    render_emotion_metric("Frustration", emotions_dict.get("frustration", 0), "#F44336")

    st.markdown("---")
    try:
        live_memory = backend.memory
        
        memory_count = live_memory.get_memory_count()
        
        health = live_memory.health_check()

        if health["embedding_model_loaded"] and health["chromadb_connected"]:
            if health.get("is_persistent", True):
                st.metric("🧠 Erinnerungen", f"{memory_count:,}")
                st.caption("Langzeitgedaechtnis aktiv")
            else:
                st.metric("🧠 Erinnerungen", f"{memory_count:,}")
                st.caption("In-Memory Modus (nicht persistent)")
        else:
            error_details = []
            if not health["embedding_model_loaded"]:
                error_details.append("Embedding-Modell")
            if not health["chromadb_connected"]:
                error_details.append("ChromaDB")
            
            if error_details:
                st.metric("🧠 Erinnerungen", f"{memory_count:,}")
                st.caption(f"⚠️ Probleme: {', '.join(error_details)}")
            else:
                st.metric("🧠 Erinnerungen", f"{memory_count:,}")
                st.caption("⚠️ Memory-System Probleme")

        if memory_count > 0:
            try:
                recent = live_memory.get_recent_memories(limit=1)
                if recent:
                    last_memory = recent[0]
                    if isinstance(last_memory, dict):
                        timestamp_str = last_memory.get('timestamp')
                    else:
                        timestamp_str = getattr(last_memory, 'timestamp', None)
                    
                    if timestamp_str:
                        formatted = _format_timestamp_german(timestamp_str)
                        st.caption(f"Letzte: {formatted}")
                    else:
                        st.caption("Letzte: Unbekannt")
                else:
                    st.caption("Letzte: Unbekannt")
            except Exception:
                st.caption("Letzte: Unbekannt")

    except Exception as e:
        st.metric("[BRAIN] Erinnerungen", "Fehler")
        st.caption(f"[ERROR] {str(e)[:30]}...")
    
    st.markdown("---")
    try:
        stm_count = st.session_state.get("short_term_count", 0)
        
        if stm_count > 0:
            st.metric("Kurzzeit", f"{stm_count} Eintraege")
            st.caption("Aktive Eintraege (24h)")
        else:
            if hasattr(backend, 'short_term_memory_v2'):
                backend_count = backend.short_term_memory_v2.get_count()
                st.session_state.short_term_count = backend_count
                st.metric("Kurzzeit", f"{backend_count} Eintraege")
                if backend_count > 0:
                    st.caption("Aktive Eintraege (24h)")
                else:
                    st.caption("Keine aktiven Eintraege")
            else:
                st.metric("Kurzzeit", "0 Eintraege")
                st.caption("Keine aktiven Eintraege")
    except Exception as e:
        st.metric("Kurzzeit", "Fehler")
        st.caption(f"[ERROR] {str(e)[:20]}...")


def render_brain_monitor(metadata: Dict[str, Any]):
    """
    Rendert das Brain Monitor Debug-Panel für eine Nachricht.
    Strukturierte Ansicht mit aufklappbaren Sektionen pro Verarbeitungs-Schritt.
    """
    if not metadata:
        return
    
    st.markdown("""
    <style>
        .bm-header { 
            font-size: 0.85rem; 
            font-weight: 600; 
            color: #c9d1d9; 
            margin-bottom: 8px;
            padding: 6px 10px;
            background: rgba(22, 27, 34, 0.8);
            border-radius: 4px;
            border-left: 3px solid #58a6ff;
        }
        .bm-section { 
            margin: 6px 0; 
            padding: 4px 0;
        }
        .bm-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-left: 8px;
        }
        .bm-badge-success { background: #238636; color: #fff; }
        .bm-badge-info { background: #1f6feb; color: #fff; }
        .bm-badge-warning { background: #9e6a03; color: #fff; }
    </style>
    """, unsafe_allow_html=True)
    
    _render_input_section(metadata)
    _render_thought_section(metadata)
    _render_intent_section(metadata)
    _render_tool_calls_section(metadata)
    _render_emotions_section(metadata)
    _render_memories_section(metadata)


def _render_input_section(metadata: Dict[str, Any]):
    """Rendert die Input-Analyse Sektion."""
    with st.expander("INPUT ANALYSE", expanded=False):
        input_text = metadata.get("input_analysis", "N/A")
        st.info(input_text)
        
        if metadata.get("intent_type"):
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Intent", metadata.get("intent_type", "N/A"))
            with col2:
                conf = metadata.get("intent_confidence", 0)
                st.metric("Confidence", f"{conf:.0%}" if conf else "N/A")


def _render_thought_section(metadata: Dict[str, Any]):
    """Rendert die Chain of Thought Sektion."""
    thought = metadata.get("thought_process", "")
    if thought:
        with st.expander("CHAIN OF THOUGHT", expanded=False):
            st.text_area("Gedankenprozess", thought, height=150, disabled=True, label_visibility="collapsed")


def _render_intent_section(metadata: Dict[str, Any]):
    """Rendert die Intent Analysis JSON Sektion."""
    raw_json = metadata.get("intent_raw_json", {})
    if raw_json:
        with st.expander("INTENT ANALYSIS (JSON)", expanded=False):
            _render_json_with_highlight(raw_json)


def _render_tool_calls_section(metadata: Dict[str, Any]):
    """Rendert die Tool Calls Sektion."""
    tool_calls = metadata.get("tool_calls", [])
    executed = metadata.get("tool_calls_executed", 0)
    
    if executed > 0 or tool_calls:
        with st.expander(f"TOOL CALLS ({executed})", expanded=False):
            if not tool_calls:
                st.info(f"{executed} Tool(s) ausgefuehrt")
            else:
                for i, tc in enumerate(tool_calls):
                    tool_name = tc.get("tool", tc.get("name", "unknown"))
                    action = tc.get("action", "N/A")
                    data = tc.get("data", {})
                    
                    st.markdown(f"**Tool #{i+1}: `{tool_name}`**")
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        st.caption(f"Action: {action}")
                    with col2:
                        if data:
                            _render_json_mini(data)
                    if i < len(tool_calls) - 1:
                        st.divider()


def _render_emotions_section(metadata: Dict[str, Any]):
    """Rendert die Emotions-Delta Sektion."""
    with st.expander("EMOTIONS-DELTA", expanded=False):
        if metadata.get("emotions_delta"):
            emotion_names = {
                "happiness": "Freude",
                "joy": "Freude",
                "trust": "Vertrauen", 
                "energy": "Energie",
                "curiosity": "Neugier",
                "frustration": "Frustration",
                "motivation": "Motivation"
            }
            
            cols = st.columns(3)
            col_idx = 0
            for emotion, data in metadata["emotions_delta"].items():
                if isinstance(data, dict):
                    change = data.get("change", 0)
                    before = data.get("before", 0)
                    after = data.get("after", 0)
                else:
                    continue
                    
                name = emotion_names.get(emotion, emotion)
                
                with cols[col_idx % 3]:
                    if change > 0:
                        st.success(f"{name}: {before}% -> {after}% (+{change})")
                    elif change < 0:
                        st.error(f"{name}: {before}% -> {after}% ({change})")
                    else:
                        st.info(f"{name}: {before}%")
                col_idx += 1
        else:
            st.caption("Keine Emotions-Aenderungen")


def _render_memories_section(metadata: Dict[str, Any]):
    """Rendert die geladenen Memories Sektion."""
    memories = metadata.get("rag_memories", [])
    with st.expander(f"GELADENE MEMORIES ({len(memories)})", expanded=False):
        if not memories:
            st.info("Keine Memories geladen")
        else:
            for i, mem in enumerate(memories):
                render_memory_item(mem, i + 1)
                if i < len(memories) - 1:
                    st.divider()


def _render_json_with_highlight(data: Dict[str, Any], max_height: int = 300):
    """Rendert JSON mit Syntax-Highlighting."""
    try:
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
    except Exception:
        json_str = str(data)
    
    st.code(json_str, language="json")


def _render_json_mini(data: Dict[str, Any]):
    """Rendert ein kompaktes JSON."""
    try:
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        if len(json_str) > 500:
            json_str = json_str[:500] + "\n..."
    except Exception:
        json_str = str(data)[:500]
    
    st.code(json_str, language="json")


def _format_timestamp_german(timestamp_str: str) -> str:
    """
    Konvertiert einen UTC-Timestamp zu deutscher Zeit (Europe/Berlin).
    
    Args:
        timestamp_str: ISO-Format Timestamp String (UTC)
    
    Returns:
        Formatierter String "DD.MM.YYYY HH:MM:SS" in deutscher Zeit
    """
    if not timestamp_str:
        return "Unbekannt"
    
    try:
        dt = datetime.fromisoformat(timestamp_str)
        
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        german_tz = ZoneInfo("Europe/Berlin")
        return dt.astimezone(german_tz).strftime("%d.%m.%Y %H:%M:%S")
    except (ValueError, TypeError):
        return timestamp_str


def render_memory_item(mem: Any, index: int = 1, format_timestamp: bool = False):
    """
    Rendert eine einzelne Erinnerung konsistent für alle Views.
    
    ROBUST: Behandelt None-Werte und fehlende Felder graceful.
    
    Args:
        mem: Memory-Objekt oder Dictionary
        index: Index der Erinnerung (für Anzeige #1, #2...)
        format_timestamp: Wenn True, wird Timestamp zu deutscher Zeit konvertiert
    """
    if mem is None:
        st.caption("*Ungültige Erinnerung (None)*")
        return
    
    if isinstance(mem, dict):
        content = mem.get("content") or ""
        raw_score = mem.get("relevance_score") or 0.0
        score = int(float(raw_score) * 100) if raw_score else 0
        raw_id = mem.get("id") or "?"
        mem_id = str(raw_id)[:8] if raw_id else "?"
        label = mem.get("label") or "original"
        role = mem.get("role") or "unknown"
        mem_type = mem.get("type") or "interaction"
        timestamp = mem.get("timestamp") or ""
    else:
        content = getattr(mem, 'content', None) or ""
        raw_score = getattr(mem, 'relevance_score', None)
        score = int(float(raw_score) * 100) if raw_score else 0
        raw_id = getattr(mem, 'id', None)
        mem_id = str(raw_id)[:8] if raw_id else "?"
        label = getattr(mem, 'label', None) or 'original'
        role = getattr(mem, 'role', None) or 'unknown'
        mem_type = getattr(mem, 'mem_type', None) or 'interaction'
        timestamp = getattr(mem, 'timestamp', None) or ""
    
    if not isinstance(content, str):
        content = str(content) if content is not None else ""

    if label == "zsm gefasst":
        label_html = '<span style="color: #2ea043; font-weight: bold; border: 1px solid #2ea043; padding: 2px 6px; border-radius: 4px; font-size: 0.8em;">SUMMARY</span>'
    else:
        label_html = '<span style="color: #8b949e; font-weight: bold; border: 1px solid #8b949e; padding: 2px 6px; border-radius: 4px; font-size: 0.8em;">ORIGINAL</span>'

    role_label = "User" if role == "user" else "CHAPiE"
    type_badge = "[Interaction]" if mem_type == "interaction" else "[Summary]"

    if format_timestamp and timestamp:
        display_timestamp = _format_timestamp_german(timestamp)
    else:
        display_timestamp = timestamp

    col1, col2 = st.columns([3, 1])
    with col1:
        if display_timestamp: 
            st.markdown(f"### {label_html} {type_badge} {role_label} #{index}", unsafe_allow_html=True)
            st.markdown(f"**ID:** `{mem_id}` | **Zeit:** {display_timestamp}")
            st.markdown(content)
        else:
            st.markdown(f"**Info {index}** {label_html} (Relevanz: {score}%)", unsafe_allow_html=True)
            if content and isinstance(content, str):
                st.caption(content[:250] + "..." if len(content) > 250 else content)
            else:
                st.caption("*Keine Inhaltsdaten verfügbar*")
            
    with col2:
        if score > 0:
            st.progress(score / 100)


def render_deep_think_controls(current_total_done: int) -> str:
    """
    Rendert die Steuerungs-Buttons für den Deep Think Modus.
    
    Returns:
        String Action Code: "10", "20", "sleep", "stop" oder None
    """
    action = None
    
    with st.container(border=True):
        st.markdown("### Soll CHAPPiE weiterdenken?")
        
        # Erste Zeile: 10, 20, 30, 40 Gedanken
        cols_row1 = st.columns(4)
        with cols_row1[0]:
            if st.button("10 Gedanken", key=f"dt_10_{current_total_done}", use_container_width=True):
                return "10"
        with cols_row1[1]:
            if st.button("20 Gedanken", key=f"dt_20_{current_total_done}", use_container_width=True):
                return "20"
        with cols_row1[2]:
            if st.button("30 Gedanken", key=f"dt_30_{current_total_done}", use_container_width=True):
                return "30"
        with cols_row1[3]:
            if st.button("40 Gedanken", key=f"dt_40_{current_total_done}", use_container_width=True):
                return "40"
        
        # Zweite Zeile: 60, 100 Gedanken und Sleep
        cols_row2 = st.columns(3)
        with cols_row2[0]:
            if st.button("60 Gedanken", key=f"dt_60_{current_total_done}", use_container_width=True):
                return "60"
        with cols_row2[1]:
            if st.button("100 Gedanken", key=f"dt_100_{current_total_done}", use_container_width=True):
                return "100"
        with cols_row2[2]:
            if st.button("🌙 Sleep & Zusammenfassen", key=f"dt_sleep_{current_total_done}", use_container_width=True):
                return "sleep"
                
    return None
