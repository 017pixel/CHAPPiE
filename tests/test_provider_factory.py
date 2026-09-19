"""Tests für die Brain-Factory und Provider-Parsing Edge-Cases."""

import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from unittest.mock import MagicMock, patch  # noqa: E402

for mod in (
    "chromadb", "chromadb.config", "requests", "openai",
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

sys.modules["ollama"] = MagicMock()

from brain import get_brain  # noqa: E402
import brain as brain_module  # noqa: E402
from brain.vllm_brain import VLLMBrain  # noqa: E402
from brain.groq_brain import GroqBrain  # noqa: E402
from config.config import LLMProvider, _parse_provider, settings  # noqa: E402


def _assert_provider_setting_reload_creates_fresh_brain(provider, setting_name, first_value, second_value):
    original_value = getattr(settings, setting_name)
    original_cache = brain_module._brain_cache.copy()
    original_signatures = brain_module._brain_cache_signatures.copy()

    class _FakeBrain:
        def __init__(self, model=None):
            self.model = model
            self.runtime_setting = getattr(settings, setting_name)

    try:
        brain_module._brain_cache.clear()
        brain_module._brain_cache_signatures.clear()
        with patch.object(brain_module, "_load_export", return_value=_FakeBrain):
            setattr(settings, setting_name, first_value)
            first_brain = get_brain(provider, model="test-model")

            setattr(settings, setting_name, second_value)
            second_brain = get_brain(provider, model="test-model")

        assert first_brain is not second_brain
        assert first_brain.runtime_setting == first_value
        assert second_brain.runtime_setting == second_value
    finally:
        setattr(settings, setting_name, original_value)
        brain_module._brain_cache.clear()
        brain_module._brain_cache.update(original_cache)
        brain_module._brain_cache_signatures.clear()
        brain_module._brain_cache_signatures.update(original_signatures)


def test_get_brain_refreshes_vllm_client_after_url_reload():
    _assert_provider_setting_reload_creates_fresh_brain(
        LLMProvider.VLLM,
        "vllm_url",
        "http://vllm-before/v1",
        "http://vllm-after/v1",
    )


def test_get_brain_refreshes_ollama_client_after_host_reload():
    _assert_provider_setting_reload_creates_fresh_brain(
        LLMProvider.OLLAMA,
        "ollama_host",
        "http://ollama-before:11434",
        "http://ollama-after:11434",
    )


def test_get_brain_refreshes_groq_client_after_credential_reload():
    _assert_provider_setting_reload_creates_fresh_brain(
        LLMProvider.GROQ,
        "groq_api_key",
        "gsk_before",
        "gsk_after",
    )


def test_get_brain_vllm_returns_vllmbrain():
    brain = get_brain(LLMProvider.VLLM, model="Qwen/Qwen3.5-4B")
    assert isinstance(brain, VLLMBrain)
    assert brain.model == "Qwen/Qwen3.5-4B"


def test_get_brain_groq_returns_groqbrain():
    brain = get_brain(LLMProvider.GROQ, model="openai/gpt-oss-20b")
    assert isinstance(brain, GroqBrain)


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
    assert value_set == {"vllm", "ollama", "groq"}


def test_parse_provider_valid_vllm():
    assert _parse_provider("vllm") == LLMProvider.VLLM
    assert _parse_provider("VLLM") == LLMProvider.VLLM


def test_parse_provider_valid_ollama():
    assert _parse_provider("ollama") == LLMProvider.OLLAMA


def test_parse_provider_valid_groq():
    assert _parse_provider("groq") == LLMProvider.GROQ


def test_parse_provider_auto_returns_none():
    assert _parse_provider("auto") is None
    assert _parse_provider("") is None
    assert _parse_provider(None) is None


def test_parse_provider_groq_returns_none():
    assert _parse_provider("groq") == LLMProvider.GROQ


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
        test_get_brain_groq_returns_groqbrain,
        test_get_brain_ollama_model_name_correct,
        test_get_brain_unknown_falls_back_to_ollama,
        test_provider_enum_has_exactly_three_values,
        test_parse_provider_valid_vllm,
        test_parse_provider_valid_ollama,
        test_parse_provider_valid_groq,
        test_parse_provider_auto_returns_none,
        test_parse_provider_groq_returns_none,
        test_parse_provider_nvidia_returns_none,
        test_parse_provider_unknown_returns_none,
        test_get_brain_uses_settings_provider_when_none,
        test_get_brain_refreshes_vllm_client_after_url_reload,
        test_get_brain_refreshes_ollama_client_after_host_reload,
        test_get_brain_refreshes_groq_client_after_credential_reload,
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
