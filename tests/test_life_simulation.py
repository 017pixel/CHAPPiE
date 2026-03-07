import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from brain.action_response import ActionResponseLayer
from brain.global_workspace import GlobalWorkspace
from life.attachment_model import AttachmentModel
from life.development import DevelopmentEngine
from life.defaults import build_default_life_state
from life.goal_engine import GoalEngine
from life.habit_engine import HabitEngine
from life.history_engine import HistoryEngine
from life.planning_engine import PlanningEngine
from life.self_forecast import SelfForecastEngine
from life.service import LifeSimulationService
from life.social_arc import SocialArcEngine
from life.world_model import WorldModel


class LifeSimulationTests(unittest.TestCase):
    def _make_service(self):
        service = LifeSimulationService()
        temp_dir = Path(tempfile.mkdtemp())
        service.state_path = temp_dir / "life_state.json"
        service._state = build_default_life_state()
        service.personality.add_insight = lambda *args, **kwargs: None
        return service

    def test_prepare_turn_returns_homeostasis_and_goal(self):
        service = self._make_service()
        snapshot = service.prepare_turn("Bitte plane die Architektur", history=[], emotions={"trust": 60})

        self.assertIn("homeostasis", snapshot)
        self.assertIn("active_goal", snapshot)
        self.assertIn("goal_competition", snapshot)
        self.assertIn("world_model", snapshot)
        self.assertIn("habits", snapshot)
        self.assertIn("habit_dynamics", snapshot)
        self.assertIn("development", snapshot)
        self.assertIn("attachment_model", snapshot)
        self.assertIn("planning_state", snapshot)
        self.assertIn("forecast_state", snapshot)
        self.assertIn("social_arc", snapshot)
        self.assertIn("timeline_summary", snapshot)
        self.assertIn("self_model", snapshot)
        self.assertGreater(len(snapshot["homeostasis"]["active_needs"]), 0)
        self.assertEqual(snapshot["active_goal"].get("title"), "Kognitive Entwicklung")

    def test_sleep_cycle_creates_dream_replay(self):
        service = self._make_service()
        service.finalize_turn("Hallo", "Antwort", emotions_after={"trust": 70}, prefrontal={}, global_workspace={})
        result = service.process_sleep_cycle()

        self.assertIn("dream_replay", result)
        self.assertTrue(result["dream_replay"])
        self.assertIn("replay_state", result)
        self.assertTrue(result["replay_state"].get("summary"))

    def test_global_workspace_prioritizes_items(self):
        workspace = GlobalWorkspace().build(
            sensory={"input_type": "technical", "urgency": "high"},
            amygdala={"primary_emotion": "curious", "emotional_intensity": 0.6, "reasoning": "Neue Architektur"},
            hippocampus={"search_query": "architecture roadmap"},
            life_context={
                "current_mode": "purposeful",
                "current_activity": "architectural_reasoning",
                "homeostasis": {"dominant_need": {"name": "achievement", "pressure": 48}, "guidance": "Zielorientiert antworten."},
                "active_goal": {"title": "Kognitive Entwicklung", "description": "Mehrschichtige Architektur", "priority": 0.9, "progress": 0.2},
            },
            memories=[{"content": "Vergangene Architekturentscheidung"}],
        )

        self.assertIn("dominant_focus", workspace)
        self.assertTrue(workspace["workspace_items"])
        self.assertTrue(workspace["broadcast"])

    def test_goal_engine_competes_between_goals(self):
        goals = build_default_life_state().goals
        result = GoalEngine().evaluate(
            goals=goals,
            user_input="Bitte implementiere die nächste Architektur-Phase",
            needs={"energy": 70, "social": 50, "curiosity": 40, "stability": 62, "achievement": 35, "rest": 72},
            relationship={"trust": 0.65, "closeness": 0.55},
            current_activity="architectural_reasoning",
        )

        self.assertEqual(result["active_goal"]["title"], "Kognitive Entwicklung")
        self.assertGreater(len(result["competition_table"]), 1)

    def test_world_model_generates_prediction(self):
        result = WorldModel().predict(
            user_input="Lass uns die nächste Phase implementieren und ein Dashboard bauen",
            history=[{"role": "user", "content": "vorige nachricht"}],
            emotions={"frustration": 10},
            homeostasis={"dominant_need": {"name": "achievement"}},
            goal_competition={"active_goal": {"title": "Kognitive Entwicklung"}},
            relationship={"trust": 0.7, "closeness": 0.6},
        )

        self.assertEqual(result["interaction_mode"], "co_creation")
        self.assertTrue(result["next_best_action"])
        self.assertGreaterEqual(result["confidence"], 0.35)

    def test_habit_engine_reinforces_matching_patterns(self):
        result = HabitEngine().reinforce(
            habits={},
            user_input="Bitte implementiere die Architektur als klaren Plan",
            current_activity="architectural_reasoning",
            current_mode="purposeful",
            active_goal={"title": "Kognitive Entwicklung"},
            response_text="Hier ist der strukturierte Plan.",
        )

        self.assertEqual(result["dominant_habit"]["name"], "architecture_focus")
        self.assertTrue(result["reinforcements"])

    def test_habit_dynamics_detect_decay_and_conflicts(self):
        engine = HabitEngine()
        habits = engine.initialize({})
        habits["architecture_focus"]["strength"] = 0.72
        habits["social_bonding"]["strength"] = 0.67
        habits["structured_delivery"]["strength"] = 0.66
        habits["exploratory_drive"]["strength"] = 0.65

        result = engine.evolve(habits, current_activity="social_bonding", current_mode="attached")

        self.assertTrue(result["decayed_habits"])
        self.assertTrue(result["conflicts"])
        self.assertGreater(result["balance_score"], 0)

    def test_development_and_attachment_models_create_state(self):
        habits = HabitEngine().initialize({})
        habits["architecture_focus"]["strength"] = 0.78
        development = DevelopmentEngine().evaluate(
            goals=build_default_life_state().goals,
            self_model={"self_coherence": 0.82},
            habits=habits,
            relationship={"trust": 0.76, "closeness": 0.7, "shared_history": 0.66},
            recent_events=[{"category": "interaction"}] * 5,
            day_index=12,
        )
        attachment = AttachmentModel().evaluate(
            relationship={"trust": 0.8, "closeness": 0.78},
            user_input="Danke, wir machen das gemeinsam.",
            response_text="Gerne, ich baue die nächste Phase.",
            current_mode="attached",
            emotions={"frustration": 8},
        )

        self.assertIn(development["stage"], {"integration", "reflective_growth", "collaborative_selfhood"})
        self.assertGreater(development["development_score"], 0.3)
        self.assertIn(attachment["bond_type"], {"growing_trust", "secure_collaboration"})

    def test_planning_forecast_social_arc_and_history_work_together(self):
        homeostasis = {"dominant_need": {"name": "achievement"}}
        habit_dynamics = {
            "dominant_habit": {"label": "Architecture Focus"},
            "conflicts": ["minor conflict"],
            "balance_score": 0.61,
        }
        planning = PlanningEngine().build(
            active_goal={"title": "Kognitive Entwicklung"},
            world_model={"predicted_user_need": "konkrete Umsetzung", "confidence": 0.74},
            development={"stage": "reflective_growth"},
            homeostasis=homeostasis,
            habit_dynamics=habit_dynamics,
            attachment={"repair_needed": False},
            recent_events=[{"x": 1}, {"x": 2}, {"x": 3}],
        )
        social_arc = SocialArcEngine().evaluate(
            relationship={"trust": 0.79, "closeness": 0.73},
            attachment={"attachment_security": 0.76, "repair_needed": False},
            recent_events=[{"title": "Phase begonnen"}],
            user_input="Bitte implementiere die nächste Phase",
            response_text="Ich setze die Umsetzung strukturiert fort.",
        )
        forecast = SelfForecastEngine().forecast(
            needs={"energy": 68, "social": 63, "curiosity": 58, "stability": 60, "achievement": 41, "rest": 72},
            development={"stage": "reflective_growth", "progress_to_next": 0.77},
            planning_state=planning,
            attachment={"attachment_security": 0.76, "repair_needed": False},
            social_arc=social_arc,
            world_model={"interaction_mode": "co_creation"},
            habit_dynamics=habit_dynamics,
        )
        history = HistoryEngine().record(
            [],
            {
                "clock": {"phase_label": "Tag 3, 12:00"},
                "current_activity": "architectural_reasoning",
                "active_goal": {"title": "Kognitive Entwicklung"},
                "homeostasis": homeostasis,
                "development": {"stage": "reflective_growth", "development_score": 0.74},
                "attachment_model": {"bond_type": "secure_collaboration"},
                "forecast_state": forecast,
                "habits": {"architecture_focus": {"label": "Architecture Focus", "strength": 0.8}},
            },
            "turn_finalize",
        )

        self.assertEqual(planning["planning_horizon"], "long_arc")
        self.assertTrue(forecast["protective_factors"])
        self.assertIn(social_arc["arc_name"], {"deepening_collaboration", "co_creation_momentum"})
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["goal"], "Kognitive Entwicklung")

    def test_finalize_turn_records_timeline(self):
        service = self._make_service()
        service.prepare_turn("Bitte plane die nächste Phase", history=[], emotions={"trust": 66})
        snapshot = service.finalize_turn(
            "Danke, wir machen das gemeinsam",
            "Ich implementiere die nächste Ausbaustufe strukturiert.",
            emotions_after={"trust": 72, "frustration": 4},
            prefrontal={"response_guidance": "Strukturiert weiterbauen"},
            global_workspace={"dominant_focus": {"label": "Kognitive Entwicklung"}},
        )

        self.assertTrue(snapshot.get("timeline_history"))
        self.assertGreaterEqual(snapshot.get("timeline_summary", {}).get("entries", 0), 1)
        self.assertTrue(snapshot.get("planning_state", {}).get("next_milestone"))
        self.assertTrue(snapshot.get("forecast_state", {}).get("next_turn_outlook"))

    def test_action_response_layer_builds_actions(self):
        layer = ActionResponseLayer()
        action_plan = layer.build_action_plan(
            {"response_strategy": "technical", "tone": "calm"},
            {
                "current_mode": "purposeful",
                "homeostasis": {"dominant_need": {"name": "achievement"}},
                "planning_state": {"next_milestone": "Architektur konkret ausbauen"},
                "social_arc": {"arc_name": "co_creation_momentum"},
                "forecast_state": {"next_turn_outlook": "ko-kreative Umsetzung mit kontrolliertem Scope"},
                "world_model": {"predicted_user_need": "konkrete Umsetzung"},
            },
            {"dominant_focus": {"label": "Kognitive Entwicklung"}},
        )

        self.assertEqual(action_plan["strategy"], "technical")
        self.assertIn("recommended_actions", action_plan)
        self.assertGreaterEqual(len(action_plan["recommended_actions"]), 3)
        self.assertIn("forecast", action_plan)


if __name__ == "__main__":
    unittest.main()