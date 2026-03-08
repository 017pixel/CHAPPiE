import streamlit as st

from Chappies_Trainingspartner.daemon_manager import (
    clear_logs,
    get_daemon_logs,
    get_training_stats,
    load_training_config,
    save_training_config,
    start_daemon,
    stop_daemon,
)


def _curriculum_to_text(curriculum):
    lines = []
    for item in curriculum or []:
        topic = (item or {}).get("topic", "").strip()
        duration = (item or {}).get("duration_minutes", "infinite")
        if topic:
            lines.append(f"{topic} | {duration}")
    return "\n".join(lines)


def _parse_curriculum_text(raw_text: str, fallback_focus: str):
    curriculum = []
    for line in (raw_text or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        topic, separator, duration = stripped.partition("|")
        topic = topic.strip()
        if not topic:
            continue
        duration_value = duration.strip() if separator else "infinite"
        if duration_value.lower() != "infinite":
            try:
                duration_value = max(1, int(duration_value))
            except ValueError:
                duration_value = "infinite"
        curriculum.append({"topic": topic, "duration_minutes": duration_value})

    if not curriculum and fallback_focus.strip():
        curriculum.append({"topic": fallback_focus.strip(), "duration_minutes": "infinite"})
    return curriculum


def render_training_ui():
    """Rendert die Training-Control UI für 24/7 Training."""
    st.markdown("## Autonomes Training")
    st.markdown("Starte, stoppe, überwache und konfiguriere das autonome CHAPPiE-Training.")

    config = load_training_config()
    stats = get_training_stats()
    running = stats["running"]
    pid = stats["pid"]

    if running:
        health_status = "Gesund" if stats.get("daemon_healthy", False) else "Prüfen"
        st.success(f"🟢 **Training läuft** (PID: {pid} | {health_status})")
    else:
        last_activity = stats.get("last_activity", "Unbekannt")
        st.info(f"⚪ **Kein Training aktiv** (Letzte Aktivität: {last_activity})")

    if stats.get("current_topic"):
        st.caption(f"Aktuelles Thema: {stats['current_topic']}")

    if stats.get("diagnostic_messages"):
        with st.expander("🔍 Diagnose-Infos", expanded=not stats.get("daemon_healthy", True)):
            for msg in stats["diagnostic_messages"]:
                if "rot" in msg.lower() or "warn" in msg.lower():
                    st.warning(msg)
                else:
                    st.text(msg)

    st.divider()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Loops", stats.get("loops", 0))
    col2.metric("Exchanges", stats.get("total_exchanges", 0))
    col3.metric("Dreams/Sleep", stats.get("dreams", 0))
    col4.metric("Memory", stats.get("memory_count", 0))

    detail_left, detail_right = st.columns(2)
    with detail_left:
        st.markdown("### Aktive Konfiguration")
        st.markdown(f"- **Fokus:** {stats.get('focus') or config.get('focus_area', '-')}")
        st.markdown(f"- **Provider:** {stats.get('provider') or config.get('provider', '-')}")
        st.markdown(f"- **Sleep-Intervall:** {stats.get('sleep_interval_messages', 25)} Nachrichten")
        st.markdown(f"- **Pause pro Runde:** {stats.get('loop_pause_seconds', 0.5)} s")

    with detail_right:
        st.markdown("### Laufender Zustand")
        st.markdown(f"- **Fehler:** {stats.get('errors', 0)}")
        st.markdown(f"- **Seit letztem Sleep:** {stats.get('messages_since_dream', 0)} Nachrichten")
        st.markdown(f"- **Startzeit:** {(stats.get('start_time') or '-')[:19]}")
        st.markdown(f"- **Letzte Aktivität:** {stats.get('last_activity') or '-'}")

    st.divider()

    with st.expander("⚙️ Training konfigurieren", expanded=not running):
        provider_options = ["local", "vllm", "ollama", "groq", "cerebras", "nvidia"]
        default_provider = str(config.get("provider", "local"))
        provider_index = provider_options.index(default_provider) if default_provider in provider_options else 0

        with st.form("training_config_form"):
            persona = st.text_area("Trainer-Persona", value=config.get("persona", ""), height=100)
            focus_area = st.text_input("Fallback-Fokus", value=config.get("focus_area", ""))
            start_prompt = st.text_area("Start-Prompt", value=config.get("start_prompt", ""), height=100)

            c1, c2, c3 = st.columns(3)
            provider = c1.selectbox("Provider", provider_options, index=provider_index)
            timeout_seconds = c2.number_input("Timeout (Sek.)", min_value=10, max_value=600, value=int(config.get("timeout_seconds", 60)))
            sleep_interval = c3.number_input("Sleep nach X Nachrichten", min_value=5, max_value=200, value=int(config.get("sleep_interval_messages", 25)))

            c4, c5 = st.columns(2)
            loop_pause = c4.number_input("Pause zwischen Runden (Sek.)", min_value=0.0, max_value=60.0, value=float(config.get("loop_pause_seconds", 0.5)), step=0.5)
            request_pause = c5.number_input("Pause vor LLM-Calls (Sek.)", min_value=0.5, max_value=60.0, value=float(config.get("request_pause_seconds", 2.5)), step=0.5)

            model_name = st.text_input("Modellname (optional)", value=config.get("model_name") or "")
            curriculum_text = st.text_area(
                "Curriculum (Format: Thema | Minuten oder infinite)",
                value=_curriculum_to_text(config.get("curriculum", [])),
                height=180,
            )

            save_col, start_col, restart_col = st.columns(3)
            save_clicked = save_col.form_submit_button("Konfiguration speichern", use_container_width=True)
            start_clicked = start_col.form_submit_button("Mit Konfiguration starten", type="primary", use_container_width=True, disabled=running)
            restart_clicked = restart_col.form_submit_button("Neu starten", use_container_width=True, disabled=running)

        if save_clicked or start_clicked or restart_clicked:
            updated_config = {
                "persona": persona.strip() or config.get("persona"),
                "focus_area": focus_area.strip(),
                "start_prompt": start_prompt.strip() or config.get("start_prompt"),
                "provider": provider,
                "model_name": model_name.strip() or None,
                "timeout_seconds": int(timeout_seconds),
                "sleep_interval_messages": int(sleep_interval),
                "loop_pause_seconds": float(loop_pause),
                "request_pause_seconds": float(request_pause),
                "curriculum": _parse_curriculum_text(curriculum_text, focus_area),
            }
            saved_config = save_training_config(updated_config)

            if save_clicked:
                st.toast("Trainings-Konfiguration gespeichert")
                st.rerun()
            elif start_clicked:
                res = start_daemon(new=False, config_overrides=saved_config)
                st.toast(res["message"])
                st.rerun()
            elif restart_clicked:
                res = start_daemon(new=True, config_overrides=saved_config)
                st.toast(res["message"])
                st.rerun()

    if stats.get("curriculum"):
        with st.expander("📚 Aktuelles Curriculum", expanded=True):
            for index, item in enumerate(stats.get("curriculum", []), start=1):
                marker = "➡️" if item.get("topic") == stats.get("current_topic") else "•"
                st.markdown(f"{marker} **{index}. {item.get('topic', '-')}** — `{item.get('duration_minutes', 'infinite')}` Min")

    st.markdown("### Steuerung")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Training stoppen", use_container_width=True, disabled=not running):
            res = stop_daemon()
            st.toast(res["message"])
            st.rerun()
    with c2:
        if st.button("Ansicht aktualisieren", use_container_width=True):
            st.rerun()

    st.divider()

    with st.expander("Prozess-Logs", expanded=False):
        l1, l2, l3 = st.columns([2, 1, 1])
        with l1:
            lines = st.selectbox("Zeilen", [50, 100, 200, 500], index=1, label_visibility="collapsed")
        with l2:
            if st.button("Refresh", use_container_width=True):
                st.rerun()
        with l3:
            if st.button("Logs leeren", use_container_width=True):
                if clear_logs():
                    st.toast("Logs geleert")
                    st.rerun()

        st.code(get_daemon_logs(lines=lines), language="plaintext")

    st.caption("Dieses Training läuft im Hintergrund. Curriculum, Sleep-Intervall und Laufzeitverhalten lassen sich direkt hier verwalten.")
