import streamlit as st
from Chappies_Trainingspartner.daemon_manager import (
    is_daemon_running,
    start_daemon,
    stop_daemon,
    get_daemon_logs,
    get_training_stats,
    clear_logs
)


def render_training_ui():
    """Rendert die Training-Control UI mit App-konformem Styling."""
    
    st.markdown("""
    <style>
        @media screen and (max-width: 768px) {
            .training-control-buttons > div {
                flex-direction: column !important;
            }
            .training-control-buttons > div > div {
                width: 100% !important;
                min-width: 100% !important;
            }
            .training-logs-controls > div {
                flex-direction: column !important;
            }
            .training-logs-controls > div > div {
                width: 100% !important;
                min-width: 100% !important;
            }
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("## Training-Control")
    st.markdown("Starte, stoppe und ueberwache das autonome CHAPPiE Training.")
    
    stats = get_training_stats()
    running = stats['running']
    pid = stats['pid']
    
    if running:
        health_status = "Gesund" if stats.get('daemon_healthy', False) else "Pruefen"
        health_icon = "\u2705" if stats.get('daemon_healthy', False) else "\u26a0\ufe0f"
        st.markdown(f"""
        <div class="training-status-active">
            <span style="font-size: 1.2rem;">\U0001f7e2</span>
            <span style="font-weight: 600; color: #2ea043; margin-left: 8px;">Training laeuft</span>
            <span style="color: #8b949e; margin-left: 12px;">PID: {pid}</span>
            <span style="margin-left: 12px;">{health_icon} {health_status}</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        last_activity = stats.get('last_activity', 'Unbekannt')
        st.markdown(f"""
        <div class="training-status-inactive">
            <span style="font-size: 1.2rem;">\u26aa</span>
            <span style="color: #8b949e; margin-left: 8px;">Kein Training aktiv</span>
            <span style="color: #6e7681; margin-left: 12px;">Letzte Aktivitaet: {last_activity}</span>
        </div>
        """, unsafe_allow_html=True)
    
    if stats.get('diagnostic_messages'):
        with st.expander(":mag: Diagnose-Infos", expanded=not stats.get('daemon_healthy', True)):
            for msg in stats['diagnostic_messages']:
                if 'rot' in msg.lower() or 'warn' in msg.lower():
                    st.warning(msg)
                else:
                    st.info(msg)
    
    st.markdown("---")
    
    if stats.get('focus'):
        st.markdown(f"""
        <div class="training-info-card">
            <div class="training-metric-label">\U0001f4da Fokus</div>
            <div class="training-metric-value">{stats['focus']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    if stats.get('persona'):
        persona_display = stats['persona'][:200] + "..." if len(stats.get('persona', '')) > 200 else stats['persona']
        st.markdown(f"""
        <div class="training-info-card">
            <div class="training-metric-label">\U0001f464 Persona</div>
            <div style="color: #c9d1d9; font-style: italic; margin-top: 4px;">"{persona_display}"</div>
        </div>
        """, unsafe_allow_html=True)
    
    with st.expander("Model-Konfiguration", expanded=False):
        heartbeat_mem = stats.get('heartbeat_memory_count', 0)
        live_mem = stats.get('memory_count', 0)
        memory_display = f"{live_mem:,}"
        if heartbeat_mem > 0 and heartbeat_mem != live_mem:
            memory_display = f"{live_mem:,} (Training: {heartbeat_mem:,})"
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Modell", stats.get('model', '-'))
        with col2:
            st.metric("Provider", stats.get('provider', '-'))
        with col3:
            st.metric("Memory", memory_display)
    
    with st.expander("Training-Statistiken", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Loops", stats.get('loops', 0))
        with col2:
            st.metric("Fehler", stats.get('errors', 0))
        with col3:
            st.metric("Traeume", stats.get('dreams', 0))
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Msgs since Dream", stats.get('messages_since_dream', 0))
        with col2:
            start_time = stats.get('start_time', '-')
            st.metric("Gestartet", start_time[:16] if start_time and start_time != '-' else '-')
        with col3:
            st.metric("PID", pid if pid else '-')
    
    st.markdown("---")
    
    st.markdown("### Steuerung")
    
    focus_input = st.text_input(
        "Fokus-Bereich (optional)",
        value="",
        placeholder="z.B. Emotionale Intelligenz, Logisches Denken...",
        help="Leer lassen um vorheriges Training fortzusetzen"
    )
    
    new_training = st.checkbox("Neues Training starten", value=False)
    
    st.markdown('<div class="training-control-buttons">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button(
            "Training starten",
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
            "Training stoppen",
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
            "Neu starten",
            use_container_width=True,
            disabled=running
        ):
            result = start_daemon(focus=focus_input if focus_input else None, new=True)
            if result['success']:
                st.success(result['message'])
            else:
                st.warning(result['message'])
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    with st.expander("Logs", expanded=False):
        st.markdown('<div class="training-logs-controls">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            lines_to_show = st.selectbox(
                "Zeilen",
                [50, 100, 200, 500],
                index=1,
                label_visibility="collapsed"
            )
        
        with col2:
            if st.button("Aktualisieren", use_container_width=True):
                st.rerun()
        
        with col3:
            if st.button("Loeschen", use_container_width=True):
                if clear_logs():
                    st.success("Logs geloescht")
                    st.rerun()
                else:
                    st.error("Konnte Logs nicht loeschen")
        st.markdown('</div>', unsafe_allow_html=True)
        
        log_content = get_daemon_logs(lines=lines_to_show)
        st.code(log_content, language="plaintext", line_numbers=True)
    
    st.markdown("---")
    
    if st.button("Schliessen", use_container_width=True, type="secondary"):
        st.session_state.show_training = False
        st.rerun()
    
    st.caption("Das Training laeuft als separater Hintergrundprozess. Die UI kann geschlossen werden, waehrend das Training weiterlaeuft.")
