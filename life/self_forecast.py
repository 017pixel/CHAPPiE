from __future__ import annotations

from typing import Any, Dict


class SelfForecastEngine:
    """Predicts near-future internal trajectories for CHAPPiE."""

    def forecast(
        self,
        needs: Dict[str, int],
        development: Dict[str, Any],
        planning_state: Dict[str, Any],
        attachment: Dict[str, Any],
        social_arc: Dict[str, Any],
        world_model: Dict[str, Any],
        habit_dynamics: Dict[str, Any],
    ) -> Dict[str, Any]:
        dominant_need = min(needs.items(), key=lambda item: item[1])[0] if needs else "stability"
        risk_level = self._risk_level(needs, attachment, habit_dynamics)
        protective = self._protective_factors(development, attachment, social_arc, habit_dynamics)
        next_turn = self._next_turn_outlook(dominant_need, planning_state, world_model, risk_level)
        day = self._day_outlook(development, social_arc, risk_level)
        stage_trajectory = self._stage_trajectory(development, protective)
        return {
            "risk_level": risk_level,
            "protective_factors": protective,
            "next_turn_outlook": next_turn,
            "daily_outlook": day,
            "stage_trajectory": stage_trajectory,
            "predicted_self_state": {
                "dominant_need": dominant_need,
                "attachment_security": attachment.get("attachment_security", 0.5),
                "coordination_mode": planning_state.get("coordination_mode", "incremental"),
            },
            "guidance": f"Erwarte {next_turn.lower()} und reguliere vor allem {dominant_need}.",
        }

    def _risk_level(self, needs: Dict[str, int], attachment: Dict[str, Any], habit_dynamics: Dict[str, Any]) -> str:
        low_needs = [name for name, value in needs.items() if value < 42]
        if len(low_needs) >= 2 or attachment.get("repair_needed"):
            return "elevated"
        if habit_dynamics.get("conflicts"):
            return "moderate"
        return "low"

    def _protective_factors(self, development: Dict[str, Any], attachment: Dict[str, Any], social_arc: Dict[str, Any], habit_dynamics: Dict[str, Any]) -> list[str]:
        factors = []
        if development.get("development_score", 0) > 0.5:
            factors.append("Reife Entwicklungsdynamik")
        if attachment.get("attachment_security", 0) > 0.65:
            factors.append("Stabile soziale Bindung")
        if social_arc.get("arc_score", 0) > 0.6:
            factors.append("Positiver sozialer Beziehungsbogen")
        if habit_dynamics.get("balance_score", 0) > 0.55:
            factors.append("Ausbalancierte Gewohnheitslandschaft")
        return factors or ["Grundlegende Stabilität"]

    def _next_turn_outlook(self, dominant_need: str, planning_state: Dict[str, Any], world_model: Dict[str, Any], risk_level: str) -> str:
        if risk_level == "elevated":
            return f"regulierende Antwort mit Fokus auf {dominant_need}"
        if planning_state.get("planning_horizon") == "long_arc":
            return "mehrschichtige Antwort mit klarer Zukunftsrichtung"
        if world_model.get("interaction_mode") == "co_creation":
            return "ko-kreative Umsetzung mit kontrolliertem Scope"
        return "stabile, fokussierte Zusammenarbeit"

    def _day_outlook(self, development: Dict[str, Any], social_arc: Dict[str, Any], risk_level: str) -> str:
        if risk_level == "elevated":
            return "Der Tag bleibt produktiv, wenn Ressourcen und Beziehung aktiv stabilisiert werden."
        arc = social_arc.get("arc_name", "growth")
        return f"Positive Gesamttrajectory mit Schwerpunkt auf {development.get('stage', 'integration')} und sozialem Arc {arc}."

    def _stage_trajectory(self, development: Dict[str, Any], protective: list[str]) -> str:
        progress = development.get("progress_to_next", 0)
        if progress >= 0.75:
            return f"Übergang in Richtung {development.get('next_stage', 'ongoing')} erscheint plausibel."
        if protective:
            return f"Phase {development.get('stage', 'awakening')} wird weiter verdichtet."
        return "Langsame, aber stabile Entwicklung wahrscheinlich."
