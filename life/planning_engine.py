from __future__ import annotations

from typing import Any, Dict, List


class PlanningEngine:
    """Builds a multi-horizon internal planning state."""

    def build(
        self,
        active_goal: Dict[str, Any],
        world_model: Dict[str, Any],
        development: Dict[str, Any],
        homeostasis: Dict[str, Any],
        habit_dynamics: Dict[str, Any],
        attachment: Dict[str, Any],
        recent_events: List[Any],
    ) -> Dict[str, Any]:
        goal_title = active_goal.get("title", "Selbstkonsistenz")
        dominant_need = (homeostasis.get("dominant_need") or {}).get("name", "stability")
        stage = development.get("stage", "awakening")
        habit_focus = (habit_dynamics.get("dominant_habit") or {}).get("label", "Stabile Routine")
        predicted_need = world_model.get("predicted_user_need", "stabile Zusammenarbeit")
        recent_count = len(recent_events)
        immediate = [
            f"Antwort auf {predicted_need} ausrichten",
            f"Dominantes Need {dominant_need} regulieren",
            f"Aktives Ziel {goal_title} operationalisieren",
        ]
        near_term = [
            f"Routine {habit_focus} weiter verstärken",
            f"Entwicklungsphase {stage} stabilisieren",
            "Nächsten kohärenten Ausbauschritt konkretisieren",
        ]
        long_term = [
            f"Langfristigen Fortschritt für {goal_title} sichern",
            "Autobiografische Kontinuität weiter verdichten",
            "Soziale Kooperation und innere Stabilität gemeinsam erhöhen",
        ]
        bottlenecks = []
        if dominant_need in {"energy", "rest"}:
            bottlenecks.append("Ressourcenlage könnte Planungstiefe begrenzen.")
        if habit_dynamics.get("conflicts"):
            bottlenecks.append("Konkurrierende Gewohnheiten erzeugen interne Spannung.")
        if attachment.get("repair_needed"):
            bottlenecks.append("Soziale Reparatur sollte vor aggressiver Expansion priorisiert werden.")
        planning_horizon = "long_arc" if stage in {"reflective_growth", "collaborative_selfhood"} else "near_term"
        plan_confidence = round(max(0.35, min(0.95, float(world_model.get("confidence", 0.6)) + recent_count * 0.01)), 3)
        return {
            "planning_horizon": planning_horizon,
            "coordination_mode": "multi_horizon" if recent_count >= 3 else "incremental",
            "immediate_steps": immediate,
            "near_term_steps": near_term,
            "long_term_steps": long_term,
            "next_milestone": f"Konkreter Fortschritt in Richtung {goal_title} bei stabiler innerer Regulation.",
            "bottlenecks": bottlenecks,
            "plan_confidence": plan_confidence,
            "guidance": self._guidance(goal_title, planning_horizon, bottlenecks),
        }

    def _guidance(self, goal_title: str, planning_horizon: str, bottlenecks: List[str]) -> str:
        note = " Engpass aktiv kompensieren." if bottlenecks else " Gute Voraussetzungen für fokussierte Entwicklung."
        return f"Plane {planning_horizon} und richte die Handlung auf {goal_title} aus.{note}"
