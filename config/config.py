"""
CHAPiE - Zentrale Konfiguration
===============================
Laedt Einstellungen aus secrets.py und stellt sie bereit.
"""

import json
from pathlib import Path
from enum import Enum

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CHROMA_DB_DIR = DATA_DIR / "chroma_db"
USER_SETTINGS_PATH = DATA_DIR / "settings_overrides.json"

DATA_DIR.mkdir(exist_ok=True)
CHROMA_DB_DIR.mkdir(exist_ok=True)


class LLMProvider(str, Enum):
    OLLAMA = "ollama"
    GROQ = "groq"
    CEREBRAS = "cerebras"
    NVIDIA = "nvidia"
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
        self._user_overrides = {}
        self._needs_reload = False
        self._load_from_files()

    def _load_runtime_overrides(self):
        if not USER_SETTINGS_PATH.exists():
            return {}
        try:
            raw = json.loads(USER_SETTINGS_PATH.read_text(encoding="utf-8"))
            return raw if isinstance(raw, dict) else {}
        except Exception:
            return {}

    def _get_val(self, name, default=None):
        if name in self._user_overrides:
            return self._user_overrides[name]
        if addSecrets and hasattr(addSecrets, name):
            val = getattr(addSecrets, name)
            if val is not None:
                return val
        if hasattr(secrets, name):
            return getattr(secrets, name)
        return default

    def _load_from_files(self):
        self._user_overrides = self._load_runtime_overrides()

        provider_str = self._get_val("LLM_PROVIDER", "vllm")
        try:
            self.llm_provider = LLMProvider(provider_str.lower())
        except ValueError:
            self.llm_provider = LLMProvider.VLLM

        self.ollama_host = self._get_val("OLLAMA_HOST", "http://localhost:11434")
        self.ollama_model = self._get_val("OLLAMA_MODEL", "qwen2.5:7b")

        self.vllm_url = self._get_val("VLLM_URL", "http://localhost:8000/v1")
        self.vllm_model = self._get_val("VLLM_MODEL", "Qwen/Qwen3.5-122B-A10B-Instruct-GPTQ-Int4")

        self.groq_api_key = self._get_val("GROQ_API_KEY", "")
        self.groq_model = self._get_val("GROQ_MODEL", "moonshotai/kimi-k2-instruct-0905")

        self.cerebras_api_key = self._get_val("CEREBRAS_API_KEY", "")
        self.cerebras_model = self._get_val("CEREBRAS_MODEL", "llama-3.3-70b")

        self.nvidia_api_key = self._get_val("NVIDIA_API_KEY", "")
        self.nvidia_model = self._get_val("NVIDIA_MODEL", "deepseek-ai/deepseek-v3.1-terminus")

        self.intent_provider = _parse_provider(self._get_val("INTENT_PROVIDER", "auto"))
        self.intent_processor_model_groq = self._get_val("INTENT_PROCESSOR_MODEL_GROQ", "openai/gpt-oss-120b")
        self.intent_processor_model_cerebras = self._get_val("INTENT_PROCESSOR_MODEL_CEREBRAS", "qwen-3-235b-a22b-instruct-2507")
        self.intent_processor_model_ollama = self._get_val("INTENT_PROCESSOR_MODEL_OLLAMA", "qwen2.5:7b")
        self.intent_processor_model_vllm = self._get_val("INTENT_PROCESSOR_MODEL_VLLM", "Qwen/Qwen3.5-122B-A10B-Instruct")
        self.intent_processor_model_nvidia = self._get_val("INTENT_PROCESSOR_MODEL_NVIDIA", "deepseek-ai/deepseek-v3.1-terminus")
        self.enable_two_step_processing = self._get_val("ENABLE_TWO_STEP_PROCESSING", True)

        self.query_extraction_provider = _parse_provider(self._get_val("QUERY_EXTRACTION_PROVIDER", "auto"))
        self.query_extraction_groq_model = self._get_val("QUERY_EXTRACTION_GROQ_MODEL", "llama-3.1-8b-instant")
        self.query_extraction_ollama_model = self._get_val("QUERY_EXTRACTION_OLLAMA_MODEL", "llama3.2:1b")
        self.query_extraction_vllm_model = self._get_val("QUERY_EXTRACTION_VLLM_MODEL", "Qwen/Qwen3.5-9B-Instruct")
        self.query_extraction_nvidia_model = self._get_val("QUERY_EXTRACTION_NVIDIA_MODEL", "meta/llama-3.1-8b-instruct")
        self.query_extraction_cerebras_model = self._get_val("QUERY_EXTRACTION_CEREBRAS_MODEL", "llama-3.3-70b")
        self.enable_query_extraction = self._get_val("ENABLE_QUERY_EXTRACTION", True)

        self.emotion_analysis_model = self._get_val("EMOTION_ANALYSIS_MODEL", "qwen2.5:1.5b")
        self.emotion_analysis_host = self._get_val("EMOTION_ANALYSIS_HOST", "http://localhost:11434")

        self.embedding_model = self._get_val("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

        self.training_use_global_settings = self._get_val("TRAINING_USE_GLOBAL_SETTINGS", True)
        self.training_chappie_provider = _parse_provider(self._get_val("TRAINING_CHAPPIE_PROVIDER", "auto"))
        self.training_chappie_model = self._get_val("TRAINING_CHAPPIE_MODEL", "")
        self.training_trainer_provider = _parse_provider(self._get_val("TRAINING_TRAINER_PROVIDER", "auto"))
        self.training_trainer_model = self._get_val("TRAINING_TRAINER_MODEL", "")

        self.memory_top_k = int(self._get_val("MEMORY_TOP_K", 15))
        self.memory_min_relevance = float(self._get_val("MEMORY_MIN_RELEVANCE", 0.2))
        self.chroma_collection_name = self._get_val("CHROMA_COLLECTION", "chapie_memory")

        self.daily_info_path = self._get_val("DAILY_INFO_PATH", str(DATA_DIR / "daily_info.md"))
        self.personality_path = self._get_val("PERSONALITY_PATH", str(DATA_DIR / "personality.md"))
        self.short_term_ttl_hours = int(self._get_val("SHORT_TERM_TTL_HOURS", 24))
        self.enable_functions = self._get_val("ENABLE_FUNCTIONS", True)
        self.auto_consolidate = self._get_val("AUTO_CONSOLIDATE", True)

        self.soul_path = self._get_val("SOUL_PATH", str(DATA_DIR / "soul.md"))
        self.user_path = self._get_val("USER_PATH", str(DATA_DIR / "user.md"))
        self.preferences_path = self._get_val("PREFERENCES_PATH", str(DATA_DIR / "CHAPPiEsPreferences.md"))

        self.enable_steering = self._get_val("ENABLE_STEERING", False)
        self.steering_provider = _parse_provider(self._get_val("STEERING_PROVIDER", "vllm"))
        self.steering_model = self._get_val("STEERING_MODEL", "Qwen/Qwen3.5-122B-A10B-Instruct")

        self.cli_debug_always_on = True
        self.web_debug_default = False

        self.max_tokens = int(self._get_val("MAX_TOKENS", 1024))
        self.temperature = float(self._get_val("TEMPERATURE", 0.7))
        self.stream = bool(self._get_val("STREAM", True))
        self.chain_of_thought = bool(self._get_val("CHAIN_OF_THOUGHT", True))
        self.debug = bool(self._get_val("DEBUG", True))

    def get_effective_provider(self, step_provider=None):
        if step_provider is None or step_provider == "auto":
            return self.llm_provider
        if isinstance(step_provider, LLMProvider):
            return step_provider
        try:
            return LLMProvider(step_provider.lower())
        except (ValueError, AttributeError):
            return self.llm_provider

    def get_intent_model(self, provider=None):
        effective = self.get_effective_provider(provider if provider != "auto" else None)
        if effective == LLMProvider.GROQ:
            return self.intent_processor_model_groq
        if effective == LLMProvider.CEREBRAS:
            return self.intent_processor_model_cerebras
        if effective == LLMProvider.NVIDIA:
            return self.intent_processor_model_nvidia
        if effective == LLMProvider.VLLM:
            return self.intent_processor_model_vllm
        return self.intent_processor_model_ollama

    def get_query_extraction_model(self, provider=None):
        effective = self.get_effective_provider(provider if provider != "auto" else None)
        if effective == LLMProvider.GROQ:
            return self.query_extraction_groq_model
        if effective == LLMProvider.NVIDIA:
            return self.query_extraction_nvidia_model
        if effective == LLMProvider.CEREBRAS:
            return self.query_extraction_cerebras_model
        if effective == LLMProvider.VLLM:
            return self.query_extraction_vllm_model
        return self.query_extraction_ollama_model

    def update_from_ui(self, **kwargs):
        previous_main_provider = self.llm_provider
        previous_intent_provider = self.intent_provider
        previous_query_provider = self.query_extraction_provider
        incoming_intent_provider = kwargs.get("intent_provider")
        incoming_query_provider = kwargs.get("query_extraction_provider")

        if "llm_provider" in kwargs and kwargs["llm_provider"]:
            try:
                self.llm_provider = LLMProvider(kwargs["llm_provider"].lower())
            except Exception:
                pass

        for key in ["groq_api_key", "cerebras_api_key", "nvidia_api_key"]:
            if key in kwargs and kwargs[key] is not None:
                setattr(self, key, kwargs[key])

        for key in ["groq_model", "cerebras_model", "nvidia_model", "vllm_model", "vllm_url", "ollama_model", "ollama_host"]:
            if key in kwargs and kwargs[key]:
                setattr(self, key, kwargs[key])

        if "intent_provider" in kwargs:
            self.intent_provider = _parse_provider(kwargs["intent_provider"])
        for key in ["intent_processor_model_groq", "intent_processor_model_cerebras", "intent_processor_model_ollama", "intent_processor_model_vllm", "intent_processor_model_nvidia"]:
            if key in kwargs and kwargs[key]:
                setattr(self, key, kwargs[key])

        if "query_extraction_provider" in kwargs:
            self.query_extraction_provider = _parse_provider(kwargs["query_extraction_provider"])
        for key in ["query_extraction_groq_model", "query_extraction_ollama_model", "query_extraction_vllm_model", "query_extraction_nvidia_model", "query_extraction_cerebras_model"]:
            if key in kwargs and kwargs[key]:
                setattr(self, key, kwargs[key])

        for key in ["emotion_analysis_model", "emotion_analysis_host", "embedding_model"]:
            if key in kwargs and kwargs[key]:
                setattr(self, key, kwargs[key])

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

        for key in ["temperature", "max_tokens", "chain_of_thought", "memory_top_k", "memory_min_relevance"]:
            if key in kwargs and kwargs[key] is not None:
                setattr(self, key, kwargs[key])

        if self.llm_provider != previous_main_provider:
            if previous_intent_provider == previous_main_provider and _parse_provider(incoming_intent_provider) == previous_main_provider:
                self.intent_provider = None
            if previous_query_provider == previous_main_provider and _parse_provider(incoming_query_provider) == previous_main_provider:
                self.query_extraction_provider = None

        self._persist_to_addsecrets()
        self._needs_reload = True

    def _serialize_setting_value(self, value):
        if isinstance(value, Enum):
            return value.value
        return value

    def _persist_to_addsecrets(self):
        try:
            USER_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "LLM_PROVIDER": self.llm_provider,
                "OLLAMA_HOST": self.ollama_host,
                "OLLAMA_MODEL": self.ollama_model,
                "VLLM_URL": self.vllm_url,
                "VLLM_MODEL": self.vllm_model,
                "GROQ_API_KEY": self.groq_api_key,
                "GROQ_MODEL": self.groq_model,
                "CEREBRAS_API_KEY": self.cerebras_api_key,
                "CEREBRAS_MODEL": self.cerebras_model,
                "NVIDIA_API_KEY": self.nvidia_api_key,
                "NVIDIA_MODEL": self.nvidia_model,
                "INTENT_PROVIDER": self.intent_provider,
                "INTENT_PROCESSOR_MODEL_GROQ": self.intent_processor_model_groq,
                "INTENT_PROCESSOR_MODEL_CEREBRAS": self.intent_processor_model_cerebras,
                "INTENT_PROCESSOR_MODEL_OLLAMA": self.intent_processor_model_ollama,
                "INTENT_PROCESSOR_MODEL_VLLM": self.intent_processor_model_vllm,
                "INTENT_PROCESSOR_MODEL_NVIDIA": self.intent_processor_model_nvidia,
                "ENABLE_TWO_STEP_PROCESSING": self.enable_two_step_processing,
                "QUERY_EXTRACTION_PROVIDER": self.query_extraction_provider,
                "QUERY_EXTRACTION_GROQ_MODEL": self.query_extraction_groq_model,
                "QUERY_EXTRACTION_OLLAMA_MODEL": self.query_extraction_ollama_model,
                "QUERY_EXTRACTION_VLLM_MODEL": self.query_extraction_vllm_model,
                "QUERY_EXTRACTION_NVIDIA_MODEL": self.query_extraction_nvidia_model,
                "QUERY_EXTRACTION_CEREBRAS_MODEL": self.query_extraction_cerebras_model,
                "ENABLE_QUERY_EXTRACTION": self.enable_query_extraction,
                "EMOTION_ANALYSIS_MODEL": self.emotion_analysis_model,
                "EMOTION_ANALYSIS_HOST": self.emotion_analysis_host,
                "EMBEDDING_MODEL": self.embedding_model,
                "TRAINING_USE_GLOBAL_SETTINGS": self.training_use_global_settings,
                "TRAINING_CHAPPIE_PROVIDER": self.training_chappie_provider,
                "TRAINING_CHAPPIE_MODEL": self.training_chappie_model,
                "TRAINING_TRAINER_PROVIDER": self.training_trainer_provider,
                "TRAINING_TRAINER_MODEL": self.training_trainer_model,
                "MEMORY_TOP_K": self.memory_top_k,
                "MEMORY_MIN_RELEVANCE": self.memory_min_relevance,
                "CHROMA_COLLECTION": self.chroma_collection_name,
                "MAX_TOKENS": self.max_tokens,
                "TEMPERATURE": self.temperature,
                "STREAM": self.stream,
                "CHAIN_OF_THOUGHT": self.chain_of_thought,
                "DAILY_INFO_PATH": str(self.daily_info_path),
                "PERSONALITY_PATH": str(self.personality_path),
                "SHORT_TERM_TTL_HOURS": self.short_term_ttl_hours,
                "ENABLE_FUNCTIONS": self.enable_functions,
                "AUTO_CONSOLIDATE": self.auto_consolidate,
            }
            serialized = {key: self._serialize_setting_value(value) for key, value in payload.items()}
            USER_SETTINGS_PATH.write_text(json.dumps(serialized, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            print(f"Warnung: Konnte settings_overrides.json nicht schreiben: {e}")


settings = Settings()


def get_active_model() -> str:
    if settings.llm_provider == LLMProvider.GROQ:
        return settings.groq_model
    if settings.llm_provider == LLMProvider.CEREBRAS:
        return settings.cerebras_model
    if settings.llm_provider == LLMProvider.NVIDIA:
        return settings.nvidia_model
    if settings.llm_provider == LLMProvider.VLLM:
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