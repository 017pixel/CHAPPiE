import streamlit as st
from web_infrastructure.components import render_brain_monitor, render_memory_item

def render_chat_interface(backend):
    """Rendert die Chat-Oberfläche."""
    
    # 1. Top Command Bar (Rechteckig und gleich gross)
    st.markdown('<div style="margin-top: -30px; margin-bottom: 10px;">', unsafe_allow_html=True)
    cols = st.columns([1,1,1,1,1,1,1,0.5])  # Erweitert für /deep think
    commands = ["/sleep", "/think", "/deep think", "/help", "/stats", "/clear", "/config"]
    
    for i, cmd in enumerate(commands):
        with cols[i]:
            if st.button(cmd, key=f"top_{cmd}", help=f"Befehl {cmd} ausfuehren", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": cmd})
                st.session_state.pending_cmd = cmd
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # 2. Chat Area
    if not st.session_state.messages:
        st.markdown(f"### Hallo Benjamin! CHAPPiE v2.0 bereit.")
        st.markdown("Womit kann ich dir heute helfen?")
    
    # Message Display
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("metadata"):
                meta = msg["metadata"]
                
                # === BRAIN MONITOR (Debug Mode) ===
                if st.session_state.debug_mode:
                    with st.expander("BRAIN MONITOR (Debug)", expanded=True):
                        render_brain_monitor(meta)
                else:
                    # Normale Expander für Thoughts und RAG (wenn Debug Mode aus)
                    if meta.get("thought_process"):
                        with st.expander("Gedankenprozess"):
                            st.code(meta["thought_process"], language=None)
                    
                    # RAG Info Display
                    if meta.get("rag_memories"):
                        rag_data = meta["rag_memories"]
                        with st.expander("Relevante Infos aus Gedächtnis"):
                            if not rag_data:
                                st.info("Keine spezifischen Erinnerungen abgerufen.")
                            else:
                                for idx, m in enumerate(rag_data):
                                    render_memory_item(m, idx + 1)
                                    if idx < len(rag_data) - 1:
                                        st.divider()

    # --- INPUT ---
    if "pending_cmd" in st.session_state:
        user_input = st.session_state.pending_cmd
        del st.session_state.pending_cmd
        return user_input # Return input for processing
    else:
        user_input = st.chat_input("Schreibe eine Nachricht an CHAPPiE...")
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            return user_input # Return input for processing
    
    return None
