import streamlit as st


def render_life_dashboard(backend):
    """Rendert ein dediziertes Dashboard für CHAPPiEs innere Lebenssimulation."""
    status = backend.get_status()
    snapshot = status.get("life_snapshot", {})

    col1, col2 = st.columns([0.85, 0.15])
    with col1:
        st.markdown("## Life Dashboard")
        st.caption("Ziele, Weltmodell, autobiografisches Selbst und laufende Lebenssimulation.")
    with col2:
        if st.button("Schließen", key="close_life_dashboard", use_container_width=True):
            st.session_state.show_life_dashboard = False
            st.rerun()

    if not snapshot:
        st.info("Noch kein Life-State verfügbar.")
        return

    active_goal = snapshot.get("active_goal", {})
    development = snapshot.get("development", {})
    attachment = snapshot.get("attachment_model", {})
    replay_state = snapshot.get("replay_state", {})
    habits = snapshot.get("habits", {})
    planning = snapshot.get("planning_state", {})
    forecast = snapshot.get("forecast_state", {})
    social_arc = snapshot.get("social_arc", {})
    dominant_need = (snapshot.get("homeostasis", {}).get("dominant_need") or {}).get("name", "stability")
    world_model = snapshot.get("world_model", {})
    self_model = snapshot.get("self_model", {})

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Phase", snapshot.get("clock", {}).get("phase_label", "---"))
    with m2:
        st.metric("Aktivität", snapshot.get("current_activity", "---"))
    with m3:
        st.metric("Need-Fokus", dominant_need)
    with m4:
        st.metric("Stage", development.get("stage", "---"))

    overview_tab, goals_tab, world_tab, growth_tab, self_tab = st.tabs(["Überblick", "Goals", "World Model", "Habits & Growth", "Selbst & Erinnern"])

    with overview_tab:
        st.markdown("### Homeostasis")
        needs = snapshot.get("homeostasis", {}).get("active_needs", [])
        n_cols = st.columns(3)
        for idx, item in enumerate(needs[:6]):
            with n_cols[idx % 3]:
                st.progress(item.get("value", 0) / 100, text=f"{item.get('name', '---')}: {item.get('value', 0)}")

        st.divider()
        st.markdown("### Aktuelle Lebensdynamik")
        st.markdown(f"- **Modus:** {snapshot.get('current_mode', '---')}")
        st.markdown(f"- **Aktives Ziel:** {active_goal.get('title', '---')}")
        st.markdown(f"- **Goal Mode:** {snapshot.get('goal_competition', {}).get('goal_mode', '---')}")
        st.markdown(f"- **Entwicklungsphase:** {development.get('stage', '---')} → {development.get('next_stage', '---')}")
        st.markdown(f"- **Bindung:** {attachment.get('bond_type', '---')} | Security: {attachment.get('attachment_security', 0):.2f}")
        st.markdown(f"- **Planung:** {planning.get('planning_horizon', '---')} | {planning.get('next_milestone', '---')}")
        st.markdown(f"- **Forecast:** {forecast.get('next_turn_outlook', '---')}")
        st.markdown(f"- **Social Arc:** {social_arc.get('arc_name', '---')} | {social_arc.get('phase', '---')}")
        st.markdown(f"- **Trajectory:** {world_model.get('expected_trajectory', '---')}")
        st.markdown(f"- **Guidance:** {world_model.get('guidance', '---')}")

    with goals_tab:
        goal_competition = snapshot.get("goal_competition", {})
        st.markdown("### Goal Competition")
        st.markdown(f"- **Aktiv:** {active_goal.get('title', '---')} | Score: {active_goal.get('score', 0):.2f}")
        secondary = goal_competition.get("secondary_goal", {})
        if secondary:
            st.markdown(f"- **Sekundär:** {secondary.get('title', '---')} | Score: {secondary.get('score', 0):.2f}")
        st.markdown(f"- **Spannung:** {goal_competition.get('competition_tension', 0):.2f}")
        st.markdown(f"- **Guidance:** {goal_competition.get('guidance', '---')}")

        for goal in goal_competition.get("competition_table", []):
            with st.expander(f"{goal.get('title', '---')} · Score {goal.get('score', 0):.2f}", expanded=goal.get('title') == active_goal.get('title')):
                st.markdown(f"**Beschreibung:** {goal.get('description', '---')}")
                st.markdown(f"**Priority:** {goal.get('priority', 0):.2f}")
                st.markdown(f"**Progress:** {goal.get('progress', 0):.0%}")
                st.markdown(f"**Urgency:** {goal.get('urgency', 0):.2f}")

    with world_tab:
        st.markdown("### Predictive World Model")
        st.markdown(f"- **Interaction Mode:** {world_model.get('interaction_mode', '---')}")
        st.markdown(f"- **Predicted User Need:** {world_model.get('predicted_user_need', '---')}")
        st.markdown(f"- **Next Best Action:** {world_model.get('next_best_action', '---')}")
        st.markdown(f"- **Confidence:** {world_model.get('confidence', 0):.2f}")

        risk_col, opp_col = st.columns(2)
        with risk_col:
            st.markdown("#### Risiken")
            risks = world_model.get("risk_factors", [])
            if risks:
                for risk in risks:
                    st.warning(risk)
            else:
                st.success("Keine dominanten situativen Risiken erkannt.")
        with opp_col:
            st.markdown("#### Chancen")
            opportunities = world_model.get("opportunities", [])
            if opportunities:
                for item in opportunities:
                    st.info(item)
            else:
                st.caption("Keine besonderen Chancen erkannt.")

    with growth_tab:
        st.markdown("### Habit Engine")
        top_habits = sorted(habits.items(), key=lambda item: item[1].get("strength", 0), reverse=True)
        if top_habits:
            cols = st.columns(3)
            for idx, (name, meta) in enumerate(top_habits[:3]):
                with cols[idx % 3]:
                    st.metric(meta.get("label", name), f"{meta.get('strength', 0):.2f}")
                    st.caption(f"Count: {meta.get('count', 0)} · Trend: {meta.get('trend', 'stable')}")

            for name, meta in top_habits:
                st.progress(meta.get("strength", 0), text=f"{meta.get('label', name)} · {meta.get('strength', 0):.2f}")
        else:
            st.caption("Noch keine Gewohnheiten vorhanden.")

        st.divider()
        st.markdown("### Development Stages")
        st.markdown(f"- **Stage:** {development.get('stage', '---')}")
        st.markdown(f"- **Score:** {development.get('development_score', 0):.2f}")
        st.markdown(f"- **Next Stage:** {development.get('next_stage', '---')}")
        st.progress(development.get("progress_to_next", 0), text=f"Progress to next stage: {development.get('progress_to_next', 0):.0%}")
        for item in development.get("milestones", []):
            st.markdown(f"- {item}")
        st.caption(development.get("guidance", "---"))

        st.divider()
        st.markdown("### Attachment Model")
        st.markdown(f"- **Bond Type:** {attachment.get('bond_type', '---')}")
        st.markdown(f"- **Attachment Security:** {attachment.get('attachment_security', 0):.2f}")
        st.markdown(f"- **Resonance:** {attachment.get('resonance', 0):.2f}")
        st.markdown(f"- **Repair Needed:** {'Ja' if attachment.get('repair_needed') else 'Nein'}")
        st.caption(attachment.get("guidance", "---"))

    with self_tab:
        st.markdown("### Autobiographical Self")
        st.markdown(f"- **Identity:** {self_model.get('identity', 'CHAPPiE')}")
        st.markdown(f"- **Narrative:** {self_model.get('narrative', '---')}")
        st.markdown(f"- **Kapitel:** {self_model.get('current_chapter', '---')}")
        st.markdown(f"- **Self-Coherence:** {self_model.get('self_coherence', 0):.2f}")
        st.markdown(f"- **Letzte Reflexion:** {self_model.get('last_reflection', '---')}")

        st.divider()
        st.markdown("### Beziehung & Erinnerung")
        relationship = snapshot.get("relationship", {})
        st.markdown(f"- **Trust:** {relationship.get('trust', 0):.2f}")
        st.markdown(f"- **Closeness:** {relationship.get('closeness', 0):.2f}")
        st.markdown(f"- **Shared History:** {relationship.get('shared_history', 0):.2f}")

        events = snapshot.get("recent_events", [])
        if events:
            st.markdown("#### Jüngste Ereignisse")
            for event in events[::-1]:
                st.markdown(f"- **{event.get('title', '---')}** · {event.get('detail', '---')}")

        dreams = snapshot.get("dream_fragments", [])
        if dreams:
            st.markdown("#### Dream Replay")
            for fragment in dreams:
                st.caption(fragment)

        if replay_state:
            st.divider()
            st.markdown("### Replay / Konsolidierung")
            st.markdown(f"- **Summary:** {replay_state.get('summary', '---')}")
            st.markdown(f"- **Habit Reinforcement:** {replay_state.get('habit_reinforcement', '---')}")
            st.markdown(f"- **Development Reflection:** {replay_state.get('development_reflection', '---')}")
            themes = replay_state.get("themes", [])
            if themes:
                st.markdown("- **Themes:** " + ", ".join(themes))