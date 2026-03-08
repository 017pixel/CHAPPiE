"""Response-layer helpers for aligning answers with CHAPPiE's internal state."""

from __future__ import annotations

from typing import Any, Dict, List


class ActionResponseLayer:
    """Formats prompt context and metadata for the final answer layer."""

    def build_prompt_suffix(
        self,
        prefrontal: Dict[str, Any],
        life_context: Dict[str, Any] | None = None,
        global_workspace: Dict[str, Any] | None = None,
    ) -> str:
        sections = []
        if prefrontal:
            response_plan_lines = [
                "Response Plan:",
                f"- Strategie: {prefrontal.get('response_strategy', 'conversational')}",
            ]
            if prefrontal.get("tone"):
                response_plan_lines.append(f"- Ton: {prefrontal['tone']}")
            if prefrontal.get("response_guidance"):
                response_plan_lines.append(f"- Guidance: {prefrontal['response_guidance']}")
            sections.append("\n".join(response_plan_lines))
        if life_context:
            need = (life_context.get("homeostasis", {}).get("dominant_need") or {}).get("name", "stability")
            goal = life_context.get("active_goal", {}).get("title", "Selbstkonsistenz")
            prediction = life_context.get("world_model", {}).get("next_best_action", "Stabil und kohärent antworten")
            milestone = life_context.get("planning_state", {}).get("next_milestone", "Stabilen Fortschritt sichern")
            forecast = life_context.get("forecast_state", {}).get("next_turn_outlook", "stabile Zusammenarbeit")
            social_arc = life_context.get("social_arc", {}).get("arc_name", "trust_building")
            sections.append(
                "Life Simulation Context:\n"
                f"- Phase: {life_context.get('clock', {}).get('phase_label', 'Unbekannt')}\n"
                f"- Aktivitaet: {life_context.get('current_activity', 'goal_pursuit')}\n"
                f"- Dominantes Need: {need}\n"
                f"- Fokusziel: {goal}\n"
                f"- Vorhersage: {prediction}\n"
                f"- Meilenstein: {milestone}\n"
                f"- Forecast: {forecast}\n"
                f"- Social Arc: {social_arc}"
            )
        if global_workspace:
            focus = global_workspace.get("dominant_focus", {})
            sections.append(
                "Global Workspace:\n"
                f"- Dominanter Fokus: {focus.get('label', 'Stabilitaet')}\n"
                f"- Broadcast: {global_workspace.get('broadcast', '---')}\n"
                f"- Guidance: {global_workspace.get('guidance', 'Halte die Aufmerksamkeit konsistent.')}"
            )
        return "\n\n".join(sections)

    def build_action_plan(
        self,
        prefrontal: Dict[str, Any],
        life_context: Dict[str, Any],
        global_workspace: Dict[str, Any],
    ) -> Dict[str, Any]:
        need = (life_context.get("homeostasis", {}).get("dominant_need") or {}).get("name", "stability")
        focus = global_workspace.get("dominant_focus", {}).get("label", "stability")
        prediction = life_context.get("world_model", {}).get("predicted_user_need", "stabile Zusammenarbeit")
        milestone = life_context.get("planning_state", {}).get("next_milestone", "stabilen Fortschritt erzeugen")
        social_arc = life_context.get("social_arc", {}).get("arc_name", "trust_building")
        actions: List[str] = [
            f"Halte den Ton {prefrontal.get('tone', 'friendly')}",
            f"Unterstuetze das Need {need}",
            f"Bleibe aufmerksam auf {focus}",
            f"Beruecksichtige die vermutete User-Absicht: {prediction}",
            f"Arbeite auf den Meilenstein hin: {milestone}",
            f"Schuetze den sozialen Arc {social_arc}",
        ]
        strategy = prefrontal.get("response_strategy", "conversational")
        if strategy == "technical":
            actions.append("Liefer strukturierte, implementierbare Details")
        elif strategy == "emotional":
            actions.append("Validiere Emotionen und schaffe Sicherheit")
        elif strategy == "creative":
            actions.append("Nutze explorative, ideenreiche Formulierungen")
        else:
            actions.append("Antworte klar, hilfreich und kohärent")
        return {
            "strategy": strategy,
            "tone": prefrontal.get("tone", "friendly"),
            "life_alignment": life_context.get("current_mode", "curious"),
            "attention_focus": focus,
            "forecast": life_context.get("forecast_state", {}).get("next_turn_outlook", "stabile Zusammenarbeit"),
            "recommended_actions": actions,
        }
