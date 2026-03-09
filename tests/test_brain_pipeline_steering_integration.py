"""Sichert ab, dass Brain-Struktur intakt bleibt und Steering nur am Ende anhaengt."""

import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from brain.agents.base_agent import AgentResult  # noqa: E402
from brain.brain_pipeline import BrainPipeline  # noqa: E402
from brain.global_workspace import GlobalWorkspace  # noqa: E402


class _StaticAgent:
    def __init__(self, name, data):
        self.name = name
        self.data = data

    def process(self, _input):
        return AgentResult(agent_name=self.name, success=True, data=self.data)


class _DummyLifeSimulation:
    def prepare_turn(self, *_args, **_kwargs):
        return {
            "homeostasis": {"dominant_need": {"name": "stability", "pressure": 63}, "guidance": "Bleib stabil"},
            "current_mode": "focused",
            "current_activity": "reasoning",
        }


class _DummySleepHandler:
    def increment_interaction(self):
        return None


class _DummyActionResponse:
    def build_action_plan(self, prefrontal, _life_context, global_workspace):
        return {"strategy": prefrontal.get("response_strategy", "conversational"), "focus": global_workspace.get("dominant_focus", {}).get("label")}

    def build_prompt_suffix(self, _prefrontal, _life_context, global_workspace):
        return global_workspace.get("broadcast", "")


class _DummyMemoryEngine:
    def search_memory(self, *_args, **_kwargs):
        return [{"id": "mem-1"}]


class _DummyContextFiles:
    def get_soul_context(self):
        return "Soul context"

    def get_user_context(self):
        return "User context"

    def get_preferences_context(self):
        return "Prefs"


class _DummySteeringManager:
    def __init__(self):
        self.called_with = None

    def get_steering_payload(self, emotions_after):
        self.called_with = dict(emotions_after)
        return {"steering": {"enabled": True, "emotion_state": dict(emotions_after), "vectors": [{"name": "happiness", "source": "base", "strength": 0.4}]}}

    def is_local_provider(self):
        return True


def test_brain_pipeline_keeps_context_workspace_and_tool_path_before_steering():
    pipeline = BrainPipeline.__new__(BrainPipeline)
    pipeline.sensory_cortex = _StaticAgent("sensory", {"input_type": "conversation", "urgency": "medium"})
    pipeline.amygdala = _StaticAgent("amygdala", {"primary_emotion": "curious", "emotional_intensity": 0.42, "reasoning": "Signal", "emotions_update": {"trust": {"delta": 5}}})
    pipeline.hippocampus = _StaticAgent("hippocampus", {"search_query": "bus verpasst", "context_relevance": {"need_soul_context": True, "need_user_context": True}, "short_term_entries": [{"content": "bus verpasst", "category": "event", "importance": "normal"}]})
    pipeline.prefrontal_cortex = _StaticAgent("prefrontal", {"response_strategy": "supportive"})
    pipeline.global_workspace = GlobalWorkspace()
    pipeline.action_response = _DummyActionResponse()
    pipeline.life_simulation = _DummyLifeSimulation()
    pipeline.sleep_handler = _DummySleepHandler()
    pipeline.steering_manager = _DummySteeringManager()
    pipeline._processing_count = 0

    emotions_before = {
        "happiness": 50,
        "sadness": 50,
        "frustration": 50,
        "trust": 55,
        "curiosity": 60,
        "motivation": 52,
        "energy": 51,
    }
    result = BrainPipeline.process(
        pipeline,
        user_input="Ich habe meinen Bus verpasst.",
        history=[],
        current_emotions=emotions_before,
        memory_engine=_DummyMemoryEngine(),
        context_files=_DummyContextFiles(),
        run_background=False,
    )

    assert "global_workspace" in result
    assert result["global_workspace"]["dominant_focus"]["label"]
    assert result["memories_found"] == 1
    assert len(result["tool_calls"]) == 1
    assert result["tool_calls"][0]["tool"] == "add_short_term_memory"
    assert result["steering_mode"] == "vector"
    assert pipeline.steering_manager.called_with["trust"] == 60


if __name__ == "__main__":
    test_brain_pipeline_keeps_context_workspace_and_tool_path_before_steering()
    print("OK: brain pipeline steering integration")