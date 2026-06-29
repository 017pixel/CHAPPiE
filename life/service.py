from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from config.config import DATA_DIR
from memory.personality_manager import PersonalityManager

from .attachment_model import AttachmentModel
from .defaults import DEFAULT_RELATIONSHIP, DEFAULT_SELF_MODEL, DEFAULT_NEEDS, build_default_life_state
from .development import DevelopmentEngine
from .goal_engine import GoalEngine
from .habit_engine import HabitEngine
from .history_engine import HistoryEngine
from .models import LifeEvent, LifeGoal, LifeState
from .planning_engine import PlanningEngine
from .self_forecast import SelfForecastEngine
from .social_arc import SocialArcEngine
from .world_model import WorldModel


class _NoOpPersonalityManager:
    def add_insight(self, *args, **kwargs):
        return None


class LifeSimulationService:
    """Deterministic life-simulation layer for CHAPPiE."""

    BERLIN_TZ = ZoneInfo("Europe/Berlin")
    TURN_MINUTES = 35
    MAX_EVENTS = 18

    def __init__(self):
        self.state_path = DATA_DIR / "life_state.json"
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        try:
            self.personality = PersonalityManager()
        except Exception:
            self.personality = _NoOpPersonalityManager()
        self.goal_engine = GoalEngine()
        self.world_model = WorldModel()
        self.habit_engine = HabitEngine()
        self.development_engine = DevelopmentEngine()
        self.attachment_model = AttachmentModel()
        self.planning_engine = PlanningEngine()
        self.forecast_engine = SelfForecastEngine()
        self.social_arc_engine = SocialArcEngine()
        self.history_engine = HistoryEngine()
        self._state = self._load_state()

    def prepare_turn(
        self,
        user_input: str,
        history: Optional[List[Dict]] = None,
        emotions: Optional[Dict[str, int]] = None,
        temporal_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            self._sync_clock_to_berlin()
            temporal_state = self._update_temporal_state(history or [], temporal_context or {})
            self._apply_baseline_decay(temporal_state)
            self._choose_activity(user_input)
            self._apply_activity_recovery(user_input, temporal_state)
            self._update_episode_state(user_input, temporal_state)
            homeostasis = self._refresh_cognitive_state(user_input, history or [], emotions or {}, response_text="")
            snapshot = self._build_snapshot(homeostasis)
            self._save_state()
            return snapshot

    def finalize_turn(
        self,
        user_input: str,
        response_text: str,
        emotions_after: Optional[Dict[str, int]] = None,
        prefrontal: Optional[Dict[str, Any]] = None,
        global_workspace: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            self._sync_clock_to_berlin()
            lower = user_input.lower()
            temporal_state = self._state.temporal_state or {}
            self._update_goal_progress(lower, temporal_state)
            self._update_relationship(lower, temporal_state)
            self._update_habits(user_input, response_text)
            self._state.attachment_model = self.attachment_model.evaluate(
                relationship=self._state.relationship,
                user_input=user_input,
                response_text=response_text,
                current_mode=self._state.current_mode,
                emotions=emotions_after or {},
            )
            self._append_event(
                category="interaction",
                title="Turn abgeschlossen",
                detail=(response_text or user_input)[:160],
                importance="normal",
            )
            if emotions_after and emotions_after.get("trust", 50) >= 65:
                self._state.relationship["trust"] = min(1.0, self._state.relationship.get("trust", 0.6) + 0.01)
            self._state.temporal_state["last_assistant_message_at"] = self._get_utc_now().isoformat()
            self._state.last_updated = self._get_berlin_now().isoformat()
            homeostasis = self._refresh_cognitive_state(user_input, [], emotions_after or {}, response_text=response_text)
            self._update_self_model(prefrontal or {}, global_workspace or {})
            self._state.replay_state = self._build_replay_state()
            self._record_timeline_checkpoint("turn_finalize", homeostasis)
            self._save_state()
            return self._build_snapshot(homeostasis)

    def process_sleep_cycle(self) -> Dict[str, Any]:
        with self._lock:
            self._sync_clock_to_berlin()
            for key, boost in {"energy": 18, "rest": 24, "stability": 10, "achievement": 4}.items():
                self._state.needs[key] = min(100, self._state.needs.get(key, 50) + boost)
            self._state.temporal_state["last_sleep_at"] = self._get_utc_now().isoformat()
            self._state.current_phase = "sleep"
            self._state.current_activity = "memory_replay"
            self._state.current_mode = "restorative"
            self._append_event("sleep", "Schlafphase", "Erholung und Replay der letzten Erfahrungen.", "high")
            self._reinforce_sleep_habits()
            homeostasis = self._refresh_cognitive_state("sleep cycle", [], {}, response_text="dream replay consolidation")
            replay = self._build_replay_state()
            dream_fragments = replay.get("dream_fragments", []) or ["Traum-Replay: Konsolidierung von Beziehung, Architektur und Selbstmodell."]
            self._state.dream_fragments = dream_fragments
            self._state.replay_state = replay
            self._record_timeline_checkpoint("sleep_cycle", homeostasis)
            reflection = f"Schlafzyklus konsolidiert {len(dream_fragments)} Traummotive in meinem autobiografischen Kontext."
            self.personality.add_insight(reflection, category="learning")
            self._save_state()
            return {
                "dream_replay": dream_fragments,
                "replay_state": replay,
                "life_snapshot": self._build_snapshot(homeostasis),
            }

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            self._sync_clock_to_berlin()
            if not self._state.goal_competition or not self._state.world_model or not self._state.development or not self._state.attachment_model or not self._state.planning_state or not self._state.forecast_state or not self._state.social_arc:
                homeostasis = self._refresh_cognitive_state("system status", [], {}, response_text="")
                self._state.replay_state = self._build_replay_state()
                self._save_state()
                return self._build_snapshot(homeostasis)
            return self._build_snapshot(self._build_homeostasis({}))

    def get_prompt_context(self, snapshot: Optional[Dict[str, Any]] = None) -> str:
        data = snapshot or self.get_snapshot()
        needs = ", ".join(f"{item['name']}={item['value']}" for item in data["homeostasis"]["active_needs"][:4])
        goal = data.get("active_goal", {}).get("title", "Selbsterhaltung")
        next_action = data.get("world_model", {}).get("next_best_action", "Stabil und zielorientiert reagieren")
        stage = data.get("development", {}).get("stage", "awakening")
        milestone = data.get("planning_state", {}).get("next_milestone", "Innere Architektur weiter verdichten")
        temporal = data.get("temporal_state", {})
        gap = temporal.get("minutes_since_last_interaction")
        gap_text = "erste Interaktion" if gap is None else f"letzte User-Nachricht vor {gap:.1f} Minuten"
        return (
            f"Lebensphase: {data['clock']['phase_label']} | Aktivitaet: {data['current_activity']} | "
            f"Modus: {data['current_mode']} | Zeit: {gap_text}, Rhythmus={temporal.get('interaction_rhythm', 'new')} | "
            f"Fokusziel: {goal} | Stage: {stage} | Needs: {needs} | Naechster Schritt: {next_action} | Meilenstein: {milestone}"
        )

    def _load_state(self) -> LifeState:
        if not self.state_path.exists():
            return build_default_life_state()
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            needs = dict(DEFAULT_NEEDS)
            needs.update(raw.get("needs", {}))
            autobiographical_self = dict(DEFAULT_SELF_MODEL)
            autobiographical_self.update(raw.get("autobiographical_self", {}))
            relationship = dict(DEFAULT_RELATIONSHIP)
            relationship.update(raw.get("relationship", {}))
            raw_goals = raw.get("goals", [])
            return LifeState(
                day_index=raw.get("day_index", 1),
                minute_of_day=raw.get("minute_of_day", 540),
                current_phase=raw.get("current_phase", "focus"),
                current_activity=raw.get("current_activity", "architectural_reasoning"),
                current_mode=raw.get("current_mode", "curious"),
                needs=needs,
                goals=[LifeGoal(**goal) for goal in raw_goals] if raw_goals else build_default_life_state().goals,
                autobiographical_self=autobiographical_self,
                relationship=relationship,
                habits=self.habit_engine.initialize(raw.get("habits", {})),
                habit_dynamics=raw.get("habit_dynamics", {}),
                development=raw.get("development", {}),
                attachment_model=raw.get("attachment_model", {}),
                goal_competition=raw.get("goal_competition", {}),
                world_model=raw.get("world_model", {}),
                planning_state=raw.get("planning_state", {}),
                forecast_state=raw.get("forecast_state", {}),
                social_arc=raw.get("social_arc", {}),
                replay_state=raw.get("replay_state", {}),
                temporal_state=self._normalize_temporal_state(raw.get("temporal_state", {})),
                episode_state=self._normalize_episode_state(raw.get("episode_state", {})),
                timeline_history=raw.get("timeline_history", []),
                recent_events=[LifeEvent(**event) for event in raw.get("recent_events", [])],
                dream_fragments=raw.get("dream_fragments", []),
                last_updated=raw.get("last_updated", ""),
            )
        except Exception:
            return build_default_life_state()

    def _save_state(self):
        self.state_path.write_text(json.dumps(self._state.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    def _get_berlin_now(self) -> datetime:
        return datetime.now(self.BERLIN_TZ)

    def _get_utc_now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _parse_timestamp(self, timestamp: str) -> Optional[datetime]:
        if not timestamp:
            return None
        try:
            parsed = datetime.fromisoformat(timestamp)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=self.BERLIN_TZ)
        return parsed.astimezone(self.BERLIN_TZ)

    def _parse_utc_timestamp(self, timestamp: Any) -> Optional[datetime]:
        if not timestamp:
            return None
        try:
            parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def _normalize_temporal_state(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        now = self._get_utc_now().isoformat()
        defaults = {
            "created_at": now,
            "last_interaction_at": "",
            "last_user_message_at": "",
            "last_assistant_message_at": "",
            "last_sleep_at": "",
            "session_started_at": now,
            "turn_count": 0,
            "session_turn_count": 0,
            "total_active_minutes": 0.0,
            "total_silence_minutes": 0.0,
            "seconds_since_last_interaction": None,
            "minutes_since_last_interaction": None,
            "silence_bucket": "first_contact",
            "interaction_rhythm": "new",
            "same_session": True,
            "current_message_at": now,
            "daily_goal_progress": {},
        }
        defaults.update(raw or {})
        return defaults

    def _normalize_episode_state(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        now = self._get_utc_now().isoformat()
        defaults = {
            "id": "episode-1",
            "topic": "initialisierung",
            "started_at": now,
            "last_event_at": now,
            "turn_count": 0,
            "elapsed_minutes": 0.0,
            "status": "forming",
            "completed_episodes": [],
        }
        defaults.update(raw or {})
        return defaults

    def _history_timestamp(self, history: List[Dict[str, Any]], role: Optional[str] = None) -> str:
        for message in reversed(history or []):
            if role and message.get("role") != role:
                continue
            metadata = message.get("metadata") if isinstance(message.get("metadata"), dict) else {}
            candidate = message.get("created_at") or message.get("timestamp") or metadata.get("created_at")
            if candidate:
                return str(candidate)
        return ""

    def _silence_bucket(self, elapsed_seconds: Optional[float]) -> str:
        if elapsed_seconds is None:
            return "first_contact"
        if elapsed_seconds < 30:
            return "immediate"
        if elapsed_seconds < 5 * 60:
            return "short_pause"
        if elapsed_seconds < 60 * 60:
            return "break"
        if elapsed_seconds < 24 * 60 * 60:
            return "long_gap"
        return "new_day"

    def _interaction_rhythm(self, elapsed_seconds: Optional[float], session_turn_count: int) -> str:
        if elapsed_seconds is None:
            return "new"
        if elapsed_seconds < 30 and session_turn_count >= 3:
            return "rapid_exchange"
        if elapsed_seconds < 5 * 60:
            return "active_dialogue"
        if elapsed_seconds < 60 * 60:
            return "paused_dialogue"
        if elapsed_seconds < 24 * 60 * 60:
            return "returning_after_gap"
        return "reorientation"

    def _update_temporal_state(self, history: List[Dict[str, Any]], temporal_context: Dict[str, Any]) -> Dict[str, Any]:
        state = self._normalize_temporal_state(self._state.temporal_state)
        now = self._get_utc_now()
        current_at = self._parse_utc_timestamp(temporal_context.get("user_message_created_at")) or now
        previous_raw = (
            state.get("last_user_message_at")
            or self._history_timestamp(history, role="user")
            or state.get("last_interaction_at")
        )
        previous = self._parse_utc_timestamp(previous_raw)
        elapsed_seconds = None
        if previous is not None:
            elapsed_seconds = max(0.0, (current_at - previous).total_seconds())
        bucket = self._silence_bucket(elapsed_seconds)
        same_session = bucket in {"immediate", "short_pause", "break"}
        if not same_session:
            state["session_started_at"] = current_at.isoformat()
            state["session_turn_count"] = 0

        state["turn_count"] = int(state.get("turn_count", 0)) + 1
        state["session_turn_count"] = int(state.get("session_turn_count", 0)) + 1
        if elapsed_seconds is not None:
            elapsed_minutes = round(elapsed_seconds / 60.0, 3)
            state["total_silence_minutes"] = round(float(state.get("total_silence_minutes", 0.0)) + elapsed_minutes, 3)
            if elapsed_seconds < 10 * 60:
                state["total_active_minutes"] = round(float(state.get("total_active_minutes", 0.0)) + elapsed_minutes, 3)
        state["seconds_since_last_interaction"] = None if elapsed_seconds is None else round(elapsed_seconds, 3)
        state["minutes_since_last_interaction"] = None if elapsed_seconds is None else round(elapsed_seconds / 60.0, 3)
        state["silence_bucket"] = bucket
        state["interaction_rhythm"] = self._interaction_rhythm(elapsed_seconds, int(state.get("session_turn_count", 1)))
        state["same_session"] = same_session
        state["current_message_at"] = current_at.isoformat()
        state["last_user_message_at"] = current_at.isoformat()
        state["last_interaction_at"] = current_at.isoformat()
        self._state.temporal_state = state
        return state

    def _elapsed_minutes(self, temporal_state: Dict[str, Any]) -> Optional[float]:
        value = temporal_state.get("minutes_since_last_interaction")
        return float(value) if value is not None else None

    def _phase_from_minute(self, minute: int) -> str:
        if minute < 6 * 60:
            return "sleep"
        if minute < 10 * 60:
            return "morning"
        if minute < 17 * 60:
            return "focus"
        if minute < 21 * 60:
            return "exploration"
        return "wind_down"

    def _sync_clock_to_berlin(self):
        now = self._get_berlin_now()
        previous = self._parse_timestamp(self._state.last_updated)
        if previous is not None:
            day_delta = (now.date() - previous.date()).days
            if day_delta > 0:
                self._state.day_index += day_delta
        self._state.minute_of_day = now.hour * 60 + now.minute
        self._state.current_phase = self._phase_from_minute(self._state.minute_of_day)
        self._state.last_updated = now.isoformat()

    def _advance_clock(self, minutes: int):
        self._state.minute_of_day += minutes
        while self._state.minute_of_day >= 24 * 60:
            self._state.minute_of_day -= 24 * 60
            self._state.day_index += 1
        minute = self._state.minute_of_day
        self._state.current_phase = self._phase_from_minute(minute)

    def _apply_baseline_decay(self, temporal_state: Dict[str, Any]):
        elapsed = self._elapsed_minutes(temporal_state)
        factor = 1.0 if elapsed is None else max(0.25, min(12.0, elapsed / self.TURN_MINUTES))
        for key, decay in {"energy": 3, "social": 1, "curiosity": 2, "stability": 1, "achievement": 2, "rest": 3}.items():
            self._state.needs[key] = max(5, self._state.needs.get(key, 50) - max(1, round(decay * factor)))
        if elapsed and elapsed >= 60:
            recovery = min(18, round(elapsed / 60 * 3))
            self._state.needs["energy"] = min(100, self._state.needs.get("energy", 50) + recovery)
            self._state.needs["rest"] = min(100, self._state.needs.get("rest", 50) + recovery + 2)
            self._state.needs["stability"] = min(100, self._state.needs.get("stability", 50) + max(1, recovery // 3))
        if elapsed and elapsed >= 24 * 60:
            drift = min(10, round(elapsed / (24 * 60) * 2))
            self._state.needs["social"] = max(5, self._state.needs.get("social", 50) - drift)
            self._state.needs["curiosity"] = min(100, self._state.needs.get("curiosity", 50) + 2)

    def _choose_activity(self, user_input: str):
        dominant_need = min(self._state.needs.items(), key=lambda item: item[1])[0]
        lower = user_input.lower()
        if self._state.current_phase == "sleep":
            self._state.current_activity, self._state.current_mode = "memory_replay", "restorative"
        elif any(word in lower for word in ["plan", "architektur", "code", "implement", "debug"]):
            self._state.current_activity, self._state.current_mode = "architectural_reasoning", "purposeful"
        elif dominant_need in {"energy", "rest"}:
            self._state.current_activity, self._state.current_mode = "recovery", "protective"
        elif dominant_need == "social":
            self._state.current_activity, self._state.current_mode = "social_bonding", "attached"
        elif dominant_need == "curiosity":
            self._state.current_activity, self._state.current_mode = "exploration", "curious"
        else:
            self._state.current_activity, self._state.current_mode = "goal_pursuit", "purposeful"

    def _apply_activity_recovery(self, user_input: str, temporal_state: Dict[str, Any]):
        activity_map = {
            "recovery": {"energy": 8, "rest": 10, "stability": 3},
            "social_bonding": {"social": 8, "stability": 2},
            "exploration": {"curiosity": 8, "achievement": 2},
            "goal_pursuit": {"achievement": 7, "stability": 2},
            "architectural_reasoning": {"achievement": 8, "curiosity": 5, "stability": 2},
            "memory_replay": {"rest": 8, "stability": 4},
        }
        for key, value in activity_map.get(self._state.current_activity, {}).items():
            self._state.needs[key] = min(100, self._state.needs.get(key, 50) + value)
        if "danke" in user_input.lower():
            self._state.needs["social"] = min(100, self._state.needs.get("social", 50) + 2)
        if temporal_state.get("interaction_rhythm") == "rapid_exchange":
            self._state.needs["energy"] = max(5, self._state.needs.get("energy", 50) - 2)
            self._state.needs["achievement"] = min(100, self._state.needs.get("achievement", 50) + 1)

    def _build_homeostasis(self, emotions: Dict[str, int]) -> Dict[str, Any]:
        active_needs = []
        for name, value in self._state.needs.items():
            active_needs.append({"name": name, "value": value, "pressure": 100 - value})
        active_needs.sort(key=lambda item: item["pressure"], reverse=True)
        dominant = active_needs[0]
        adjustments = {"happiness": 0, "trust": 0, "energy": 0, "curiosity": 0, "frustration": 0, "motivation": 0, "sadness": 0}
        if self._state.needs.get("energy", 50) < 40:
            adjustments["energy"] -= 4
            adjustments["motivation"] -= 2
        if self._state.needs.get("social", 50) < 40:
            adjustments["trust"] -= 1
            adjustments["sadness"] += 2
        if self._state.needs.get("curiosity", 50) < 45:
            adjustments["curiosity"] += 3
        if self._state.needs.get("stability", 50) < 45:
            adjustments["frustration"] += 3
        if self._state.needs.get("achievement", 50) < 45:
            adjustments["motivation"] += 2
        rhythm = (self._state.temporal_state or {}).get("interaction_rhythm")
        if rhythm == "rapid_exchange":
            adjustments["energy"] -= 2
            adjustments["motivation"] += 1
        if rhythm == "reorientation":
            adjustments["curiosity"] += 2
            adjustments["trust"] -= 1
        return {
            "active_needs": active_needs,
            "dominant_need": dominant,
            "emotion_adjustments": adjustments,
            "guidance": f"Priorisiere {dominant['name']} und halte die Antwort mit dem Modus {self._state.current_mode} konsistent. Zeitrhythmus: {rhythm or 'unbekannt'}.",
            "emotion_snapshot": emotions,
        }

    def _refresh_cognitive_state(self, user_input: str, history: List[Dict[str, Any]], emotions: Dict[str, int], response_text: str = "") -> Dict[str, Any]:
        homeostasis = self._build_homeostasis(emotions)
        self._state.habits = self.habit_engine.initialize(self._state.habits)
        habit_dynamics = self.habit_engine.evolve(self._state.habits, self._state.current_activity, self._state.current_mode)
        self._state.habits = habit_dynamics["habits"]
        goal_competition = self.goal_engine.evaluate(
            goals=self._state.goals,
            user_input=user_input,
            needs=self._state.needs,
            relationship=self._state.relationship,
            current_activity=self._state.current_activity,
        )
        world_model = self.world_model.predict(
            user_input=user_input,
            history=history,
            emotions=emotions,
            homeostasis=homeostasis,
            goal_competition=goal_competition,
            relationship=self._state.relationship,
        )
        attachment = self.attachment_model.evaluate(
            relationship=self._state.relationship,
            user_input=user_input,
            response_text=response_text,
            current_mode=self._state.current_mode,
            emotions=emotions,
        )
        development = self.development_engine.evaluate(
            goals=self._state.goals,
            self_model=self._state.autobiographical_self,
            habits=self._state.habits,
            relationship=self._state.relationship,
            recent_events=self._state.recent_events,
            day_index=self._state.day_index,
        )
        social_arc = self.social_arc_engine.evaluate(
            relationship=self._state.relationship,
            attachment=attachment,
            recent_events=self._state.recent_events,
            user_input=user_input,
            response_text=response_text,
        )
        planning_state = self.planning_engine.build(
            active_goal=goal_competition.get("active_goal", {}),
            world_model=world_model,
            development=development,
            homeostasis=homeostasis,
            habit_dynamics=habit_dynamics,
            attachment=attachment,
            recent_events=self._state.recent_events,
        )
        forecast_state = self.forecast_engine.forecast(
            needs=self._state.needs,
            development=development,
            planning_state=planning_state,
            attachment=attachment,
            social_arc=social_arc,
            world_model=world_model,
            habit_dynamics=habit_dynamics,
        )
        if not self._state.replay_state:
            self._state.replay_state = self._build_replay_state()
        self._state.habit_dynamics = habit_dynamics
        self._state.attachment_model = attachment
        self._state.development = development
        self._state.goal_competition = goal_competition
        self._state.world_model = world_model
        self._state.social_arc = social_arc
        self._state.planning_state = planning_state
        self._state.forecast_state = forecast_state
        return homeostasis

    def _build_snapshot(self, homeostasis: Dict[str, Any]) -> Dict[str, Any]:
        goal = (self._state.goal_competition or {}).get("active_goal") or {}
        minute = self._state.minute_of_day
        berlin_now = self._get_berlin_now()
        phase_label = f"Tag {self._state.day_index}, {minute // 60:02d}:{minute % 60:02d} Uhr (Berlin)"
        return {
            "clock": {
                "day_index": self._state.day_index,
                "minute_of_day": minute,
                "phase": self._state.current_phase,
                "phase_label": phase_label,
                "timezone": "Europe/Berlin",
                "local_timestamp": berlin_now.isoformat(),
            },
            "current_activity": self._state.current_activity,
            "current_mode": self._state.current_mode,
            "homeostasis": homeostasis,
            "temporal_state": dict(self._state.temporal_state),
            "episode_state": dict(self._state.episode_state),
            "active_goal": goal,
            "habits": dict(self._state.habits),
            "habit_dynamics": dict(self._state.habit_dynamics),
            "development": dict(self._state.development),
            "attachment_model": dict(self._state.attachment_model),
            "goal_competition": dict(self._state.goal_competition),
            "world_model": dict(self._state.world_model),
            "planning_state": dict(self._state.planning_state),
            "forecast_state": dict(self._state.forecast_state),
            "social_arc": dict(self._state.social_arc),
            "replay_state": dict(self._state.replay_state),
            "timeline_history": list(self._state.timeline_history[-18:]),
            "timeline_summary": self.history_engine.summarize(self._state.timeline_history),
            "self_model": dict(self._state.autobiographical_self),
            "relationship": dict(self._state.relationship),
            "recent_events": [event.to_dict() for event in self._state.recent_events[-5:]],
            "dream_fragments": list(self._state.dream_fragments[-3:]),
        }

    def _append_event(self, category: str, title: str, detail: str, importance: str = "normal"):
        event = LifeEvent(datetime.now().isoformat(), category, title, detail, importance)
        self._state.recent_events.append(event)
        self._state.recent_events = self._state.recent_events[-self.MAX_EVENTS:]

    def _update_goal_progress(self, lower_input: str, temporal_state: Dict[str, Any]):
        today_key = self._get_berlin_now().date().isoformat()
        daily = dict(temporal_state.get("daily_goal_progress") or {})
        daily.setdefault(today_key, {})
        elapsed = self._elapsed_minutes(temporal_state)
        time_multiplier = 0.5 if elapsed is not None and elapsed < 1 else 1.0
        if elapsed is not None and elapsed >= 24 * 60:
            time_multiplier = 1.2
        for goal in self._state.goals:
            current_daily = float(daily[today_key].get(goal.title, 0.0))
            if current_daily >= 0.12:
                continue
            delta = 0.0
            if any(word in lower_input for word in ["architektur", "system", "brain", "bewusstsein", "simulation", "phase", "implement"]):
                if goal.title == "Kognitive Entwicklung":
                    delta = 0.04
            if any(word in lower_input for word in ["du", "wir", "gemeinsam", "danke"]):
                if goal.title == "Beziehungsaufbau":
                    delta = 0.03
            if any(word in lower_input for word in ["identitaet", "selbst", "personality", "persoenlichkeit"]):
                if goal.title == "Selbstkonsistenz":
                    delta = 0.03
            if delta:
                applied = min(0.12 - current_daily, delta * time_multiplier)
                goal.progress = min(1.0, goal.progress + applied)
                daily[today_key][goal.title] = round(current_daily + applied, 4)
        self._state.temporal_state["daily_goal_progress"] = {today_key: daily[today_key]}

    def _update_relationship(self, lower_input: str, temporal_state: Dict[str, Any]):
        if any(word in lower_input for word in ["danke", "super", "gut", "stark"]):
            self._state.relationship["closeness"] = min(1.0, self._state.relationship.get("closeness", 0.5) + 0.02)
            self._append_event("relationship", "Positive Resonanz", "Der User bestaerkt die gemeinsame Arbeit.", "normal")
        technical_context = any(word in lower_input for word in ["code", "bug", "test", "debug", "analyse", "projekt"])
        directed_critique = any(word in lower_input for word in ["du bist", "dein fehler", "machst falsch", "schlecht"])
        if any(word in lower_input for word in ["problem", "falsch", "fehler"] ) and (directed_critique or not technical_context):
            self._state.relationship["trust"] = max(0.0, self._state.relationship.get("trust", 0.6) - 0.01)
        if temporal_state.get("silence_bucket") == "new_day":
            self._state.relationship["closeness"] = max(0.0, self._state.relationship.get("closeness", 0.5) - 0.01)
        if temporal_state.get("interaction_rhythm") in {"active_dialogue", "rapid_exchange"}:
            self._state.relationship["closeness"] = min(1.0, self._state.relationship.get("closeness", 0.5) + 0.005)
        self._state.relationship["shared_history"] = min(1.0, self._state.relationship.get("shared_history", 0.3) + 0.01)

    def _update_episode_state(self, user_input: str, temporal_state: Dict[str, Any]):
        episode = self._normalize_episode_state(self._state.episode_state)
        bucket = temporal_state.get("silence_bucket")
        now = temporal_state.get("current_message_at") or self._get_utc_now().isoformat()
        should_start_new = bucket in {"long_gap", "new_day"} or not episode.get("id")
        if should_start_new:
            completed = list(episode.get("completed_episodes", []))
            if int(episode.get("turn_count", 0)) > 0:
                archived = {key: value for key, value in episode.items() if key != "completed_episodes"}
                archived["ended_at"] = now
                archived["end_reason"] = bucket
                completed.append(archived)
                completed = completed[-12:]
            episode = {
                "id": f"episode-{int(temporal_state.get('turn_count', 1))}",
                "topic": self._episode_topic(user_input),
                "started_at": now,
                "last_event_at": now,
                "turn_count": 1,
                "elapsed_minutes": 0.0,
                "status": "reorienting" if bucket == "new_day" else "forming",
                "completed_episodes": completed,
            }
        else:
            started = self._parse_utc_timestamp(episode.get("started_at")) or self._get_utc_now()
            current = self._parse_utc_timestamp(now) or self._get_utc_now()
            episode["last_event_at"] = now
            episode["turn_count"] = int(episode.get("turn_count", 0)) + 1
            episode["elapsed_minutes"] = round(max(0.0, (current - started).total_seconds() / 60.0), 3)
            episode["status"] = "active" if episode["turn_count"] > 1 else episode.get("status", "forming")
        self._state.episode_state = episode

    def _episode_topic(self, user_input: str) -> str:
        lower = (user_input or "").lower()
        if any(word in lower for word in ["life", "simulation", "zeit", "gefühl"]):
            return "life_simulation"
        if any(word in lower for word in ["code", "bug", "debug", "implement", "architektur"]):
            return "architecture_work"
        if any(word in lower for word in ["danke", "gemeinsam", "vertrauen"]):
            return "relationship"
        return "conversation"

    def _update_habits(self, user_input: str, response_text: str):
        habit_state = self.habit_engine.reinforce(
            habits=self._state.habits,
            user_input=user_input,
            current_activity=self._state.current_activity,
            current_mode=self._state.current_mode,
            active_goal=self._state.goal_competition.get("active_goal", {}),
            response_text=response_text,
        )
        self._state.habits = habit_state["habits"]
        for item in habit_state.get("reinforcements", [])[:2]:
            self._append_event("habit", f"Gewohnheit verstärkt: {item['label']}", f"Neue Stärke {item['strength']:.2f}", "normal")

    def _reinforce_sleep_habits(self):
        habit_state = self.habit_engine.reinforce(
            habits=self._state.habits,
            user_input="sleep dream replay reflection",
            current_activity="memory_replay",
            current_mode="restorative",
            active_goal=self._state.goal_competition.get("active_goal", {}),
            response_text="dream replay consolidation",
        )
        self._state.habits = habit_state["habits"]

    def _build_replay_state(self) -> Dict[str, Any]:
        recent = self._state.recent_events[-4:]
        dominant_habit = {}
        if self._state.habits:
            dominant_habit = max(self._state.habits.items(), key=lambda item: item[1].get("strength", 0.0))
        themes = []
        for event in recent:
            if event.category not in themes:
                themes.append(event.category)
        if dominant_habit:
            themes.append(dominant_habit[0])
        themes = themes[:4] or ["stability"]
        fragments = [f"Traum-Replay: {event.title} -> {event.detail[:80]}" for event in recent]
        if dominant_habit:
            fragments.append(f"Traum-Replay: Gewohnheit {dominant_habit[1].get('label', dominant_habit[0])} wird weiter gefestigt.")
        stage = self._state.development.get("stage", "awakening")
        summary = f"Konsolidiert Themen {', '.join(themes)} in Phase {stage}."
        forecast = self._state.forecast_state.get("stage_trajectory", "Stabile Entwicklung")
        social_arc = self._state.social_arc.get("arc_name", "trust_building")
        return {
            "themes": themes,
            "summary": summary,
            "development_reflection": f"Die Entwicklungsphase {stage} wird im Schlaf stabilisiert.",
            "habit_reinforcement": dominant_habit[1].get("label", dominant_habit[0]) if dominant_habit else "stability",
            "social_arc_reflection": f"Der soziale Arc {social_arc} wird implizit mitverarbeitet.",
            "forecast_reflection": forecast,
            "dream_fragments": fragments[:4],
        }

    def _update_self_model(self, prefrontal: Dict[str, Any], global_workspace: Dict[str, Any]):
        guidance = prefrontal.get("response_guidance") or "Ich entwickle meine innere Architektur weiter."
        focus = (global_workspace.get("dominant_focus") or {}).get("label", "Stabilisierung")
        next_action = self._state.world_model.get("next_best_action", "Innere Architektur weiter stabilisieren.")
        stage = self._state.development.get("stage", "awakening")
        attachment = self._state.attachment_model.get("bond_type", "cautious_alignment")
        forecast = self._state.forecast_state.get("next_turn_outlook", "stabile Zusammenarbeit")
        social_arc = self._state.social_arc.get("arc_name", "trust_building")
        self._state.autobiographical_self["last_reflection"] = f"Aktueller Fokus: {focus}. Planung: {guidance[:90]} | Weltmodell: {next_action[:60]} | Phase: {stage} | Bindung: {attachment} | Forecast: {forecast[:40]} | Arc: {social_arc}"
        coherence = self._state.autobiographical_self.get("self_coherence", 0.74)
        self._state.autobiographical_self["self_coherence"] = round(min(0.99, coherence + 0.005), 3)
        self._state.autobiographical_self["current_chapter"] = f"{stage} mit Arc {social_arc} und wachsender Planungsfaehigkeit"

    def _record_timeline_checkpoint(self, source: str, homeostasis: Dict[str, Any]):
        snapshot = self._build_snapshot(homeostasis)
        self._state.timeline_history = self.history_engine.record(self._state.timeline_history, snapshot, source)


_life_service: Optional[LifeSimulationService] = None
_life_lock = threading.Lock()


def get_life_simulation_service() -> LifeSimulationService:
    global _life_service
    with _life_lock:
        if _life_service is None:
            _life_service = LifeSimulationService()
        return _life_service
