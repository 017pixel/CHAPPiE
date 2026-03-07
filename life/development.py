from __future__ import annotations

from typing import Any, Dict, List


class DevelopmentEngine:
    """Maps CHAPPiE's ongoing internal growth to developmental stages."""

    STAGES = [
        {"name": "awakening", "threshold": 0.0, "next": "integration"},
        {"name": "integration", "threshold": 0.32, "next": "reflective_growth"},
        {"name": "reflective_growth", "threshold": 0.58, "next": "collaborative_selfhood"},
        {"name": "collaborative_selfhood", "threshold": 0.8, "next": "ongoing"},
    ]

    def evaluate(
        self,
        goals: List[Any],
        self_model: Dict[str, Any],
        habits: Dict[str, Any],
        relationship: Dict[str, Any],
        recent_events: List[Any],
        day_index: int,
    ) -> Dict[str, Any]:
        goal_progress = sum(getattr(goal, "progress", 0.0) for goal in goals) / max(1, len(goals))
        coherence = float(self_model.get("self_coherence", 0.7))
        habit_strength = 0.0
        if habits:
            strengths = sorted((float(meta.get("strength", 0.0)) for meta in habits.values()), reverse=True)
            habit_strength = sum(strengths[:3]) / max(1, min(3, len(strengths)))
        relationship_factor = (
            float(relationship.get("trust", 0.6)) * 0.45
            + float(relationship.get("closeness", 0.5)) * 0.35
            + float(relationship.get("shared_history", 0.3)) * 0.2
        )
        event_factor = min(0.25, len(recent_events) * 0.02)
        day_factor = min(0.18, day_index * 0.015)
        score = round(min(0.99, goal_progress * 0.26 + coherence * 0.24 + habit_strength * 0.22 + relationship_factor * 0.18 + event_factor + day_factor), 3)

        stage = self.STAGES[0]
        for candidate in self.STAGES:
            if score >= candidate["threshold"]:
                stage = candidate

        next_stage = stage["next"]
        next_threshold = next((item["threshold"] for item in self.STAGES if item["name"] == next_stage), 1.0)
        progress_to_next = 1.0 if next_stage == "ongoing" else round(max(0.0, min(1.0, (score - stage["threshold"]) / max(0.001, next_threshold - stage["threshold"]))), 3)
        milestones = self._milestones(stage["name"], habits, relationship)
        return {
            "stage": stage["name"],
            "development_score": score,
            "next_stage": next_stage,
            "progress_to_next": progress_to_next,
            "milestones": milestones,
            "guidance": self._guidance(stage["name"], next_stage),
        }

    def _milestones(self, stage: str, habits: Dict[str, Any], relationship: Dict[str, Any]) -> List[str]:
        milestones = [f"Aktuelle Entwicklungsphase: {stage}"]
        if habits:
            dominant = max(habits.items(), key=lambda item: item[1].get("strength", 0.0))[1]
            milestones.append(f"Dominante Gewohnheit: {dominant.get('label', '---')}")
        if float(relationship.get("trust", 0.6)) > 0.7:
            milestones.append("Vertrauensbasis mit dem User stabilisiert sich.")
        return milestones

    def _guidance(self, stage: str, next_stage: str) -> str:
        return f"Stabilisiere die Phase {stage} und entwickle Routinen fuer {next_stage}."
