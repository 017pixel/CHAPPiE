import streamlit as st
from web_infrastructure.components import render_brain_monitor, render_memory_item
from web_infrastructure.ui_utils import UI_VERSION, chunk_items

COMMANDS = [
    "/sleep", "/life", "/world", "/habits", "/stage",
    "/plan", "/forecast", "/arc", "/timeline", "/think",
    "/deep think", "/help", "/stats", "/clear", "/config",
]
COMMANDS_PER_ROW = 5


def _render_assistant_message(msg: dict):
    meta = msg.get("metadata") or {}
    rag_data = meta.get("rag_memories", [])
    memory_count = len(rag_data) if rag_data else 0
    auto_expand_reasoning = bool(meta.get("reasoning_only"))

    if memory_count > 0:
        st.caption(f"📎 **{memory_count} Einträge als Kontext geladen**")

    st.markdown(msg["content"])

    if meta.get("pending"):
        st.caption(meta.get("status_text") or "Nachricht wird im Hintergrund weiter verarbeitet...")
        return

    if meta.get("reasoning_only"):
        st.caption("CHAPPiE hat nachgedacht, aber keine finale Antwort formuliert.")

    if meta.get("model_reasoning"):
        with st.expander("Modell-Reasoning", expanded=auto_expand_reasoning):
            st.code(meta["model_reasoning"], language=None)

    if meta.get("thought_process"):
        with st.expander("CHAPPiEs Gedankenprozess", expanded=auto_expand_reasoning):
            st.code(meta["thought_process"], language=None)

    if st.session_state.debug_mode:
        with st.expander("BRAIN MONITOR", expanded=False):
            render_brain_monitor(meta)
    else:
        if rag_data:
            with st.expander("Geladener Kontext", expanded=False):
                for idx, memory in enumerate(rag_data):
                    render_memory_item(memory, idx + 1)
                    if idx < len(rag_data) - 1:
                        st.divider()

def render_chat_interface(backend):
    """Rendert die Chat-Oberfläche."""
    
    # Chat Input Sichtbarkeit
    st.markdown("""
    <style>
        .stChatInputContainer { z-index: 99 !important; }
        div[data-testid="column"] div[data-testid="stButton"] > button {
            min-height: 3.2rem;
            white-space: normal;
        }
    </style>
    """, unsafe_allow_html=True)

    # ==========================================
    # 1. COMMANDS MENU
    # ==========================================
    with st.expander("Befehle", expanded=False):
        st.caption("Schnellzugriff auf Reflexion, Life-Simulation, Timeline und Systemeinstellungen.")
        for row in chunk_items(COMMANDS, COMMANDS_PER_ROW):
            row_cols = st.columns(COMMANDS_PER_ROW)
            for index in range(COMMANDS_PER_ROW):
                with row_cols[index]:
                    if index < len(row):
                        cmd = row[index]
                        if st.button(cmd, key=f"cmd_{cmd}", use_container_width=True):
                            st.session_state.messages.append({"role": "user", "content": cmd})
                            st.session_state.pending_cmd = cmd
                            st.rerun()
                    else:
                        st.empty()

    # ==========================================
    # 2. WELCOME SCREEN & STATUS
    # ==========================================
    if not st.session_state.messages:
        status = backend.get_status()
        
        # Normale Header-Struktur ohne Hero-Boxen
        st.markdown(f"## Hallo Benjamin! CHAPPiE v {UI_VERSION}")
        st.markdown("Wie kann ich dir helfen?")
        st.divider()
        
        col1, col2, col3 = st.columns(3)
        
        # Brain Status
        with col1:
            brain_status = "Bereit" if status.get('brain_available') else "Offline"
            model_info = status.get('model', 'Unbekannt')
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">LLM / BEWUSSTSEIN</div>
                <div class="metric-value">{brain_status}</div>
                <div class="metric-sub">{model_info}</div>
            </div>
            """, unsafe_allow_html=True)
            
        # Langzeit
        with col2:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">LANGZEITGEDÄCHTNIS</div>
                <div class="metric-value">{backend.memory.get_memory_count():,}</div>
                <div class="metric-sub">Gespeicherte Erinnerungen</div>
            </div>
            """, unsafe_allow_html=True)
            
        # Kurzzeit
        with col3:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">KURZZEITGEDÄCHTNIS</div>
                <div class="metric-value">{backend.short_term_memory_v2.get_count()}</div>
                <div class="metric-sub">Aktive Einträge</div>
            </div>
            """, unsafe_allow_html=True)

        life_snapshot = status.get("life_snapshot", {})
        if life_snapshot:
            goal = life_snapshot.get("active_goal", {})
            dominant_need = (life_snapshot.get("homeostasis", {}).get("dominant_need") or {}).get("name", "stability")
            st.caption(
                f"Life-Simulation: {life_snapshot.get('clock', {}).get('phase_label', '---')} | "
                f"{life_snapshot.get('current_activity', '---')} | Need: {dominant_need} | Ziel: {goal.get('title', '---')}"
            )
        
        st.markdown("<br/>", unsafe_allow_html=True)

    # ==========================================
    # 3. MESSAGE HISTORY
    # ==========================================
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant" and msg.get("metadata"):
                _render_assistant_message(msg)
            else:
                st.markdown(msg["content"])

    # ==========================================
    # 4. INPUT AREA & RETURN LOGIC
    # ==========================================
    has_pending_response = any(
        msg.get("role") == "assistant" and (msg.get("metadata") or {}).get("pending")
        for msg in st.session_state.messages
    )
    if has_pending_response:
        st.caption("CHAPPiE verarbeitet noch eine Nachricht im Hintergrund. Bitte warte kurz.")

    user_input = st.chat_input("Nachricht an CHAPPiE...", disabled=has_pending_response)
    
    if st.session_state.pending_cmd:
        cmd = st.session_state.pending_cmd
        st.session_state.pending_cmd = None
        return cmd
        
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        return user_input
    
    return None
