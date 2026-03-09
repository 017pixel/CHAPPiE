"""Schnelle Regressionstests fuer Debug-Monitor-Daten."""

import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from brain.global_workspace import GlobalWorkspace  # noqa: E402
from memory.debug_logger import DebugLogger  # noqa: E402


def test_global_workspace_exposes_math_trace():
    workspace = GlobalWorkspace().build(
        sensory={"input_type": "technical", "urgency": "high"},
        amygdala={"primary_emotion": "focused", "emotional_intensity": 0.4, "reasoning": "Signal"},
        hippocampus={"search_query": "debug monitor"},
        life_context={
            "homeostasis": {"dominant_need": {"name": "stability", "pressure": 62}, "guidance": "Bleib stabil"},
            "active_goal": {"title": "Debug Ausbau", "priority": 0.8, "progress": 0.2},
            "world_model": {"predicted_user_need": "transparency", "confidence": 0.7, "risk_factors": ["latency"]},
            "planning_state": {"planning_horizon": "near_term", "plan_confidence": 0.65, "bottlenecks": ["complexity"]},
            "forecast_state": {"risk_level": "medium"},
            "social_arc": {"arc_name": "trust_building", "arc_score": 0.55},
            "current_mode": "purposeful",
            "current_activity": "architectural_reasoning",
        },
        memories=[{"id": "1"}, {"id": "2"}],
    )
    assert isinstance(workspace.get("math_trace"), list)
    assert len(workspace["math_trace"]) >= 4
    assert any(step.get("source") == "homeostasis" for step in workspace["math_trace"])


def test_debug_logger_clear_and_dict_output():
    logger = DebugLogger(max_entries=5)
    logger.log_info("TURN", "Start", {"provider": "vllm"})
    logger.log_warning("TEST", "Warnung")
    entries = logger.get_entries_as_dict()
    assert len(entries) == 2
    assert entries[0]["category"] == "TURN"
    logger.clear()
    assert logger.get_entries() == []


def test_debug_logger_keeps_emotion_steering_details():
    logger = DebugLogger(max_entries=5)
    logger.log_info(
        "EMOTION_STEERING",
        "Layer-Manipulation vorbereitet",
        {
            "prompt_emotion_mode": "local_layer_only",
            "forced_local_qwen_steering": True,
            "emotion_state": {"happiness": 82, "sadness": 21},
            "base_vectors": [{"name": "happiness", "source": "base"}],
            "active_vectors": [
                {"name": "frustration", "strength": 1.02},
                {"name": "crashout", "strength": 0.88},
            ],
        },
    )
    entries = logger.get_entries_as_dict()
    assert entries[0]["category"] == "EMOTION_STEERING"
    assert entries[0]["details"]["prompt_emotion_mode"] == "local_layer_only"
    assert entries[0]["details"]["emotion_state"]["happiness"] == 82
    assert entries[0]["details"]["base_vectors"][0]["name"] == "happiness"
    assert entries[0]["details"]["active_vectors"][1]["name"] == "crashout"


if __name__ == "__main__":
    test_global_workspace_exposes_math_trace()
    test_debug_logger_clear_and_dict_output()
    test_debug_logger_keeps_emotion_steering_details()
    print("OK: debug monitor data")
