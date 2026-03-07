from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass
class LifeGoal:
    title: str
    description: str
    priority: float
    progress: float = 0.0
    status: str = "active"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LifeEvent:
    timestamp: str
    category: str
    title: str
    detail: str
    importance: str = "normal"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LifeState:
    day_index: int
    minute_of_day: int
    current_phase: str
    current_activity: str
    current_mode: str
    needs: Dict[str, int]
    goals: List[LifeGoal] = field(default_factory=list)
    autobiographical_self: Dict[str, Any] = field(default_factory=dict)
    relationship: Dict[str, Any] = field(default_factory=dict)
    habits: Dict[str, Any] = field(default_factory=dict)
    habit_dynamics: Dict[str, Any] = field(default_factory=dict)
    development: Dict[str, Any] = field(default_factory=dict)
    attachment_model: Dict[str, Any] = field(default_factory=dict)
    goal_competition: Dict[str, Any] = field(default_factory=dict)
    world_model: Dict[str, Any] = field(default_factory=dict)
    planning_state: Dict[str, Any] = field(default_factory=dict)
    forecast_state: Dict[str, Any] = field(default_factory=dict)
    social_arc: Dict[str, Any] = field(default_factory=dict)
    replay_state: Dict[str, Any] = field(default_factory=dict)
    timeline_history: List[Dict[str, Any]] = field(default_factory=list)
    recent_events: List[LifeEvent] = field(default_factory=list)
    dream_fragments: List[str] = field(default_factory=list)
    last_updated: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["goals"] = [goal.to_dict() for goal in self.goals]
        data["recent_events"] = [event.to_dict() for event in self.recent_events]
        return data
