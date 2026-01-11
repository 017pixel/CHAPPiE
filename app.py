import streamlit as st
import json
import time
import uuid
import os
from typing import Dict, Any, List, Optional

# CHAPiE imports
from config.config import settings, get_active_model, PROJECT_ROOT
from config.prompts import SYSTEM_PROMPT, get_system_prompt_with_emotions
from memory.memory_engine import MemoryEngine
from memory.emotions_engine import EmotionsEngine, analyze_sentiment_simple
from memory.chat_manager import ChatManager
from brain import get_brain, Message
from brain.base_brain import GenerationConfig
from brain.response_parser import parse_chain_of_thought

# ============================================
# KONFIGURATION UND INITIALISIERUNG
# ============================================

st.set_page_config(
    page_title="CHAPPiE - Cognitive Hybrid Assistant",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialisierung der Session States
if "session_id" not in st.session_state:
    st.session_state.session_id = None # Aktuelle Chat-ID
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_emotions" not in st.session_state:
    st.session_state.current_emotions = {
        "joy": 50, "trust": 50, "energy": 80, "curiosity": 60
    }
if "show_settings" not in st.session_state:
    st.session_state.show_settings = False

# ============================================
# BACKEND KLASSE
# ============================================

@st.cache_resource
def init_chappie():
    """Initialisiert das Backend (Memory, Emotions, Brain, ChatManager)."""
    class CHAPPiEBackend:
        def __init__(self):
            # Module init
            self.memory = MemoryEngine()
            self.emotions = EmotionsEngine()
            self.brain = get_brain()
            # Chat Manager init
            data_dir = os.path.join(PROJECT_ROOT, "data")
            self.chat_manager = ChatManager(data_dir)

        def get_status(self) -> Dict[str, Any]:
            state = self.emotions.get_state()
            try:
                brain_ok = self.brain.is_available()
            except:
                brain_ok = False
            
            return {
                "brain_available": brain_ok,
                "model": get_active_model(),
                "emotions": {
                    "joy": state.happiness,
                    "trust": state.trust,
                    "energy": state.energy,
                    "curiosity": state.curiosity,
                },
            }
        
        def process(self, user_input: str, history: List[Dict]) -> Dict[str, Any]:
            # 1. Sentiment Analyse & Emotion Update
            sentiment = analyze_sentiment_simple(user_input)
            self.emotions.update_from_sentiment(sentiment)

            # 2. RAG Memory Search
            memories = self.memory.search_memory(user_input, top_k=settings.memory_top_k)
            memories_for_prompt = self.memory.format_memories_for_prompt(memories)

            # 3. Prompt Building
            state = self.emotions.get_state()
            system_prompt = get_system_prompt_with_emotions(
                **state.__dict__,
                use_chain_of_thought=settings.chain_of_thought
            )

            # Baue Nachrichten-Verlauf beachte Context
            messages = self.brain.build_prompt(system_prompt, memories_for_prompt, user_input, history)

            # 4. Generierung
            gen_config = GenerationConfig(
                max_tokens=settings.max_tokens,
                temperature=settings.temperature,
                stream=False,
            )
            raw_response = self.brain.generate(messages, config=gen_config)

            # 5. Parsing (CoT)
            if settings.chain_of_thought:
                parsed = parse_chain_of_thought(raw_response)
                display_response = parsed.answer
                thought = parsed.thought or ""
            else:
                display_response = raw_response
                thought = ""
            
            # 6. Kurzzeitgedächtnis speichern
            self.memory.add_memory(user_input, role="user")
            self.memory.add_memory(display_response, role="assistant")

            return {
                "response_text": display_response,
                "emotions": {
                    "joy": state.happiness,
                    "trust": state.trust,
                    "energy": state.energy,
                    "curiosity": state.curiosity,
                },
                "thought_process": thought,
                # Wir geben hier die rohen Memory-Objekte zurück für die GUI Anzeige
                "rag_memories": memories, 
            }

    return CHAPPiEBackend()

# ============================================
# FRONTEND / DESIGN
# ============================================

def _inject_modern_css():
    st.markdown("""
    <style>
        /* Import Font: Outfit */
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

        /* --- GLOBAL RESET & VARS --- */
        :root {
            --bg-color: #0d1117;
            --sidebar-bg: #010409;
            --card-bg: #161b22;
            --accent-green: #1a5c20; /* Dark Green Border */
            --accent-green-bright: #2ea043;
            --text-primary: #c9d1d9;
            --text-secondary: #8b949e;
            --border-color: #30363d;
        }

        html, body, [class*="css"] {
            font-family: 'Outfit', sans-serif !important;
            background-color: var(--bg-color) !important;
            color: var(--text-primary);
        }

        /* --- BUTTONS --- */
        .stButton button {
            background-color: var(--card-bg) !important;
            color: var(--text-primary) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 4px !important;
            transition: all 0.2s ease-in-out;
            font-weight: 500;
            width: 100% !important;
            padding: 10px 15px !important;
            margin-bottom: 5px !important;
            white-space: nowrap !important;
            display: inline-block !important;
            overflow: hidden;
            text-overflow: ellipsis;
            text-align: left !important;
        }

        .stButton button:hover, .stButton button:active, .stButton button:focus {
            border-color: var(--accent-green) !important;
            box-shadow: 0 0 8px rgba(26, 92, 32, 0.4) !important;
            color: #fff !important;
            background-color: #1c2128 !important;
        }

        /* Ensure the top row buttons are wider and spaced correctly */
        [data-testid="column"] .stButton button {
            width: 160px !important;
            justify-content: center !important;
            text-align: center !important;
        }
        
        div[data-testid="stHorizontalBlock"] {
            gap: 8px !important;
        }

        /* Sidebar Spacing */
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            gap: 0.4rem !important;
        }

        /* --- SIDEBAR --- */
        [data-testid="stSidebar"] {
            background-color: var(--sidebar-bg) !important;
            border-right: 1px solid var(--border-color);
        }
        
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
             color: #fff !important;
             font-weight: 700;
        }

        /* --- MAIN AREA --- */
        .stApp {
            background-color: var(--bg-color);
        }

        /* Chat Input */
        .stChatInputContainer {
            padding-bottom: 20px !important;
        }
        .stChatInputContainer textarea {
            background-color: var(--card-bg) !important;
            color: #fff !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 12px !important;
        }
        
        /* Thoughts & Code Block Wrapping (Fix horizontal scroll) */
        code {
            white-space: pre-wrap !important;
            word-wrap: break-word !important;
        }
        
        /* Status Bars */
        .emotion-bar-bg {
            background-color: #21262d;
            border-radius: 4px;
            height: 6px;
            width: 100%;
            margin-bottom: 12px;
            margin-top: 4px;
        }
        .emotion-bar-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.5s ease;
        }

        /* Header Logo */
        .header-logo {
            font-size: 1.5rem;
            font-weight: 700;
            color: #fff;
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 20px;
        }
    </style>
    """, unsafe_allow_html=True)

def render_emotion_metric(label, value, color="#2ea043"):
    st.markdown(f"""
    <div style="font-size: 0.8rem; color: #8b949e; display: flex; justify-content: space-between;">
        <span>{label}</span>
        <span>{value}%</span>
    </div>
    <div class="emotion-bar-bg">
        <div class="emotion-bar-fill" style="width: {value}%; background-color: {color};"></div>
    </div>
    """, unsafe_allow_html=True)

# ============================================
# LOGIK / MAIN LOOP
# ============================================

def main():
    _inject_modern_css()
    backend = init_chappie()

    # --- SESSION MANAGEMENT ---
    if not st.session_state.session_id:
        st.session_state.session_id = backend.chat_manager.create_session()
        st.session_state.messages = []

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown('<div class="header-logo">CHAPPiE</div>', unsafe_allow_html=True)

        if st.button("Neuer Chat", use_container_width=True):
            st.session_state.session_id = backend.chat_manager.create_session()
            st.session_state.messages = []
            st.rerun()

        st.markdown("---")
        
        st.markdown("**VITALZEICHEN**")
        emo = st.session_state.current_emotions
        render_emotion_metric("Freude", emo.get("joy", 50), "#FFD700")
        render_emotion_metric("Vertrauen", emo.get("trust", 50), "#2196F3")
        render_emotion_metric("Energie", emo.get("energy", 80), "#F44336")
        render_emotion_metric("Neugier", emo.get("curiosity", 60), "#9C27B0")
        
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

        st.markdown("---")
        if st.button("Einstellungen", use_container_width=True):
            st.session_state.show_settings = not st.session_state.show_settings
            st.rerun()

    # --- MAIN CONTENT ---
    
    # Settings Overlay / Area
    if st.session_state.show_settings:
        st.markdown("## Einstellungen")
        
        with st.container(border=True):
            st.subheader("Generierung")
            new_temp = st.slider("Temperatur", 0.0, 1.0, float(settings.temperature), 0.1)
            new_tokens = st.number_input("Max Tokens", 100, 4000, int(settings.max_tokens), 100)
            new_cot = st.toggle("Chain of Thought (Gedankenprozess)", bool(settings.chain_of_thought))
            
            st.subheader("Gedächtnis")
            new_k = st.slider("Memory Top-K", 1, 10, int(settings.memory_top_k))

            if st.button("Speichern & Schließen", use_container_width=True):
                settings.temperature = new_temp
                settings.max_tokens = new_tokens
                settings.chain_of_thought = new_cot
                settings.memory_top_k = new_k
                st.session_state.show_settings = False
                st.success("Einstellungen übernommen!")
                time.sleep(1)
                st.rerun()
        
        st.markdown("---")
        return # Skip chat while settings are open
    
    # 1. Top Command Bar
    cols = st.columns([2,2,2,2,2,5])
    commands = ["/sleep", "/help", "/stats", "/clear", "/config"]
    
    for i, cmd in enumerate(commands):
        with cols[i]:
            if st.button(cmd, key=f"top_{cmd}"):
                st.session_state.messages.append({"role": "user", "content": cmd})
                st.session_state.pending_cmd = cmd
                st.rerun()

    st.markdown("---")

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
                
                # Expanders for Thoughts and RAG
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
                                # Handle both Objects (fresh) and Dicts (loaded from JSON)
                                if isinstance(m, dict):
                                    content = m.get("content", "")
                                    score = m.get("relevance_score", 0.0)
                                else:
                                    content = m.content
                                    score = m.relevance_score
                                
                                st.markdown(f"**Info {idx+1}** (Relevanz: {int(score*100)}%)")
                                st.progress(score)
                                st.caption(content[:250] + "..." if len(content) > 250 else content)
                                if idx < len(rag_data) - 1:
                                    st.divider()

    # --- INPUT ---
    if "pending_cmd" in st.session_state:
        user_input = st.session_state.pending_cmd
        del st.session_state.pending_cmd
        should_process = True
    else:
        user_input = st.chat_input("Schreibe eine Nachricht an CHAPPiE...")
        should_process = bool(user_input)
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})

    # --- PROCESSING ---
    if should_process:
        with st.chat_message("user"):
            st.markdown(user_input)

        if user_input.strip().lower() == "/sleep":
            with st.status("System verarbeitet Erinnerungen...", expanded=True):
                res = backend.memory.consolidate_memories(backend.brain)
                backend.emotions.restore_energy(30)
            assistant_msg = {"role": "assistant", "content": f"Schlafzyklus beendet. \n\n{res}", "metadata": {"thought_process": "Kommando /sleep ausgeführt."}}
        
        elif user_input.strip().lower() == "/clear":
             st.session_state.messages = []
             st.session_state.session_id = backend.chat_manager.create_session()
             st.rerun()
             return
        
        elif user_input.strip().lower() == "/help":
            help_text = """**CHAPPiE Commands:**

- **/sleep** - Startet die Traum-Phase (konsolidiert Erinnerungen)
- **/clear** - Löscht aktuellen Chat und startet neue Sitzung
- **/stats** - Zeigt System-Statistiken
- **/config** - Öffnet Einstellungen
- **/help** - Zeigt diese Hilfe

**Tipp:** Klicke auf die Buttons oben für schnellen Zugriff!"""
            assistant_msg = {"role": "assistant", "content": help_text, "metadata": {"thought_process": "Kommando /help ausgeführt."}}
        
        elif user_input.strip().lower() == "/stats":
            status = backend.get_status()
            memory_count = backend.memory.get_memory_count()
            stats_text = f"""**System-Statistiken:**

🧠 **Brain:** {'✅ Verfügbar' if status['brain_available'] else '❌ Nicht verfügbar'}
📊 **Modell:** {status['model']}
💾 **Erinnerungen:** {memory_count} gespeichert

**Emotionen:**
- 😊 Freude: {status['emotions']['joy']}%
- 🤝 Vertrauen: {status['emotions']['trust']}%
- ⚡ Energie: {status['emotions']['energy']}%
- 🔍 Neugier: {status['emotions']['curiosity']}%"""
            assistant_msg = {"role": "assistant", "content": stats_text, "metadata": {"thought_process": "Kommando /stats ausgeführt."}}
        
        elif user_input.strip().lower() == "/config":
            st.session_state.show_settings = True
            st.rerun()
            return
        
        else:
            with st.chat_message("assistant"):
                with st.spinner("CHAPPiE denkt nach..."):
                    result = backend.process(user_input, st.session_state.messages[:-1])
                    st.markdown(result["response_text"])
                    st.session_state.current_emotions = result["emotions"]
            
            # Helper to serialize memories for JSON storage (Memory objects are not JSON serializable by default)
            formatted_memories = []
            if result.get("rag_memories"):
                for m in result["rag_memories"]:
                     formatted_memories.append({
                         "content": m.content,
                         "relevance_score": m.relevance_score,
                         "role": m.role
                     })

            assistant_msg = {
                "role": "assistant",
                "content": result["response_text"],
                "metadata": {
                    "thought_process": result.get("thought_process"),
                    "rag_memories": formatted_memories
                }
            }

        st.session_state.messages.append(assistant_msg)
        backend.chat_manager.save_session(st.session_state.session_id, st.session_state.messages)
        st.rerun()

if __name__ == "__main__":
    main()
