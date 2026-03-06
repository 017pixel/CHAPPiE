import streamlit as st
from web_infrastructure.components import render_brain_monitor, render_memory_item

def render_chat_interface(backend):
    """Rendert die Chat-Oberfläche."""
    
    # Chat Input Sichtbarkeit
    st.markdown("""
    <style>
        .stChatInputContainer { z-index: 99 !important; }
    </style>
    """, unsafe_allow_html=True)

    # ==========================================
    # 1. COMMANDS MENU
    # ==========================================
    commands = ["/sleep", "/think", "/deep think", "/help", "/stats", "/clear", "/config"]

    with st.expander("Befehle", expanded=False):
        m_cols = st.columns(len(commands))
        for i, cmd in enumerate(commands):
            with m_cols[i]:
                if st.button(cmd, key=f"cmd_{cmd}", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "content": cmd})
                    st.session_state.pending_cmd = cmd
                    st.rerun()

    # ==========================================
    # 2. WELCOME SCREEN & STATUS
    # ==========================================
    if not st.session_state.messages:
        status = backend.get_status()
        
        # Normale Header-Struktur ohne Hero-Boxen
        st.markdown("## Hallo Benjamin! CHAPPiE v2.0")
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
        
        st.markdown("<br/>", unsafe_allow_html=True)

    # ==========================================
    # 3. MESSAGE HISTORY
    # ==========================================
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant" and msg.get("metadata"):
                meta = msg["metadata"]
                rag_data = meta.get("rag_memories", [])
                memory_count = len(rag_data) if rag_data else 0
                
                # Context Files / Memories Info-Leiste vor der Antwort
                if memory_count > 0:
                    st.caption(f"📎 **{memory_count} Einträge als Kontext geladen**")
                
                st.markdown(msg["content"])
                
                if st.session_state.debug_mode:
                    with st.expander("BRAIN MONITOR", expanded=False):
                        render_brain_monitor(meta)
                else:
                    if meta.get("thought_process"):
                        with st.expander("Gedankenprozess", expanded=False):
                            st.code(meta["thought_process"], language=None)
                    
                    if rag_data:
                        with st.expander("Geladener Kontext", expanded=False):
                            for idx, m in enumerate(rag_data):
                                render_memory_item(m, idx + 1)
                                if idx < len(rag_data) - 1:
                                    st.divider()
            else:
                st.markdown(msg["content"])

    # ==========================================
    # 4. INPUT AREA & RETURN LOGIC
    # ==========================================
    user_input = st.chat_input("Nachricht an CHAPPiE...")
    
    if st.session_state.pending_cmd:
        cmd = st.session_state.pending_cmd
        st.session_state.pending_cmd = None
        return cmd
        
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        return user_input
    
    return None
