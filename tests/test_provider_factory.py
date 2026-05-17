"""Tests für die Brain-Factory und Provider-Parsing Edge-Cases."""

import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from unittest.mock import MagicMock

for mod in (
    "chromadb", "chromadb.config", "requests", "openai",
    "brain.groq_brain", "brain.nvidia_brain",
    "brain.brain_pipeline", "brain.steering_api_server",
    "brain.steering_backend", "brain.deep_think", "brain.global_workspace",
    "brain.action_response", "brain.response_parser", "brain.agents",
    "brain.cerebras_limits", "life", "memory", "memory.memory_engine",
    "memory.emotions_engine", "memory.sleep_phase", "memory.forgetting_curve",
    "memory.context_files", "memory.chat_manager", "memory.short_term_memory",
    "memory.short_term_memory_v2", "memory.personality_manager",
    "memory.function_registry", "memory.intent_processor", "memory.debug_logger",
    "sentence_transformers",
):
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

# ollama muss als Modul gemocked werden, damit brain.ollama_brain importierbar ist
sys.modules["ollama"] = MagicMock()

from brain import get_brain
from brain.vllm_brain import VLLMBrain
from brain.cerebras_brain import CerebrasBrain
from config.config import LLMProvider, _parse_provider, settings


def test_get_brain_vllm_returns_vllmbrain():
    brain = get_brain(LLMProvider.VLLM, model="Qwen/Qwen3.5-4B")
    assert isinstance(brain, VLLMBrain)
    assert brain.model == "Qwen/Qwen3.5-4B"


def test_get_brain_cerebras_returns_cerebrasbrain():
    brain = get_brain(LLMProvider.CEREBRAS, model="llama-3.1-8b")
    assert isinstance(brain, CerebrasBrain)


def test_get_brain_ollama_model_name_correct():
    brain = get_brain(LLMProvider.OLLAMA, model="qwen3.5:9b")
    assert brain.model == "qwen3.5:9b"


def test_get_brain_unknown_falls_back_to_ollama():
    original = settings.llm_provider
    try:
        settings.llm_provider = "invalid_provider_value_xyz"
        brain = get_brain()
        assert brain.model == settings.ollama_model
    finally:
        settings.llm_provider = original


def test_provider_enum_has_exactly_three_values():
    values = list(LLMProvider)
    assert len(values) == 3
    value_set = {v.value for v in values}
    assert value_set == {"vllm", "ollama", "cerebras"}


def test_parse_provider_valid_vllm():
    assert _parse_provider("vllm") == LLMProvider.VLLM
    assert _parse_provider("VLLM") == LLMProvider.VLLM


def test_parse_provider_valid_ollama():
    assert _parse_provider("ollama") == LLMProvider.OLLAMA


def test_parse_provider_valid_cerebras():
    assert _parse_provider("cerebras") == LLMProvider.CEREBRAS


def test_parse_provider_auto_returns_none():
    assert _parse_provider("auto") is None
    assert _parse_provider("") is None
    assert _parse_provider(None) is None


def test_parse_provider_groq_returns_none():
    assert _parse_provider("groq") is None


def test_parse_provider_nvidia_returns_none():
    assert _parse_provider("nvidia") is None


def test_parse_provider_unknown_returns_none():
    assert _parse_provider("anthropic") is None
    assert _parse_provider("openai") is None


def test_get_brain_uses_settings_provider_when_none():
    original = settings.llm_provider
    try:
        settings.llm_provider = LLMProvider.VLLM
        brain = get_brain()
        assert isinstance(brain, VLLMBrain)
    finally:
        settings.llm_provider = original


if __name__ == "__main__":
    tests = [
        test_get_brain_vllm_returns_vllmbrain,
        test_get_brain_cerebras_returns_cerebrasbrain,
        test_get_brain_ollama_model_name_correct,
        test_get_brain_unknown_falls_back_to_ollama,
        test_provider_enum_has_exactly_three_values,
        test_parse_provider_valid_vllm,
        test_parse_provider_valid_ollama,
        test_parse_provider_valid_cerebras,
        test_parse_provider_auto_returns_none,
        test_parse_provider_groq_returns_none,
        test_parse_provider_nvidia_returns_none,
        test_parse_provider_unknown_returns_none,
        test_get_brain_uses_settings_provider_when_none,
    ]
    passed = 0
    for test in tests:
        try:
            test()
            print(f"  [OK] {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
    print(f"\n{passed}/{len(tests)} tests passed")
