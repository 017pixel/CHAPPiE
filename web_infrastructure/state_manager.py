import streamlit as st
from config.config import settings, LLMProvider
from web_infrastructure.ui_utils import bootstrap_current_emotions, normalize_emotions

def init_session_state():
    """Initialisiert die Streamlit Session States."""
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_updated_at" not in st.session_state:
        st.session_state.session_updated_at = None
    if "current_emotions" not in st.session_state:
        st.session_state.current_emotions = {}
    elif st.session_state.get("current_emotions_loaded"):
        st.session_state.current_emotions = normalize_emotions(st.session_state.get("current_emotions"))
    if "current_emotions_loaded" not in st.session_state:
        st.session_state.current_emotions_loaded = False
    if "show_settings" not in st.session_state:
        st.session_state.show_settings = False
    if "show_memories" not in st.session_state:
        st.session_state.show_memories = False
    if "show_training" not in st.session_state:
        st.session_state.show_training = False
    if "show_life_dashboard" not in st.session_state:
        st.session_state.show_life_dashboard = False
    if "show_growth_dashboard" not in st.session_state:
        st.session_state.show_growth_dashboard = False
    if "debug_mode" not in st.session_state:
        st.session_state.debug_mode = False
    if "deep_think_active" not in st.session_state:
        st.session_state.deep_think_active = False
    if "deep_think_steps" not in st.session_state:
        st.session_state.deep_think_steps = []
    if "deep_think_total_done" not in st.session_state:
        st.session_state.deep_think_total_done = 0
    if "deep_think_pending_batches" not in st.session_state:
        st.session_state.deep_think_pending_batches = 0
    
    if "pending_cmd" not in st.session_state:
        st.session_state.pending_cmd = None
    
    if "short_term_count" not in st.session_state:
        st.session_state.short_term_count = 0
    if "current_life_state" not in st.session_state:
        st.session_state.current_life_state = {}
    if "current_workspace" not in st.session_state:
        st.session_state.current_workspace = {}
    
    if "show_soul_context" not in st.session_state:
        st.session_state.show_soul_context = False
    if "show_user_context" not in st.session_state:
        st.session_state.show_user_context = False
    if "show_prefs_context" not in st.session_state:
        st.session_state.show_prefs_context = False

    if "api_check_done" not in st.session_state:
        if settings.llm_provider == LLMProvider.GROQ and not settings.groq_api_key:
            st.session_state.show_settings = True
            st.warning("⚠️ Bitte konfiguriere deinen API Key in den Einstellungen.")
        st.session_state.api_check_done = True
    
    if "memories_page" not in st.session_state:
        st.session_state.memories_page = 0
    
    if "last_filter_label" not in st.session_state:
        st.session_state.last_filter_label = "Alle"
    if "last_filter_type" not in st.session_state:
        st.session_state.last_filter_type = "Alle"


def sync_current_emotions(backend, force: bool = False):
    """Lädt die persistierten Vitalzeichen aus dem Backend in den Session-State."""
    backend_snapshot = {}
    try:
        backend_snapshot = backend._get_emotions_snapshot()
    except Exception:
        backend_snapshot = {}

    current_emotions, loaded = bootstrap_current_emotions(
        st.session_state.get("current_emotions"),
        backend_snapshot,
        already_loaded=(False if force else bool(st.session_state.get("current_emotions_loaded"))),
    )
    st.session_state.current_emotions = current_emotions
    st.session_state.current_emotions_loaded = loaded
    if current_emotions:
        st.session_state.last_emo_settings_hash = hash(str(current_emotions))
    return current_emotions


def restore_active_chat_session(backend):
    """Stellt die zuletzt aktive Chat-Session wieder her oder erzeugt eine neue."""
    if st.session_state.get("session_id"):
        return

    session_data = backend.chat_manager.load_active_session()
    st.session_state.session_id = session_data.get("id")
    st.session_state.messages = session_data.get("messages", [])
    st.session_state.session_updated_at = session_data.get("updated_at")


def sync_current_chat_session(backend):
    """Synchronisiert den aktuellen Chat mit dem gespeicherten Stand auf Platte."""
    session_id = st.session_state.get("session_id")
    if not session_id:
        return

    session_data = backend.chat_manager.load_session(session_id)
    updated_at = session_data.get("updated_at")
    if updated_at == st.session_state.get("session_updated_at"):
        return

    st.session_state.messages = session_data.get("messages", [])
    st.session_state.session_updated_at = updated_at
