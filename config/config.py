"""
CHAPiE - Zentrale Konfiguration
===============================
Laedt Einstellungen aus secrets.py und stellt sie bereit.
"""

from pathlib import Path
from enum import Enum

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CHROMA_DB_DIR = DATA_DIR / "chroma_db"

DATA_DIR.mkdir(exist_ok=True)
CHROMA_DB_DIR.mkdir(exist_ok=True)


class LLMProvider(str, Enum):
    OLLAMA = "ollama"
    GROQ = "groq"
    CEREBRAS = "cerebras"
    NVIDIA = "nvidia"


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
        self._load_from_files()

    def _get_val(self, name, default=None):
        if addSecrets and hasattr(addSecrets, name):
            val = getattr(addSecrets, name)
            if val:
                return val
        if hasattr(secrets, name):
            return getattr(secrets, name)
        return default

    def _load_from_files(self):
        provider_str = self._get_val("LLM_PROVIDER", "groq")
        try:
            self.llm_provider = LLMProvider(provider_str.lower())
        except ValueError:
            self.llm_provider = LLMProvider.GROQ

        self.ollama_host = self._get_val("OLLAMA_HOST", "http://localhost:11434")
        self.ollama_model = self._get_val("OLLAMA_MODEL", "llama3:8b")
        
        self.groq_api_key = self._get_val("GROQ_API_KEY", "")
        self.groq_model = self._get_val("GROQ_MODEL", "moonshotai/kimi-k2-instruct-0905")
        
        self.cerebras_api_key = self._get_val("CEREBRAS_API_KEY", "")
        self.cerebras_model = self._get_val("CEREBRAS_MODEL", "llama-3.3-70b")
        
        self.nvidia_api_key = self._get_val("NVIDIA_API_KEY", "")
        self.nvidia_model = self._get_val("NVIDIA_MODEL", "deepseek-ai/deepseek-v3.1-terminus")

        self.intent_provider = _parse_provider(self._get_val("INTENT_PROVIDER", "auto"))
        self.intent_processor_model_groq = self._get_val("INTENT_PROCESSOR_MODEL_GROQ", "openai/gpt-oss-120b")
        self.intent_processor_model_cerebras = self._get_val("INTENT_PROCESSOR_MODEL_CEREBRAS", "qwen-3-235b-a22b-instruct-2507")
        self.intent_processor_model_ollama = self._get_val("INTENT_PROCESSOR_MODEL_OLLAMA", "llama3:8b")
        self.intent_processor_model_nvidia = self._get_val("INTENT_PROCESSOR_MODEL_NVIDIA", "deepseek-ai/deepseek-v3.1-terminus")
        self.enable_two_step_processing = self._get_val("ENABLE_TWO_STEP_PROCESSING", True)

        self.query_extraction_provider = _parse_provider(self._get_val("QUERY_EXTRACTION_PROVIDER", "auto"))
        self.query_extraction_groq_model = self._get_val("QUERY_EXTRACTION_GROQ_MODEL", "llama-3.1-8b-instant")
        self.query_extraction_ollama_model = self._get_val("QUERY_EXTRACTION_OLLAMA_MODEL", "llama3.2:1b")
        self.enable_query_extraction = self._get_val("ENABLE_QUERY_EXTRACTION", True)

        self.emotion_analysis_model = self._get_val("EMOTION_ANALYSIS_MODEL", "qwen2.5:1.5b")
        self.emotion_analysis_host = self._get_val("EMOTION_ANALYSIS_HOST", "http://localhost:11434")

        self.embedding_model = self._get_val("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        
        self.training_use_global_settings = self._get_val("TRAINING_USE_GLOBAL_SETTINGS", True)
        self.training_chappie_provider = _parse_provider(self._get_val("TRAINING_CHAPPIE_PROVIDER", "auto"))
        self.training_chappie_model = self._get_val("TRAINING_CHAPPIE_MODEL", "")
        self.training_trainer_provider = _parse_provider(self._get_val("TRAINING_TRAINER_PROVIDER", "auto"))
        self.training_trainer_model = self._get_val("TRAINING_TRAINER_MODEL", "")

        self.memory_top_k = int(self._get_val("MEMORY_TOP_K", 5))
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
        elif effective == LLMProvider.CEREBRAS:
            return self.intent_processor_model_cerebras
        elif effective == LLMProvider.NVIDIA:
            return self.intent_processor_model_nvidia
        return self.intent_processor_model_ollama

    def get_query_extraction_model(self, provider=None):
        effective = self.get_effective_provider(provider if provider != "auto" else None)
        if effective == LLMProvider.GROQ:
            return self.query_extraction_groq_model
        return self.query_extraction_ollama_model

    def update_from_ui(self, **kwargs):
        if "llm_provider" in kwargs and kwargs["llm_provider"]:
            try:
                self.llm_provider = LLMProvider(kwargs["llm_provider"].lower())
            except:
                pass

        for key in ["groq_api_key", "cerebras_api_key", "nvidia_api_key"]:
            if key in kwargs and kwargs[key] is not None:
                setattr(self, key, kwargs[key])

        for key in ["groq_model", "cerebras_model", "nvidia_model", "ollama_model", "ollama_host"]:
            if key in kwargs and kwargs[key]:
                setattr(self, key, kwargs[key])

        if "intent_provider" in kwargs:
            self.intent_provider = _parse_provider(kwargs["intent_provider"])
        for key in ["intent_processor_model_groq", "intent_processor_model_cerebras", 
                    "intent_processor_model_ollama", "intent_processor_model_nvidia"]:
            if key in kwargs and kwargs[key]:
                setattr(self, key, kwargs[key])

        if "query_extraction_provider" in kwargs:
            self.query_extraction_provider = _parse_provider(kwargs["query_extraction_provider"])
        for key in ["query_extraction_groq_model", "query_extraction_ollama_model"]:
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

        self._persist_to_addsecrets()
        self._needs_reload = True

    def _persist_to_addsecrets(self):
        try:
            addsecrets_path = PROJECT_ROOT / "config" / "addSecrets.py"
            with open(addsecrets_path, "w", encoding="utf-8") as f:
                f.write("# Automatisch generierte Benutzer-Overrides\n")
                f.write("# Diese Datei wird von der UI aktualisiert - nicht manuell bearbeiten!\n\n")

                f.write(f"LLM_PROVIDER = '{self.llm_provider.value}'\n\n")

                f.write("# === API Keys ===\n")
                if self.groq_api_key:
                    f.write(f"GROQ_API_KEY = '{self.groq_api_key}'\n")
                if self.cerebras_api_key:
                    f.write(f"CEREBRAS_API_KEY = '{self.cerebras_api_key}'\n")
                if self.nvidia_api_key:
                    f.write(f"NVIDIA_API_KEY = '{self.nvidia_api_key}'\n")

                f.write("\n# === Chat-Modelle ===\n")
                f.write(f"GROQ_MODEL = '{self.groq_model}'\n")
                f.write(f"CEREBRAS_MODEL = '{self.cerebras_model}'\n")
                f.write(f"NVIDIA_MODEL = '{self.nvidia_model}'\n")
                f.write(f"OLLAMA_MODEL = '{self.ollama_model}'\n")
                f.write(f"OLLAMA_HOST = '{self.ollama_host}'\n")

                f.write("\n# === Intent Processor (Step 1) ===\n")
                if self.intent_provider:
                    f.write(f"INTENT_PROVIDER = '{self.intent_provider.value}'\n")
                f.write(f"INTENT_PROCESSOR_MODEL_GROQ = '{self.intent_processor_model_groq}'\n")
                f.write(f"INTENT_PROCESSOR_MODEL_CEREBRAS = '{self.intent_processor_model_cerebras}'\n")
                f.write(f"INTENT_PROCESSOR_MODEL_OLLAMA = '{self.intent_processor_model_ollama}'\n")
                f.write(f"INTENT_PROCESSOR_MODEL_NVIDIA = '{self.intent_processor_model_nvidia}'\n")

                f.write("\n# === Query Extraction ===\n")
                if self.query_extraction_provider:
                    f.write(f"QUERY_EXTRACTION_PROVIDER = '{self.query_extraction_provider.value}'\n")
                f.write(f"QUERY_EXTRACTION_GROQ_MODEL = '{self.query_extraction_groq_model}'\n")
                f.write(f"QUERY_EXTRACTION_OLLAMA_MODEL = '{self.query_extraction_ollama_model}'\n")

                f.write("\n# === Emotion Analysis ===\n")
                f.write(f"EMOTION_ANALYSIS_MODEL = '{self.emotion_analysis_model}'\n")
                f.write(f"EMOTION_ANALYSIS_HOST = '{self.emotion_analysis_host}'\n")

                f.write("\n# === Embedding ===\n")
                f.write(f"EMBEDDING_MODEL = '{self.embedding_model}'\n")

                f.write("\n# === Training ===\n")
                f.write(f"TRAINING_USE_GLOBAL_SETTINGS = {self.training_use_global_settings}\n")
                if self.training_chappie_provider:
                    f.write(f"TRAINING_CHAPPIE_PROVIDER = '{self.training_chappie_provider.value}'\n")
                if self.training_chappie_model:
                    f.write(f"TRAINING_CHAPPIE_MODEL = '{self.training_chappie_model}'\n")
                if self.training_trainer_provider:
                    f.write(f"TRAINING_TRAINER_PROVIDER = '{self.training_trainer_provider.value}'\n")
                if self.training_trainer_model:
                    f.write(f"TRAINING_TRAINER_MODEL = '{self.training_trainer_model}'\n")

                f.write("\n# === Memory ===\n")
                f.write(f"MEMORY_TOP_K = {self.memory_top_k}\n")
                f.write(f"MEMORY_MIN_RELEVANCE = {self.memory_min_relevance}\n")
                f.write(f"CHROMA_COLLECTION = '{self.chroma_collection_name}'\n")

                f.write("\n# === Generation ===\n")
                f.write(f"MAX_TOKENS = {self.max_tokens}\n")
                f.write(f"TEMPERATURE = {self.temperature}\n")
                f.write(f"STREAM = {self.stream}\n")
                f.write(f"CHAIN_OF_THOUGHT = {self.chain_of_thought}\n")

                f.write("\n# === Short-Term Memory ===\n")
                daily_path = str(self.daily_info_path).replace('\\', '/')
                personality_path = str(self.personality_path).replace('\\', '/')
                f.write(f"DAILY_INFO_PATH = '{daily_path}'\n")
                f.write(f"PERSONALITY_PATH = '{personality_path}'\n")
                f.write(f"SHORT_TERM_TTL_HOURS = {self.short_term_ttl_hours}\n")
                f.write(f"ENABLE_FUNCTIONS = {self.enable_functions}\n")
                f.write(f"AUTO_CONSOLIDATE = {self.auto_consolidate}\n")

        except Exception as e:
            print(f"Warnung: Konnte addSecrets.py nicht schreiben: {e}")


settings = Settings()


def get_active_model() -> str:
    if settings.llm_provider == LLMProvider.GROQ:
        return settings.groq_model
    elif settings.llm_provider == LLMProvider.CEREBRAS:
        return settings.cerebras_model
    elif settings.llm_provider == LLMProvider.NVIDIA:
        return settings.nvidia_model
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
