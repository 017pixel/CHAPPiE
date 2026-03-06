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
    """Rendert die Training-Control UI (Uncodixified)."""
    
    st.markdown("## Autonomes Training")
    st.markdown("Starte, stoppe und überwache das autonome CHAPPiE Training.")
    
    stats = get_training_stats()
    running = stats['running']
    pid = stats['pid']
    
    # 1. Status Panel
    if running:
        health_status = "Gesund" if stats.get('daemon_healthy', False) else "Prüfen"
        st.success(f"🟢 **Training läuft** (PID: {pid} | {health_status})")
    else:
        last_activity = stats.get('last_activity', 'Unbekannt')
        st.info(f"⚪ **Kein Training aktiv** (Letzte Aktivität: {last_activity})")
    
    # 2. Diagnose-Meldungen
    if stats.get('diagnostic_messages'):
        with st.expander("🔍 Diagnose-Infos", expanded=not stats.get('daemon_healthy', True)):
            for msg in stats['diagnostic_messages']:
                if 'rot' in msg.lower() or 'warn' in msg.lower():
                    st.warning(msg)
                else:
                    st.text(msg)
    
    st.divider()
    
    # 3. Fokus & Persona Infos
    if stats.get('focus'):
        st.markdown(f"**📚 Fokus:** {stats['focus']}")
    
    if stats.get('persona'):
        persona_display = stats['persona'][:200] + "..." if len(stats.get('persona', '')) > 200 else stats['persona']
        st.markdown(f"**👤 Persona:** _{persona_display}_")
        
    st.divider()
    
    # 4. Statistiken
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Config")
        heartbeat_mem = stats.get('heartbeat_memory_count', 0)
        live_mem = stats.get('memory_count', 0)
        memory_display = f"{live_mem:,}"
        if heartbeat_mem > 0 and heartbeat_mem != live_mem:
            memory_display = f"{live_mem:,} (Training: {heartbeat_mem:,})"
            
        st.markdown(f"- **Modell:** {stats.get('model', '-')}")
        st.markdown(f"- **Provider:** {stats.get('provider', '-')}")
        st.markdown(f"- **Memory Count:** {memory_display}")

    with col2:
        st.markdown("### Fortschritt")
        st.markdown(f"- **Loops:** {stats.get('loops', 0)}")
        st.markdown(f"- **Fehler:** {stats.get('errors', 0)}")
        st.markdown(f"- **Träume:** {stats.get('dreams', 0)} (seit {stats.get('messages_since_dream', 0)} Msg)")
        st.markdown(f"- **Startzeit:** {stats.get('start_time', '-')[:16]}")
    
    st.divider()
    
    # 5. Steuerung
    st.markdown("### Steuerung")
    focus_input = st.text_input("Fokus-Bereich (optional)", placeholder="z.B. Emotionale Intelligenz...", help="Leer lassen für Fortsetzung")
    new_training = st.checkbox("Als neues Training starten")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Training starten", type="primary", use_container_width=True, disabled=running):
            res = start_daemon(focus=focus_input if focus_input else None, new=new_training)
            st.toast(res['message'])
            st.rerun()
    with c2:
        if st.button("Training stoppen", use_container_width=True, disabled=not running):
            res = stop_daemon()
            st.toast(res['message'])
            st.rerun()
    with c3:
        if st.button("Neustart", use_container_width=True, disabled=running):
            res = start_daemon(focus=focus_input if focus_input else None, new=True)
            st.toast(res['message'])
            st.rerun()
            
    st.divider()
    
    # 6. Logs
    with st.expander("Prozess-Logs", expanded=False):
        l1, l2, l3 = st.columns([2,1,1])
        with l1:
            lines = st.selectbox("Zeilen", [50, 100, 200, 500], index=1, label_visibility="collapsed")
        with l2:
            if st.button("Refresh", use_container_width=True): st.rerun()
        with l3:
            if st.button("Logs leeren", use_container_width=True):
                if clear_logs():
                    st.toast("Logs geleert")
                    st.rerun()
        
        st.code(get_daemon_logs(lines=lines), language="plaintext")
        
    st.caption("Dieses Training läuft im Hintergrund, du kannst die Seite jederzeit verlassen.")
