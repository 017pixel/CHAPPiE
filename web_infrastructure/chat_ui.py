import streamlit as st
from web_infrastructure.components import render_brain_monitor, render_memory_item

def render_chat_interface(backend):
    """Rendert die Chat-Oberfläche."""
    
    # ==========================================
    # CSS: Card Styling & Chat Input
    # ==========================================
    st.markdown("""
    <style>
        /* Card Styling */
        .info-card-box {
            background-color: #161b22; 
            border: 1px solid #30363d; 
            border-radius: 8px; 
            padding: 15px; 
            color: #c9d1d9;
            height: auto; 
            min-height: 110px;
            margin-bottom: 15px; 
            box-shadow: 0 2px 6px rgba(0,0,0,0.2);
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        /* Chat Input Visibility Hook */
        .stChatInputContainer {
            z-index: 999 !important;
        }
    </style>
    """, unsafe_allow_html=True)


    # ==========================================
    # 1. COMMANDS NAVIGATION (Single Expander)
    # ==========================================
    commands = ["/sleep", "/think", "/deep think", "/help", "/stats", "/clear", "/config"]

    with st.expander("Menü & Befehle", expanded=False):
        m_cols = st.columns(4)  # 4 columns for better spacing on PC
        for i, cmd in enumerate(commands):
            with m_cols[i % 4]:
                if st.button(cmd, key=f"cmd_{cmd}", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "content": cmd})
                    st.session_state.pending_cmd = cmd
                    st.rerun()


    # ==========================================
    # 2. WELCOME SCREEN & STATUS
    # ==========================================
    
    if not st.session_state.messages:
        status = backend.get_status()
        
        # Welcome Banner
        st.markdown("""
        <div style='background: linear-gradient(135deg, #0d1117 0%, #161b22 100%); 
                    padding: 20px; 
                    border-radius: 12px; 
                    margin-bottom: 20px; 
                    border: 1px solid #30363d;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.5);'>
            <h2 style='color: #c9d1d9; margin: 0; font-weight: 600; font-family: "Outfit", sans-serif; font-size: 1.4rem;'>
                Hallo Benjamin! CHAPPiE v2.0
            </h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Status Cards
        col1, col2, col3 = st.columns(3)
        
        # Brain Status
        with col1:
            st.markdown(f"""
            <div class="info-card-box">
                <div style='font-size: 0.8rem; color: #8b949e; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px;'>Brain</div>
                <div style='font-size: 1.1rem; font-weight: 600; margin-bottom: 2px;'>
                    {"Bereit" if status.get('brain_available') else "Offline"}
                </div>
                <div style='font-size: 0.8rem; color: #58a6ff;'>{status.get('model', 'Unbekannt')}</div>
            </div>
            """, unsafe_allow_html=True)
            
        # Long Term
        with col2:
            st.markdown(f"""
            <div class="info-card-box">
                <div style='font-size: 0.8rem; color: #8b949e; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px;'>Langzeit</div>
                <div style='font-size: 1.1rem; font-weight: 600; color: #3fb950;'>
                    {backend.memory.get_memory_count():,}
                </div>
                <div style='font-size: 0.8rem;'>Erinnerungen</div>
            </div>
            """, unsafe_allow_html=True)
            
        # Short Term
        with col3:
            st.markdown(f"""
            <div class="info-card-box">
                <div style='font-size: 0.8rem; color: #8b949e; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px;'>Kurzzeit</div>
                <div style='font-size: 1.1rem; font-weight: 600; color: #d2a8ff;'>
                    {backend.short_term_memory_v2.get_count()}
                </div>
                <div style='font-size: 0.8rem;'>Einträge</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
        st.caption("💬 **Wie kann ich helfen?**")

    
    # ==========================================
    # 3. MESSAGE HISTORY
    # ==========================================
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("metadata"):
                meta = msg["metadata"]
                
                if st.session_state.debug_mode:
                    with st.expander("BRAIN MONITOR", expanded=True):
                        render_brain_monitor(meta)
                else:
                    if meta.get("thought_process"):
                        with st.expander("Gedankenprozess"):
                            st.code(meta["thought_process"], language=None)
                    
                    if meta.get("rag_memories"):
                        rag_data = meta["rag_memories"]
                        with st.expander("Relevante Infos"):
                            if not rag_data:
                                st.info("Keine Daten.")
                            else:
                                for idx, m in enumerate(rag_data):
                                    render_memory_item(m, idx + 1)
                                    if idx < len(rag_data) - 1:
                                        st.divider()

    # ==========================================
    # 4. INPUT AREA & RETURN LOGIC
    # ==========================================
    user_input = st.chat_input("Nachricht an CHAPPiE...")
    
    # Check for pending command from button clicks
    if st.session_state.pending_cmd:
        cmd = st.session_state.pending_cmd
        st.session_state.pending_cmd = None  # Reset to None, not delete
        return cmd
        
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        return user_input
    
    return None
