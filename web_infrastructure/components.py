import streamlit as st
from typing import Dict, Any, List
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import json

def render_emotion_metric(label, value, color="#81c784"):
    st.markdown(f"""
    <div style="font-size: 0.8rem; color: #a0a0a0; display: flex; justify-content: space-between;">
        <span>{label}</span>
        <span>{value}%</span>
    </div>
    <div class="emotion-bar-bg">
        <div class="emotion-bar-fill" style="width: {value}%; background-color: {color};"></div>
    </div>
    """, unsafe_allow_html=True)


def render_vital_signs(backend):
    """Rendert den kompletten Block der Vitalzeichen ohne übertriebene Effekte."""
    emotions_dict = st.session_state.get("current_emotions", {})
    if not emotions_dict:
        try:
            emotions_dict = backend._get_emotions_snapshot()
        except:
            emotions_dict = {}

    render_emotion_metric("Freude", emotions_dict.get("joy", 50), "#81c784")
    render_emotion_metric("Vertrauen", emotions_dict.get("trust", 50), "#00a3cc")
    render_emotion_metric("Energie", emotions_dict.get("energy", 80), "#f5f5f5")
    render_emotion_metric("Neugier", emotions_dict.get("curiosity", 60), "#ff6b9d")
    render_emotion_metric("Motivation", emotions_dict.get("motivation", 80), "#a0a0a0")

    st.divider()
    
    try:
        live_memory = backend.memory
        memory_count = live_memory.get_memory_count()
        health = live_memory.health_check()

        if health["embedding_model_loaded"] and health["chromadb_connected"]:
            st.markdown(f"**Langzeit:** {memory_count:,}")
        else:
            st.markdown(f"**Langzeit:** {memory_count:,} (Fehler)")

        if memory_count > 0:
            try:
                recent = live_memory.get_recent_memories(limit=1)
                if recent:
                    last_memory = recent[0]
                    # Ensure timestamp extraction works for both dicts and objects
                    timestamp_str = last_memory.get('timestamp') if isinstance(last_memory, dict) else getattr(last_memory, 'timestamp', None)
                    
                    formatted = _format_timestamp_german(timestamp_str) if timestamp_str else "Unbekannt"
                    st.caption(f"Letzte: {formatted}")
            except Exception:
                pass
    except Exception as e:
        st.markdown("**Langzeit:** Fehler")
    
    try:
        stm_count = st.session_state.get("short_term_count", 0)
        
        if stm_count > 0:
            st.markdown(f"**Kurzzeit:** {stm_count}")
        else:
            if hasattr(backend, 'short_term_memory_v2'):
                backend_count = backend.short_term_memory_v2.get_count()
                st.session_state.short_term_count = backend_count
                st.markdown(f"**Kurzzeit:** {backend_count}")
    except Exception:
        pass


def render_brain_monitor(metadata: Dict[str, Any]):
    if not metadata:
        return
        
    def render_section(title, content, type_class):
        st.markdown(f'<div class="brain-monitor-section {type_class}"><strong>{title}</strong><br/>{content}</div>', unsafe_allow_html=True)
    
    input_text = metadata.get("input_analysis", "")
    if input_text:
        render_section("INPUT ANALYSE", input_text, "input")
        
    thought = metadata.get("thought_process", "")
    if thought:
        render_section("GEDANKEN", thought, "thought")

    tool_calls = metadata.get("tool_calls", [])
    if tool_calls:
        render_section(f"TOOLS ({len(tool_calls)} ausgefuehrt)", f"Tools: {', '.join(t.get('tool', t.get('name', '')) for t in tool_calls)}", "input")


def _format_timestamp_german(timestamp_str: str) -> str:
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
    """Rendert eine einzelne Erinnerung. Normal UI Format."""
    if mem is None:
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

    type_badge = "ZUSAMMENFASSUNG" if label == "zsm gefasst" else "ORIGINAL"
    role_label = "Benutzer" if role == "user" else "CHAPPiE"

    display_timestamp = _format_timestamp_german(timestamp) if (format_timestamp and timestamp) else ""

    with st.container(border=True):
        if display_timestamp:
            st.markdown(f"**#{index} | {type_badge} | {role_label} | {display_timestamp} | ID: `{mem_id}`**")
        else:
            st.markdown(f"**#{index} | {type_badge} | {role_label}** (Relevanz: {score}%)")
            
        st.markdown(content)

def render_deep_think_controls(current_total_done: int) -> str:
    """
    Rendert die Steuerungs-Buttons für den Deep Think Modus.
    
    Returns:
        String Action Code: "10", "20", "30", "40", "60", "100", "sleep", "stop" oder None
    """
    st.markdown("### Weiterdenken?")
    
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
    
    cols_row2 = st.columns(3)
    with cols_row2[0]:
        if st.button("60 Gedanken", key=f"dt_60_{current_total_done}", use_container_width=True):
            return "60"
    with cols_row2[1]:
        if st.button("100 Gedanken", key=f"dt_100_{current_total_done}", use_container_width=True):
            return "100"
    with cols_row2[2]:
        if st.button("🌙 Sleep", key=f"dt_sleep_{current_total_done}", use_container_width=True):
            return "sleep"
            
    return None
