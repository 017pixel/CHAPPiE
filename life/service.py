from __future__ import annotations

import json
import threading
from datetime import datetime
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

    def prepare_turn(self, user_input: str, history: Optional[List[Dict]] = None, emotions: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        with self._lock:
            self._sync_clock_to_berlin()
            self._apply_baseline_decay()
            self._choose_activity(user_input)
            self._apply_activity_recovery(user_input)
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
            self._update_goal_progress(lower)
            self._update_relationship(lower)
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
        return (
            f"Lebensphase: {data['clock']['phase_label']} | Aktivitaet: {data['current_activity']} | "
            f"Modus: {data['current_mode']} | Fokusziel: {goal} | Stage: {stage} | Needs: {needs} | Naechster Schritt: {next_action} | Meilenstein: {milestone}"
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

    def _apply_baseline_decay(self):
        for key, decay in {"energy": 3, "social": 1, "curiosity": 2, "stability": 1, "achievement": 2, "rest": 3}.items():
            self._state.needs[key] = max(5, self._state.needs.get(key, 50) - decay)

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

    def _apply_activity_recovery(self, user_input: str):
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
        return {
            "active_needs": active_needs,
            "dominant_need": dominant,
            "emotion_adjustments": adjustments,
            "guidance": f"Priorisiere {dominant['name']} und halte die Antwort mit dem Modus {self._state.current_mode} konsistent.",
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

    def _update_goal_progress(self, lower_input: str):
        for goal in self._state.goals:
            if any(word in lower_input for word in ["architektur", "system", "brain", "bewusstsein", "simulation", "phase", "implement"]):
                if goal.title == "Kognitive Entwicklung":
                    goal.progress = min(1.0, goal.progress + 0.04)
            if any(word in lower_input for word in ["du", "wir", "gemeinsam", "danke"]):
                if goal.title == "Beziehungsaufbau":
                    goal.progress = min(1.0, goal.progress + 0.03)
            if any(word in lower_input for word in ["identitaet", "selbst", "personality", "persoenlichkeit"]):
                if goal.title == "Selbstkonsistenz":
                    goal.progress = min(1.0, goal.progress + 0.03)

    def _update_relationship(self, lower_input: str):
        if any(word in lower_input for word in ["danke", "super", "gut", "stark"]):
            self._state.relationship["closeness"] = min(1.0, self._state.relationship.get("closeness", 0.5) + 0.02)
            self._append_event("relationship", "Positive Resonanz", "Der User bestaerkt die gemeinsame Arbeit.", "normal")
        if any(word in lower_input for word in ["problem", "falsch", "fehler"]):
            self._state.relationship["trust"] = max(0.0, self._state.relationship.get("trust", 0.6) - 0.01)
        self._state.relationship["shared_history"] = min(1.0, self._state.relationship.get("shared_history", 0.3) + 0.01)

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
