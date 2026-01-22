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
        
        # === Memory / Embedding ===
        self.embedding_model = self._get_val("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.memory_top_k = int(self._get_val("MEMORY_TOP_K", 5))
        self.chroma_collection_name = self._get_val("CHROMA_COLLECTION", "chapie_memory")

        # === Query Extraction ===
        self.enable_query_extraction = self._get_val("ENABLE_QUERY_EXTRACTION", True)
        self.query_extraction_groq_model = self._get_val("QUERY_EXTRACTION_GROQ_MODEL", "llama-3.1-8b-instant")
        self.query_extraction_ollama_model = self._get_val("QUERY_EXTRACTION_OLLAMA_MODEL", "llama3.2:1b")

        # === Generation ===
        self.max_tokens = int(self._get_val("MAX_TOKENS", 1024))
        self.temperature = float(self._get_val("TEMPERATURE", 0.7))
        self.stream = bool(self._get_val("STREAM", True))
        
        # === Chain of Thought ===
        self.chain_of_thought = bool(self._get_val("CHAIN_OF_THOUGHT", True))
        
        # === System ===
        self.debug = bool(self._get_val("DEBUG", True))

    def update_from_ui(self, provider=None, api_key=None, model=None, cerebras_api_key=None):
        """Erlaubt Updates zur Laufzeit durch die UI."""
        if provider:
            try:
                self.llm_provider = LLMProvider(provider.lower())
            except: pass
            
        if api_key is not None: # Leerer String ist erlaubt (Loeschen)
            # Je nach aktuellem Provider den richtigen Key setzen
            if self.llm_provider == LLMProvider.CEREBRAS:
                self.cerebras_api_key = api_key
            else:
                self.groq_api_key = api_key
        
        # Expliziter Cerebras API Key (separat)
        if cerebras_api_key is not None:
            self.cerebras_api_key = cerebras_api_key
            
        if model:
            if self.llm_provider == LLMProvider.GROQ:
                self.groq_model = model
            elif self.llm_provider == LLMProvider.CEREBRAS:
                self.cerebras_model = model
            else:
                self.ollama_model = model


# === Globale Settings-Instanzen ===
settings = Settings()


def get_active_model() -> str:
    """Gibt das aktive Modell basierend auf dem Provider zurueck."""
    if settings.llm_provider == LLMProvider.GROQ:
        return settings.groq_model
    elif settings.llm_provider == LLMProvider.CEREBRAS:
        return settings.cerebras_model
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
    table.add_row("Temperature", str(settings.temperature))
    table.add_row("Streaming", "Ja" if settings.stream else "Nein")
    table.add_row("Chain of Thought", "Ja" if settings.chain_of_thought else "Nein")
    table.add_row("Debug", "Ja" if settings.debug else "Nein")
    
    console.print(table)


if __name__ == "__main__":
    # Test: Zeige Konfiguration
    print_config()
