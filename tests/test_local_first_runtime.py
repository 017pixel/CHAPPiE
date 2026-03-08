"""Lokale Runtime-Konfiguration für Brain-Agenten und Provider prüfen."""

import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from brain import get_brain
from brain.action_response import ActionResponseLayer
from brain.agents.amygdala import AmygdalaAgent
from brain.agents.basal_ganglia import BasalGangliaAgent
from brain.agents.hippocampus import HippocampusAgent
from brain.agents.memory_agent import MemoryAgent
from brain.agents.neocortex import NeocortexAgent
from brain.agents.prefrontal_cortex import PrefrontalCortexAgent
from brain.agents.sensory_cortex import SensoryCortexAgent
from brain.agents.steering_manager import SteeringManager
from brain.ollama_brain import OllamaBrain
from brain.vllm_brain import VLLMBrain
from config.brain_config import BRAIN_AGENT_CONFIGS
from config.config import LLMProvider, get_active_model, settings
from config.prompts import build_system_prompt


def assert_agent_matches_config(agent, config_key: str):
    cfg = BRAIN_AGENT_CONFIGS[config_key]
    assert agent.provider == cfg.provider, f"{config_key}: provider mismatch"
    assert agent.model_id == cfg.model_id, f"{config_key}: model mismatch"
    assert agent.default_temperature == cfg.temperature, f"{config_key}: temperature mismatch"
    assert agent.default_max_tokens == cfg.max_tokens, f"{config_key}: max_tokens mismatch"


def test_agents_use_brain_config_defaults():
    assert_agent_matches_config(SensoryCortexAgent(), "sensory_cortex")
    assert_agent_matches_config(AmygdalaAgent(), "amygdala")
    assert_agent_matches_config(HippocampusAgent(), "hippocampus")
    assert_agent_matches_config(PrefrontalCortexAgent(), "prefrontal_cortex")
    assert_agent_matches_config(BasalGangliaAgent(), "basal_ganglia")
    assert_agent_matches_config(NeocortexAgent(), "neocortex")
    assert_agent_matches_config(MemoryAgent(), "memory_agent")


def test_get_active_model_supports_vllm():
    original_provider = settings.llm_provider
    original_model = settings.vllm_model
    try:
        settings.llm_provider = LLMProvider.VLLM
        settings.vllm_model = "Qwen/Test-Model"
        assert get_active_model() == "Qwen/Test-Model"
    finally:
        settings.llm_provider = original_provider
        settings.vllm_model = original_model


def test_get_brain_can_target_provider_and_model():
    vllm_brain = get_brain(provider=LLMProvider.VLLM, model="Qwen/Test-Model")
    assert isinstance(vllm_brain, VLLMBrain)
    assert vllm_brain.model == "Qwen/Test-Model"

    ollama_brain = get_brain(provider=LLMProvider.OLLAMA, model="qwen2.5:7b")
    assert isinstance(ollama_brain, OllamaBrain)
    assert ollama_brain.model == "qwen2.5:7b"


def test_local_qwen_prefers_layer_only_emotion_mode():
    original_provider = settings.llm_provider
    original_model = settings.vllm_model
    original_steering = settings.enable_steering
    try:
        settings.llm_provider = LLMProvider.VLLM
        settings.vllm_model = "Qwen/Qwen3.5-35B-A3B"
        settings.enable_steering = False
        manager = SteeringManager()

        assert manager.should_force_local_emotion_steering() is True
        assert manager.should_use_prompt_emotions() is False

        prompt = build_system_prompt(happiness=88, frustration=82, include_emotion_status=False)
        assert "DEIN AKTUELLER EMOTIONALER STATUS" not in prompt

        payload = manager.get_steering_payload({
            "happiness": 22,
            "trust": 15,
            "energy": 72,
            "curiosity": 44,
            "frustration": 96,
            "motivation": 80,
            "sadness": 14,
        }, force=True)
        assert payload.get("steering", {}).get("enabled") is True
        assert payload["steering"]["dominant_emotion"] in {"frustration", "crashout", "guarded"}
        assert any(v.get("name") == "crashout" for v in payload["steering"].get("vectors", []))
    finally:
        settings.llm_provider = original_provider
        settings.vllm_model = original_model
        settings.enable_steering = original_steering


def test_api_models_keep_prompt_emotion_rules():
    original_provider = settings.llm_provider
    original_model = settings.groq_model
    try:
        settings.llm_provider = LLMProvider.GROQ
        settings.groq_model = "openai/gpt-oss-120b"
        manager = SteeringManager()

        assert manager.should_force_local_emotion_steering() is False
        assert manager.should_use_prompt_emotions() is True

        prompt = build_system_prompt(happiness=88, frustration=82, include_emotion_status=True)
        assert "DEIN AKTUELLER EMOTIONALER STATUS" in prompt
    finally:
        settings.llm_provider = original_provider
        settings.groq_model = original_model


def test_action_response_suffix_can_skip_fixed_tone_directives():
    suffix = ActionResponseLayer().build_prompt_suffix(
        {"response_strategy": "conversational", "response_guidance": "Antworte direkt."},
        None,
        None,
    )
    assert "- Strategie: conversational" in suffix
    assert "- Ton:" not in suffix
    assert "Antworte direkt." in suffix


if __name__ == "__main__":
    test_agents_use_brain_config_defaults()
    test_get_active_model_supports_vllm()
    test_get_brain_can_target_provider_and_model()
    test_local_qwen_prefers_layer_only_emotion_mode()
    test_api_models_keep_prompt_emotion_rules()
    test_action_response_suffix_can_skip_fixed_tone_directives()
    print("OK: local-first runtime configuration is consistent")