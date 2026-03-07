import streamlit as st


def render_growth_dashboard(backend):
    """Zeigt Entwicklungsverlauf, Planung und Timeline-History."""
    status = backend.get_status()
    snapshot = status.get("life_snapshot", {})

    col1, col2 = st.columns([0.85, 0.15])
    with col1:
        st.markdown("## Growth & Timeline Dashboard")
        st.caption("Langzeitplanung, Forecasts, Social Arcs und autobiografische Verlaufsspur.")
    with col2:
        if st.button("Schließen", key="close_growth_dashboard", use_container_width=True):
            st.session_state.show_growth_dashboard = False
            st.rerun()

    if not snapshot:
        st.info("Noch keine Growth-Daten verfügbar.")
        return

    planning = snapshot.get("planning_state", {})
    forecast = snapshot.get("forecast_state", {})
    social_arc = snapshot.get("social_arc", {})
    timeline = snapshot.get("timeline_history", [])
    summary = snapshot.get("timeline_summary", {})
    development = snapshot.get("development", {})
    dynamics = snapshot.get("habit_dynamics", {})

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Planning Horizon", planning.get("planning_horizon", "---"))
    with m2:
        st.metric("Forecast Risk", forecast.get("risk_level", "---"))
    with m3:
        st.metric("Social Arc", social_arc.get("arc_name", "---"))
    with m4:
        st.metric("Timeline Entries", summary.get("entries", 0))

    plan_tab, forecast_tab, timeline_tab = st.tabs(["Planning", "Forecast & Arc", "Timeline"])

    with plan_tab:
        st.markdown("### Multi-Horizon Planning")
        st.markdown(f"- **Coordination Mode:** {planning.get('coordination_mode', '---')}")
        st.markdown(f"- **Confidence:** {planning.get('plan_confidence', 0):.2f}")
        st.markdown(f"- **Milestone:** {planning.get('next_milestone', '---')}")
        st.caption(planning.get("guidance", "---"))

        c1, c2, c3 = st.columns(3)
        for col, title, items in [
            (c1, "Immediate", planning.get("immediate_steps", [])),
            (c2, "Near Term", planning.get("near_term_steps", [])),
            (c3, "Long Term", planning.get("long_term_steps", [])),
        ]:
            with col:
                st.markdown(f"#### {title}")
                for item in items:
                    st.markdown(f"- {item}")

        if planning.get("bottlenecks"):
            st.markdown("#### Bottlenecks")
            for item in planning.get("bottlenecks", []):
                st.warning(item)

        st.divider()
        st.markdown("### Habit Dynamics")
        st.markdown(f"- **Balance Score:** {dynamics.get('balance_score', 0):.2f}")
        st.caption(dynamics.get("guidance", "---"))
        for item in dynamics.get("conflicts", []):
            st.warning(item)
        if dynamics.get("decayed_habits"):
            for item in dynamics.get("decayed_habits", [])[:4]:
                st.caption(f"Decay: {item.get('label', '---')} {item.get('from', 0):.2f} → {item.get('to', 0):.2f}")

    with forecast_tab:
        st.markdown("### Self Forecasting")
        st.markdown(f"- **Next Turn:** {forecast.get('next_turn_outlook', '---')}")
        st.markdown(f"- **Daily Outlook:** {forecast.get('daily_outlook', '---')}")
        st.markdown(f"- **Stage Trajectory:** {forecast.get('stage_trajectory', '---')}")
        st.caption(forecast.get("guidance", "---"))

        st.markdown("#### Protective Factors")
        for item in forecast.get("protective_factors", []):
            st.info(item)

        st.divider()
        st.markdown("### Social Arc")
        st.markdown(f"- **Arc Name:** {social_arc.get('arc_name', '---')}")
        st.markdown(f"- **Phase:** {social_arc.get('phase', '---')}")
        st.markdown(f"- **Arc Score:** {social_arc.get('arc_score', 0):.2f}")
        st.markdown(f"- **Episode:** {social_arc.get('current_episode', '---')}")
        st.caption(social_arc.get("guidance", "---"))

        st.divider()
        st.markdown("### Development Trend")
        st.metric("Development Score", f"{development.get('development_score', 0):.2f}")
        st.progress(development.get("progress_to_next", 0), text=f"To {development.get('next_stage', '---')}: {development.get('progress_to_next', 0):.0%}")

    with timeline_tab:
        st.markdown("### Timeline Summary")
        st.markdown(f"- **Summary:** {summary.get('summary', '---')}")
        if summary.get("stage_series"):
            st.line_chart(summary.get("stage_series"))

        st.divider()
        st.markdown("### Recent Timeline Entries")
        if timeline:
            for item in timeline[::-1][:12]:
                st.markdown(
                    f"- **{item.get('phase_label', '---')}** · {item.get('source', '---')} · "
                    f"Goal={item.get('goal', '---')} · Stage={item.get('stage', '---')} · Bond={item.get('bond', '---')} · Habit={item.get('top_habit', '---')}"
                )
                st.caption(item.get("forecast", "---"))
        else:
            st.caption("Noch keine Timeline-Einträge vorhanden.")