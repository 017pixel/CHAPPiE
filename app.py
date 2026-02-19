import streamlit as st
from web_infrastructure.styles import inject_modern_css
from web_infrastructure.backend_wrapper import init_chappie
from web_infrastructure.state_manager import init_session_state
from web_infrastructure.sidebar_ui import render_sidebar
from web_infrastructure.settings_ui import render_settings_overlay
from web_infrastructure.memories_ui import render_memories_overlay
from web_infrastructure.context_ui import render_context_overlays
from web_infrastructure.chat_ui import render_chat_interface
from web_infrastructure.command_handler import process_command, process_chat_message
from web_infrastructure.training_ui import render_training_ui

# ============================================
# KONFIGURATION UND INITIALISIERUNG
# ============================================

st.set_page_config(
    page_title="CHAPPiE - Cognitive Hybrid Assistant",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    # 1. Styles & State
    init_session_state()
    inject_modern_css()
    
    # 2. Backend Init
    backend = init_chappie()
    
    # 3. Sidebar Render
    render_sidebar(backend)
    
    # 4. Context Overlays (Soul, User, Prefs) - werden vor anderen Overlays angezeigt
    render_context_overlays(backend)
    
    # 5. Main Content Routing
    if st.session_state.show_memories:
        render_memories_overlay(backend)
    elif st.session_state.show_settings:
        render_settings_overlay(backend)
    elif st.session_state.show_training:
        render_training_ui()
    else:
        # Chat Interface & Input Loop
        user_input = render_chat_interface(backend)
        
        # 6. Input Processing
        if user_input:
            # Check for commands (/sleep, /think, etc.)
            command_processed = process_command(user_input, backend)
            
            # If not a command, process as chat message
            if not command_processed:
                process_chat_message(user_input, backend)

if __name__ == "__main__":
    main()
