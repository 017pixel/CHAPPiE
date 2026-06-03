"""
CHAPiE - Zentrale Konfiguration
===============================
Laedt Einstellungen aus CHAPPIE_CONFIG.json und stellt sie bereit.
"""

from pathlib import Path
from enum import Enum

from config.root_config import load_root_config_values, write_root_config

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CHROMA_DB_DIR = DATA_DIR / "chroma_db"

DATA_DIR.mkdir(exist_ok=True)
CHROMA_DB_DIR.mkdir(exist_ok=True)


class LLMProvider(str, Enum):
    OLLAMA = "ollama"
    GROQ = "groq"
    VLLM = "vllm"


try:
    from config import secrets
except ImportError:
    import types
    secrets = types.ModuleType("secrets")

try:
    from config import addSecrets
except ImportError:
    addSecrets = None


def _parse_provider(val):
    if val is None or val == "auto" or val == "":
        return None
    try:
        return LLMProvider(val.lower())
    except ValueError:
        return None


class Settings:
    def __init__(self):
        self._root_values = load_root_config_values()
        self._load_from_files()

    def _get_val(self, name, default=None):
        if name in self._root_values:
            return self._root_values[name]
        if addSecrets and hasattr(addSecrets, name):
            val = getattr(addSecrets, name)
            if val:
                return val
        if hasattr(secrets, name):
            return getattr(secrets, name)
        return default

    def _load_from_files(self):
        provider_str = self._get_val("LLM_PROVIDER", "vllm")
        try:
            self.llm_provider = LLMProvider(provider_str.lower())
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
        self.enable_two_step_processing = self._get_val("ENABLE_TWO_STEP_PROCESSING", True)

        self.query_extraction_provider = _parse_provider(self._get_val("QUERY_EXTRACTION_PROVIDER", "groq"))
        self.query_extraction_ollama_model = self._get_val("QUERY_EXTRACTION_OLLAMA_MODEL", "llama3.2:1b")
        self.query_extraction_vllm_model = self._get_val("QUERY_EXTRACTION_VLLM_MODEL", "Qwen/Qwen3.5-4B")
        self.query_extraction_groq_model = self._get_val("QUERY_EXTRACTION_GROQ_MODEL", "llama-3.1-8b-instant")
        self.enable_query_extraction = self._get_val("ENABLE_QUERY_EXTRACTION", True)
        self.query_extraction_min_words_for_llm = int(self._get_val("QUERY_EXTRACTION_MIN_WORDS_FOR_LLM", 7))

        self.emotion_analysis_model = self._get_val("EMOTION_ANALYSIS_MODEL", "qwen3.5:9b")
        self.emotion_analysis_host = self._get_val("EMOTION_ANALYSIS_HOST", "http://localhost:11434")

        self.embedding_model = self._get_val("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        
        self.training_use_global_settings = self._get_val("TRAINING_USE_GLOBAL_SETTINGS", True)
        self.training_chappie_provider = _parse_provider(self._get_val("TRAINING_CHAPPIE_PROVIDER", "auto"))
        self.training_chappie_model = self._get_val("TRAINING_CHAPPIE_MODEL", "")
        self.training_trainer_provider = _parse_provider(self._get_val("TRAINING_TRAINER_PROVIDER", "auto"))
        self.training_trainer_model = self._get_val("TRAINING_TRAINER_MODEL", "")

        # Finetune configuration
        self.finetune_enabled = bool(self._get_val("FINETUNE_ENABLED", True))
        self.finetune_models_dir = Path(self._get_val("FINETUNE_MODELS_DIR", str(DATA_DIR / "finetuned_models")))
        self.finetune_chats_dir = Path(self._get_val("FINETUNE_CHATS_DIR", str(DATA_DIR / "finetune_chats")))
        self.finetune_active_adapter = self._get_val("FINETUNE_ACTIVE_ADAPTER", None)
        self.finetune_default_lora_r = int(self._get_val("FINETUNE_DEFAULT_LORA_R", 16))
        self.finetune_default_lora_alpha = int(self._get_val("FINETUNE_DEFAULT_LORA_ALPHA", 32))
        self.finetune_default_lr = float(self._get_val("FINETUNE_DEFAULT_LR", 2e-4))
        self.finetune_default_epochs = int(self._get_val("FINETUNE_DEFAULT_EPOCHS", 1))
        self.finetune_default_batch_size = int(self._get_val("FINETUNE_DEFAULT_BATCH_SIZE", 4))
        self.finetune_default_grad_accum = int(self._get_val("FINETUNE_DEFAULT_GRAD_ACCUM", 4))
        self.finetune_general_de_ratio = float(self._get_val("FINETUNE_GENERAL_DE_RATIO", 0.15))
        self.finetune_bf16_fallback = bool(self._get_val("FINETUNE_BF16_FALLBACK", True))

        self.memory_top_k = int(self._get_val("MEMORY_TOP_K", 40))
        self.memory_min_relevance = float(self._get_val("MEMORY_MIN_RELEVANCE", 0.2))
        self.chroma_collection_name = self._get_val("CHROMA_COLLECTION", "chapie_memory")
        self.memory_consolidation_enabled = self._get_val("MEMORY_CONSOLIDATION_ENABLED", True)
        self.memory_consolidation_groq_model = self._get_val("MEMORY_CONSOLIDATION_GROQ_MODEL", "openai/gpt-oss-120b")
        self.memory_consolidation_max_tokens = int(self._get_val("MEMORY_CONSOLIDATION_MAX_TOKENS", 1500))

        self.daily_info_path = self._get_val("DAILY_INFO_PATH", str(DATA_DIR / "daily_info.md"))
        self.personality_path = self._get_val("PERSONALITY_PATH", str(DATA_DIR / "personality.md"))
        self.short_term_ttl_hours = int(self._get_val("SHORT_TERM_TTL_HOURS", 24))
        self.stm_summary_threshold = int(self._get_val("STM_SUMMARY_THRESHOLD", 5))
        self.stm_summary_batch_size = int(self._get_val("STM_SUMMARY_BATCH_SIZE", 5))
        self.enable_functions = self._get_val("ENABLE_FUNCTIONS", True)
        self.auto_consolidate = self._get_val("AUTO_CONSOLIDATE", True)

        self.soul_path = self._get_val("SOUL_PATH", str(DATA_DIR / "soul.md"))
        self.user_path = self._get_val("USER_PATH", str(DATA_DIR / "user.md"))
        self.preferences_path = self._get_val("PREFERENCES_PATH", str(DATA_DIR / "CHAPPiEsPreferences.md"))

        # Neu: Steering-Konfiguration
        self.enable_steering = self._get_val("ENABLE_STEERING", True)
        self.steering_provider = _parse_provider(self._get_val("STEERING_PROVIDER", "vllm"))
        self.steering_model = self._get_val("STEERING_MODEL", "Qwen/Qwen3.5-4B")
        self.steering_quantize = bool(self._get_val("STEERING_QUANTIZE", True))
        self.steering_context_length = int(self._get_val("STEERING_CONTEXT_LENGTH", 4096))

        self.cli_debug_always_on = True
        self.web_debug_default = False

        self.max_tokens = int(self._get_val("MAX_TOKENS", 2200))
        self.chappie_thinking_token_limit = int(self._get_val("CHAPPIE_THINKING_TOKEN_LIMIT", 800))
        self.chappie_answer_token_limit = int(self._get_val("CHAPPIE_ANSWER_TOKEN_LIMIT", 1200))
        self.temperature = float(self._get_val("TEMPERATURE", 0.85))
        self.repetition_penalty = float(self._get_val("REPETITION_PENALTY", 1.15))
        self.stream = bool(self._get_val("STREAM", True))
        self.chain_of_thought = bool(self._get_val("CHAIN_OF_THOUGHT", False))
        self.debug = bool(self._get_val("DEBUG", True))
        self.history_max_messages = int(self._get_val("HISTORY_MAX_MESSAGES", 20))
        self.context_token_limit = int(self._get_val("CONTEXT_TOKEN_LIMIT", 7000))
        self.context_token_warning_threshold = int(self._get_val("CONTEXT_TOKEN_WARNING_THRESHOLD", 6500))

        self.groq_requests_per_minute = int(self._get_val("GROQ_REQUESTS_PER_MINUTE", 250))
        self.groq_requests_per_hour = int(self._get_val("GROQ_REQUESTS_PER_HOUR", 6000))
        self.groq_requests_per_day = int(self._get_val("GROQ_REQUESTS_PER_DAY", 144000))
        self.groq_tokens_per_minute = int(self._get_val("GROQ_TOKENS_PER_MINUTE", 250000))
        self.groq_tokens_per_hour = int(self._get_val("GROQ_TOKENS_PER_HOUR", 6000000))
        self.groq_tokens_per_day = int(self._get_val("GROQ_TOKENS_PER_DAY", 144000000))

    def get_effective_provider(self, step_provider=None):
        if step_provider is None or step_provider == "auto":
            return self.llm_provider
        if isinstance(step_provider, LLMProvider):
            return step_provider
        try:
            return LLMProvider(step_provider.lower())
        except (ValueError, AttributeError):
            return self.llm_provider

    def resolve_vllm_runtime_model(self, requested_model=None):
        """Resolve the effective model name for single-endpoint vLLM deployments."""
        if self.vllm_force_single_model:
            return self.vllm_model
        return requested_model or self.vllm_model

    def get_intent_model(self, provider=None):
        effective = self.get_effective_provider(provider if provider != "auto" else None)
        if effective == LLMProvider.GROQ:
            return self.intent_processor_model_groq
        elif effective == LLMProvider.VLLM:
            return self.resolve_vllm_runtime_model(self.intent_processor_model_vllm)
        return self.intent_processor_model_ollama

    def get_query_extraction_model(self, provider=None):
        effective = self.get_effective_provider(provider if provider != "auto" else None)
        if effective == LLMProvider.GROQ:
            return self.query_extraction_groq_model
        elif effective == LLMProvider.VLLM:
            return self.resolve_vllm_runtime_model(self.query_extraction_vllm_model)
        return self.query_extraction_ollama_model

    def update_from_ui(self, **kwargs):
        old_provider = self.llm_provider
        if "llm_provider" in kwargs and kwargs["llm_provider"]:
            try:
                self.llm_provider = LLMProvider(kwargs["llm_provider"].lower())
            except:
                pass

        for key in ["groq_api_key"]:
            if key in kwargs and kwargs[key] is not None:
                setattr(self, key, kwargs[key])

        for key in ["groq_model", "groq_format_model", "groq_memory_model", "vllm_model", "vllm_url",
                     "ollama_model", "ollama_host", "memory_consolidation_groq_model"]:
            if key in kwargs and kwargs[key]:
                setattr(self, key, kwargs[key])
        if "vllm_force_single_model" in kwargs:
            self.vllm_force_single_model = bool(kwargs["vllm_force_single_model"])

        if "intent_provider" in kwargs:
            parsed = _parse_provider(kwargs["intent_provider"])
            if old_provider != self.llm_provider and parsed == old_provider:
                self.intent_provider = None
            else:
                self.intent_provider = parsed
        for key in ["intent_processor_model_groq",
                    "intent_processor_model_ollama", "intent_processor_model_vllm"]:
            if key in kwargs and kwargs[key]:
                setattr(self, key, kwargs[key])

        if "query_extraction_provider" in kwargs:
            parsed = _parse_provider(kwargs["query_extraction_provider"])
            if old_provider != self.llm_provider and parsed == old_provider:
                self.query_extraction_provider = None
            else:
                self.query_extraction_provider = parsed
        for key in [
            "query_extraction_ollama_model",
            "query_extraction_vllm_model",
            "query_extraction_groq_model",
        ]:
            if key in kwargs and kwargs[key]:
                setattr(self, key, kwargs[key])
        if "query_extraction_min_words_for_llm" in kwargs and kwargs["query_extraction_min_words_for_llm"] is not None:
            self.query_extraction_min_words_for_llm = int(kwargs["query_extraction_min_words_for_llm"])

        for key in ["emotion_analysis_model", "emotion_analysis_host", "embedding_model"]:
            if key in kwargs and kwargs[key]:
                setattr(self, key, kwargs[key])

        if "enable_steering" in kwargs:
            self.enable_steering = bool(kwargs["enable_steering"])
        if "steering_provider" in kwargs:
            self.steering_provider = _parse_provider(kwargs["steering_provider"])
        if "steering_model" in kwargs and kwargs["steering_model"]:
            self.steering_model = kwargs["steering_model"]
        if "steering_quantize" in kwargs:
            self.steering_quantize = bool(kwargs["steering_quantize"])
        if "steering_context_length" in kwargs and kwargs["steering_context_length"] is not None:
            self.steering_context_length = int(kwargs["steering_context_length"])

        if "training_use_global_settings" in kwargs:
            self.training_use_global_settings = kwargs["training_use_global_settings"]
        if "training_chappie_provider" in kwargs:
            self.training_chappie_provider = _parse_provider(kwargs["training_chappie_provider"])
        if "training_chappie_model" in kwargs:
            self.training_chappie_model = kwargs["training_chappie_model"]
        if "training_trainer_provider" in kwargs:
            self.training_trainer_provider = _parse_provider(kwargs["training_trainer_provider"])
        if "training_trainer_model" in kwargs:
            self.training_trainer_model = kwargs["training_trainer_model"]

        if "finetune_enabled" in kwargs:
            self.finetune_enabled = bool(kwargs["finetune_enabled"])
        if "finetune_active_adapter" in kwargs:
            self.finetune_active_adapter = kwargs["finetune_active_adapter"] or None
        for key in [
            "finetune_models_dir", "finetune_chats_dir", "finetune_default_lora_r",
            "finetune_default_lora_alpha", "finetune_default_lr", "finetune_default_epochs",
            "finetune_default_batch_size", "finetune_default_grad_accum", "finetune_general_de_ratio",
            "finetune_bf16_fallback",
        ]:
            if key in kwargs and kwargs[key] is not None:
                setattr(self, key, kwargs[key])

        for key in [
            "temperature", "repetition_penalty", "max_tokens", "chain_of_thought",
            "memory_top_k", "memory_min_relevance",
            "memory_consolidation_enabled", "memory_consolidation_max_tokens",
            "chappie_thinking_token_limit", "chappie_answer_token_limit",
            "history_max_messages", "context_token_limit", "context_token_warning_threshold",
            "stm_summary_threshold", "stm_summary_batch_size",
            "groq_requests_per_minute", "groq_requests_per_hour",
            "groq_requests_per_day", "groq_tokens_per_minute",
            "groq_tokens_per_hour", "groq_tokens_per_day",
        ]:
            if key in kwargs and kwargs[key] is not None:
                setattr(self, key, kwargs[key])
        if "enable_two_step_processing" in kwargs:
            self.enable_two_step_processing = bool(kwargs["enable_two_step_processing"])

        self._persist_to_root_config()
        self._needs_reload = True

    def _export_root_values(self):
        def provider_value(value):
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
            "DAILY_INFO_PATH": self.daily_info_path,
            "PERSONALITY_PATH": self.personality_path,
            "SOUL_PATH": self.soul_path,
            "USER_PATH": self.user_path,
            "PREFERENCES_PATH": self.preferences_path,
            "TRAINING_USE_GLOBAL_SETTINGS": self.training_use_global_settings,
            "TRAINING_CHAPPIE_PROVIDER": provider_value(self.training_chappie_provider),
            "TRAINING_CHAPPIE_MODEL": self.training_chappie_model,
            "TRAINING_TRAINER_PROVIDER": provider_value(self.training_trainer_provider),
            "TRAINING_TRAINER_MODEL": self.training_trainer_model,
            "FINETUNE_ENABLED": self.finetune_enabled,
            "FINETUNE_MODELS_DIR": str(self.finetune_models_dir),
            "FINETUNE_CHATS_DIR": str(self.finetune_chats_dir),
            "FINETUNE_ACTIVE_ADAPTER": self.finetune_active_adapter or "",
            "FINETUNE_DEFAULT_LORA_R": self.finetune_default_lora_r,
            "FINETUNE_DEFAULT_LORA_ALPHA": self.finetune_default_lora_alpha,
            "FINETUNE_DEFAULT_LR": self.finetune_default_lr,
            "FINETUNE_DEFAULT_EPOCHS": self.finetune_default_epochs,
            "FINETUNE_DEFAULT_BATCH_SIZE": self.finetune_default_batch_size,
            "FINETUNE_DEFAULT_GRAD_ACCUM": self.finetune_default_grad_accum,
            "FINETUNE_GENERAL_DE_RATIO": self.finetune_general_de_ratio,
            "FINETUNE_BF16_FALLBACK": self.finetune_bf16_fallback,
            "DEBUG": self.debug,
            "ENABLE_FUNCTIONS": self.enable_functions,
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

    def _persist_to_root_config(self):
        try:
            write_root_config(self._export_root_values())
        except Exception as e:
            print(f"Warnung: Konnte CHAPPIE_CONFIG.json nicht schreiben: {e}")

    def _persist_to_addsecrets(self):
        """Legacy alias: neue Runtime-Settings werden in CHAPPIE_CONFIG.json gespeichert."""
        self._persist_to_root_config()

settings = Settings()


def get_active_model() -> str:
    if settings.llm_provider == LLMProvider.GROQ:
        return settings.groq_model
    elif settings.llm_provider == LLMProvider.VLLM:
        return settings.vllm_model
    return settings.ollama_model


def print_config():
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    table = Table(title="CHAPiE Konfiguration", show_header=True)
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
