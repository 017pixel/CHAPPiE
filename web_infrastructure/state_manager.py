import streamlit as st
from config.config import settings, LLMProvider

def init_session_state():
    """Initialisiert die Streamlit Session States."""
    if "session_id" not in st.session_state:
        st.session_state.session_id = None # Aktuelle Chat-ID
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if st.session_state.get("current_emotions") is None:
        st.session_state.current_emotions = {
            "joy": 50, "trust": 50, "energy": 80, "curiosity": 60,
            "frustration": 0, "motivation": 80  # Neue Emotionen
        }
    if "show_settings" not in st.session_state:
        st.session_state.show_settings = False
    if "show_memories" not in st.session_state:
        st.session_state.show_memories = False
    # Brain Monitor Debug Mode
    if "debug_mode" not in st.session_state:
        st.session_state.debug_mode = False
    # Deep Think State
    if "deep_think_active" not in st.session_state:
        st.session_state.deep_think_active = False
    if "deep_think_steps" not in st.session_state:
        st.session_state.deep_think_steps = []
    if "deep_think_total_done" not in st.session_state:
        st.session_state.deep_think_total_done = 0
    if "deep_think_pending_batches" not in st.session_state:
        st.session_state.deep_think_pending_batches = 0
    
    # Memory Enhancement State
    if "pending_cmd" not in st.session_state:
        st.session_state.pending_cmd = None
    
    # Short-term Memory Count fuer Sidebar Anzeige
    if "short_term_count" not in st.session_state:
        st.session_state.short_term_count = 0
    
    # Context Files Anzeige States
    if "show_soul_context" not in st.session_state:
        st.session_state.show_soul_context = False
    if "show_user_context" not in st.session_state:
        st.session_state.show_user_context = False
    if "show_prefs_context" not in st.session_state:
        st.session_state.show_prefs_context = False

    # API Check State (einmalig)
    if "api_check_done" not in st.session_state:
        if settings.llm_provider == LLMProvider.GROQ and not settings.groq_api_key:
            st.session_state.show_settings = True
            st.warning("⚠️ Bitte konfiguriere deinen API Key in den Einstellungen.")
        st.session_state.api_check_done = True
