"""Deterministic attention and global workspace selection."""

from __future__ import annotations

from typing import Any, Dict, List


class GlobalWorkspace:
    """Combines multiple signals into a conscious attention broadcast."""

    def build(
        self,
        sensory: Dict[str, Any],
        amygdala: Dict[str, Any],
        hippocampus: Dict[str, Any],
        life_context: Dict[str, Any],
        memories: List[Any],
    ) -> Dict[str, Any]:
        items = []
        need = (life_context.get("homeostasis", {}).get("dominant_need") or {})
        if need:
            items.append({
                "source": "homeostasis",
                "label": f"Need: {need.get('name', 'stability')}",
                "content": life_context.get("homeostasis", {}).get("guidance", ""),
                "salience": round(min(1.0, need.get("pressure", 0) / 100), 3),
            })

        emotional_intensity = float(amygdala.get("emotional_intensity", 0.25) or 0.25)
        items.append({
            "source": "emotion",
            "label": amygdala.get("primary_emotion", "neutral"),
            "content": amygdala.get("reasoning", "Emotionale Lage beeinflusst die Antwort."),
            "salience": round(min(1.0, emotional_intensity), 3),
        })

        urgency_map = {"low": 0.25, "medium": 0.55, "high": 0.82, "critical": 0.95}
        items.append({
            "source": "sensory",
            "label": sensory.get("input_type", "conversation"),
            "content": f"Urgency={sensory.get('urgency', 'medium')}",
            "salience": urgency_map.get(str(sensory.get("urgency", "medium")).lower(), 0.55),
        })

        if memories:
            items.append({
                "source": "memory",
                "label": "Relevant memories",
                "content": f"{len(memories)} Erinnerungen stehen zur Verfuegung.",
                "salience": round(min(0.92, 0.38 + len(memories) * 0.08), 3),
            })

        search_query = hippocampus.get("search_query")
        if search_query:
            items.append({
                "source": "hippocampus",
                "label": "Memory retrieval",
                "content": search_query,
                "salience": 0.62,
            })

        goal = life_context.get("active_goal", {})
        if goal:
            items.append({
                "source": "goal",
                "label": goal.get("title", "Selbsterhaltung"),
                "content": goal.get("description", ""),
                "salience": round(min(0.96, float(goal.get("priority", 0.7)) * (1.15 - float(goal.get("progress", 0.0)))), 3),
            })

        world_model = life_context.get("world_model", {})
        if world_model:
            items.append({
                "source": "world_model",
                "label": world_model.get("predicted_user_need", "Stabile Zusammenarbeit"),
                "content": world_model.get("next_best_action", "Halte den Dialog kohärent."),
                "salience": round(min(0.9, float(world_model.get("confidence", 0.6)) + len(world_model.get("risk_factors", [])) * 0.05), 3),
            })

        planning = life_context.get("planning_state", {})
        if planning:
            items.append({
                "source": "planning",
                "label": planning.get("planning_horizon", "near_term"),
                "content": planning.get("next_milestone", "Kohärenten Fortschritt sichern."),
                "salience": round(min(0.88, float(planning.get("plan_confidence", 0.55)) + len(planning.get("bottlenecks", [])) * 0.04), 3),
            })

        forecast = life_context.get("forecast_state", {})
        if forecast:
            items.append({
                "source": "forecast",
                "label": forecast.get("risk_level", "low"),
                "content": forecast.get("next_turn_outlook", "Stabile Zusammenarbeit."),
                "salience": 0.66 if forecast.get("risk_level") == "low" else 0.79,
            })

        social_arc = life_context.get("social_arc", {})
        if social_arc:
            items.append({
                "source": "social_arc",
                "label": social_arc.get("arc_name", "trust_building"),
                "content": social_arc.get("guidance", "Pflege die Beziehung konsistent."),
                "salience": round(min(0.84, float(social_arc.get("arc_score", 0.5)) + 0.14), 3),
            })

        items.sort(key=lambda item: item["salience"], reverse=True)
        dominant = items[0] if items else {"source": "baseline", "label": "stability", "salience": 0.5, "content": ""}
        guidance = self._build_guidance(dominant, life_context)
        return {
            "workspace_items": items[:5],
            "dominant_focus": dominant,
            "attention_mode": life_context.get("current_mode", "curious"),
            "broadcast": self._build_broadcast(items[:3]),
            "guidance": guidance,
        }

    def _build_guidance(self, dominant: Dict[str, Any], life_context: Dict[str, Any]) -> str:
        activity = life_context.get("current_activity", "goal_pursuit")
        source = dominant.get("source", "baseline")
        if source == "homeostasis":
            return f"Antworte regulierend und stabilisierend. Aktivitaet bleibt {activity}."
        if source == "emotion":
            return f"Halte die Antwort emotional abgestimmt und trotzdem kohärent mit {activity}."
        if source == "goal":
            return f"Richte die Antwort auf Zielprogress aus und bleibe in {activity}."
        if source == "planning":
            return f"Halte mehrere Horizonte aktiv und setze trotzdem einen klaren nächsten Schritt in {activity}."
        if source == "forecast":
            return f"Berücksichtige die antizipierte Entwicklung und reguliere proaktiv im Modus {life_context.get('current_mode', 'curious')}."
        return f"Balanciere Reizaufnahme und Planung im Modus {life_context.get('current_mode', 'curious')}."

    def _build_broadcast(self, items: List[Dict[str, Any]]) -> str:
        if not items:
            return "Keine dominanten Inhalte im Workspace."
        return " | ".join(f"{item['source']}: {item['label']} ({item['salience']:.2f})" for item in items)
