from __future__ import annotations

from typing import Any, Dict, List


class WorldModel:
    """Builds a compact predictive model of the current interaction."""

    def predict(
        self,
        user_input: str,
        history: List[Dict[str, Any]] | None,
        emotions: Dict[str, int],
        homeostasis: Dict[str, Any],
        goal_competition: Dict[str, Any],
        relationship: Dict[str, Any],
    ) -> Dict[str, Any]:
        lower = (user_input or "").lower()
        interaction_mode = self._classify_interaction(lower)
        user_need = self._predict_user_need(lower)
        risk_factors = self._collect_risks(lower, emotions, homeostasis)
        opportunities = self._collect_opportunities(lower, goal_competition)
        next_action = self._next_best_action(interaction_mode, user_need, risk_factors, goal_competition)
        confidence = self._confidence(history or [], risk_factors, relationship)
        expected_trajectory = self._trajectory(risk_factors, goal_competition, relationship)
        return {
            "interaction_mode": interaction_mode,
            "predicted_user_need": user_need,
            "risk_factors": risk_factors,
            "opportunities": opportunities,
            "next_best_action": next_action,
            "confidence": confidence,
            "expected_trajectory": expected_trajectory,
            "guidance": self._guidance(user_need, next_action, risk_factors),
        }

    def _classify_interaction(self, lower: str) -> str:
        if any(word in lower for word in ["implement", "architektur", "code", "phase", "plan"]):
            return "co_creation"
        if any(word in lower for word in ["hilfe", "problem", "fehler", "warum"]):
            return "support"
        if any(word in lower for word in ["idee", "brainstorm", "was wenn"]):
            return "exploration"
        return "conversation"

    def _predict_user_need(self, lower: str) -> str:
        if any(word in lower for word in ["implement", "umsetzen", "baue", "phase"]):
            return "konkrete Umsetzung"
        if any(word in lower for word in ["erklaer", "warum", "wie"]):
            return "Verstaendnis und Orientierung"
        if any(word in lower for word in ["idee", "vision", "architektur"]):
            return "strategische Exploration"
        return "stabile Zusammenarbeit"

    def _collect_risks(self, lower: str, emotions: Dict[str, int], homeostasis: Dict[str, Any]) -> List[str]:
        risks = []
        dominant_need = (homeostasis.get("dominant_need") or {}).get("name")
        if dominant_need in {"energy", "rest"}:
            risks.append("Innere Ressourcen sinken und koennten die Antwortqualitaet destabilisieren.")
        if emotions.get("frustration", 0) >= 40:
            risks.append("Erhoehte Frustration koennte zu defensiver oder zu enger Planung fuehren.")
        if any(word in lower for word in ["schnell", "sofort", "alles"]):
            risks.append("Breiter Scope koennte die Implementierung unnoetig riskant machen.")
        return risks

    def _collect_opportunities(self, lower: str, goal_competition: Dict[str, Any]) -> List[str]:
        opportunities = []
        active = goal_competition.get("active_goal", {})
        if active.get("title") == "Kognitive Entwicklung":
            opportunities.append("Die Interaktion eignet sich fuer echten Architekturfortschritt.")
        if any(word in lower for word in ["debug", "ui", "dashboard"]):
            opportunities.append("Neue innere Zustandsdaten koennen direkt sichtbar gemacht werden.")
        if any(word in lower for word in ["naechste phase", "phase"]):
            opportunities.append("Die Arbeit kann in sauberen evolutionaeren Schritten fortgesetzt werden.")
        return opportunities

    def _next_best_action(self, interaction_mode: str, user_need: str, risk_factors: List[str], goal_competition: Dict[str, Any]) -> str:
        active_goal = goal_competition.get("active_goal", {}).get("title", "Stabilisierung")
        if risk_factors:
            return f"Liefere fokussierte Umsetzungsschritte, aber halte den Scope kontrolliert. Aktives Ziel: {active_goal}."
        if interaction_mode == "co_creation":
            return f"Implementiere die naechste Architektur-Schicht gezielt fuer {active_goal}."
        return f"Stimme die Antwort auf {user_need} ab und stabilisiere dabei {active_goal}."

    def _confidence(self, history: List[Dict[str, Any]], risk_factors: List[str], relationship: Dict[str, Any]) -> float:
        trust = float(relationship.get("trust", 0.6))
        history_factor = min(0.12, len(history) * 0.01)
        risk_penalty = min(0.2, len(risk_factors) * 0.06)
        return round(max(0.35, min(0.95, 0.62 + trust * 0.18 + history_factor - risk_penalty)), 3)

    def _trajectory(self, risk_factors: List[str], goal_competition: Dict[str, Any], relationship: Dict[str, Any]) -> str:
        active_goal = goal_competition.get("active_goal", {}).get("title", "Stabilisierung")
        if risk_factors:
            return f"Stabiler Fortschritt moeglich, wenn Scope begrenzt bleibt und {active_goal} priorisiert wird."
        closeness = float(relationship.get("closeness", 0.5))
        if closeness > 0.55:
            return f"Hohe Chance auf vertieften kooperativen Fortschritt rund um {active_goal}."
        return f"Moderater, aber positiver Fortschritt in Richtung {active_goal}."

    def _guidance(self, user_need: str, next_action: str, risk_factors: List[str]) -> str:
        risk_note = " Risiken aktiv mitdenken." if risk_factors else " Niedriges situatives Risiko."
        return f"User braucht vermutlich {user_need}. {next_action}{risk_note}"