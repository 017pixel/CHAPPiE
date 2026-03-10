"""CLI soll auch ohne optionales colorama importierbar bleiben."""

import contextlib
import importlib
import io
import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)


def test_chappie_cli_imports_without_colorama():
    sys.modules.pop("colorama", None)
    sys.modules.pop("chappie_brain_cli", None)

    module = importlib.import_module("chappie_brain_cli")

    assert module.Colors.RESET is not None
    assert callable(module.print_log)


def test_cli_runtime_uses_effective_model_resolvers():
    module = importlib.import_module("chappie_brain_cli")
    cli = module.CHAPPiEBrainCLI.__new__(module.CHAPPiEBrainCLI)

    class _Backend:
        @staticmethod
        def get_status():
            return {"model": "Qwen/Qwen3.5-4B"}

    cli.backend = _Backend()
    cli._build_steering_report = lambda: {"mode": "local_layer_only", "prompt_emotions_enabled": False}

    original_intent_provider = module.settings.intent_provider
    original_query_provider = module.settings.query_extraction_provider
    original_vllm_model = module.settings.vllm_model
    original_intent_vllm = module.settings.intent_processor_model_vllm
    original_query_vllm = module.settings.query_extraction_vllm_model
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            module.settings.intent_provider = None
            module.settings.query_extraction_provider = None
            module.settings.vllm_model = "Qwen/Qwen3.5-4B"
            module.settings.intent_processor_model_vllm = "Qwen/Intent-Override"
            module.settings.query_extraction_vllm_model = "Qwen/Query-Override"
            cli._show_runtime()
    finally:
        module.settings.intent_provider = original_intent_provider
        module.settings.query_extraction_provider = original_query_provider
        module.settings.vllm_model = original_vllm_model
        module.settings.intent_processor_model_vllm = original_intent_vllm
        module.settings.query_extraction_vllm_model = original_query_vllm

    output = buf.getvalue()
    assert "Intent-Modell:      Qwen/Qwen3.5-4B" in output
    assert "Query-Modell:       Qwen/Qwen3.5-4B" in output


if __name__ == "__main__":
    test_chappie_cli_imports_without_colorama()
    test_cli_runtime_uses_effective_model_resolvers()
    print("OK: CLI import fallback")