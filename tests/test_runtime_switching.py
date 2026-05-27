"""Gezielte Regressionstests für Provider-Switching und Berliner Life-Zeit."""

import os
import sys
from datetime import datetime
from unittest.mock import MagicMock

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

for mod in (
    "chromadb", "chromadb.config", "requests", "openai",
    "brain.groq_brain", "brain.nvidia_brain",
    "brain.steering_api_server", "brain.steering_backend",
    "brain.deep_think", "brain.global_workspace",
    "brain.action_response", "brain.groq_limits",
    "memory.emotions_engine", "memory.chat_manager",
    "memory.short_term_memory", "memory.short_term_memory_v2",
    "memory.personality_manager", "memory.function_registry",
    "memory.intent_processor", "memory.debug_logger",
    "sentence_transformers",
):
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

sys.modules["ollama"] = MagicMock()

from config.config import LLMProvider, settings
from config.root_config import ROOT_CONFIG_PATH as USER_SETTINGS_PATH
from brain.response_parser import looks_like_model_error
from life.service import LifeSimulationService


TRACKED_SETTINGS = (
    "llm_provider",
    "intent_provider",
    "query_extraction_provider",
)


def _backup_settings_state():
    file_exists = USER_SETTINGS_PATH.exists()
    file_content = USER_SETTINGS_PATH.read_text(encoding="utf-8") if file_exists else None
    values = {name: getattr(settings, name) for name in TRACKED_SETTINGS}
    return file_exists, file_content, values


def _restore_settings_state(file_exists, file_content, values):
    for name, value in values.items():
        setattr(settings, name, value)
    if file_exists:
        USER_SETTINGS_PATH.write_text(file_content, encoding="utf-8")
    elif USER_SETTINGS_PATH.exists():
        USER_SETTINGS_PATH.unlink()


def test_provider_switch_resets_old_followers_to_auto():
    backup = _backup_settings_state()
    try:
        settings.llm_provider = LLMProvider.GROQ
        settings.intent_provider = LLMProvider.GROQ
        settings.query_extraction_provider = LLMProvider.GROQ

        settings.update_from_ui(
            llm_provider="ollama",
            intent_provider="groq",
            query_extraction_provider="groq",
        )

        assert settings.llm_provider == LLMProvider.OLLAMA
        assert settings.intent_provider is None
        assert settings.query_extraction_provider is None
    finally:
        _restore_settings_state(*backup)


class _FixedBerlinLifeService(LifeSimulationService):
    def _get_berlin_now(self):
        return datetime(2026, 3, 7, 19, 14, tzinfo=self.BERLIN_TZ)


def test_life_snapshot_uses_berlin_time():
    service = _FixedBerlinLifeService()
    service._state.last_updated = ""
    service._sync_clock_to_berlin()
    snapshot = service.get_snapshot()

    assert snapshot["clock"]["minute_of_day"] == (19 * 60 + 14)
    assert snapshot["clock"]["phase"] == "exploration"
    assert snapshot["clock"]["timezone"] == "Europe/Berlin"
    assert "19:14" in snapshot["clock"]["phase_label"]


def test_model_error_detection_catches_sticky_provider_errors_and_empty_responses():
    assert looks_like_model_error("Groq Fehler: Error 404 model not found") is True
    assert looks_like_model_error("   ") is True
    assert looks_like_model_error("Hallo Benjamin, schön dich zu sehen.") is False


def test_error_detection_catches_all_active_providers():
    assert looks_like_model_error("vLLM Fehler: timeout") is True
    assert looks_like_model_error("VLLM Fehler: timeout") is True
    assert looks_like_model_error("Ollama Fehler: connection refused") is True
    assert looks_like_model_error("Groq Fehler: rate limit") is True
    assert looks_like_model_error("Groq Fehler: timeout") is True
    assert looks_like_model_error("NVIDIA Fehler: timeout") is False


def test_provider_switch_vllm_to_groq_preserves_models():
    backup = _backup_settings_state()
    try:
        settings.llm_provider = LLMProvider.VLLM
        settings.vllm_model = "Qwen/Qwen3.5-4B"
        settings.llm_provider = LLMProvider.GROQ
        settings.groq_model = "qwen-3-235b-a22b-instruct-2507"

        from config.config import get_active_model
        assert settings.llm_provider == LLMProvider.GROQ
        assert get_active_model() == "qwen-3-235b-a22b-instruct-2507"
        assert settings.vllm_model == "Qwen/Qwen3.5-4B"
    finally:
        _restore_settings_state(*backup)


def test_provider_switch_groq_to_ollama_keeps_groq_model():
    backup = _backup_settings_state()
    try:
        settings.llm_provider = LLMProvider.GROQ
        settings.groq_model = "llama-3.1-8b"
        settings.llm_provider = LLMProvider.OLLAMA

        from config.config import get_active_model
        assert get_active_model() == settings.ollama_model
        assert settings.groq_model == "llama-3.1-8b"
    finally:
        _restore_settings_state(*backup)


def test_intent_model_resolves_per_provider():
    backup = _backup_settings_state()
    try:
        settings.llm_provider = LLMProvider.GROQ
        settings.intent_provider = LLMProvider.GROQ
        assert settings.get_intent_model() == settings.intent_processor_model_groq

        settings.llm_provider = LLMProvider.VLLM
        settings.intent_provider = LLMProvider.VLLM
        assert settings.get_intent_model() == settings.intent_processor_model_vllm

        settings.llm_provider = LLMProvider.OLLAMA
        settings.intent_provider = LLMProvider.OLLAMA
        assert settings.get_intent_model() == settings.intent_processor_model_ollama
    finally:
        _restore_settings_state(*backup)


def test_query_extraction_model_resolves_per_provider():
    backup = _backup_settings_state()
    try:
        settings.llm_provider = LLMProvider.GROQ
        settings.query_extraction_provider = LLMProvider.GROQ
        assert settings.get_query_extraction_model() == settings.query_extraction_groq_model

        settings.llm_provider = LLMProvider.VLLM
        settings.query_extraction_provider = LLMProvider.VLLM
        assert settings.get_query_extraction_model() == settings.query_extraction_vllm_model

        settings.llm_provider = LLMProvider.OLLAMA
        settings.query_extraction_provider = LLMProvider.OLLAMA
        assert settings.get_query_extraction_model() == settings.query_extraction_ollama_model
    finally:
        _restore_settings_state(*backup)


def test_auto_intent_falls_back_to_main_provider():
    backup = _backup_settings_state()
    try:
        settings.llm_provider = LLMProvider.GROQ
        settings.intent_provider = None
        assert settings.get_intent_model() == settings.intent_processor_model_groq

        settings.llm_provider = LLMProvider.VLLM
        settings.intent_provider = None
        assert settings.get_intent_model() == settings.intent_processor_model_vllm
    finally:
        _restore_settings_state(*backup)


if __name__ == "__main__":
    test_provider_switch_resets_old_followers_to_auto()
    test_life_snapshot_uses_berlin_time()
    test_model_error_detection_catches_sticky_provider_errors_and_empty_responses()
    test_error_detection_catches_all_active_providers()
    test_provider_switch_vllm_to_groq_preserves_models()
    test_provider_switch_groq_to_ollama_keeps_groq_model()
    test_intent_model_resolves_per_provider()
    test_query_extraction_model_resolves_per_provider()
    test_auto_intent_falls_back_to_main_provider()
    print("OK: runtime switching and Berlin clock regression tests passed")
