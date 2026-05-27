"""Root JSON configuration for CHAPPiE."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict


PROJECT_ROOT = Path(__file__).parent.parent
ROOT_CONFIG_PATH = PROJECT_ROOT / "CHAPPIE_CONFIG.json"
ROOT_CONFIG_EXAMPLE_PATH = PROJECT_ROOT / "CHAPPIE_CONFIG.example.json"


DEFAULT_ROOT_CONFIG: Dict[str, Dict[str, Any]] = {
    "api": {
        "groq_api_key": "DEIN_GROQ_API_KEY_HIER",
    },
    "local_models": {
        "llm_provider": "vllm",
        "vllm_url": "http://localhost:8000/v1",
        "vllm_model": "Qwen/Qwen3.5-4B",
        "vllm_force_single_model": True,
        "ollama_host": "http://localhost:11434",
        "ollama_model": "qwen3.5:9b",
        "enable_steering": True,
        "steering_provider": "vllm",
        "steering_model": "Qwen/Qwen3.5-4B",
    },
    "cloud_models": {
        "groq_model": "llama-3.3-70b-versatile",
        "groq_format_model": "openai/gpt-oss-120b",
        "groq_memory_model": "openai/gpt-oss-120b",
    },
    "small_tasks": {
        "intent_provider": "groq",
        "intent_processor_model_groq": "llama-3.1-8b-instant",
        "intent_processor_model_ollama": "qwen3.5:9b",
        "intent_processor_model_vllm": "Qwen/Qwen3.5-4B",
        "enable_two_step_processing": True,
        "query_extraction_provider": "groq",
        "query_extraction_groq_model": "llama-3.1-8b-instant",
        "query_extraction_ollama_model": "llama3.2:1b",
        "query_extraction_vllm_model": "Qwen/Qwen3.5-4B",
        "enable_query_extraction": True,
        "query_extraction_min_words_for_llm": 7,
    },
    "generation": {
        "max_tokens": 3300,
        "chappie_thinking_token_limit": 2500,
        "chappie_answer_token_limit": 800,
        "temperature": 0.7,
        "stream": True,
        "chain_of_thought": True,
        "history_max_messages": 20,
        "context_token_limit": 7000,
        "context_token_warning_threshold": 6500,
    },
    "memory": {
        "memory_top_k": 40,
        "memory_min_relevance": 0.2,
        "chroma_collection": "chapie_memory",
        "embedding_model": "all-MiniLM-L6-v2",
        "short_term_ttl_hours": 24,
        "stm_summary_threshold": 5,
        "stm_summary_batch_size": 5,
        "auto_consolidate": True,
        "memory_consolidation_enabled": True,
        "memory_consolidation_groq_model": "openai/gpt-oss-120b",
        "memory_consolidation_max_tokens": 1500,
    },
    "groq_limits": {
        "requests_per_minute": 250,
        "requests_per_hour": 6000,
        "requests_per_day": 144000,
        "tokens_per_minute": 250000,
        "tokens_per_hour": 6000000,
        "tokens_per_day": 144000000,
    },
    "paths": {
        "daily_info_path": "data/daily_info.md",
        "personality_path": "data/personality.md",
        "soul_path": "data/soul.md",
        "user_path": "data/user.md",
        "preferences_path": "data/CHAPPiEsPreferences.md",
    },
    "training": {
        "training_use_global_settings": True,
        "training_chappie_provider": "auto",
        "training_chappie_model": "",
        "training_trainer_provider": "auto",
        "training_trainer_model": "",
    },
    "debug": {
        "debug": True,
        "enable_functions": True,
    },
}


KEY_PATHS = {
    key.upper(): (section, key)
    for section, values in DEFAULT_ROOT_CONFIG.items()
    for key in values
}


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def load_root_config_values(path: Path = ROOT_CONFIG_PATH) -> Dict[str, Any]:
    data = _read_json(path)
    values: Dict[str, Any] = {}
    for config_key, (section, key) in KEY_PATHS.items():
        section_data = data.get(section, {})
        if isinstance(section_data, dict) and key in section_data:
            values[config_key] = section_data[key]
    return values


def build_root_config(values: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    config = deepcopy(DEFAULT_ROOT_CONFIG)
    for config_key, value in values.items():
        path = KEY_PATHS.get(config_key.upper())
        if not path:
            continue
        section, key = path
        config[section][key] = value
    return config


def write_root_config(values: Dict[str, Any], path: Path = ROOT_CONFIG_PATH) -> None:
    config = build_root_config(values)
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
