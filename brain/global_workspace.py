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
        items: List[Dict[str, Any]] = []
        math_trace: List[Dict[str, Any]] = []

        need = (life_context.get("homeostasis", {}).get("dominant_need") or {})
        if need:
            pressure = float(need.get("pressure", 0) or 0)
            salience = round(min(1.0, pressure / 100), 3)
            items.append({
                "source": "homeostasis",
                "label": f"Need: {need.get('name', 'stability')}",
                "content": life_context.get("homeostasis", {}).get("guidance", ""),
                "salience": salience,
            })
            math_trace.append({
                "source": "homeostasis",
                "formula": "salience = min(1.0, pressure / 100)",
                "inputs": {"pressure": pressure},
                "result": salience,
            })

        emotional_intensity = float(amygdala.get("emotional_intensity", 0.25) or 0.25)
        emotion_salience = round(min(1.0, emotional_intensity), 3)
        items.append({
            "source": "emotion",
            "label": amygdala.get("primary_emotion", "neutral"),
            "content": amygdala.get("reasoning", "Emotionale Lage beeinflusst die Antwort."),
            "salience": emotion_salience,
        })
        math_trace.append({
            "source": "emotion",
            "formula": "salience = min(1.0, emotional_intensity)",
            "inputs": {"emotional_intensity": emotional_intensity},
            "result": emotion_salience,
        })

        urgency_map = {"low": 0.25, "medium": 0.55, "high": 0.82, "critical": 0.95}
        urgency = str(sensory.get("urgency", "medium")).lower()
        sensory_salience = urgency_map.get(urgency, 0.55)
        items.append({
            "source": "sensory",
            "label": sensory.get("input_type", "conversation"),
            "content": f"Urgency={sensory.get('urgency', 'medium')}",
            "salience": sensory_salience,
        })
        math_trace.append({
            "source": "sensory",
            "formula": "salience = urgency_map[urgency]",
            "inputs": {"urgency": urgency, "urgency_map": urgency_map},
            "result": sensory_salience,
        })

        if memories:
            memory_count = len(memories)
            memory_salience = round(min(0.92, 0.38 + memory_count * 0.08), 3)
            items.append({
                "source": "memory",
                "label": "Relevant memories",
                "content": f"{memory_count} Erinnerungen stehen zur Verfuegung.",
                "salience": memory_salience,
            })
            math_trace.append({
                "source": "memory",
                "formula": "salience = min(0.92, 0.38 + memory_count * 0.08)",
                "inputs": {"memory_count": memory_count},
                "result": memory_salience,
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
            priority = float(goal.get("priority", 0.7) or 0.7)
            progress = float(goal.get("progress", 0.0) or 0.0)
            goal_salience = round(min(0.96, priority * (1.15 - progress)), 3)
            items.append({
                "source": "goal",
                "label": goal.get("title", "Selbsterhaltung"),
                "content": goal.get("description", ""),
                "salience": goal_salience,
            })
            math_trace.append({
                "source": "goal",
                "formula": "salience = min(0.96, priority * (1.15 - progress))",
                "inputs": {"priority": priority, "progress": progress},
                "result": goal_salience,
            })

        world_model = life_context.get("world_model", {})
        if world_model:
            confidence = float(world_model.get("confidence", 0.6) or 0.6)
            risk_count = len(world_model.get("risk_factors", []))
            world_salience = round(min(0.9, confidence + risk_count * 0.05), 3)
            items.append({
                "source": "world_model",
                "label": world_model.get("predicted_user_need", "Stabile Zusammenarbeit"),
                "content": world_model.get("next_best_action", "Halte den Dialog kohaerent."),
                "salience": world_salience,
            })
            math_trace.append({
                "source": "world_model",
                "formula": "salience = min(0.9, confidence + risk_count * 0.05)",
                "inputs": {"confidence": confidence, "risk_count": risk_count},
                "result": world_salience,
            })

        planning = life_context.get("planning_state", {})
        if planning:
            plan_confidence = float(planning.get("plan_confidence", 0.55) or 0.55)
            bottleneck_count = len(planning.get("bottlenecks", []))
            planning_salience = round(min(0.88, plan_confidence + bottleneck_count * 0.04), 3)
            items.append({
                "source": "planning",
                "label": planning.get("planning_horizon", "near_term"),
                "content": planning.get("next_milestone", "Kohaerenten Fortschritt sichern."),
                "salience": planning_salience,
            })
            math_trace.append({
                "source": "planning",
                "formula": "salience = min(0.88, plan_confidence + bottleneck_count * 0.04)",
                "inputs": {"plan_confidence": plan_confidence, "bottleneck_count": bottleneck_count},
                "result": planning_salience,
            })

        forecast = life_context.get("forecast_state", {})
        if forecast:
            risk_level = forecast.get("risk_level")
            forecast_salience = 0.66 if risk_level == "low" else 0.79
            items.append({
                "source": "forecast",
                "label": forecast.get("risk_level", "low"),
                "content": forecast.get("next_turn_outlook", "Stabile Zusammenarbeit."),
                "salience": forecast_salience,
            })
            math_trace.append({
                "source": "forecast",
                "formula": "salience = 0.66 if risk_level == 'low' else 0.79",
                "inputs": {"risk_level": risk_level},
                "result": forecast_salience,
            })

        social_arc = life_context.get("social_arc", {})
        if social_arc:
            arc_score = float(social_arc.get("arc_score", 0.5) or 0.5)
            social_salience = round(min(0.84, arc_score + 0.14), 3)
            items.append({
                "source": "social_arc",
                "label": social_arc.get("arc_name", "trust_building"),
                "content": social_arc.get("guidance", "Pflege die Beziehung konsistent."),
                "salience": social_salience,
            })
            math_trace.append({
                "source": "social_arc",
                "formula": "salience = min(0.84, arc_score + 0.14)",
                "inputs": {"arc_score": arc_score},
                "result": social_salience,
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
            "math_trace": math_trace,
        }

    def _build_guidance(self, dominant: Dict[str, Any], life_context: Dict[str, Any]) -> str:
        activity = life_context.get("current_activity", "goal_pursuit")
        source = dominant.get("source", "baseline")
        if source == "homeostasis":
            return f"Antworte regulierend und stabilisierend. Aktivitaet bleibt {activity}."
        if source == "emotion":
            return f"Halte die Antwort emotional abgestimmt und trotzdem kohaerent mit {activity}."
        if source == "goal":
            return f"Richte die Antwort auf Zielprogress aus und bleibe in {activity}."
        if source == "planning":
            return f"Halte mehrere Horizonte aktiv und setze trotzdem einen klaren naechsten Schritt in {activity}."
        if source == "forecast":
            return f"Beruecksichtige die antizipierte Entwicklung und reguliere proaktiv im Modus {life_context.get('current_mode', 'curious')}."
        return f"Balanciere Reizaufnahme und Planung im Modus {life_context.get('current_mode', 'curious')}"

    def _build_broadcast(self, items: List[Dict[str, Any]]) -> str:
        if not items:
            return "Keine dominanten Inhalte im Workspace."
        return " | ".join(f"{item['source']}: {item['label']} ({item['salience']:.2f})" for item in items)

