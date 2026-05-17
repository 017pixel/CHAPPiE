"""Integritaetstests: Keine stale groq/nvidia Keys in Settings und Provider-Parsing."""

import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from unittest.mock import MagicMock

sys.modules["ollama"] = MagicMock()
sys.modules["chromadb"] = MagicMock()
sys.modules["sentence_transformers"] = MagicMock()

from config.config import settings, LLMProvider, _parse_provider, get_active_model
from config.root_config import DEFAULT_ROOT_CONFIG, build_root_config


def test_llm_provider_enum_no_groq():
    values = [v.value for v in LLMProvider]
    assert "groq" not in values


def test_llm_provider_enum_no_nvidia():
    values = [v.value for v in LLMProvider]
    assert "nvidia" not in values


def test_settings_export_no_groq_keys():
    exported = settings._export_root_values()
    groq_keys = [k for k in exported if "groq" in k.lower()]
    assert len(groq_keys) == 0, f"Found stale groq keys: {groq_keys}"


def test_settings_export_no_nvidia_keys():
    exported = settings._export_root_values()
    nvidia_keys = [k for k in exported if "nvidia" in k.lower()]
    assert len(nvidia_keys) == 0, f"Found stale nvidia keys: {nvidia_keys}"


def test_settings_no_groq_attributes():
    for attr in dir(settings):
        if not attr.startswith("_"):
            assert "groq" not in attr.lower(), f"Stale groq attribute: {attr}"


def test_settings_no_nvidia_attributes():
    for attr in dir(settings):
        if not attr.startswith("_"):
            assert "nvidia" not in attr.lower(), f"Stale nvidia attribute: {attr}"


def test_default_root_config_no_groq():
    flat = _flatten_config(DEFAULT_ROOT_CONFIG)
    groq_keys = [k for k in flat if "groq" in k.lower()]
    assert len(groq_keys) == 0, f"Stale groq keys in DEFAULT_ROOT_CONFIG: {groq_keys}"


def test_default_root_config_no_nvidia():
    flat = _flatten_config(DEFAULT_ROOT_CONFIG)
    nvidia_keys = [k for k in flat if "nvidia" in k.lower()]
    assert len(nvidia_keys) == 0, f"Stale nvidia keys in DEFAULT_ROOT_CONFIG: {nvidia_keys}"


def test_default_root_config_has_cerebras_keys():
    flat = _flatten_config(DEFAULT_ROOT_CONFIG)
    cerebras_keys = [k for k in flat if "cerebras" in k.lower()]
    assert len(cerebras_keys) > 0, "Cerebras keys missing from DEFAULT_ROOT_CONFIG"


def test_get_active_model_no_groq_or_nvidia():
    original = settings.llm_provider
    try:
        for provider in list(LLMProvider):
            settings.llm_provider = provider
            model = get_active_model()
            assert isinstance(model, str) and len(model) > 0
            assert "groq" not in model.lower()
            assert "nvidia" not in model.lower()
    finally:
        settings.llm_provider = original


def test_get_intent_model_cerebras():
    original_provider = settings.intent_provider
    original_model = settings.llm_provider
    try:
        settings.intent_provider = LLMProvider.CEREBRAS
        settings.llm_provider = LLMProvider.CEREBRAS
        model = settings.get_intent_model()
        assert isinstance(model, str)
        assert model == settings.intent_processor_model_cerebras
    finally:
        settings.intent_provider = original_provider
        settings.llm_provider = original_model


def test_get_query_extraction_model_ollama():
    original_provider = settings.query_extraction_provider
    original_model = settings.llm_provider
    try:
        settings.query_extraction_provider = LLMProvider.OLLAMA
        settings.llm_provider = LLMProvider.OLLAMA
        model = settings.get_query_extraction_model()
        assert model == settings.query_extraction_ollama_model
    finally:
        settings.query_extraction_provider = original_provider
        settings.llm_provider = original_model


def _flatten_config(config, prefix=""):
    result = []
    for key, value in config.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.extend(_flatten_config(value, full_key))
        else:
            result.append(full_key)
    return result


if __name__ == "__main__":
    tests = [
        test_llm_provider_enum_no_groq,
        test_llm_provider_enum_no_nvidia,
        test_settings_export_no_groq_keys,
        test_settings_export_no_nvidia_keys,
        test_settings_no_groq_attributes,
        test_settings_no_nvidia_attributes,
        test_default_root_config_no_groq,
        test_default_root_config_no_nvidia,
        test_default_root_config_has_cerebras_keys,
        test_get_active_model_no_groq_or_nvidia,
        test_get_intent_model_cerebras,
        test_get_query_extraction_model_ollama,
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
