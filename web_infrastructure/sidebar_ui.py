import streamlit as st
from web_infrastructure.components import render_vital_signs

def render_sidebar(backend):
    """Rendert die Sidebar-Navigation und Verlauf."""
    with st.sidebar:
        st.markdown('<div class="header-logo">CHAPPiE</div>', unsafe_allow_html=True)

        if st.button("Neuer Chat", use_container_width=True, key="sidebar_new_chat"):
            st.session_state.session_id = backend.chat_manager.create_session()
            st.session_state.messages = []
            st.rerun()

        if st.button("Alle Erinnerungen", use_container_width=True, key="sidebar_memories"):
            st.session_state.show_memories = not st.session_state.show_memories
            st.rerun()
        
        if st.button("Einstellungen", use_container_width=True, key="sidebar_settings"):
            st.session_state.show_settings = not st.session_state.show_settings
            st.rerun()
        
        # === BRAIN MONITOR TOGGLE ===
        st.markdown("---")
        debug_label = "DEBUG MODE: ON" if st.session_state.debug_mode else "DEBUG MODE: OFF"
        if st.button(debug_label, use_container_width=True, key="sidebar_debug_toggle"):
            st.session_state.debug_mode = not st.session_state.debug_mode
            st.rerun()

        st.markdown("---")
        
        st.markdown("**VITALZEICHEN**")
        render_vital_signs(backend)
        
        st.markdown("---")

        st.markdown("**VERLAUF**")
        sessions = backend.chat_manager.list_sessions()
        
        for s in sessions[:25]:
            # Highlight current session
            label = s['title'][:30]
            if s["id"] == st.session_state.session_id:
                label = f"> {label}"
            
            if st.button(label, key=f"sess_{s['id']}", use_container_width=True):
                st.session_state.session_id = s["id"]
                data = backend.chat_manager.load_session(s["id"])
                st.session_state.messages = data.get("messages", [])
                st.rerun()
