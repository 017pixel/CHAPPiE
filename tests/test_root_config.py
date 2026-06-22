import sys
from pathlib import Path
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config.root_config import build_root_config, load_root_config_values, write_root_config


def test_root_config_roundtrip_keeps_groq_small_task_defaults():
    with TemporaryDirectory() as tmp_dir:
        config_path = Path(tmp_dir) / "CHAPPIE_CONFIG.json"
        write_root_config(
            {
                "GROQ_API_KEY": "test-key",
                "LLM_PROVIDER": "vllm",
                "VLLM_MODEL": "Qwen/Qwen3.5-4B",
                "QUERY_EXTRACTION_PROVIDER": "groq",
            },
            path=config_path,
        )

        values = load_root_config_values(config_path)

    assert values["GROQ_API_KEY"] == "test-key"
    assert values["LLM_PROVIDER"] == "vllm"
    assert values["VLLM_MODEL"] == "Qwen/Qwen3.5-4B"
    assert values["QUERY_EXTRACTION_PROVIDER"] == "groq"


def test_build_root_config_contains_generation_budgets():
    config = build_root_config({})

    assert config["generation"]["max_tokens"] == 450
    assert config["generation"]["chappie_thinking_token_limit"] == 650
    assert config["generation"]["chappie_answer_token_limit"] == 450
    assert config["small_tasks"]["intent_processor_model_groq"] == "llama-3.1-8b-instant"


if __name__ == "__main__":
    test_root_config_roundtrip_keeps_groq_small_task_defaults()
    test_build_root_config_contains_generation_budgets()
    print("OK: root config")
