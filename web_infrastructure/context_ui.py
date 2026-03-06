import streamlit as st

@st.dialog("Kontext-Datei betrachten", width="large")
def show_context_modal(title, content):
    st.markdown(f"### {title}")
    st.text_area("Inhalt", content, height=600, disabled=True, label_visibility="collapsed")
    if st.button("Schließen", use_container_width=True):
        st.rerun()

def render_context_overlays(backend):
    """Rendert Overlay-Dialoge für Context-Dateien (Soul, User, Prefs) als Full-Page."""
    
    # === SOUL CONTEXT ===
    if st.session_state.get("show_soul_context", False):
        try:
            content = backend.context_files.get_soul_context()
        except Exception as e:
            content = f"Fehler beim Laden von soul.md: {e}"
        
        st.session_state.show_soul_context = False
        show_context_modal("CHAPPiE's Selbstwahrnehmung (soul.md)", content)
        
    # === USER CONTEXT ===
    if st.session_state.get("show_user_context", False):
        try:
            content = backend.context_files.get_user_context()
        except Exception as e:
            content = f"Fehler beim Laden von user.md: {e}"
            
        st.session_state.show_user_context = False
        show_context_modal("Benutzerprofil (user.md)", content)
        
    # === PREFERENCES CONTEXT ===
    if st.session_state.get("show_prefs_context", False):
        try:
            content = backend.context_files.get_preferences_context()
        except Exception as e:
            content = f"Fehler beim Laden von CHAPPiEsPreferences.md: {e}"
            
        st.session_state.show_prefs_context = False
        show_context_modal("Vorlieben & Einstellungen (CHAPPiEsPreferences.md)", content)
