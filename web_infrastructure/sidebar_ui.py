import streamlit as st
from web_infrastructure.components import render_vital_signs

def render_sidebar(backend):
    """Rendert die Sidebar-Navigation und Verlauf."""
    with st.sidebar:
        st.markdown("## CHAPPiE")

        if st.button("Neuer Chat", use_container_width=True, key="sidebar_new_chat"):
            st.session_state.session_id = backend.chat_manager.create_session()
            st.session_state.messages = []
            st.rerun()

        if st.button("Alle Erinnerungen", use_container_width=True, key="sidebar_memories"):
            st.session_state.show_memories = not st.session_state.show_memories
            st.session_state.show_settings = False
            st.session_state.show_training = False
            st.rerun()
        
        if st.button("Einstellungen", use_container_width=True, key="sidebar_settings"):
            st.session_state.show_settings = not st.session_state.show_settings
            st.session_state.show_memories = False
            st.session_state.show_training = False
            st.rerun()
        
        if st.button("Autonomes Training", use_container_width=True, key="sidebar_training"):
            st.session_state.show_training = not st.session_state.show_training
            st.session_state.show_memories = False
            st.session_state.show_settings = False
            st.rerun()
        
        st.divider()
        debug_label = "DEBUG MODE: ON" if getattr(st.session_state, 'debug_mode', False) else "DEBUG MODE: OFF"
        if st.button(debug_label, use_container_width=True, key="sidebar_debug_toggle", type="primary" if getattr(st.session_state, 'debug_mode', False) else "secondary"):
            st.session_state.debug_mode = not getattr(st.session_state, 'debug_mode', False)
            st.rerun()

        st.divider()
        st.markdown("**VITALZEICHEN**")
        render_vital_signs(backend)
        
        st.divider()
        st.markdown("**KONTEXT-DATEIEN**")
        
        if st.button("soul.md (Selbstwahrnehmung)", key="show_soul", use_container_width=True):
            st.session_state.show_soul_context = True
            st.rerun()
        
        if st.button("user.md (Benutzerprofil)", key="show_user", use_container_width=True):
            st.session_state.show_user_context = True
            st.rerun()
        
        if st.button("CHAPPiEsPreferences", key="show_prefs", use_container_width=True):
            st.session_state.show_prefs_context = True
            st.rerun()
                
        st.divider()

        st.markdown("**VERLAUF**")
        try:
            sessions = backend.chat_manager.list_sessions()
            for s in sessions[:25]:
                label = s['title'][:30]
                if s["id"] == getattr(st.session_state, 'session_id', None):
                    label = f"• {label}"
                
                if st.button(label, key=f"sess_{s['id']}", use_container_width=True):
                    st.session_state.session_id = s["id"]
                    data = backend.chat_manager.load_session(s["id"])
                    st.session_state.messages = data.get("messages", [])
                    st.rerun()
        except Exception as e:
            st.error(f"Fehler: {e}")
