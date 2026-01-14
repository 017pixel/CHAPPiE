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
from memory.emotions_engine import EmotionsEngine
from memory.chat_manager import ChatManager
from brain import get_brain, Message
from brain.base_brain import GenerationConfig
from brain.response_parser import parse_chain_of_thought
from brain.deep_think import DeepThinkEngine, DeepThinkStep

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
            # Deep Think Engine
            self.deep_think_engine = DeepThinkEngine(
                memory_engine=self.memory,
                emotions_engine=self.emotions,
                brain=self.brain
            )

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
        
        def _get_emotions_snapshot(self) -> Dict[str, int]:
            """Erstellt einen Snapshot der aktuellen Emotionen."""
            state = self.emotions.get_state()
            return {
                "joy": state.happiness,
                "trust": state.trust,
                "energy": state.energy,
                "curiosity": state.curiosity,
                "frustration": state.frustration,
                "motivation": state.motivation
            }
        
        def process(self, user_input: str, history: List[Dict]) -> Dict[str, Any]:
            # ===== BRAIN MONITOR: Emotionen VORHER =====
            emotions_before = self._get_emotions_snapshot()
            
            # 1. LLM-basierte Emotions-Analyse (intelligent, kontextbewusst)
            self.emotions.analyze_and_update(user_input)
            
            # ===== BRAIN MONITOR: Emotionen NACHHER =====
            emotions_after = self._get_emotions_snapshot()
            
            # ===== BRAIN MONITOR: Delta berechnen =====
            emotions_delta = {}
            for key in emotions_before:
                delta = emotions_after[key] - emotions_before[key]
                if delta != 0:
                    emotions_delta[key] = {
                        "before": emotions_before[key],
                        "after": emotions_after[key],
                        "change": delta
                    }

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
            
            # 6. Kurzzeitgedaechtnis speichern
            self.memory.add_memory(user_input, role="user")
            self.memory.add_memory(display_response, role="assistant")

            return {
                "response_text": display_response,
                "emotions": emotions_after,
                "emotions_before": emotions_before,  # BRAIN MONITOR
                "emotions_delta": emotions_delta,    # BRAIN MONITOR
                "thought_process": thought,
                "rag_memories": memories,
                "input_analysis": user_input,        # BRAIN MONITOR
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
        
        /* Command Buttons (oben) - rechteckig und einheitlich */
        [data-testid="stHorizontalBlock"] .stButton button {
            background-color: var(--card-bg) !important;
            color: var(--text-primary) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 4px !important; /* RECHTECKIG */
            transition: all 0.2s ease-in-out !important;
            font-weight: 500 !important;
            width: 100% !important;
            padding: 8px 10px !important;
            font-size: 0.85rem !important;
            text-align: center !important;
            height: 40px !important; /* Einheitliche Hoehe */
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
        }

        [data-testid="stHorizontalBlock"] .stButton button:hover {
            border-color: #2ea043 !important; /* GRUENER HOVER */
            box-shadow: 0 0 10px rgba(46, 160, 67, 0.4) !important;
            color: #fff !important;
            background-color: #1c2128 !important;
        }
        
        /* ============================================ */
        /* BRAIN MONITOR STYLES */
        /* ============================================ */
        
        .brain-monitor {
            background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 12px;
            margin-top: 10px;
            font-family: 'Consolas', 'Monaco', monospace;
        }
        
        .brain-monitor-header {
            display: flex;
            align-items: center;
            gap: 8px;
            color: #58a6ff;
            font-weight: 600;
            font-size: 0.9rem;
            margin-bottom: 10px;
            cursor: pointer;
        }
        
        .brain-monitor-section {
            background: rgba(22, 27, 34, 0.8);
            border-left: 3px solid #30363d;
            padding: 8px 12px;
            margin: 8px 0;
            border-radius: 0 4px 4px 0;
        }
        
        .brain-monitor-section.input {
            border-left-color: #58a6ff;
        }
        
        .brain-monitor-section.thought {
            border-left-color: #a371f7;
        }
        
        .brain-monitor-section.emotion {
            border-left-color: #f85149;
        }
        
        .brain-monitor-section.memory {
            border-left-color: #3fb950;
        }
        
        .emotion-delta-positive {
            color: #3fb950;
            font-weight: 600;
        }
        
        .emotion-delta-negative {
            color: #f85149;
            font-weight: 600;
        }
        
        .emotion-delta-neutral {
            color: #8b949e;
        }
        
        .memory-item {
            background: rgba(48, 54, 61, 0.5);
            border-radius: 4px;
            padding: 6px 10px;
            margin: 4px 0;
            font-size: 0.8rem;
        }
        
        .memory-score {
            color: #3fb950;
            font-weight: 600;
        }
        
        /* ============================================ */
        /* DEEP THINK STYLES */
        /* ============================================ */
        
        .deep-think-container {
            background: linear-gradient(135deg, #0d1117 0%, #1a1f2e 100%);
            border: 1px solid #238636;
            border-radius: 12px;
            padding: 20px;
            margin: 15px 0;
        }
        
        .deep-think-header {
            color: #58a6ff;
            font-size: 1.2rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 15px;
        }
        
        .deep-think-step {
            background: rgba(22, 27, 34, 0.9);
            border-left: 3px solid #a371f7;
            padding: 12px 16px;
            margin: 10px 0;
            border-radius: 0 8px 8px 0;
        }
        
        .deep-think-step-number {
            color: #a371f7;
            font-weight: 700;
            font-size: 0.9rem;
        }
        
        .deep-think-thought {
            color: #c9d1d9;
            margin-top: 8px;
            line-height: 1.6;
        }
        
        .deep-think-controls {
            display: flex;
            gap: 10px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        
        .deep-think-btn {
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s ease;
        }
        
        .deep-think-btn-continue {
            background: #238636;
            border: 1px solid #2ea043;
            color: #fff;
        }
        
        .deep-think-btn-stop {
            background: #21262d;
            border: 1px solid #f85149;
            color: #f85149;
        }

        /* --- DEEP THINK MENU --- */
        .deep-think-menu {
            background-color: var(--card-bg) !important;
            border: 1px solid var(--accent-green) !important;
            border-radius: 8px !important;
            padding: 20px !important;
            margin: 20px 0 !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
        }

        .deep-think-menu h3 {
            color: #fff !important;
            font-weight: 600 !important;
            margin-bottom: 15px !important;
            border-bottom: 1px solid var(--border-color) !important;
            padding-bottom: 10px !important;
        }

        .deep-think-buttons {
            display: flex !important;
            gap: 10px !important;
            flex-wrap: wrap !important;
            margin-top: 15px !important;
        }

        .deep-think-buttons .stButton button {
            background-color: #21262d !important;
            color: #fff !important;
            border: 1px solid var(--accent-green) !important;
            border-radius: 6px !important;
            padding: 12px 20px !important;
            font-weight: 600 !important;
            transition: all 0.2s ease-in-out !important;
            min-width: 160px !important;
            flex: 1 !important;
        }

        .deep-think-buttons .stButton button:hover {
            background-color: var(--accent-green) !important;
            box-shadow: 0 0 15px rgba(46, 160, 67, 0.6) !important;
            transform: translateY(-2px) !important;
        }

        .deep-think-buttons .stButton button:active {
            transform: translateY(0) !important;
        }

        /* Deep Think Selectbox Styling */
        .deep-think-buttons .stSelectbox > div > div {
            background-color: #21262d !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 6px !important;
        }

        .deep-think-buttons .stSelectbox label {
            color: var(--text-secondary) !important;
            font-size: 0.9rem !important;
        }

        /* Deep Think Stop Button Special Style */
        .deep-think-stop-btn .stButton button {
            background-color: #3d1515 !important;
            border-color: #f85149 !important;
        }

        .deep-think-stop-btn .stButton button:hover {
            background-color: #f85149 !important;
            box-shadow: 0 0 15px rgba(248, 81, 73, 0.6) !important;
        }

        /* Deep Think Sleep Button Special Style */
        .deep-think-sleep-btn .stButton button {
            background-color: #1a3a5c !important;
            border-color: #58a6ff !important;
        }

        .deep-think-sleep-btn .stButton button:hover {
            background-color: #58a6ff !important;
            box-shadow: 0 0 15px rgba(88, 166, 255, 0.6) !important;
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


def render_vital_signs(emotions_dict: Dict[str, int]):
    """Rendert den kompletten Block der Vitalzeichen."""
    render_emotion_metric("Freude", emotions_dict.get("joy", 50), "#FFD700")      # Gold
    render_emotion_metric("Vertrauen", emotions_dict.get("trust", 50), "#2196F3") # Blau
    render_emotion_metric("Energie", emotions_dict.get("energy", 80), "#4CAF50")  # Gruen
    render_emotion_metric("Neugier", emotions_dict.get("curiosity", 60), "#9C27B0") # Lila
    render_emotion_metric("Motivation", emotions_dict.get("motivation", 80), "#FF9800") # Orange
    render_emotion_metric("Frustration", emotions_dict.get("frustration", 0), "#F44336") # Rot


def render_brain_monitor(metadata: Dict[str, Any]):
    """
    Rendert das Brain Monitor Debug-Panel für eine Nachricht.
    Nutzt Streamlit-native Elemente statt HTML für bessere Kompatibilität.
    """
    if not metadata:
        return
    
    # === INPUT ANALYSE ===
    st.markdown("**🔵 INPUT ANALYSE**")
    input_text = metadata.get("input_analysis", "N/A")
    st.info(input_text)
    
    # === GEDANKE (Chain of Thought) ===
    st.markdown("**🟣 GEDANKE (Chain of Thought)**")
    thought = metadata.get("thought_process", "")
    if thought:
        st.text_area("Gedankenprozess", thought, height=150, disabled=True, label_visibility="collapsed")
    else:
        st.caption("(Kein Chain-of-Thought aktiviert oder vorhanden)")
    
    # === EMOTIONS-DELTA ===
    st.markdown("**🔴 EMOTIONS-DELTA**")
    if metadata.get("emotions_delta"):
        emotion_names = {
            "joy": "Freude",
            "trust": "Vertrauen", 
            "energy": "Energie",
            "curiosity": "Neugier",
            "frustration": "Frustration",
            "motivation": "Motivation"
        }
        
        cols = st.columns(3)
        col_idx = 0
        for emotion, data in metadata["emotions_delta"].items():
            change = data.get("change", 0)
            before = data.get("before", 0)
            after = data.get("after", 0)
            name = emotion_names.get(emotion, emotion)
            
            with cols[col_idx % 3]:
                if change > 0:
                    st.success(f"{name}: {before}% → {after}% (+{change})")
                elif change < 0:
                    st.error(f"{name}: {before}% → {after}% ({change})")
                else:
                    st.info(f"{name}: {before}% (keine Änderung)")
            col_idx += 1
    else:
        st.caption("Keine Emotions-Änderungen")
    
    # === GELADENE MEMORIES ===
    st.markdown("**🟢 GELADENE MEMORIES**")
    if metadata.get("rag_memories"):
        for i, mem in enumerate(metadata["rag_memories"]):
            if isinstance(mem, dict):
                content = mem.get("content", "")[:150]
                score = int(mem.get("relevance_score", 0) * 100)
                mem_id = mem.get("id", "?")[:8]
                label = mem.get("label", "original")
            else:
                content = mem.content[:150] if hasattr(mem, 'content') else str(mem)[:150]
                score = int(mem.relevance_score * 100) if hasattr(mem, 'relevance_score') else 0
                mem_id = mem.id[:8] if hasattr(mem, 'id') else "?"
                label = getattr(mem, 'label', 'original')
            
            # Zeige Memory mit Progress Bar
            col1, col2 = st.columns([3, 1])
            with col1:
                label_badge = "🔖" if label == "zsm gefasst" else "📝"
                st.markdown(f"{label_badge} `{mem_id}...` **[{score}%]**")
                st.caption(f"{content}...")
            with col2:
                st.progress(score / 100)
    else:
        st.caption("Keine Memories geladen")


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

        if st.button("Alle Erinnerungen", use_container_width=True):
            st.session_state.show_memories = not st.session_state.show_memories
            st.rerun()
        
        if st.button("Einstellungen", use_container_width=True):
            st.session_state.show_settings = not st.session_state.show_settings
            st.rerun()
        
        # === BRAIN MONITOR TOGGLE ===
        st.markdown("---")
        debug_label = "DEBUG MODE: ON" if st.session_state.debug_mode else "DEBUG MODE: OFF"
        if st.button(debug_label, use_container_width=True):
            st.session_state.debug_mode = not st.session_state.debug_mode
            st.rerun()

        st.markdown("---")
        
        st.markdown("**VITALZEICHEN**")
        render_vital_signs(st.session_state.current_emotions)
        
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

    # --- MAIN CONTENT ---

    # Memories Overlay / Area
    if st.session_state.show_memories:
        st.markdown("## Alle Erinnerungen")

        if st.button("Schließen", key="close_memories_top", use_container_width=True):
            st.session_state.show_memories = False
            st.rerun()

        with st.container(border=True):
            # Alle Erinnerungen laden
            all_memories = backend.memory.get_recent_memories(limit=1000)

            if not all_memories:
                st.info("Keine Erinnerungen vorhanden.")
            else:
                st.markdown(f"**Gesamt: {len(all_memories)} Erinnerungen**")

                # Filter-Optionen
                col1, col2 = st.columns(2)
                with col1:
                    filter_label = st.selectbox("Filter nach Label", ["Alle", "original", "zsm gefasst"])
                with col2:
                    filter_type = st.selectbox("Filter nach Typ", ["Alle", "interaction", "summary"])

                # Filter anwenden
                filtered_memories = []
                for mem in all_memories:
                    label = getattr(mem, 'label', 'original')
                    label_match = filter_label == "Alle" or label == filter_label
                    type_match = filter_type == "Alle" or mem.mem_type == filter_type
                    if label_match and type_match:
                        filtered_memories.append(mem)

                st.markdown(f"**Angezeigt: {len(filtered_memories)} Erinnerungen**")

                # Erinnerungen anzeigen
                for i, mem in enumerate(filtered_memories):
                    # Label-Formatierung (sicherstellen, dass label existiert)
                    label = getattr(mem, 'label', 'original')
                    if label == "zsm gefasst":
                        label_html = '<span style="color: #2ea043; font-weight: bold;">[zsm gefasst]</span>'
                    else:
                        label_html = '<span style="color: #8b949e; font-weight: bold;">[original]</span>'

                    # Typ-Formatierung
                    type_badge = "[Interaction]" if mem.mem_type == "interaction" else "[Summary]"

                    # Role-Formatierung
                    role_label = "User" if mem.role == "user" else "CHAPiE"

                    st.markdown(f"### {label_html} {type_badge} {role_label} #{i+1}", unsafe_allow_html=True)
                    st.markdown(f"**ID:** `{mem.id}`")
                    st.markdown(f"**Zeit:** {mem.timestamp}")
                    st.markdown(f"**Inhalt:**")
                    st.markdown(mem.content)
                    st.divider()



        st.markdown("---")
        return # Skip chat while memories are open

    # Settings Overlay / Area
    if st.session_state.show_settings:
        st.markdown("## Einstellungen")
        
        # Tabs fuer verschiedene Einstellungsbereiche
        tab1, tab2, tab3 = st.tabs(["Generierung", "Emotionen", "Datenbank"])
        
        with tab1:
            st.subheader("Generierungs-Einstellungen")
            new_temp = st.slider("Temperatur", 0.0, 1.0, float(settings.temperature), 0.1,
                                help="Hoehere Werte = kreativere Antworten")
            new_tokens = st.number_input("Max Tokens", 100, 8000, int(settings.max_tokens), 100,
                                        help="Maximale Laenge der Antworten")
            new_cot = st.toggle("Chain of Thought (Gedankenprozess)", bool(settings.chain_of_thought),
                               help="Zeigt CHAPPiEs Denkprozess")
            
            st.subheader("Gedaechtnis")
            new_k = st.slider("Memory Top-K", 1, 10, int(settings.memory_top_k),
                             help="Anzahl der Erinnerungen die abgerufen werden")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Speichern", use_container_width=True, type="primary"):
                    settings.temperature = new_temp
                    settings.max_tokens = new_tokens
                    settings.chain_of_thought = new_cot
                    settings.memory_top_k = new_k
                    st.success("Einstellungen gespeichert!")
                    time.sleep(0.5)
                    st.rerun()
            with col2:
                if st.button("Schliessen", use_container_width=True):
                    st.session_state.show_settings = False
                    st.rerun()
        
        with tab2:
            st.subheader("Emotionen bearbeiten")
            st.info("Hier kannst du CHAPPiEs emotionalen Zustand manuell anpassen.")
            
            emo = st.session_state.current_emotions
            
            new_joy = st.slider("Freude", 0, 100, int(emo.get("joy", 50)), 
                               help="Gluecklichkeits-Level")
            new_trust = st.slider("Vertrauen", 0, 100, int(emo.get("trust", 50)),
                                 help="Vertrauens-Level zum User")
            new_energy = st.slider("Energie", 0, 100, int(emo.get("energy", 80)),
                                  help="Energie-Level (sinkt bei viel Arbeit)")
            new_curiosity = st.slider("Neugier", 0, 100, int(emo.get("curiosity", 60)),
                                     help="Wie neugierig CHAPPiE ist")
            new_motivation = st.slider("Motivation", 0, 100, int(emo.get("motivation", 80)),
                                      help="Motivations-Level")
            new_frustration = st.slider("Frustration", 0, 100, int(emo.get("frustration", 0)),
                                       help="Frustrations-Level (niedrig ist besser)")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Emotionen speichern", use_container_width=True, type="primary"):
                    st.session_state.current_emotions = {
                        "joy": new_joy,
                        "trust": new_trust,
                        "energy": new_energy,
                        "curiosity": new_curiosity,
                        "frustration": new_frustration,
                        "motivation": new_motivation
                    }
                    # Auch im Backend aktualisieren
                    backend.emotions.state.happiness = new_joy
                    backend.emotions.state.trust = new_trust
                    backend.emotions.state.energy = new_energy
                    backend.emotions.state.curiosity = new_curiosity
                    backend.emotions.state.frustration = new_frustration
                    backend.emotions.state.motivation = new_motivation
                    backend.emotions._save_state()  # Persistieren
                    st.success("Emotionen aktualisiert!")
                    time.sleep(0.5)
                    st.rerun()
            with col2:
                if st.button("Zuruecksetzen", use_container_width=True):
                    st.session_state.current_emotions = {
                        "joy": 50, "trust": 50, "energy": 80, "curiosity": 60,
                        "frustration": 0, "motivation": 80
                    }
                    backend.emotions.reset()
                    st.success("Emotionen zurueckgesetzt!")
                    time.sleep(0.5)
                    st.rerun()
        
        with tab3:
            st.subheader("Datenbank-Verwaltung")
            
            memory_count = backend.memory.get_memory_count()
            st.metric("Gespeicherte Erinnerungen", memory_count)
            
            st.warning("Achtung: Das Loeschen der ChromaDB ist nicht rueckgaengig zu machen!")
            
            # Sicherheits-Checkbox
            confirm_delete = st.checkbox("Ich verstehe, dass alle Erinnerungen unwiderruflich geloescht werden")
            
            if st.button("ChromaDB loeschen", use_container_width=True, 
                        type="primary" if confirm_delete else "secondary",
                        disabled=not confirm_delete):
                if confirm_delete:
                    deleted_count = backend.memory.clear_memory()
                    st.success(f"{deleted_count} Erinnerungen geloescht!")
                    time.sleep(1)
                    st.rerun()
        
        st.markdown("---")
        return # Skip chat while settings are open
    
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
                                    # Handle both Objects (fresh) and Dicts (loaded from JSON)
                                    if isinstance(m, dict):
                                        content = m.get("content", "")
                                        score = m.get("relevance_score", 0.0)
                                        label = m.get("label", "original")
                                    else:
                                        content = m.content
                                        score = m.relevance_score
                                        label = getattr(m, 'label', 'original')

                                    # Label-Formatierung
                                    if label == "zsm gefasst":
                                        label_html = '<span style="color: #2ea043; font-weight: bold;">[zsm gefasst]</span>'
                                    else:
                                        label_html = '<span style="color: #8b949e; font-weight: bold;">[original]</span>'

                                    st.markdown(f"**Info {idx+1}** {label_html} (Relevanz: {int(score*100)}%)", unsafe_allow_html=True)
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
            assistant_msg = {"role": "assistant", "content": f"Schlafzyklus beendet. \n\n{res}", "metadata": {"thought_process": "Kommando /sleep ausgefuehrt."}}
        
        elif user_input.strip().lower().startswith("/think"):
            # Alter /think Befehl - einfache 10 Schritte Reflexion
            parts = user_input.strip().split(" ", 1)
            topic = parts[1] if len(parts) > 1 else ""
            
            thought_log = []
            
            with st.status("CHAPPiE denkt nach...", expanded=True) as status:
                for step_result in backend.memory.think_deep(backend.brain, topic=topic, steps=10, delay=1.0):
                    step = step_result["step"]
                    total = step_result["total_steps"]
                    thought = step_result["thought"]
                    mem_count = step_result["memories_found"]
                    
                    log_entry = f"**Schritt {step}/{total}** ({mem_count} Erinnerungen gefunden)\n> {thought}"
                    thought_log.append(log_entry)
                    st.write(f"Schritt {step}/{total}: {thought[:80]}...")
                    
                    if step_result.get("error"):
                        status.update(label="Fehler im Think-Modus", state="error")
                        break
                
                status.update(label="Denkprozess abgeschlossen!", state="complete")
            
            full_thoughts = "\n\n".join(thought_log)
            response_text = f"**Mein Denkprozess (10 Schritte):**\n\n{full_thoughts}\n\n---\n*Alle Gedanken wurden als Erinnerungen gespeichert.*"
            
            assistant_msg = {
                "role": "assistant", 
                "content": response_text, 
                "metadata": {"thought_process": f"Think-Modus mit Thema: {topic if topic else 'Allgemeine Selbstreflexion'}"}
            }
        
        elif user_input.strip().lower().startswith("/deep think"):
            # === /deep think MODUS MIT HUMAN-IN-THE-LOOP ===
            
            # Prüfe ob bereits ein Deep Think Zyklus läuft
            if not st.session_state.deep_think_active:
                st.session_state.deep_think_active = True
                st.session_state.deep_think_steps = []
                st.session_state.deep_think_total_done = 0
            
            # Dekrementiere pending_batches falls gesetzt (für Multi-Batch)
            auto_continue = False
            if st.session_state.deep_think_pending_batches > 1:
                st.session_state.deep_think_pending_batches -= 1
                auto_continue = True
            elif st.session_state.deep_think_pending_batches == 1:
                st.session_state.deep_think_pending_batches = 0
            
            # Führe 10 Iterationen durch
            current_batch_steps = []
            
            with st.status(f"CHAPPiE Deep Think (Batch {st.session_state.deep_think_total_done // 10 + 1})...", expanded=True) as status:
                for step_result in backend.deep_think_engine.think_cycle(iterations=10, delay=1.5, max_tokens=5000):
                    step = step_result.step
                    total = step_result.total_steps
                    thought = step_result.thought
                    
                    current_batch_steps.append(step_result)
                    
                    # === VITALZEICHEN LIVE UPDATEN ===
                    new_emotions = {
                        "joy": step_result.emotions_after.get("happiness", 50),
                        "trust": step_result.emotions_after.get("trust", 50),
                        "energy": step_result.emotions_after.get("energy", 80),
                        "curiosity": step_result.emotions_after.get("curiosity", 60),
                        "frustration": step_result.emotions_after.get("frustration", 0),
                        "motivation": step_result.emotions_after.get("motivation", 80)
                    }
                    st.session_state.current_emotions = new_emotions
                    
                    # Zeige Live-Vitalzeichen im Status-Container
                    st.markdown("---")
                    st.markdown("**📊 Live-Vitalzeichen:**")
                    cols_vitals = st.columns(3)
                    with cols_vitals[0]:
                        st.write(f"🟢 Freude: {new_emotions['joy']}%")
                        st.write(f"🔵 Vertrauen: {new_emotions['trust']}%")
                    with cols_vitals[1]:
                        st.write(f"⚡ Energie: {new_emotions['energy']}%")
                        st.write(f"🟣 Neugier: {new_emotions['curiosity']}%")
                    with cols_vitals[2]:
                        st.write(f"🧡 Motivation: {new_emotions['motivation']}%")
                        st.write(f"🔴 Frustration: {new_emotions['frustration']}%")
                    st.markdown("---")
                    
                    # Fortschritt ohne HTML anzeigen
                    delta_info = ""
                    if step_result.emotions_delta:
                        changes = []
                        # Übersetzung für Delta-Anzeige
                        name_map = {"happiness": "Freude", "trust": "Vertrauen", "energy": "Energie", 
                                   "curiosity": "Neugier", "frustration": "Frust", "motivation": "Motivation"}
                        for emo_key, delta in step_result.emotions_delta.items():
                            if delta != 0:
                                name = name_map.get(emo_key, emo_key)
                                sign = "+" if delta > 0 else ""
                                changes.append(f"{name}: {sign}{delta}")
                        if changes:
                            delta_info = f" | Delta: {', '.join(changes)}"
                    
                    st.write(f"**Schritt {step}/{total}:** {thought[:70]}...{delta_info}")
                    
                    if step_result.error:
                        status.update(label=f"Fehler: {step_result.error}", state="error")
                        break
                
                status.update(label=f"Batch abgeschlossen! ({len(current_batch_steps)} Gedanken)", state="complete")
            
            # Update Session State
            st.session_state.deep_think_steps.extend(current_batch_steps)
            st.session_state.deep_think_total_done += len(current_batch_steps)
            
            # Zusammenfassung
            summary = backend.deep_think_engine.get_summary_after_cycle(current_batch_steps)
            
            # Formatiere Gedanken OHNE HTML (nur Markdown)
            thoughts_md = ""
            name_map = {"happiness": "Freude", "trust": "Vertrauen", "energy": "Energie", 
                       "curiosity": "Neugier", "frustration": "Frust", "motivation": "Motivation"}
            
            for step in current_batch_steps:
                if not step.error:
                    delta_parts = []
                    for emo_key, val in step.emotions_delta.items():
                        if val != 0:
                            name = name_map.get(emo_key, emo_key)
                            sign = "+" if val > 0 else ""
                            color_emoji = "🟢" if val > 0 else "🔴"
                            delta_parts.append(f"{color_emoji} {name}: {sign}{val}")
                    delta_str = ", ".join(delta_parts) if delta_parts else "keine Änderung"
                    
                    thoughts_md += f"""
**Schritt {step.step}/{step.total_steps}**
> {step.thought}

*Emotions-Delta: {delta_str}* | *Memories: {len(step.memories_used)}*

---
"""
            
            # Gesamt-Delta formatieren (ohne HTML)
            total_delta_parts = []
            for emo_key, val in summary.get("emotions_total_delta", {}).items():
                if val != 0:
                    name = name_map.get(emo_key, emo_key)
                    sign = "+" if val > 0 else ""
                    emoji = "🟢" if val > 0 else "🔴"
                    total_delta_parts.append(f"{emoji} {name}: {sign}{val}")
            total_delta_str = ", ".join(total_delta_parts) if total_delta_parts else "keine Netto-Änderung"
            
            response_text = f"""## Deep Think Zyklus abgeschlossen

**Statistiken:**
- Gedanken in diesem Batch: {len(current_batch_steps)}
- Gesamt Gedanken bisher: {st.session_state.deep_think_total_done}
- Eindeutige Memories abgerufen: {summary.get("memories_accessed", 0)}
- Gesamt Emotions-Delta: {total_delta_str}

---

### Gedanken-Protokoll:
{thoughts_md}

---
*Alle Gedanken wurden mit `source: self_reflection` in ChromaDB gespeichert.*
"""
            
            # Speichere Nachricht ZUERST
            assistant_msg = {
                "role": "assistant", 
                "content": response_text, 
                "metadata": {
                    "thought_process": f"Deep Think Batch {st.session_state.deep_think_total_done // 10}",
                    "deep_think_stats": summary
                }
            }
            st.session_state.messages.append(assistant_msg)
            backend.chat_manager.save_session(st.session_state.session_id, st.session_state.messages)
            
            # Human-in-the-Loop: Zeige Buttons für Fortsetzung NACH der Nachricht
            with st.container(border=True):
                st.markdown("### Soll CHAPPiE weiterdenken?")
                
                # Erste Zeile: 10, 20, 30, 40 Gedanken
                cols_row1 = st.columns(4)
                with cols_row1[0]:
                    if st.button("10 Gedanken", key=f"deep_think_10_{st.session_state.deep_think_total_done}", use_container_width=True):
                        st.session_state.pending_cmd = "/deep think"
                        st.rerun()
                with cols_row1[1]:
                    if st.button("20 Gedanken", key=f"deep_think_20_{st.session_state.deep_think_total_done}", use_container_width=True):
                        st.session_state.deep_think_pending_batches = 2
                        st.session_state.pending_cmd = "/deep think"
                        st.rerun()
                with cols_row1[2]:
                    if st.button("30 Gedanken", key=f"deep_think_30_{st.session_state.deep_think_total_done}", use_container_width=True):
                        st.session_state.deep_think_pending_batches = 3
                        st.session_state.pending_cmd = "/deep think"
                        st.rerun()
                with cols_row1[3]:
                    if st.button("40 Gedanken", key=f"deep_think_40_{st.session_state.deep_think_total_done}", use_container_width=True):
                        st.session_state.deep_think_pending_batches = 4
                        st.session_state.pending_cmd = "/deep think"
                        st.rerun()
                
                # Zweite Zeile: 60, 100 Gedanken und Sleep
                cols_row2 = st.columns(3)
                with cols_row2[0]:
                    if st.button("60 Gedanken", key=f"deep_think_60_{st.session_state.deep_think_total_done}", use_container_width=True):
                        st.session_state.deep_think_pending_batches = 6
                        st.session_state.pending_cmd = "/deep think"
                        st.rerun()
                with cols_row2[1]:
                    if st.button("100 Gedanken", key=f"deep_think_100_{st.session_state.deep_think_total_done}", use_container_width=True):
                        st.session_state.deep_think_pending_batches = 10
                        st.session_state.pending_cmd = "/deep think"
                        st.rerun()
                with cols_row2[2]:
                    if st.button("🌙 Sleep & Zusammenfassen", key=f"deep_think_sleep_{st.session_state.deep_think_total_done}", use_container_width=True):
                        # Beende Deep Think und starte /sleep
                        st.session_state.deep_think_active = False
                        st.session_state.deep_think_steps = []
                        st.session_state.deep_think_total_done = 0
                        # Füge finale Zusammenfassung hinzu
                        final_summary = f"""## Deep Think Session beendet

**Gesamt-Statistiken:**
- Durchgeführte Gedanken: {st.session_state.deep_think_total_done}
- Gesamt Emotions-Delta: {total_delta_str}

*Starte nun /sleep Modus zur Konsolidierung aller Erinnerungen...*
"""
                        final_msg = {"role": "assistant", "content": final_summary, "metadata": {"thought_process": "Deep Think Session beendet"}}
                        st.session_state.messages.append(final_msg)
                        backend.chat_manager.save_session(st.session_state.session_id, st.session_state.messages)
                        # Starte /sleep
                        st.session_state.pending_cmd = "/sleep"
                        st.rerun()
            
            # Wenn auto_continue aktiv (Multi-Batch), automatisch nächsten Batch starten
            if auto_continue:
                st.session_state.pending_cmd = "/deep think"
                st.rerun()
                return
            
            # Kein st.rerun() hier, damit die Buttons sichtbar bleiben!
            return
        
        elif user_input.strip().lower() == "/clear":
             st.session_state.messages = []
             st.session_state.session_id = backend.chat_manager.create_session()
             st.rerun()
             return
        
        elif user_input.strip().lower() == "/help":
            help_text = """**CHAPPiE Commands:**

- **/sleep** - Startet die Traum-Phase (konsolidiert Erinnerungen)
- **/think [thema]** - Einfacher Reflektionsmodus (10 Schritte)
- **/deep think** - Rekursive Selbstreflexion mit Human-in-the-Loop (10 Schritte pro Batch, fortsetzbar)
- **/clear** - Loescht aktuellen Chat und startet neue Sitzung
- **/stats** - Zeigt System-Statistiken
- **/config** - Oeffnet Einstellungen
- **/help** - Zeigt diese Hilfe

**Debug Mode:**
Aktiviere den DEBUG MODE Button in der Sidebar fuer das Brain Monitor Panel.

**Tipp:** Klicke auf die Buttons oben fuer schnellen Zugriff!"""
            assistant_msg = {"role": "assistant", "content": help_text, "metadata": {"thought_process": "Kommando /help ausgefuehrt."}}
        
        elif user_input.strip().lower() == "/stats":
            status = backend.get_status()
            memory_count = backend.memory.get_memory_count()
            stats_text = f"""**System-Statistiken:**

**Brain:** {'Verfügbar' if status['brain_available'] else 'Nicht verfügbar'}
**Modell:** {status['model']}
**Erinnerungen:** {memory_count} gespeichert

**Emotionen:**
- Freude: {status['emotions']['joy']}%
- Vertrauen: {status['emotions']['trust']}%
- Energie: {status['emotions']['energy']}%
- Neugier: {status['emotions']['curiosity']}%"""
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
                         "role": m.role,
                         "label": getattr(m, 'label', 'original'),
                         "id": m.id  # Für Brain Monitor
                     })

            assistant_msg = {
                "role": "assistant",
                "content": result["response_text"],
                "metadata": {
                    "thought_process": result.get("thought_process"),
                    "rag_memories": formatted_memories,
                    # BRAIN MONITOR Debug-Daten
                    "emotions_delta": result.get("emotions_delta", {}),
                    "emotions_before": result.get("emotions_before", {}),
                    "input_analysis": result.get("input_analysis", user_input)
                }
            }

        st.session_state.messages.append(assistant_msg)
        backend.chat_manager.save_session(st.session_state.session_id, st.session_state.messages)
        st.rerun()

if __name__ == "__main__":
    main()
