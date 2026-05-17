"""Unit-Tests für CerebrasBrain — ohne echte API-Calls."""

import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from unittest.mock import MagicMock, patch

for mod in (
    "ollama", "chromadb", "chromadb.config", "requests", "openai",
    "brain.ollama_brain", "brain.groq_brain", "brain.nvidia_brain",
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

from brain.cerebras_brain import CerebrasBrain, CEREBRAS_MODELS
from brain.base_brain import BaseBrain, Message, GenerationConfig
from config.config import settings, LLMProvider


def test_cerebrasbrain_is_basebrain_subclass():
    assert issubclass(CerebrasBrain, BaseBrain)


def test_is_missing_key_empty():
    assert CerebrasBrain._is_missing_key("") is True
    assert CerebrasBrain._is_missing_key("   ") is True
    assert CerebrasBrain._is_missing_key(None) is True


def test_is_missing_key_placeholder():
    assert CerebrasBrain._is_missing_key("DEIN_CEREBRAS_API_KEY_HIER") is True
    assert CerebrasBrain._is_missing_key("DEIN_KEY") is True


def test_is_missing_key_valid():
    assert CerebrasBrain._is_missing_key("csk-1234567890abcdef") is False


def test_get_model_info_without_key():
    brain = CerebrasBrain(model="llama-3.1-8b", api_key="")
    info = brain.get_model_info()
    assert info["name"] == "llama-3.1-8b"
    assert info["provider"] == "cerebras"
    assert info["local"] is False
    assert info["api_configured"] is False


def test_get_model_info_with_key():
    brain = CerebrasBrain(model="qwen-3-235b-a22b-instruct-2507", api_key="csk-testkey123")
    info = brain.get_model_info()
    assert info["provider"] == "cerebras"
    assert info["name"] == "qwen-3-235b-a22b-instruct-2507"
    assert info["api_configured"] is True
    assert info["local"] is False


def test_is_available_false_without_key():
    brain = CerebrasBrain(model="llama-3.1-8b", api_key="")
    assert brain.is_available() is False


def test_is_available_true_with_valid_key():
    with patch("brain.cerebras_brain.OpenAI") as mock_openai:
        mock_openai.return_value = MagicMock()
        brain = CerebrasBrain(model="llama-3.1-8b", api_key="csk-testkey123")
        assert brain.is_available() is True


def test_generate_returns_error_when_not_initialized():
    brain = CerebrasBrain(model="llama-3.1-8b", api_key="")
    messages = [Message(role="user", content="Hallo")]
    config = GenerationConfig(max_tokens=50, temperature=0.7, stream=False)
    response = brain.generate(messages, config)
    assert isinstance(response, str)
    assert "FEHLER" in response


def test_list_models_returns_empty_when_not_initialized():
    brain = CerebrasBrain(model="llama-3.1-8b", api_key="")
    assert brain.list_models() == []


def test_cerebras_models_dict_not_empty():
    assert len(CEREBRAS_MODELS) == 2
    assert "llama-3.1-8b" in CEREBRAS_MODELS
    assert "qwen-3-235b-a22b-instruct-2507" in CEREBRAS_MODELS


def test_model_defaults_from_settings():
    original_model = settings.cerebras_model
    try:
        settings.cerebras_model = "qwen-3-235b-a22b-instruct-2507"
        brain = CerebrasBrain(api_key="csk-test")
        assert brain.model == "qwen-3-235b-a22b-instruct-2507"
    finally:
        settings.cerebras_model = original_model


def test_model_explicit_overrides_settings():
    brain = CerebrasBrain(model="qwen-3-235b-a22b-instruct-2507", api_key="csk-test")
    assert brain.model == "qwen-3-235b-a22b-instruct-2507"


def test_api_key_explicit_overrides_settings():
    brain = CerebrasBrain(api_key="csk-explicit", model="llama-3.1-8b")
    assert brain.api_key == "csk-explicit"


if __name__ == "__main__":
    tests = [
        test_cerebrasbrain_is_basebrain_subclass,
        test_is_missing_key_empty,
        test_is_missing_key_placeholder,
        test_is_missing_key_valid,
        test_get_model_info_without_key,
        test_get_model_info_with_key,
        test_is_available_false_without_key,
        test_is_available_true_with_valid_key,
        test_generate_returns_error_when_not_initialized,
        test_list_models_returns_empty_when_not_initialized,
        test_cerebras_models_dict_not_empty,
        test_model_defaults_from_settings,
        test_model_explicit_overrides_settings,
        test_api_key_explicit_overrides_settings,
    ]
    passed = 0
    for test in tests:
        try:
            test()
            print(f"  [OK] {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
