from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List


class HistoryEngine:
    """Maintains a compact autobiographical timeline of development."""

    MAX_HISTORY = 72

    def record(self, history: List[Dict[str, Any]] | None, snapshot: Dict[str, Any], source: str) -> List[Dict[str, Any]]:
        items = list(history or [])
        dominant_need = (snapshot.get("homeostasis", {}).get("dominant_need") or {}).get("name", "stability")
        active_goal = snapshot.get("active_goal", {}).get("title", "Selbstkonsistenz")
        development = snapshot.get("development", {})
        attachment = snapshot.get("attachment_model", {})
        forecast = snapshot.get("forecast_state", {})
        top_habit = self._top_habit(snapshot.get("habits", {}))
        items.append(
            {
                "timestamp": datetime.now().isoformat(),
                "source": source,
                "phase_label": snapshot.get("clock", {}).get("phase_label", "---"),
                "activity": snapshot.get("current_activity", "---"),
                "goal": active_goal,
                "dominant_need": dominant_need,
                "stage": development.get("stage", "awakening"),
                "bond": attachment.get("bond_type", "cautious_alignment"),
                "top_habit": top_habit,
                "forecast": forecast.get("next_turn_outlook", "---"),
                "development_score": development.get("development_score", 0),
            }
        )
        return items[-self.MAX_HISTORY :]

    def summarize(self, history: List[Dict[str, Any]] | None) -> Dict[str, Any]:
        items = list(history or [])
        if not items:
            return {"entries": 0, "stage_series": [], "goal_series": [], "summary": "Noch keine Timeline-History vorhanden."}
        stage_series = [round(float(item.get("development_score", 0)), 3) for item in items[-12:]]
        goal_series = [item.get("goal", "---") for item in items[-8:]]
        latest = items[-1]
        return {
            "entries": len(items),
            "stage_series": stage_series,
            "goal_series": goal_series,
            "summary": f"{len(items)} Timeline-Einträge. Letzter Fokus: {latest.get('goal', '---')} bei Phase {latest.get('stage', '---')}.",
        }

    def _top_habit(self, habits: Dict[str, Any]) -> str:
        if not habits:
            return "stability"
        name, meta = max(habits.items(), key=lambda item: item[1].get("strength", 0.0))
        return meta.get("label", name)