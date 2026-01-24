import streamlit as st
from typing import Dict, Any
from memory.memory_engine import MemoryEngine

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


def render_vital_signs(backend):
    """Rendert den kompletten Block der Vitalzeichen."""
    # Fallback für Emotions (falls nicht im Session State)
    emotions_dict = st.session_state.get("current_emotions", {})
    if not emotions_dict:
        try:
            emotions_dict = backend._get_emotions_snapshot()
        except:
            emotions_dict = {}

    render_emotion_metric("Freude", emotions_dict.get("joy", 50), "#FFD700")      # Gold
    render_emotion_metric("Vertrauen", emotions_dict.get("trust", 50), "#2196F3") # Blau
    render_emotion_metric("Energie", emotions_dict.get("energy", 80), "#4CAF50")  # Gruen
    render_emotion_metric("Neugier", emotions_dict.get("curiosity", 60), "#9C27B0") # Lila
    render_emotion_metric("Motivation", emotions_dict.get("motivation", 80), "#FF9800") # Orange
    render_emotion_metric("Frustration", emotions_dict.get("frustration", 0), "#F44336") # Rot

    # Memory Status hinzufügen
    st.markdown("---")
    try:
        # Optimierung: Nutze die existierende Memory-Instanz vom Backend
        # statt eine neue zu erstellen (verhindert Reloads)
        live_memory = backend.memory
        
        memory_count = live_memory.get_memory_count()
        
        # Health Check ist nun sehr schnell, da Instanz existiert
        health = live_memory.health_check()

        if health["embedding_model_loaded"] and health["chromadb_connected"]:
            st.metric("Erinnerungen", f"{memory_count:,}")
            st.caption("Live-Daten aus Training")
        else:
            st.metric("🧠 Erinnerungen", f"{memory_count:,}")
            st.caption("⚠️ Memory-System Probleme")

        # Zeige letzte Memory wenn verfügbar
        if memory_count > 0:
            try:
                # Nutze cached memory engine
                recent = live_memory.get_recent_memories(limit=1)
                if recent:
                    last_memory = recent[0]
                    # Robust attribute access
                    if isinstance(last_memory, dict):
                        timestamp_str = last_memory.get('timestamp', 'Unbekannt')
                    else:
                        timestamp_str = getattr(last_memory, 'timestamp', 'Unbekannt')
                        
                    if timestamp_str and timestamp_str != 'Unbekannt':
                        try:
                            from datetime import datetime
                            dt = datetime.fromisoformat(timestamp_str)
                            formatted = dt.strftime("%d.%m.%Y %H:%M:%S")
                            st.caption(f"Letzte: {formatted}")
                        except ValueError:
                            st.caption("Letzte: Unbekannt")
                    else:
                        st.caption("Letzte: Unbekannt")
            except Exception as ex:
                # Silent fail für UI cleaness
                pass

    except Exception as e:
        st.metric("🧠 Erinnerungen", "Fehler")
        st.caption(f"❌ {str(e)[:30]}...")


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
            render_memory_item(mem, i + 1)
    else:
        st.caption("Keine Memories geladen")


def render_memory_item(mem: Any, index: int = 1):
    """
    Rendert eine einzelne Erinnerung konsistent für alle Views.
    
    Args:
        mem: Memory-Objekt oder Dictionary
        index: Index der Erinnerung (für Anzeige #1, #2...)
    """
    # Handle both Objects (fresh) and Dicts (loaded from JSON)
    if isinstance(mem, dict):
        content = mem.get("content", "")
        score = int(mem.get("relevance_score", 0.0) * 100)
        mem_id = mem.get("id", "?")[:8]
        label = mem.get("label", "original")
        role = mem.get("role", "unknown")
        mem_type = mem.get("type", "interaction")
        timestamp = mem.get("timestamp", "")
    else:
        content = mem.content
        score = int(mem.relevance_score * 100) if hasattr(mem, 'relevance_score') else 0
        mem_id = mem.id[:8] if hasattr(mem, 'id') else "?"
        label = getattr(mem, 'label', 'original')
        role = getattr(mem, 'role', 'unknown')
        mem_type = getattr(mem, 'mem_type', 'interaction')
        timestamp = getattr(mem, 'timestamp', "")

    # Label-Formatierung
    if label == "zsm gefasst":
        label_html = '<span style="color: #2ea043; font-weight: bold; border: 1px solid #2ea043; padding: 2px 6px; border-radius: 4px; font-size: 0.8em;">SUMMARY</span>'
        badge_symbol = "S" # Fallback char if needed, but we use label_html
    else:
        label_html = '<span style="color: #8b949e; font-weight: bold; border: 1px solid #8b949e; padding: 2px 6px; border-radius: 4px; font-size: 0.8em;">ORIGINAL</span>'
        badge_symbol = "O"

    # Role & Type Badges (für Memories View)
    role_label = "User" if role == "user" else "CHAPiE"
    type_badge = "[Interaction]" if mem_type == "interaction" else "[Summary]"

    # Flexible Anzeige: Wenn wir im Chat sind (kurz), sonst (lang)
    col1, col2 = st.columns([3, 1])
    with col1:
        # Header bauen
        # header = f"{label_badge} `{mem_id}...`" # OLD with emoji
        if timestamp: 
            # Detaillierte Ansicht (Memories Overlay)
            st.markdown(f"### {label_html} {type_badge} {role_label} #{index}", unsafe_allow_html=True)
            st.markdown(f"**ID:** `{mem_id}` | **Zeit:** {timestamp}")
            st.markdown(content)
        else:
            # Kompakte Ansicht (Chat RAG)
            st.markdown(f"**Info {index}** {label_html} (Relevanz: {score}%)", unsafe_allow_html=True)
            if content and isinstance(content, str):
                st.caption(content[:250] + "..." if len(content) > 250 else content)
            else:
                st.caption("*Keine Inhaltsdaten verfügbar*")
            
    with col2:
        # Nur Score anzeigen wenn relevant
        if score > 0:
            st.progress(score / 100)


def render_deep_think_controls(current_total_done: int) -> str:
    """
    Rendert die Steuerungs-Buttons für den Deep Think Modus.
    
    Returns:
        String Action Code: "10", "20", "sleep", "stop" oder None
    """
    action = None
    
    with st.container(border=True):
        st.markdown("### Soll CHAPPiE weiterdenken?")
        
        # Erste Zeile: 10, 20, 30, 40 Gedanken
        cols_row1 = st.columns(4)
        with cols_row1[0]:
            if st.button("10 Gedanken", key=f"dt_10_{current_total_done}", use_container_width=True):
                return "10"
        with cols_row1[1]:
            if st.button("20 Gedanken", key=f"dt_20_{current_total_done}", use_container_width=True):
                return "20"
        with cols_row1[2]:
            if st.button("30 Gedanken", key=f"dt_30_{current_total_done}", use_container_width=True):
                return "30"
        with cols_row1[3]:
            if st.button("40 Gedanken", key=f"dt_40_{current_total_done}", use_container_width=True):
                return "40"
        
        # Zweite Zeile: 60, 100 Gedanken und Sleep
        cols_row2 = st.columns(3)
        with cols_row2[0]:
            if st.button("60 Gedanken", key=f"dt_60_{current_total_done}", use_container_width=True):
                return "60"
        with cols_row2[1]:
            if st.button("100 Gedanken", key=f"dt_100_{current_total_done}", use_container_width=True):
                return "100"
        with cols_row2[2]:
            if st.button("🌙 Sleep & Zusammenfassen", key=f"dt_sleep_{current_total_done}", use_container_width=True):
                return "sleep"
                
    return None
