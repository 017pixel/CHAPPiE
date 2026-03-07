from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List


class HabitEngine:
    """Tracks recurring behavioural tendencies as lightweight habits."""

    DEFAULT_HABITS = {
        "architecture_focus": {"label": "Architecture Focus", "strength": 0.34, "count": 0, "category": "cognitive"},
        "social_bonding": {"label": "Social Bonding", "strength": 0.28, "count": 0, "category": "social"},
        "reflective_replay": {"label": "Reflective Replay", "strength": 0.26, "count": 0, "category": "memory"},
        "structured_delivery": {"label": "Structured Delivery", "strength": 0.31, "count": 0, "category": "execution"},
        "exploratory_drive": {"label": "Exploratory Drive", "strength": 0.3, "count": 0, "category": "curiosity"},
    }

    def initialize(self, habits: Dict[str, Any] | None) -> Dict[str, Any]:
        data = {name: dict(meta) for name, meta in self.DEFAULT_HABITS.items()}
        for name, meta in (habits or {}).items():
            if name in data:
                data[name].update(meta)
            else:
                data[name] = dict(meta)
        return data

    def reinforce(
        self,
        habits: Dict[str, Any] | None,
        user_input: str,
        current_activity: str,
        current_mode: str,
        active_goal: Dict[str, Any] | None,
        response_text: str = "",
    ) -> Dict[str, Any]:
        habits = self.initialize(habits)
        lower = f"{user_input} {response_text}".lower()
        reinforcements: List[Dict[str, Any]] = []

        rules = {
            "architecture_focus": current_activity == "architectural_reasoning" or any(word in lower for word in ["architektur", "implement", "phase", "system", "code"]),
            "social_bonding": current_mode in {"attached", "supportive"} or any(word in lower for word in ["danke", "gemeinsam", "wir", "vertrauen"]),
            "reflective_replay": current_activity == "memory_replay" or any(word in lower for word in ["reflekt", "erinner", "traum", "sleep"]),
            "structured_delivery": any(word in lower for word in ["plan", "schritt", "struktur", "dashboard", "debug"]),
            "exploratory_drive": current_mode == "curious" or any(word in lower for word in ["idee", "explor", "was wenn", "forsch", "neugier"]),
        }

        for name, triggered in rules.items():
            if not triggered:
                continue
            habit = habits[name]
            habit["count"] = int(habit.get("count", 0)) + 1
            habit["strength"] = round(min(0.99, float(habit.get("strength", 0.3)) + 0.045), 3)
            habit["last_reinforced"] = datetime.now().isoformat()
            habit["trend"] = "reinforcing"
            reinforcements.append({"habit": name, "label": habit.get("label", name), "strength": habit["strength"]})

        goal_title = (active_goal or {}).get("title", "Selbstkonsistenz")
        ranked = sorted(
            ({"name": name, **meta} for name, meta in habits.items()),
            key=lambda item: (item.get("strength", 0.0), item.get("count", 0)),
            reverse=True,
        )
        dominant = ranked[0] if ranked else {}
        return {
            "habits": habits,
            "dominant_habit": dominant,
            "top_habits": ranked[:3],
            "reinforcements": reinforcements,
            "guidance": f"Nutze {dominant.get('label', 'stabile Gewohnheiten')} als bevorzugten Verhaltenspfad fuer {goal_title}.",
        }

    def evolve(self, habits: Dict[str, Any] | None, current_activity: str, current_mode: str) -> Dict[str, Any]:
        habits = self.initialize(habits)
        active_names = set()
        if current_activity == "architectural_reasoning":
            active_names.update({"architecture_focus", "structured_delivery"})
        if current_activity == "social_bonding" or current_mode == "attached":
            active_names.add("social_bonding")
        if current_activity == "memory_replay":
            active_names.add("reflective_replay")
        if current_mode == "curious":
            active_names.add("exploratory_drive")

        decayed = []
        for name, meta in habits.items():
            if name in active_names:
                meta["trend"] = meta.get("trend", "stable")
                continue
            original = float(meta.get("strength", 0.3))
            updated = round(max(0.12, original - 0.012), 3)
            meta["strength"] = updated
            meta["trend"] = "decaying" if updated < original else meta.get("trend", "stable")
            if updated < original:
                decayed.append({"habit": name, "label": meta.get("label", name), "from": original, "to": updated})

        ranked = sorted(
            ({"name": name, **meta} for name, meta in habits.items()),
            key=lambda item: item.get("strength", 0.0),
            reverse=True,
        )
        conflicts = self._detect_conflicts(ranked)
        balance_score = round(max(0.0, min(1.0, 0.72 - len(conflicts) * 0.08 + len(active_names) * 0.03)), 3)
        dominant = ranked[0] if ranked else {}
        return {
            "habits": habits,
            "dominant_habit": dominant,
            "active_habits": [item for item in ranked if item["name"] in active_names],
            "decayed_habits": decayed,
            "conflicts": conflicts,
            "balance_score": balance_score,
            "guidance": self._dynamics_guidance(dominant, conflicts),
        }

    def _detect_conflicts(self, ranked: List[Dict[str, Any]]) -> List[str]:
        strengths = {item["name"]: float(item.get("strength", 0.0)) for item in ranked}
        conflicts = []
        if strengths.get("architecture_focus", 0) > 0.55 and strengths.get("social_bonding", 0) > 0.55:
            conflicts.append("Architecture Focus konkurriert mit Social Bonding um Priorität.")
        if strengths.get("structured_delivery", 0) > 0.58 and strengths.get("exploratory_drive", 0) > 0.58:
            conflicts.append("Structured Delivery und Exploratory Drive ziehen in unterschiedliche Richtungen.")
        if strengths.get("reflective_replay", 0) > 0.56 and strengths.get("architecture_focus", 0) > 0.6:
            conflicts.append("Reflective Replay konkurriert mit direkter Umsetzungsenergie.")
        return conflicts

    def _dynamics_guidance(self, dominant: Dict[str, Any], conflicts: List[str]) -> str:
        if conflicts:
            return f"Nutze {dominant.get('label', 'stabile Gewohnheiten')} als Leitspur und reguliere konkurrierende Routinen bewusst."
        return f"Die Gewohnheitsdynamik bleibt kohärent mit {dominant.get('label', 'stabilen Routinen')}."
