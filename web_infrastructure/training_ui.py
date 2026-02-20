import streamlit as st
from Chappies_Trainingspartner.daemon_manager import (
    is_daemon_running,
    start_daemon,
    stop_daemon,
    get_daemon_logs,
    get_training_stats,
    clear_logs
)


def _render_stat_card(label: str, value, icon: str = ""):
    """Rendert eine einzelne Stat-Karte mit Outline."""
    st.markdown(f"""
    <div style="
        border: 1px solid #3b3b5c;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        background: linear-gradient(145deg, #1e1e2e, #252540);
        margin-bottom: 8px;
    ">
        <div style="font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px;">
            {icon} {label}
        </div>
        <div style="font-size: 24px; font-weight: bold; color: #fff; margin-top: 5px;">
            {value}
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_stat_row(items: list, mobile_stack: bool = False):
    """Rendert eine Reihe von Stat-Karten. Auf Mobile werden sie untereinander gestapelt."""
    if mobile_stack:
        for label, value, icon in items:
            _render_stat_card(label, value, icon)
    else:
        cols = st.columns(len(items))
        for i, (label, value, icon) in enumerate(items):
            with cols[i]:
                _render_stat_card(label, value, icon)


def render_training_ui():
    """Rendert die Training-Control UI."""
    
    st.markdown("""
    <style>
        /* Training UI Mobile Anpassungen */
        @media screen and (max-width: 768px) {
            /* Stat-Karten untereinander auf Mobile */
            .training-stat-row > div {
                flex-direction: column !important;
            }
            .training-stat-row > div > div {
                width: 100% !important;
                min-width: 100% !important;
            }
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("## Training-Control")
    st.markdown("Starte, stoppe und überwache das autonome CHAPPiE Training.")
    
    stats = get_training_stats()
    running = stats['running']
    pid = stats['pid']
    
    if running:
        health_status = "✅ Gesund" if stats.get('daemon_healthy', False) else "⚠️ Prüfen"
        health_color = "#4ade80" if stats.get('daemon_healthy', False) else "#fbbf24"
        st.markdown(f"""
        <div style="
            background: linear-gradient(90deg, #1a472a, #2d5a3d);
            border: 1px solid #4ade80;
            border-radius: 10px;
            padding: 15px 20px;
            margin-bottom: 20px;
        ">
            <span style="font-size: 20px;">●</span>
            <span style="font-weight: bold; color: #4ade80; margin-left: 10px;">Training läuft</span>
            <span style="color: #888; margin-left: 15px;">PID: {pid}</span>
            <span style="color: {health_color}; margin-left: 15px;">{health_status}</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        last_activity = stats.get('last_activity', 'Unbekannt')
        st.markdown(f"""
        <div style="
            background: linear-gradient(90deg, #2a2a3e, #35354a);
            border: 1px solid #555;
            border-radius: 10px;
            padding: 15px 20px;
            margin-bottom: 20px;
        ">
            <span style="font-size: 20px;">○</span>
            <span style="color: #888; margin-left: 10px;">Kein Training aktiv</span>
            <span style="color: #666; margin-left: 15px;">Letzte Aktivität: {last_activity}</span>
        </div>
        """, unsafe_allow_html=True)
    
    if stats.get('diagnostic_messages'):
        with st.expander("🔍 Diagnose-Infos", expanded=not stats.get('daemon_healthy', True)):
            for msg in stats['diagnostic_messages']:
                if '🔴' in msg or '⚠️' in msg:
                    st.warning(msg)
                else:
                    st.info(msg)
    
    st.markdown("---")
    
    st.markdown("### Model-Konfiguration")
    st.markdown('<div class="training-stat-row">', unsafe_allow_html=True)
    
    heartbeat_mem = stats.get('heartbeat_memory_count', 0)
    live_mem = stats.get('memory_count', 0)
    memory_display = f"{live_mem:,}"
    if heartbeat_mem > 0 and heartbeat_mem != live_mem:
        memory_display = f"{live_mem:,} (Training: {heartbeat_mem:,})"
    
    _render_stat_row([
        ("Modell", stats.get('model', '-'), "🤖"),
        ("Provider", stats.get('provider', '-'), "☁️"),
        ("Memory", memory_display, "🧠"),
    ])
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("### Training-Statistiken")
    st.markdown('<div class="training-stat-row">', unsafe_allow_html=True)
    _render_stat_row([
        ("Loops", stats.get('loops', 0), "🔄"),
        ("Fehler", stats.get('errors', 0), "⚠️"),
        ("Träume", stats.get('dreams', 0), "💭"),
    ])
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="training-stat-row">', unsafe_allow_html=True)
    _render_stat_row([
        ("Msgs since Dream", stats.get('messages_since_dream', 0), "📊"),
        ("Gestartet", stats.get('start_time', '-')[:16] if stats.get('start_time') else '-', "🕐"),
        ("PID", pid if pid else '-', "🔧"),
    ])
    st.markdown('</div>', unsafe_allow_html=True)
    
    if stats.get('focus'):
        st.markdown(f"""
        <div style="
            border: 1px solid #3b3b5c;
            border-radius: 10px;
            padding: 15px;
            background: #1e1e2e;
            margin-top: 15px;
        ">
            <div style="font-size: 12px; color: #888; text-transform: uppercase;">📚 Fokus</div>
            <div style="color: #fff; margin-top: 5px;">{stats['focus']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    if stats.get('persona'):
        persona_display = stats['persona'][:150] + "..." if len(stats.get('persona', '')) > 150 else stats['persona']
        st.markdown(f"""
        <div style="
            border: 1px solid #3b3b5c;
            border-radius: 10px;
            padding: 15px;
            background: #1e1e2e;
            margin-top: 10px;
        ">
            <div style="font-size: 12px; color: #888; text-transform: uppercase;">👤 Persona</div>
            <div style="color: #fff; margin-top: 5px; font-style: italic;">"{persona_display}"</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("### Steuerung")
    
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        focus_input = st.text_input(
            "Fokus-Bereich (optional)",
            value="",
            placeholder="z.B. Emotionale Intelligenz, Logisches Denken...",
            help="Leer lassen um vorheriges Training fortzusetzen"
        )
    
    with col_right:
        st.markdown("<br>", unsafe_allow_html=True)
        new_training = st.checkbox("Neues Training starten", value=False)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button(
            "▶️ Training starten",
            type="primary",
            use_container_width=True,
            disabled=running
        ):
            result = start_daemon(focus=focus_input if focus_input else None, new=new_training)
            if result['success']:
                st.success(result['message'])
            else:
                st.warning(result['message'])
            st.rerun()
    
    with col2:
        if st.button(
            "⏹️ Training stoppen",
            type="secondary",
            use_container_width=True,
            disabled=not running
        ):
            result = stop_daemon()
            if result['success']:
                st.success(result['message'])
            else:
                st.warning(result['message'])
            st.rerun()
    
    with col3:
        if st.button(
            "🔄 Neu starten",
            use_container_width=True,
            disabled=running
        ):
            result = start_daemon(focus=focus_input if focus_input else None, new=True)
            if result['success']:
                st.success(result['message'])
            else:
                st.warning(result['message'])
            st.rerun()
    
    st.markdown("---")
    
    st.markdown("### Logs")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        lines_to_show = st.selectbox(
            "Zeilen",
            [50, 100, 200, 500],
            index=1,
            label_visibility="collapsed"
        )
    
    with col2:
        if st.button("🔄 Aktualisieren", use_container_width=True):
            st.rerun()
    
    with col3:
        if st.button("🗑️ Logs löschen", use_container_width=True):
            if clear_logs():
                st.success("Logs gelöscht")
                st.rerun()
            else:
                st.error("Konnte Logs nicht löschen")
    
    log_content = get_daemon_logs(lines=lines_to_show)
    
    st.code(log_content, language="plaintext", line_numbers=True)
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("❌ Schließen", use_container_width=True, type="secondary"):
            st.session_state.show_training = False
            st.rerun()
    
    st.caption("Das Training läuft als separater Hintergrundprozess. Die UI kann geschlossen werden, während das Training weiterläuft.")
