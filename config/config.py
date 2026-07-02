"""
CHAPPiE - zentrale Konfiguration

Eine Datei fuer Runtime-Settings, Defaults, JSON-Persistenz und Brain-Agent-
Konfiguration. Das Frontend schreibt weiterhin in CHAPPIE_CONFIG.json; diese
Datei bleibt die vom UI veraenderbare Runtime-Override-Datei.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional


# ----------
# Pfade
# ----------

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CHROMA_DB_DIR = DATA_DIR / "chroma_db"
ROOT_CONFIG_PATH = PROJECT_ROOT / "CHAPPIE_CONFIG.json"

DATA_DIR.mkdir(exist_ok=True)
CHROMA_DB_DIR.mkdir(exist_ok=True)


# ----------
# Provider
# ----------

class LLMProvider(str, Enum):
    OLLAMA = "ollama"
    GROQ = "groq"
    VLLM = "vllm"


def _parse_provider(val: Any) -> Optional[LLMProvider]:
    if val is None or val == "auto" or val == "":
        return None
    try:
        return LLMProvider(str(val).lower())
    except ValueError:
        return None


try:
    from config import secrets  # type: ignore
except ImportError:
    import types

    secrets = types.ModuleType("secrets")

try:
    from config import addSecrets  # type: ignore
except ImportError:
    addSecrets = None


# ----------
# Lesbare Standard-Konfiguration
# ----------

DEFAULT_CONFIG: Dict[str, Dict[str, Any]] = {
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
        "steering_quantize": True,
        "steering_context_length": 4096,
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
        "emotion_analysis_model": "qwen3.5:9b",
        "emotion_analysis_host": "http://localhost:11434",
    },
    "generation": {
        "max_tokens": 450,
        "chappie_thinking_token_limit": 650,
        "chappie_answer_token_limit": 450,
        "temperature": 0.7,
        "repetition_penalty": 1.15,
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
        "personality_path": "data/personality.md",
        "soul_path": "data/soul.md",
        "user_path": "data/user.md",
        "preferences_path": "data/CHAPPiEsPreferences.md",
        "finetune_models_dir": "data/finetune_models",
        "finetune_chats_dir": "data/finetune_chats",
        "chroma_persist_directory": "data/chroma_db",
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
        "cli_debug_always_on": True,
        "web_debug_default": False,
    },
}

DEFAULT_ROOT_CONFIG = DEFAULT_CONFIG

KEY_PATHS = {
    key.upper(): (section, key)
    for section, values in DEFAULT_CONFIG.items()
    for key in values
}


# ----------
# Brain-Agent-Defaults
# ----------

@dataclass
class AgentModelConfig:
    """Modell- und Generierungswerte fuer einen Brain-Agent."""

    model_id: str
    provider: LLMProvider
    temperature: float = 0.3
    max_tokens: int = 1024
    description: str = ""


BRAIN_AGENT_CONFIGS: Dict[str, AgentModelConfig] = {
    "sensory_cortex": AgentModelConfig("Qwen/Qwen3.5-4B", LLMProvider.VLLM, 0.1, 512, "Input classification"),
    "amygdala": AgentModelConfig("Qwen/Qwen3.5-4B", LLMProvider.VLLM, 0.2, 512, "Emotional analysis"),
    "hippocampus": AgentModelConfig("Qwen/Qwen3.5-4B", LLMProvider.VLLM, 0.2, 768, "Memory operations"),
    "prefrontal_cortex": AgentModelConfig("Qwen/Qwen3.5-4B", LLMProvider.VLLM, 0.3, 1024, "Main orchestration"),
    "basal_ganglia": AgentModelConfig("Qwen/Qwen3.5-4B", LLMProvider.VLLM, 0.2, 512, "Reward evaluation"),
    "neocortex": AgentModelConfig("Qwen/Qwen3.5-4B", LLMProvider.VLLM, 0.2, 768, "Memory consolidation"),
    "memory_agent": AgentModelConfig("Qwen/Qwen3.5-4B", LLMProvider.VLLM, 0.2, 768, "Tool call decisions"),
}


# ----------
# Sleep und Vergessen
# ----------

SLEEP_PHASE_CONFIG = {
    "triggers": {
        "time_based": {"enabled": True, "interval_hours": 24},
        "interaction_based": {"enabled": True, "interval_interactions": 25},
        "manual": {"enabled": True, "command": "/sleep"},
    },
    "consolidation": {
        "min_memory_age_hours": 1,
        "max_consolidation_depth": 1,
        "require_original_interaction": True,
        "batch_size": 50,
    },
}

FORGETTING_CURVE_CONFIG = {
    "ebbinghaus": {
        "retention_after_20min": 0.58,
        "retention_after_1h": 0.44,
        "retention_after_1day": 0.33,
        "retention_after_1month": 0.21,
    },
    "memory_strength": {
        "initial": 1.0,
        "max": 10.0,
        "boost_per_recall": 0.5,
        "decay_rate": 0.1,
    },
    "spaced_repetition": {
        "intervals_hours": [1, 12, 24, 72, 168, 336, 720],
        "min_strength_for_archive": 0.3,
    },
}


# ----------
# JSON Runtime-Persistenz
# ----------

def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def load_config_values(path: Path = ROOT_CONFIG_PATH) -> Dict[str, Any]:
    data = _read_json(path)
    values: Dict[str, Any] = {}
    for config_key, (section, key) in KEY_PATHS.items():
        section_data = data.get(section, {})
        if isinstance(section_data, dict) and key in section_data:
            values[config_key] = section_data[key]
    return values


def build_config(values: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    config = deepcopy(DEFAULT_CONFIG)
    for config_key, value in values.items():
        path = KEY_PATHS.get(config_key.upper())
        if not path:
            continue
        section, key = path
        config[section][key] = value
    return config


def write_config(values: Dict[str, Any], path: Path = ROOT_CONFIG_PATH) -> None:
    config = build_config(values)
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# Alte Funktionsnamen bleiben in derselben Datei fuer Tests/Tools erhalten.
load_root_config_values = load_config_values
build_root_config = build_config
write_root_config = write_config


# ----------
# Settings-Klasse
# ----------

class Settings:
    def __init__(self):
        self._root_values = load_config_values()
        self._load_from_files()

    def _get_val(self, name: str, default: Any = None) -> Any:
        if name in self._root_values:
            return self._root_values[name]
        if addSecrets and hasattr(addSecrets, name):
            val = getattr(addSecrets, name)
            return default if val in (None, "") else val
        if hasattr(secrets, name):
            return getattr(secrets, name)
        return default

    def _get_path(self, name: str, default: Any = None) -> str:
        raw = self._get_val(name, default)
        if raw is None:
            return str(default) if default else ""
        p = str(raw)
        if p and not p.startswith("/"):
            p = str(PROJECT_ROOT / p)
        return p

    def _load_from_files(self) -> None:
        provider_str = self._get_val("LLM_PROVIDER", "vllm")
        try:
            self.llm_provider = LLMProvider(str(provider_str).lower())
        except ValueError:
            self.llm_provider = LLMProvider.OLLAMA

        self.ollama_host = self._get_val("OLLAMA_HOST", "http://localhost:11434")
        self.ollama_model = self._get_val("OLLAMA_MODEL", "qwen3.5:9b")
        self.vllm_url = self._get_val("VLLM_URL", "http://localhost:8000/v1")
        self.vllm_model = self._get_val("VLLM_MODEL", "Qwen/Qwen3.5-4B")
        self.vllm_force_single_model = bool(self._get_val("VLLM_FORCE_SINGLE_MODEL", True))

        self.groq_api_key = self._get_val("GROQ_API_KEY", "")
        self.groq_model = self._get_val("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.groq_format_model = self._get_val("GROQ_FORMAT_MODEL", "openai/gpt-oss-120b")
        self.groq_memory_model = self._get_val("GROQ_MEMORY_MODEL", "openai/gpt-oss-120b")

        self.intent_provider = _parse_provider(self._get_val("INTENT_PROVIDER", "groq"))
        self.intent_processor_model_groq = self._get_val("INTENT_PROCESSOR_MODEL_GROQ", "llama-3.1-8b-instant")
        self.intent_processor_model_ollama = self._get_val("INTENT_PROCESSOR_MODEL_OLLAMA", "qwen3.5:9b")
        self.intent_processor_model_vllm = self._get_val("INTENT_PROCESSOR_MODEL_VLLM", "Qwen/Qwen3.5-4B")
        self.enable_two_step_processing = bool(self._get_val("ENABLE_TWO_STEP_PROCESSING", True))

        self.query_extraction_provider = _parse_provider(self._get_val("QUERY_EXTRACTION_PROVIDER", "groq"))
        self.query_extraction_ollama_model = self._get_val("QUERY_EXTRACTION_OLLAMA_MODEL", "llama3.2:1b")
        self.query_extraction_vllm_model = self._get_val("QUERY_EXTRACTION_VLLM_MODEL", "Qwen/Qwen3.5-4B")
        self.query_extraction_groq_model = self._get_val("QUERY_EXTRACTION_GROQ_MODEL", "llama-3.1-8b-instant")
        self.enable_query_extraction = bool(self._get_val("ENABLE_QUERY_EXTRACTION", True))
        self.query_extraction_min_words_for_llm = int(self._get_val("QUERY_EXTRACTION_MIN_WORDS_FOR_LLM", 7))

        self.emotion_analysis_model = self._get_val("EMOTION_ANALYSIS_MODEL", "qwen3.5:9b")
        self.emotion_analysis_host = self._get_val("EMOTION_ANALYSIS_HOST", "http://localhost:11434")
        self.embedding_model = self._get_val("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

        self.training_use_global_settings = bool(self._get_val("TRAINING_USE_GLOBAL_SETTINGS", True))
        self.training_chappie_provider = _parse_provider(self._get_val("TRAINING_CHAPPIE_PROVIDER", "auto"))
        self.training_chappie_model = self._get_val("TRAINING_CHAPPIE_MODEL", "")
        self.training_trainer_provider = _parse_provider(self._get_val("TRAINING_TRAINER_PROVIDER", "auto"))
        self.training_trainer_model = self._get_val("TRAINING_TRAINER_MODEL", "")

        self.memory_top_k = int(self._get_val("MEMORY_TOP_K", 40))
        self.memory_min_relevance = float(self._get_val("MEMORY_MIN_RELEVANCE", 0.2))
        self.chroma_collection_name = self._get_val("CHROMA_COLLECTION", "chapie_memory")
        self.memory_consolidation_enabled = bool(self._get_val("MEMORY_CONSOLIDATION_ENABLED", True))
        self.memory_consolidation_groq_model = self._get_val("MEMORY_CONSOLIDATION_GROQ_MODEL", "openai/gpt-oss-120b")
        self.memory_consolidation_max_tokens = int(self._get_val("MEMORY_CONSOLIDATION_MAX_TOKENS", 1500))
        self.short_term_ttl_hours = int(self._get_val("SHORT_TERM_TTL_HOURS", 24))
        self.stm_summary_threshold = int(self._get_val("STM_SUMMARY_THRESHOLD", 5))
        self.stm_summary_batch_size = int(self._get_val("STM_SUMMARY_BATCH_SIZE", 5))
        self.auto_consolidate = bool(self._get_val("AUTO_CONSOLIDATE", True))

        self.personality_path = self._get_path("PERSONALITY_PATH", str(DATA_DIR / "personality.md"))
        self.soul_path = self._get_path("SOUL_PATH", str(DATA_DIR / "soul.md"))
        self.user_path = self._get_path("USER_PATH", str(DATA_DIR / "user.md"))
        self.preferences_path = self._get_path("PREFERENCES_PATH", str(DATA_DIR / "CHAPPiEsPreferences.md"))
        self.finetune_models_dir = self._get_path("FINETUNE_MODELS_DIR", str(DATA_DIR / "finetune_models"))
        self.finetune_chats_dir = self._get_path("FINETUNE_CHATS_DIR", str(DATA_DIR / "finetune_chats"))
        self.chroma_persist_directory = self._get_path("CHROMA_PERSIST_DIRECTORY", str(CHROMA_DB_DIR))

        self.enable_steering = bool(self._get_val("ENABLE_STEERING", True))
        self.steering_provider = _parse_provider(self._get_val("STEERING_PROVIDER", "vllm"))
        self.steering_model = self._get_val("STEERING_MODEL", "Qwen/Qwen3.5-4B")
        self.steering_quantize = bool(self._get_val("STEERING_QUANTIZE", True))
        self.steering_context_length = int(self._get_val("STEERING_CONTEXT_LENGTH", 4096))

        self.max_tokens = int(self._get_val("MAX_TOKENS", 450))
        self.chappie_thinking_token_limit = int(self._get_val("CHAPPIE_THINKING_TOKEN_LIMIT", 650))
        self.chappie_answer_token_limit = int(self._get_val("CHAPPIE_ANSWER_TOKEN_LIMIT", 450))
        self.temperature = float(self._get_val("TEMPERATURE", 0.7))
        self.repetition_penalty = float(self._get_val("REPETITION_PENALTY", 1.15))
        self.stream = bool(self._get_val("STREAM", True))
        self.chain_of_thought = bool(self._get_val("CHAIN_OF_THOUGHT", True))
        self.debug = bool(self._get_val("DEBUG", True))
        self.enable_functions = bool(self._get_val("ENABLE_FUNCTIONS", True))
        self.cli_debug_always_on = bool(self._get_val("CLI_DEBUG_ALWAYS_ON", True))
        self.web_debug_default = bool(self._get_val("WEB_DEBUG_DEFAULT", False))
        self.history_max_messages = int(self._get_val("HISTORY_MAX_MESSAGES", 20))
        self.context_token_limit = int(self._get_val("CONTEXT_TOKEN_LIMIT", 7000))
        self.context_token_warning_threshold = int(self._get_val("CONTEXT_TOKEN_WARNING_THRESHOLD", 6500))

        self.groq_requests_per_minute = int(self._get_val("GROQ_REQUESTS_PER_MINUTE", 250))
        self.groq_requests_per_hour = int(self._get_val("GROQ_REQUESTS_PER_HOUR", 6000))
        self.groq_requests_per_day = int(self._get_val("GROQ_REQUESTS_PER_DAY", 144000))
        self.groq_tokens_per_minute = int(self._get_val("GROQ_TOKENS_PER_MINUTE", 250000))
        self.groq_tokens_per_hour = int(self._get_val("GROQ_TOKENS_PER_HOUR", 6000000))
        self.groq_tokens_per_day = int(self._get_val("GROQ_TOKENS_PER_DAY", 144000000))

    def get_effective_provider(self, step_provider: Any = None) -> LLMProvider:
        if step_provider is None or step_provider == "auto":
            return self.llm_provider
        if isinstance(step_provider, LLMProvider):
            return step_provider
        try:
            return LLMProvider(str(step_provider).lower())
        except (ValueError, AttributeError):
            return self.llm_provider

    def resolve_vllm_runtime_model(self, requested_model: Optional[str] = None) -> str:
        if self.vllm_force_single_model:
            return self.vllm_model
        return requested_model or self.vllm_model

    def get_intent_model(self, provider: Any = None) -> str:
        effective = self.get_effective_provider(provider if provider != "auto" else None)
        if effective == LLMProvider.GROQ:
            return self.intent_processor_model_groq
        if effective == LLMProvider.VLLM:
            return self.resolve_vllm_runtime_model(self.intent_processor_model_vllm)
        return self.intent_processor_model_ollama

    def get_query_extraction_model(self, provider: Any = None) -> str:
        effective = self.get_effective_provider(provider if provider != "auto" else None)
        if effective == LLMProvider.GROQ:
            return self.query_extraction_groq_model
        if effective == LLMProvider.VLLM:
            return self.resolve_vllm_runtime_model(self.query_extraction_vllm_model)
        return self.query_extraction_ollama_model

    def update_from_ui(self, **kwargs: Any) -> None:
        old_provider = self.llm_provider
        if kwargs.get("llm_provider"):
            parsed = _parse_provider(kwargs["llm_provider"])
            if parsed:
                self.llm_provider = parsed

        for key in ["groq_api_key"]:
            if key in kwargs and kwargs[key] is not None:
                setattr(self, key, kwargs[key])

        string_keys = [
            "groq_model", "groq_format_model", "groq_memory_model",
            "vllm_model", "vllm_url", "ollama_model", "ollama_host",
            "memory_consolidation_groq_model", "intent_processor_model_groq",
            "intent_processor_model_ollama", "intent_processor_model_vllm",
            "query_extraction_ollama_model", "query_extraction_vllm_model",
            "query_extraction_groq_model", "emotion_analysis_model",
            "emotion_analysis_host", "embedding_model", "steering_model",
            "training_chappie_model", "training_trainer_model",
        ]
        for key in string_keys:
            if key in kwargs and kwargs[key]:
                setattr(self, key, kwargs[key])

        for key in ["intent_provider", "query_extraction_provider", "steering_provider", "training_chappie_provider", "training_trainer_provider"]:
            if key in kwargs:
                parsed = _parse_provider(kwargs[key])
                if key in ("intent_provider", "query_extraction_provider") and old_provider != self.llm_provider and parsed == old_provider:
                    parsed = None
                setattr(self, key, parsed)

        bool_keys = [
            "vllm_force_single_model", "enable_steering", "steering_quantize",
            "training_use_global_settings", "chain_of_thought",
            "memory_consolidation_enabled", "enable_two_step_processing",
        ]
        for key in bool_keys:
            if key in kwargs and kwargs[key] is not None:
                setattr(self, key, bool(kwargs[key]))

        numeric_keys = [
            "temperature", "repetition_penalty", "max_tokens", "memory_top_k",
            "memory_min_relevance", "memory_consolidation_max_tokens",
            "chappie_thinking_token_limit", "chappie_answer_token_limit",
            "history_max_messages", "context_token_limit",
            "context_token_warning_threshold", "stm_summary_threshold",
            "stm_summary_batch_size", "query_extraction_min_words_for_llm",
            "steering_context_length", "groq_requests_per_minute",
            "groq_requests_per_hour", "groq_requests_per_day",
            "groq_tokens_per_minute", "groq_tokens_per_hour",
            "groq_tokens_per_day",
        ]
        for key in numeric_keys:
            if key in kwargs and kwargs[key] is not None:
                setattr(self, key, kwargs[key])

        self._persist_to_root_config()
        self._needs_reload = True

    def _export_root_values(self) -> Dict[str, Any]:
        def provider_value(value: Optional[LLMProvider]) -> str:
            return value.value if value is not None else "auto"

        return {
            "LLM_PROVIDER": self.llm_provider.value,
            "GROQ_API_KEY": self.groq_api_key,
            "GROQ_MODEL": self.groq_model,
            "GROQ_FORMAT_MODEL": self.groq_format_model,
            "GROQ_MEMORY_MODEL": self.groq_memory_model,
            "VLLM_MODEL": self.vllm_model,
            "VLLM_URL": self.vllm_url,
            "VLLM_FORCE_SINGLE_MODEL": self.vllm_force_single_model,
            "OLLAMA_MODEL": self.ollama_model,
            "OLLAMA_HOST": self.ollama_host,
            "INTENT_PROVIDER": provider_value(self.intent_provider),
            "INTENT_PROCESSOR_MODEL_GROQ": self.intent_processor_model_groq,
            "INTENT_PROCESSOR_MODEL_OLLAMA": self.intent_processor_model_ollama,
            "INTENT_PROCESSOR_MODEL_VLLM": self.intent_processor_model_vllm,
            "ENABLE_TWO_STEP_PROCESSING": self.enable_two_step_processing,
            "QUERY_EXTRACTION_PROVIDER": provider_value(self.query_extraction_provider),
            "QUERY_EXTRACTION_OLLAMA_MODEL": self.query_extraction_ollama_model,
            "QUERY_EXTRACTION_VLLM_MODEL": self.query_extraction_vllm_model,
            "QUERY_EXTRACTION_GROQ_MODEL": self.query_extraction_groq_model,
            "ENABLE_QUERY_EXTRACTION": self.enable_query_extraction,
            "QUERY_EXTRACTION_MIN_WORDS_FOR_LLM": self.query_extraction_min_words_for_llm,
            "EMOTION_ANALYSIS_MODEL": self.emotion_analysis_model,
            "EMOTION_ANALYSIS_HOST": self.emotion_analysis_host,
            "EMBEDDING_MODEL": self.embedding_model,
            "MEMORY_TOP_K": self.memory_top_k,
            "MEMORY_MIN_RELEVANCE": self.memory_min_relevance,
            "CHROMA_COLLECTION": self.chroma_collection_name,
            "MEMORY_CONSOLIDATION_ENABLED": self.memory_consolidation_enabled,
            "MEMORY_CONSOLIDATION_GROQ_MODEL": self.memory_consolidation_groq_model,
            "MEMORY_CONSOLIDATION_MAX_TOKENS": self.memory_consolidation_max_tokens,
            "SHORT_TERM_TTL_HOURS": self.short_term_ttl_hours,
            "STM_SUMMARY_THRESHOLD": self.stm_summary_threshold,
            "STM_SUMMARY_BATCH_SIZE": self.stm_summary_batch_size,
            "AUTO_CONSOLIDATE": self.auto_consolidate,
            "MAX_TOKENS": self.max_tokens,
            "CHAPPIE_THINKING_TOKEN_LIMIT": self.chappie_thinking_token_limit,
            "CHAPPIE_ANSWER_TOKEN_LIMIT": self.chappie_answer_token_limit,
            "TEMPERATURE": self.temperature,
            "REPETITION_PENALTY": self.repetition_penalty,
            "STREAM": self.stream,
            "CHAIN_OF_THOUGHT": self.chain_of_thought,
            "ENABLE_STEERING": self.enable_steering,
            "STEERING_PROVIDER": provider_value(self.steering_provider),
            "STEERING_MODEL": self.steering_model,
            "STEERING_QUANTIZE": self.steering_quantize,
            "STEERING_CONTEXT_LENGTH": self.steering_context_length,
            "PERSONALITY_PATH": self.personality_path,
            "SOUL_PATH": self.soul_path,
            "USER_PATH": self.user_path,
            "PREFERENCES_PATH": self.preferences_path,
            "FINETUNE_MODELS_DIR": self.finetune_models_dir,
            "FINETUNE_CHATS_DIR": self.finetune_chats_dir,
            "CHROMA_PERSIST_DIRECTORY": self.chroma_persist_directory,
            "TRAINING_USE_GLOBAL_SETTINGS": self.training_use_global_settings,
            "TRAINING_CHAPPIE_PROVIDER": provider_value(self.training_chappie_provider),
            "TRAINING_CHAPPIE_MODEL": self.training_chappie_model,
            "TRAINING_TRAINER_PROVIDER": provider_value(self.training_trainer_provider),
            "TRAINING_TRAINER_MODEL": self.training_trainer_model,
            "DEBUG": self.debug,
            "ENABLE_FUNCTIONS": self.enable_functions,
            "CLI_DEBUG_ALWAYS_ON": self.cli_debug_always_on,
            "WEB_DEBUG_DEFAULT": self.web_debug_default,
            "HISTORY_MAX_MESSAGES": self.history_max_messages,
            "CONTEXT_TOKEN_LIMIT": self.context_token_limit,
            "CONTEXT_TOKEN_WARNING_THRESHOLD": self.context_token_warning_threshold,
            "GROQ_REQUESTS_PER_MINUTE": self.groq_requests_per_minute,
            "GROQ_REQUESTS_PER_HOUR": self.groq_requests_per_hour,
            "GROQ_REQUESTS_PER_DAY": self.groq_requests_per_day,
            "GROQ_TOKENS_PER_MINUTE": self.groq_tokens_per_minute,
            "GROQ_TOKENS_PER_HOUR": self.groq_tokens_per_hour,
            "GROQ_TOKENS_PER_DAY": self.groq_tokens_per_day,
        }

    def _persist_to_root_config(self) -> None:
        try:
            write_config(self._export_root_values())
        except Exception as e:
            print(f"Warnung: Konnte CHAPPIE_CONFIG.json nicht schreiben: {e}")

    def _persist_to_addsecrets(self) -> None:
        self._persist_to_root_config()


# ----------
# Zugriffsfunktionen
# ----------

settings = Settings()


def get_active_model() -> str:
    if settings.llm_provider == LLMProvider.GROQ:
        return settings.groq_model
    if settings.llm_provider == LLMProvider.VLLM:
        return settings.vllm_model
    return settings.ollama_model


def get_agent_config(agent_name: str) -> Optional[AgentModelConfig]:
    return BRAIN_AGENT_CONFIGS.get(agent_name)


def get_all_agent_configs() -> Dict[str, AgentModelConfig]:
    return BRAIN_AGENT_CONFIGS.copy()


def get_sleep_config() -> Dict[str, Any]:
    return deepcopy(SLEEP_PHASE_CONFIG)


def get_forgetting_curve_config() -> Dict[str, Any]:
    return deepcopy(FORGETTING_CURVE_CONFIG)


def print_config() -> None:
    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(title="CHAPPiE Konfiguration", show_header=True)
    table.add_column("Setting", style="cyan")
    table.add_column("Wert", style="green")
    table.add_row("LLM Provider", settings.llm_provider.value)
    table.add_row("Aktives Modell", get_active_model())
    table.add_row("Intent Provider", str(settings.intent_provider or "auto"))
    table.add_row("Intent Modell", settings.get_intent_model())
    table.add_row("Emotion Modell", settings.emotion_analysis_model)
    table.add_row("Embedding Modell", settings.embedding_model)
    table.add_row("Memory Top-K", str(settings.memory_top_k))
    table.add_row("Temperature", str(settings.temperature))
    console.print(table)


if __name__ == "__main__":
    print_config()
