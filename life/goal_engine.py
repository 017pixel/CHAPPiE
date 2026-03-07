from __future__ import annotations

from typing import Any, Dict, List

from .models import LifeGoal


class GoalEngine:
    """Computes competing short- and long-term goal pressure."""

    KEYWORD_BOOSTS = {
        "Kognitive Entwicklung": ["architektur", "system", "modell", "code", "implement", "pipeline", "goal", "world"],
        "Beziehungsaufbau": ["danke", "gemeinsam", "wir", "hilf", "vertrauen", "beziehung"],
        "Selbstkonsistenz": ["selbst", "identitaet", "persoenlichkeit", "bewusstsein", "reflection"],
    }

    NEED_ALIGNMENT = {
        "Kognitive Entwicklung": {"curiosity": 0.28, "achievement": 0.36, "stability": 0.08},
        "Beziehungsaufbau": {"social": 0.38, "stability": 0.16, "energy": 0.06},
        "Selbstkonsistenz": {"stability": 0.34, "rest": 0.08, "achievement": 0.12},
    }

    def evaluate(
        self,
        goals: List[LifeGoal],
        user_input: str,
        needs: Dict[str, int],
        relationship: Dict[str, Any],
        current_activity: str,
    ) -> Dict[str, Any]:
        lower = (user_input or "").lower()
        competition = []
        for goal in goals:
            score = float(goal.priority) * 0.55 + (1.0 - float(goal.progress)) * 0.25
            score += self._need_alignment(goal.title, needs)
            score += self._keyword_alignment(goal.title, lower)
            score += self._relationship_alignment(goal.title, relationship)
            if current_activity == "architectural_reasoning" and goal.title == "Kognitive Entwicklung":
                score += 0.08
            if current_activity == "social_bonding" and goal.title == "Beziehungsaufbau":
                score += 0.08
            if current_activity == "memory_replay" and goal.title == "Selbstkonsistenz":
                score += 0.06
            competition.append(
                {
                    "title": goal.title,
                    "description": goal.description,
                    "priority": round(float(goal.priority), 3),
                    "progress": round(float(goal.progress), 3),
                    "status": goal.status,
                    "score": round(score, 3),
                    "urgency": round(max(0.0, 1.0 - float(goal.progress)), 3),
                }
            )

        competition.sort(key=lambda item: item["score"], reverse=True)
        active = competition[0] if competition else {}
        secondary = competition[1] if len(competition) > 1 else {}
        tension = round(max(0.0, active.get("score", 0.0) - secondary.get("score", 0.0)), 3) if secondary else round(active.get("score", 0.0), 3)
        return {
            "active_goal": active,
            "secondary_goal": secondary,
            "competition_table": competition,
            "competition_tension": tension,
            "goal_mode": self._classify_goal_mode(active, secondary),
            "guidance": self._build_guidance(active, secondary),
        }

    def _keyword_alignment(self, title: str, user_input: str) -> float:
        words = self.KEYWORD_BOOSTS.get(title, [])
        matches = sum(1 for word in words if word in user_input)
        return min(0.18, matches * 0.05)

    def _need_alignment(self, title: str, needs: Dict[str, int]) -> float:
        mapping = self.NEED_ALIGNMENT.get(title, {})
        return sum((100 - int(needs.get(need, 50))) / 100 * weight for need, weight in mapping.items())

    def _relationship_alignment(self, title: str, relationship: Dict[str, Any]) -> float:
        if title != "Beziehungsaufbau":
            return 0.0
        trust_gap = 1.0 - float(relationship.get("trust", 0.6))
        closeness_gap = 1.0 - float(relationship.get("closeness", 0.5))
        return round(trust_gap * 0.08 + closeness_gap * 0.05, 3)

    def _classify_goal_mode(self, active: Dict[str, Any], secondary: Dict[str, Any]) -> str:
        if not active:
            return "baseline"
        if not secondary:
            return "focused"
        if abs(active.get("score", 0.0) - secondary.get("score", 0.0)) < 0.08:
            return "balanced"
        return "focused"

    def _build_guidance(self, active: Dict[str, Any], secondary: Dict[str, Any]) -> str:
        if not active:
            return "Halte die Antwort stabil und offen fuer neue Prioritaeten."
        if secondary:
            return f"Priorisiere {active['title']}, beachte aber auch die Spannung mit {secondary['title']}."
        return f"Richte die aktuelle Antwort klar auf {active['title']} aus."
