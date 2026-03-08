import streamlit as st
from typing import Dict, Any, List
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import json

from web_infrastructure.ui_utils import (
    EMOTION_COLORS,
    EMOTION_DISPLAY_ORDER,
    EMOTION_LABELS,
    normalize_emotions,
)

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

    emotions_dict = normalize_emotions(emotions_dict)
    st.session_state.current_emotions = emotions_dict

    for emotion_key in EMOTION_DISPLAY_ORDER:
        render_emotion_metric(
            EMOTION_LABELS[emotion_key],
            emotions_dict[emotion_key],
            EMOTION_COLORS[emotion_key],
        )

    try:
        life_snapshot = backend.get_status().get("life_snapshot", {})
        if life_snapshot:
            goal = life_snapshot.get("active_goal", {})
            dominant_need = (life_snapshot.get("homeostasis", {}).get("dominant_need") or {}).get("name", "stability")
            world_model = life_snapshot.get("world_model", {})
            stage = life_snapshot.get("development", {}).get("stage", "---")
            horizon = life_snapshot.get("planning_state", {}).get("planning_horizon", "---")
            st.caption(f"Life: {life_snapshot.get('clock', {}).get('phase_label', '---')}")
            st.caption(f"Aktivität: {life_snapshot.get('current_activity', '---')}")
            st.caption(f"Need: {dominant_need} | Ziel: {goal.get('title', '---')} | Stage: {stage} | Plan: {horizon}")
            st.caption(f"Vorhersage: {world_model.get('predicted_user_need', '---')}")
    except Exception:
        pass

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

    def render_json_block(data: Any):
        st.code(json.dumps(data, indent=2, ensure_ascii=False, default=str), language="json")

    provider = metadata.get("provider", "-")
    model = metadata.get("model", "-")
    processing_time = metadata.get("processing_time_ms", 0)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption("Provider")
        st.write(provider or "-")
    with col2:
        st.caption("Modell")
        st.write(model or "-")
    with col3:
        st.caption("Laufzeit")
        st.write(f"{processing_time:.1f} ms")

    input_text = metadata.get("input_analysis", "")
    intent_type = metadata.get("intent_type", "-")
    intent_confidence = metadata.get("intent_confidence", 0.0)
    intent_raw = metadata.get("intent_raw_json", {}) if isinstance(metadata.get("intent_raw_json", {}), dict) else {}
    with st.expander("Phase 1: Input und Intent", expanded=False):
        st.markdown(f"**Intent:** `{intent_type}` ({intent_confidence:.1%})")
        if input_text:
            st.markdown("**Input Analyse:**")
            st.write(input_text)
        if intent_raw:
            st.markdown("**Step-1 Roh-JSON:**")
            render_json_block(intent_raw)

    available_tools = metadata.get("available_tools", []) or []
    selected_tools = metadata.get("selected_tools", []) or []
    unused_tools = metadata.get("unused_tools", []) or []
    tool_calls = metadata.get("tool_calls", []) or []
    with st.expander("Phase 2: Tool-Orchestrierung", expanded=False):
        st.markdown(f"**Verfuegbare Tools:** {', '.join(available_tools) if available_tools else '-'}")
        st.markdown(f"**Ausgewaehlte Tools:** {', '.join(selected_tools) if selected_tools else 'keine'}")
        st.markdown(f"**Nicht genutzte Tools:** {', '.join(unused_tools) if unused_tools else 'keine'}")
        if tool_calls:
            for idx, call in enumerate(tool_calls, start=1):
                with st.expander(f"Tool Call #{idx}: {call.get('tool', call.get('name', 'unknown'))}", expanded=False):
                    render_json_block(call)
        else:
            st.info("Keine Tool Calls ausgefuehrt.")

    before = normalize_emotions(metadata.get("emotions_before", {}))
    delta = metadata.get("emotions_delta", {}) if isinstance(metadata.get("emotions_delta", {}), dict) else {}
    life_snapshot = metadata.get("life_snapshot", {}) if isinstance(metadata.get("life_snapshot", {}), dict) else {}
    homeostasis = life_snapshot.get("homeostasis", {}) if isinstance(life_snapshot.get("homeostasis", {}), dict) else {}
    adjustments = homeostasis.get("emotion_adjustments", {}) if isinstance(homeostasis.get("emotion_adjustments", {}), dict) else {}
    with st.expander("Phase 3: Emotionen und Homeostasis", expanded=False):
        rows = []
        for key in EMOTION_DISPLAY_ORDER:
            before_val = before.get(key, 0)
            if key in delta and isinstance(delta[key], dict):
                after_val = delta[key].get("after", before_val)
                change = delta[key].get("change", after_val - before_val)
            else:
                after_val = before_val
                change = 0
            rows.append({
                "emotion": EMOTION_LABELS.get(key, key),
                "before": before_val,
                "after": after_val,
                "delta": change,
                "homeostasis_adjustment": adjustments.get(key, 0),
            })
        st.dataframe(rows, use_container_width=True)
        if homeostasis:
            st.markdown("**Homeostasis Snapshot:**")
            render_json_block(homeostasis)

    workspace = metadata.get("global_workspace", {}) if isinstance(metadata.get("global_workspace", {}), dict) else {}
    with st.expander("Phase 4: Layer-Pipeline", expanded=False):
        layer_blocks = [
            ("Goal Engine", life_snapshot.get("goal_competition", {})),
            ("World Model", life_snapshot.get("world_model", {})),
            ("Planning", life_snapshot.get("planning_state", {})),
            ("Forecast", life_snapshot.get("forecast_state", {})),
            ("Social Arc", life_snapshot.get("social_arc", {})),
            ("Attachment", life_snapshot.get("attachment_model", {})),
            ("Development", life_snapshot.get("development", {})),
            ("Habit Dynamics", life_snapshot.get("habit_dynamics", {})),
        ]
        for title, block in layer_blocks:
            with st.expander(title, expanded=False):
                if block:
                    render_json_block(block)
                else:
                    st.write("Keine Daten")

        with st.expander("Global Workspace", expanded=False):
            workspace_items = workspace.get("workspace_items", []) if isinstance(workspace.get("workspace_items", []), list) else []
            if workspace_items:
                st.dataframe(workspace_items, use_container_width=True)
            else:
                st.write("Keine Workspace Items")
            math_trace = workspace.get("math_trace", []) if isinstance(workspace.get("math_trace", []), list) else []
            if math_trace:
                st.markdown("**Mathematische Verarbeitung:**")
                st.dataframe(math_trace, use_container_width=True)
            st.markdown("**Broadcast:**")
            st.write(workspace.get("broadcast", "-"))

    thought = metadata.get("thought_process", "")
    action_plan = metadata.get("action_plan", {}) if isinstance(metadata.get("action_plan", {}), dict) else {}
    with st.expander("Phase 5: Antwortgenerierung", expanded=False):
        if thought:
            st.markdown("**Reasoning / Gedankenprozess:**")
            st.code(thought, language=None)
        if action_plan:
            st.markdown("**Action Plan:**")
            render_json_block(action_plan)

    debug_entries = metadata.get("debug_entries", []) if isinstance(metadata.get("debug_entries", []), list) else []
    debug_log = metadata.get("debug_log", "")
    with st.expander("Phase 6: Event-Log (alle Schritte)", expanded=False):
        if debug_entries:
            for idx, entry in enumerate(debug_entries, start=1):
                title = f"{entry.get('timestamp', '--:--:--')} | {entry.get('category', '-')}: {entry.get('message', '-')}"
                with st.expander(f"#{idx} {title}", expanded=False):
                    st.markdown(f"**Level:** `{entry.get('level', '-')}`")
                    details = entry.get("details", {})
                    if details:
                        render_json_block(details)
        else:
            st.write("Keine strukturierten Debug-Events vorhanden.")
        if debug_log:
            with st.expander("Raw Debug Log", expanded=False):
                st.code(debug_log, language=None)


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
