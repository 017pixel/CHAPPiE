"""Integritaetstests: Groq Support und keine stale Keys."""

import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from unittest.mock import MagicMock

sys.modules["ollama"] = MagicMock()
sys.modules["chromadb"] = MagicMock()
sys.modules["sentence_transformers"] = MagicMock()

from config.config import settings, LLMProvider
from config.config import DEFAULT_ROOT_CONFIG


def test_llm_provider_has_groq():
    values = [v.value for v in LLMProvider]
    assert "groq" in values


def test_llm_provider_enum_no_nvidia():
    values = [v.value for v in LLMProvider]
    assert "nvidia" not in values


def test_llm_provider_enum_has_exactly_three_values():
    values = list(LLMProvider)
    assert len(values) == 3
    value_set = {v.value for v in values}
    assert value_set == {"vllm", "ollama", "groq"}


def test_settings_export_has_groq_keys():
    exported = settings._export_root_values()
    groq_keys = [k for k in exported if "groq" in k.lower()]
    assert len(groq_keys) > 0, f"No groq keys found in export: {list(exported.keys())}"


def test_settings_has_groq_attributes():
    found = False
    for attr in dir(settings):
        if not attr.startswith("_") and "groq" in attr.lower():
            found = True
            break
    assert found, "No groq attributes on settings"


def test_default_root_config_has_groq_keys():
    flat = _flatten_config(DEFAULT_ROOT_CONFIG)
    groq_keys = [k for k in flat if "groq" in k.lower()]
    assert len(groq_keys) > 0, f"No groq keys in DEFAULT_ROOT_CONFIG: {flat}"


def test_default_root_config_has_no_stale_cerebras_keys():
    flat = _flatten_config(DEFAULT_ROOT_CONFIG)
    cerebras_keys = [k for k in flat if "cerebras" in k.lower()]
    assert len(cerebras_keys) == 0, f"Stale cerebras keys found: {cerebras_keys}"


def test_get_intent_model_groq():
    original_provider = settings.intent_provider
    original_model = settings.llm_provider
    try:
        settings.intent_provider = LLMProvider.GROQ
        settings.llm_provider = LLMProvider.GROQ
        model = settings.get_intent_model()
        assert isinstance(model, str)
        assert model == settings.intent_processor_model_groq
    finally:
        settings.intent_provider = original_provider
        settings.llm_provider = original_model


def test_get_query_extraction_model_groq():
    original_provider = settings.query_extraction_provider
    original_model = settings.llm_provider
    try:
        settings.query_extraction_provider = LLMProvider.GROQ
        settings.llm_provider = LLMProvider.GROQ
        model = settings.get_query_extraction_model()
        assert model == settings.query_extraction_groq_model
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
        test_llm_provider_has_groq,
        test_llm_provider_enum_no_nvidia,
        test_llm_provider_enum_has_exactly_three_values,
        test_settings_export_has_groq_keys,
        test_settings_has_groq_attributes,
        test_default_root_config_has_groq_keys,
        test_default_root_config_has_no_stale_cerebras_keys,
        test_get_intent_model_groq,
        test_get_query_extraction_model_groq,
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
