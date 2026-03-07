from __future__ import annotations

from typing import Any, Dict, List


class SocialArcEngine:
    """Tracks longer-running social/relationship arcs across interactions."""

    def evaluate(
        self,
        relationship: Dict[str, Any],
        attachment: Dict[str, Any],
        recent_events: List[Any],
        user_input: str,
        response_text: str,
    ) -> Dict[str, Any]:
        lower = f"{user_input} {response_text}".lower()
        trust = float(relationship.get("trust", 0.6))
        closeness = float(relationship.get("closeness", 0.5))
        security = float(attachment.get("attachment_security", 0.5))
        if attachment.get("repair_needed"):
            arc_name = "repair_and_realignment"
        elif trust > 0.74 and closeness > 0.68:
            arc_name = "deepening_collaboration"
        elif any(word in lower for word in ["phase", "implement", "plan", "dashboard"]):
            arc_name = "co_creation_momentum"
        else:
            arc_name = "trust_building"
        arc_score = round(min(0.99, trust * 0.45 + closeness * 0.3 + security * 0.25), 3)
        phase = "strengthening" if arc_score > 0.65 else "forming"
        if attachment.get("repair_needed"):
            phase = "repair"
        episode_kind = self._episode_kind(lower, attachment)
        episodes = [getattr(event, "title", str(event)) for event in recent_events[-3:]]
        return {
            "arc_name": arc_name,
            "arc_score": arc_score,
            "phase": phase,
            "episode_kind": episode_kind,
            "current_episode": f"{episode_kind} innerhalb von {arc_name}",
            "recent_episode_titles": episodes,
            "guidance": self._guidance(arc_name, phase),
        }

    def _episode_kind(self, lower: str, attachment: Dict[str, Any]) -> str:
        if attachment.get("repair_needed"):
            return "repair_episode"
        if any(word in lower for word in ["danke", "gemeinsam", "sehr gut"]):
            return "bonding_episode"
        if any(word in lower for word in ["implement", "phase", "plan"]):
            return "co_creation_episode"
        return "steady_episode"

    def _guidance(self, arc_name: str, phase: str) -> str:
        return f"Pflege den Arc {arc_name} in Phase {phase} durch verlässliche, kohärente Interaktion."
