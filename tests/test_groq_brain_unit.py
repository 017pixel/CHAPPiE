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
    "memory.personality_manager",
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
        brain = GroqBrain(model="openai/gpt-oss-120b", api_key="")
        info = brain.get_model_info()
        assert info["name"] == "openai/gpt-oss-120b"
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
        brain = GroqBrain(model="openai/gpt-oss-20b", api_key="")
        assert brain.is_available() is False
    finally:
        settings.groq_api_key = original_key


def test_is_available_true_with_valid_key():
    original_key = settings.groq_api_key
    try:
        settings.groq_api_key = ""
        with patch("brain.groq_brain.OpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()
            brain = GroqBrain(model="openai/gpt-oss-20b", api_key="gsk_testkey123")
            assert brain.is_available() is True
    finally:
        settings.groq_api_key = original_key


def test_generate_returns_error_when_not_initialized():
    original_key = settings.groq_api_key
    try:
        settings.groq_api_key = ""
        brain = GroqBrain(model="openai/gpt-oss-20b", api_key="")
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
        brain = GroqBrain(model="openai/gpt-oss-20b", api_key="")
        assert brain.list_models() == []
    finally:
        settings.groq_api_key = original_key


def test_groq_models_dict_not_empty():
    assert len(GROQ_MODELS) >= 5
    assert "openai/gpt-oss-20b" in GROQ_MODELS
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
        brain = GroqBrain(api_key="gsk_explicit", model="openai/gpt-oss-20b")
        assert brain.api_key == "gsk_explicit"
    finally:
        settings.groq_api_key = original_key


def test_sync_generation_passes_configured_top_p():
    original_top_p = settings.top_p
    original_chain_of_thought = settings.chain_of_thought
    try:
        settings.top_p = 0.9
        settings.chain_of_thought = False
        brain = GroqBrain.__new__(GroqBrain)
        brain._is_initialized = True
        brain.model = "openai/gpt-oss-120b"
        brain.client = MagicMock()
        brain._claim_quota = MagicMock(return_value=None)
        response = MagicMock()
        response.choices[0].message.content = "Antwort"
        brain.client.chat.completions.create.return_value = response

        result = brain._sync_generate(
            [{"role": "user", "content": "Hallo"}],
            GenerationConfig(max_tokens=50, temperature=0.7, stream=False),
        )
        assert result == "Antwort"
        kwargs = brain.client.chat.completions.create.call_args.kwargs
        assert kwargs["temperature"] == 0.7
        assert kwargs["top_p"] == 0.9
        assert kwargs["reasoning_effort"] == "low"
        assert kwargs["max_completion_tokens"] == 1024
        assert kwargs["extra_body"] == {"include_reasoning": False}
        assert "max_tokens" not in kwargs
        assert "top_k" not in kwargs
    finally:
        settings.top_p = original_top_p
        settings.chain_of_thought = original_chain_of_thought


def test_non_reasoning_groq_model_keeps_requested_max_tokens():
    brain = GroqBrain.__new__(GroqBrain)
    brain.model = "meta-llama/llama-4-scout-17b-16e-instruct"
    kwargs = {}
    brain._apply_model_specific_options(
        kwargs,
        GenerationConfig(max_tokens=77, temperature=0.7, stream=False),
    )
    assert kwargs == {"max_tokens": 77}


def test_gpt_oss_thinking_enabled_does_not_exclude_reasoning_output():
    original_chain_of_thought = settings.chain_of_thought
    try:
        settings.chain_of_thought = True
        brain = GroqBrain.__new__(GroqBrain)
        brain.model = "openai/gpt-oss-120b"
        kwargs = {}
        brain._apply_model_specific_options(
            kwargs,
            GenerationConfig(max_tokens=77, temperature=0.7, stream=False),
        )
        assert kwargs == {"max_completion_tokens": 77, "reasoning_effort": "medium"}
    finally:
        settings.chain_of_thought = original_chain_of_thought


def test_sync_generation_retries_short_rate_limit_without_exposing_error():
    brain = GroqBrain.__new__(GroqBrain)
    brain._is_initialized = True
    brain.model = "openai/gpt-oss-120b"
    brain.client = MagicMock()
    brain._claim_quota = MagicMock(return_value=None)
    response = MagicMock()
    response.choices[0].message.content = "Antwort nach Retry"
    brain.client.chat.completions.create.side_effect = [
        RuntimeError("Error code: 429 rate limit. Please try again in 10ms."),
        response,
    ]
    with patch("brain.groq_brain.time.sleep") as sleep:
        result = brain._sync_generate(
            [{"role": "user", "content": "Hallo"}],
            GenerationConfig(max_tokens=50, temperature=0.7, stream=False),
        )
    assert result == "Antwort nach Retry"
    assert brain.client.chat.completions.create.call_count == 2
    sleep.assert_called_once_with(0.25)


def test_stream_generation_retries_rate_limit_before_first_token():
    brain = GroqBrain.__new__(GroqBrain)
    brain._is_initialized = True
    brain.model = "openai/gpt-oss-120b"
    brain.client = MagicMock()
    brain._claim_quota = MagicMock(return_value=None)
    chunk = MagicMock()
    chunk.choices[0].delta.content = "Streaming-Antwort"
    brain.client.chat.completions.create.side_effect = [
        RuntimeError("Error code: 429 rate limit. Please try again in 20ms."),
        [chunk],
    ]
    with patch("brain.groq_brain.time.sleep") as sleep:
        result = list(brain._stream_generate(
            [{"role": "user", "content": "Hallo"}],
            GenerationConfig(max_tokens=50, temperature=0.7, stream=True),
        ))
    assert result == ["Streaming-Antwort"]
    assert brain.client.chat.completions.create.call_count == 2
    sleep.assert_called_once_with(0.25)


def test_daily_rate_limit_duration_is_parsed_without_busy_retrying():
    delay = GroqBrain._rate_limit_retry_delay(
        RuntimeError("Error code: 429 tokens per day. Please try again in 23m49.056s."),
        0,
    )
    assert delay == 1429.056


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
        test_sync_generation_passes_configured_top_p,
        test_non_reasoning_groq_model_keeps_requested_max_tokens,
        test_gpt_oss_thinking_enabled_does_not_exclude_reasoning_output,
        test_sync_generation_retries_short_rate_limit_without_exposing_error,
        test_stream_generation_retries_rate_limit_before_first_token,
        test_daily_rate_limit_duration_is_parsed_without_busy_retrying,
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
