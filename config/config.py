"""
CHAPiE - Zentrale Konfiguration
===============================
Laedt Einstellungen aus secrets.py und stellt sie bereit.
"""

from pathlib import Path
from enum import Enum

# === Projekt-Pfade ===
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CHROMA_DB_DIR = DATA_DIR / "chroma_db"

# Erstelle Verzeichnisse falls nicht vorhanden
DATA_DIR.mkdir(exist_ok=True)
CHROMA_DB_DIR.mkdir(exist_ok=True)


class LLMProvider(str, Enum):
    """Verfuegbare LLM-Backend Provider."""
    OLLAMA = "ollama"
    GROQ = "groq"
    CEREBRAS = "cerebras"
    NVIDIA = "nvidia"


# === Lade Einstellungen ===
# 1. Lade Defaults aus secrets.py
try:
    from config import secrets
except ImportError:
    # Fallback falls secrets.py komplett fehlt
    import types
    secrets = types.ModuleType("secrets")

# 2. Versuche addSecrets.py zu laden (User Overrides)
try:
    from config import addSecrets
except ImportError:
    addSecrets = None

class Settings:
    """
    Hauptkonfiguration fuer CHAPiE.
    Hierarchie: UI > addSecrets.py > secrets.py
    """
    
    def __init__(self):
        self._load_from_files()

    def _get_val(self, name, default=None):
        """Hilfsfunktion: Holt Wert aus addSecrets, dann secrets, dann default."""
        # 1. Check addSecrets
        if addSecrets and hasattr(addSecrets, name):
            val = getattr(addSecrets, name)
            if val: return val # Nur wenn nicht leer
            
        # 2. Check secrets
        if hasattr(secrets, name):
            return getattr(secrets, name)
            
        # 3. Default
        return default

    def _load_from_files(self):
        # === LLM Backend ===
        provider_str = self._get_val("LLM_PROVIDER", "groq")
        try:
            self.llm_provider = LLMProvider(provider_str.lower())
        except ValueError:
            self.llm_provider = LLMProvider.GROQ

        # === Ollama ===
        self.ollama_host = self._get_val("OLLAMA_HOST", "http://localhost:11434")
        self.ollama_model = self._get_val("OLLAMA_MODEL", "llama3:8b")
        self.emotion_analysis_model = self._get_val("EMOTION_ANALYSIS_MODEL", "qwen2.5:1.5b")
        
        # === Groq ===
        self.groq_api_key = self._get_val("GROQ_API_KEY", "")
        self.groq_model = self._get_val("GROQ_MODEL", "moonshotai/kimi-k2-instruct-0905")
        
        # === Cerebras ===
        self.cerebras_api_key = self._get_val("CEREBRAS_API_KEY", "")
        self.cerebras_model = self._get_val("CEREBRAS_MODEL", "llama-3.3-70b")
        
        # === NVIDIA NIM ===
        self.nvidia_api_key = self._get_val("NVIDIA_API_KEY", "")
        self.nvidia_model = self._get_val("NVIDIA_MODEL", "deepseek-ai/deepseek-v3.1-terminus")
        
        # === Memory / Embedding ===
        self.embedding_model = self._get_val("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.memory_top_k = int(self._get_val("MEMORY_TOP_K", 5))
        self.memory_min_relevance = float(self._get_val("MEMORY_MIN_RELEVANCE", 0.2))
        self.chroma_collection_name = self._get_val("CHROMA_COLLECTION", "chapie_memory")

        # === Short-Term Memory / Daily Info ===
        self.daily_info_path = self._get_val("DAILY_INFO_PATH", str(DATA_DIR / "daily_info.md"))
        self.personality_path = self._get_val("PERSONALITY_PATH", str(DATA_DIR / "personality.md"))
        self.short_term_ttl_hours = int(self._get_val("SHORT_TERM_TTL_HOURS", 24))
        self.enable_functions = self._get_val("ENABLE_FUNCTIONS", True)
        self.auto_consolidate = self._get_val("AUTO_CONSOLIDATE", True)

        # === Query Extraction ===
        self.enable_query_extraction = self._get_val("ENABLE_QUERY_EXTRACTION", True)
        self.query_extraction_groq_model = self._get_val("QUERY_EXTRACTION_GROQ_MODEL", "llama-3.1-8b-instant")
        self.query_extraction_ollama_model = self._get_val("QUERY_EXTRACTION_OLLAMA_MODEL", "llama3.2:1b")

        # === Intent Processor (Step 1) ===
        # NEUE MODELLE fuer Intent Analysis (Step 1):
        # - Cerebras: qwen-3-235b-a22b-instruct-2507
        # - Groq: openai/gpt-oss-120b
        # - Ollama: gpt-oss-20b
        self.enable_two_step_processing = self._get_val("ENABLE_TWO_STEP_PROCESSING", True)
        self.intent_processor_model_groq = self._get_val("INTENT_PROCESSOR_MODEL_GROQ", "openai/gpt-oss-120b")
        self.intent_processor_model_cerebras = self._get_val("INTENT_PROCESSOR_MODEL_CEREBRAS", "qwen-3-235b-a22b-instruct-2507")
        self.intent_processor_model_ollama = self._get_val("INTENT_PROCESSOR_MODEL_OLLAMA", "gpt-oss-20b")
        self.intent_processor_model_nvidia = self._get_val("INTENT_PROCESSOR_MODEL_NVIDIA", "deepseek-ai/deepseek-v3.1-terminus")
        
        # === Context Files ===
        self.soul_path = self._get_val("SOUL_PATH", str(DATA_DIR / "soul.md"))
        self.user_path = self._get_val("USER_PATH", str(DATA_DIR / "user.md"))
        self.preferences_path = self._get_val("PREFERENCES_PATH", str(DATA_DIR / "CHAPPiEsPreferences.md"))
        
        # === Debug Mode ===
        # CLI: Debug ist immer an
        # Web UI: Debug ist standardmäßig aus (per /debug oder Button aktivierbar)
        self.cli_debug_always_on = True
        self.web_debug_default = False

        # === Generation ===
        self.max_tokens = int(self._get_val("MAX_TOKENS", 1024))
        self.temperature = float(self._get_val("TEMPERATURE", 0.7))
        self.stream = bool(self._get_val("STREAM", True))
        
        # === Chain of Thought ===
        self.chain_of_thought = bool(self._get_val("CHAIN_OF_THOUGHT", True))
        
        # === System ===
        self.debug = bool(self._get_val("DEBUG", True))

    def update_from_ui(self, provider=None, api_key=None, model=None, cerebras_api_key=None,
                       nvidia_api_key=None, temperature=None, max_tokens=None, chain_of_thought=None, 
                       memory_top_k=None, memory_min_relevance=None):
        """Erlaubt Updates zur Laufzeit durch die UI."""
        if provider:
            try:
                self.llm_provider = LLMProvider(provider.lower())
            except: pass

        if api_key is not None:
            if self.llm_provider == LLMProvider.CEREBRAS:
                self.cerebras_api_key = api_key
            elif self.llm_provider == LLMProvider.NVIDIA:
                self.nvidia_api_key = api_key
            else:
                self.groq_api_key = api_key

        if cerebras_api_key is not None:
            self.cerebras_api_key = cerebras_api_key
            
        if nvidia_api_key is not None:
            self.nvidia_api_key = nvidia_api_key

        if model:
            if self.llm_provider == LLMProvider.GROQ:
                self.groq_model = model
            elif self.llm_provider == LLMProvider.CEREBRAS:
                self.cerebras_model = model
            elif self.llm_provider == LLMProvider.NVIDIA:
                self.nvidia_model = model
            else:
                self.ollama_model = model

        # Generation settings
        if temperature is not None:
            self.temperature = temperature
        if max_tokens is not None:
            self.max_tokens = max_tokens
        if chain_of_thought is not None:
            self.chain_of_thought = chain_of_thought
        if memory_top_k is not None:
            self.memory_top_k = memory_top_k
        if memory_min_relevance is not None:
            self.memory_min_relevance = memory_min_relevance

        # Persist to addSecrets.py
        self._persist_to_addsecrets()
        
        # Signal that a reload is needed (for frontend to know)
        self._needs_reload = True

    def _persist_to_addsecrets(self):
        """Schreibt die aktuellen Settings in addSecrets.py für Persistierung."""
        try:
            addsecrets_path = PROJECT_ROOT / "config" / "addSecrets.py"
            with open(addsecrets_path, "w") as f:
                f.write("# Automatisch generierte Benutzer-Overrides\n")
                f.write("# Diese Datei wird von der UI aktualisiert - nicht manuell bearbeiten!\n\n")

                # Provider
                f.write(f"LLM_PROVIDER = '{self.llm_provider.value}'\n")

                # API Keys
                if self.groq_api_key:
                    f.write(f"GROQ_API_KEY = '{self.groq_api_key}'\n")
                if self.cerebras_api_key:
                    f.write(f"CEREBRAS_API_KEY = '{self.cerebras_api_key}'\n")
                if self.nvidia_api_key:
                    f.write(f"NVIDIA_API_KEY = '{self.nvidia_api_key}'\n")

                # Models
                f.write(f"GROQ_MODEL = '{self.groq_model}'\n")
                f.write(f"CEREBRAS_MODEL = '{self.cerebras_model}'\n")
                f.write(f"NVIDIA_MODEL = '{self.nvidia_model}'\n")
                f.write(f"OLLAMA_MODEL = '{self.ollama_model}'\n")
                f.write(f"OLLAMA_HOST = '{self.ollama_host}'\n")
                f.write(f"EMOTION_ANALYSIS_MODEL = '{self.emotion_analysis_model}'\n")
                f.write(f"EMBEDDING_MODEL = '{self.embedding_model}'\n")

                # Memory
                f.write(f"MEMORY_TOP_K = {self.memory_top_k}\n")
                f.write(f"MEMORY_MIN_RELEVANCE = {self.memory_min_relevance}\n")
                f.write(f"CHROMA_COLLECTION = '{self.chroma_collection_name}'\n")

                # Query Extraction
                f.write(f"ENABLE_QUERY_EXTRACTION = {self.enable_query_extraction}\n")
                f.write(f"QUERY_EXTRACTION_GROQ_MODEL = '{self.query_extraction_groq_model}'\n")
                f.write(f"QUERY_EXTRACTION_OLLAMA_MODEL = '{self.query_extraction_ollama_model}'\n")

                # Generation
                f.write(f"MAX_TOKENS = {self.max_tokens}\n")
                f.write(f"TEMPERATURE = {self.temperature}\n")
                f.write(f"STREAM = {self.stream}\n")

                # Chain of Thought
                f.write(f"CHAIN_OF_THOUGHT = {self.chain_of_thought}\n")

                # Short-Term Memory / Daily Info
                # Use forward slashes for paths to avoid backslash escape issues
                daily_path = self.daily_info_path.replace('\\', '/')
                personality_path = self.personality_path.replace('\\', '/')
                f.write(f"DAILY_INFO_PATH = '{daily_path}'\n")
                f.write(f"PERSONALITY_PATH = '{personality_path}'\n")
                f.write(f"SHORT_TERM_TTL_HOURS = {self.short_term_ttl_hours}\n")
                f.write(f"ENABLE_FUNCTIONS = {self.enable_functions}\n")
                f.write(f"AUTO_CONSOLIDATE = {self.auto_consolidate}\n")

        except Exception as e:
            print(f"Warnung: Konnte addSecrets.py nicht schreiben: {e}")


# === Globale Settings-Instanzen ===
settings = Settings()


def get_active_model() -> str:
    """Gibt das aktive Modell basierend auf dem Provider zurueck."""
    if settings.llm_provider == LLMProvider.GROQ:
        return settings.groq_model
    elif settings.llm_provider == LLMProvider.CEREBRAS:
        return settings.cerebras_model
    elif settings.llm_provider == LLMProvider.NVIDIA:
        return settings.nvidia_model
    return settings.ollama_model



def print_config():
    """Gibt die aktuelle Konfiguration aus (fuer Debug)."""
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    table = Table(title="CHAPiE Konfiguration", show_header=True)
    table.add_column("Setting", style="cyan")
    table.add_column("Wert", style="green")
    
    table.add_row("LLM Provider", settings.llm_provider.value)
    table.add_row("Aktives Modell", get_active_model())
    table.add_row("Embedding Modell", settings.embedding_model)
    table.add_row("Memory Top-K", str(settings.memory_top_k))
    table.add_row("Min Relevanz", f"{settings.memory_min_relevance:.2f}")
    table.add_row("Temperature", str(settings.temperature))
    table.add_row("Streaming", "Ja" if settings.stream else "Nein")
    table.add_row("Chain of Thought", "Ja" if settings.chain_of_thought else "Nein")
    table.add_row("Debug", "Ja" if settings.debug else "Nein")
    
    console.print(table)


if __name__ == "__main__":
    # Test: Zeige Konfiguration
    print_config()
