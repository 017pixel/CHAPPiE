import streamlit as st


def render_context_overlays(backend):
    """Rendert Overlay-Dialoge für Context-Dateien (Soul, User, Prefs)."""
    
    # === SOUL CONTEXT ANZEIGE ===
    if st.session_state.show_soul_context:
        with st.container(border=True):
            st.markdown("### CHAPPiE's Selbstwahrnehmung (soul.md)")
            
            try:
                soul_content = backend.context_files.get_soul_context()
                st.text_area("Inhalt", soul_content, height=400, disabled=True, 
                           label_visibility="collapsed")
            except Exception as e:
                st.error(f"Fehler beim Laden von soul.md: {e}")
            
            if st.button("Schliessen", key="close_soul", use_container_width=True):
                st.session_state.show_soul_context = False
                st.rerun()
    
    # === USER CONTEXT ANZEIGE ===
    if st.session_state.show_user_context:
        with st.container(border=True):
            st.markdown("### Benutzerprofil (user.md)")
            
            try:
                user_content = backend.context_files.get_user_context()
                st.text_area("Inhalt", user_content, height=400, disabled=True,
                           label_visibility="collapsed")
            except Exception as e:
                st.error(f"Fehler beim Laden von user.md: {e}")
            
            if st.button("Schliessen", key="close_user", use_container_width=True):
                st.session_state.show_user_context = False
                st.rerun()
    
    # === PREFERENCES CONTEXT ANZEIGE ===
    if st.session_state.show_prefs_context:
        with st.container(border=True):
            st.markdown("### Vorlieben & Einstellungen (CHAPPiEsPreferences.md)")
            
            try:
                prefs_content = backend.context_files.get_preferences_context()
                st.text_area("Inhalt", prefs_content, height=400, disabled=True,
                           label_visibility="collapsed")
            except Exception as e:
                st.error(f"Fehler beim Laden von CHAPPiEsPreferences.md: {e}")
            
            if st.button("Schliessen", key="close_prefs", use_container_width=True):
                st.session_state.show_prefs_context = False
                st.rerun()
