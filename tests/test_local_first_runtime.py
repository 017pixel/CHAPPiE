"""Lokale Runtime-Konfiguration für Brain-Agenten und Provider prüfen."""

import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from brain import get_brain
from brain.agents.amygdala import AmygdalaAgent
from brain.agents.basal_ganglia import BasalGangliaAgent
from brain.agents.hippocampus import HippocampusAgent
from brain.agents.memory_agent import MemoryAgent
from brain.agents.neocortex import NeocortexAgent
from brain.agents.prefrontal_cortex import PrefrontalCortexAgent
from brain.agents.sensory_cortex import SensoryCortexAgent
from brain.ollama_brain import OllamaBrain
from brain.vllm_brain import VLLMBrain
from config.brain_config import BRAIN_AGENT_CONFIGS
from config.config import LLMProvider, get_active_model, settings


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


if __name__ == "__main__":
    test_agents_use_brain_config_defaults()
    test_get_active_model_supports_vllm()
    test_get_brain_can_target_provider_and_model()
    print("OK: local-first runtime configuration is consistent")