"""Unit-Tests für GroqBrain — ohne echte API-Calls."""

import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from unittest.mock import MagicMock, patch

for mod in (
    "ollama", "chromadb", "chromadb.config", "requests", "openai",
    "brain.ollama_brain",
    "brain.nvidia_brain",
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

from brain.groq_brain import GroqBrain, GROQ_MODELS
from brain.base_brain import BaseBrain, Message, GenerationConfig
from config.config import settings, LLMProvider


def test_groqbrain_is_basebrain_subclass():
    assert issubclass(GroqBrain, BaseBrain)


def test_is_missing_key_empty():
    assert GroqBrain._is_missing_key("") is True
    assert GroqBrain._is_missing_key("   ") is True
    assert GroqBrain._is_missing_key(None) is True


def test_is_missing_key_invalid():
    assert GroqBrain._is_missing_key("DEIN_GROQ_API_KEY_HIER") is True
    assert GroqBrain._is_missing_key("DEIN_KEY") is True


def test_is_missing_key_valid():
    assert GroqBrain._is_missing_key("gsk_1234567890abcdef") is False


def test_get_model_info_without_key():
    original_key = settings.groq_api_key
    try:
        settings.groq_api_key = ""
        brain = GroqBrain(model="llama-3.3-70b-versatile", api_key="")
        info = brain.get_model_info()
        assert info["name"] == "llama-3.3-70b-versatile"
        assert info["provider"] == "groq"
        assert info["local"] is False
        assert info["api_configured"] is False
    finally:
        settings.groq_api_key = original_key


def test_get_model_info_with_key():
    original_key = settings.groq_api_key
    try:
        settings.groq_api_key = ""
        brain = GroqBrain(model="openai/gpt-oss-120b", api_key="gsk_testkey123")
        info = brain.get_model_info()
        assert info["provider"] == "groq"
        assert info["name"] == "openai/gpt-oss-120b"
        assert info["api_configured"] is True
        assert info["local"] is False
    finally:
        settings.groq_api_key = original_key


def test_is_available_false_without_key():
    original_key = settings.groq_api_key
    try:
        settings.groq_api_key = ""
        brain = GroqBrain(model="llama-3.1-8b-instant", api_key="")
        assert brain.is_available() is False
    finally:
        settings.groq_api_key = original_key


def test_is_available_true_with_valid_key():
    original_key = settings.groq_api_key
    try:
        settings.groq_api_key = ""
        with patch("brain.groq_brain.OpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()
            brain = GroqBrain(model="llama-3.1-8b-instant", api_key="gsk_testkey123")
            assert brain.is_available() is True
    finally:
        settings.groq_api_key = original_key


def test_generate_returns_error_when_not_initialized():
    original_key = settings.groq_api_key
    try:
        settings.groq_api_key = ""
        brain = GroqBrain(model="llama-3.1-8b-instant", api_key="")
        messages = [Message(role="user", content="Hallo")]
        config = GenerationConfig(max_tokens=50, temperature=0.7, stream=False)
        response = brain.generate(messages, config)
        assert isinstance(response, str)
        assert "FEHLER" in response
    finally:
        settings.groq_api_key = original_key


def test_list_models_returns_empty_when_not_initialized():
    original_key = settings.groq_api_key
    try:
        settings.groq_api_key = ""
        brain = GroqBrain(model="llama-3.1-8b-instant", api_key="")
        assert brain.list_models() == []
    finally:
        settings.groq_api_key = original_key


def test_groq_models_dict_not_empty():
    assert len(GROQ_MODELS) >= 5
    assert "llama-3.1-8b-instant" in GROQ_MODELS
    assert "openai/gpt-oss-120b" in GROQ_MODELS


def test_model_defaults_from_settings():
    original_model = settings.groq_model
    original_key = settings.groq_api_key
    try:
        settings.groq_api_key = ""
        settings.groq_model = "openai/gpt-oss-120b"
        brain = GroqBrain(api_key="gsk_test")
        assert brain.model == "openai/gpt-oss-120b"
    finally:
        settings.groq_model = original_model
        settings.groq_api_key = original_key


def test_model_explicit_overrides_settings():
    original_key = settings.groq_api_key
    try:
        settings.groq_api_key = ""
        brain = GroqBrain(model="qwen/qwen3-32b", api_key="gsk_test")
        assert brain.model == "qwen/qwen3-32b"
    finally:
        settings.groq_api_key = original_key


def test_api_key_explicit_overrides_settings():
    original_key = settings.groq_api_key
    try:
        settings.groq_api_key = ""
        brain = GroqBrain(api_key="gsk_explicit", model="llama-3.1-8b-instant")
        assert brain.api_key == "gsk_explicit"
    finally:
        settings.groq_api_key = original_key


if __name__ == "__main__":
    tests = [
        test_groqbrain_is_basebrain_subclass,
        test_is_missing_key_empty,
        test_is_missing_key_invalid,
        test_is_missing_key_valid,
        test_get_model_info_without_key,
        test_get_model_info_with_key,
        test_is_available_false_without_key,
        test_is_available_true_with_valid_key,
        test_generate_returns_error_when_not_initialized,
        test_list_models_returns_empty_when_not_initialized,
        test_groq_models_dict_not_empty,
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
