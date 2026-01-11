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


# === Lade Einstellungen aus secrets.py ===
from config import secrets


class Settings:
    """
    Hauptkonfiguration fuer CHAPiE.
    Laedt Werte aus secrets.py.
    """
    
    # === LLM Backend ===
    llm_provider: LLMProvider = LLMProvider(secrets.LLM_PROVIDER.lower())
    
    # === Ollama ===
    ollama_host: str = secrets.OLLAMA_HOST
    ollama_model: str = secrets.OLLAMA_MODEL
    
    # === Groq ===
    groq_api_key: str = secrets.GROQ_API_KEY
    groq_model: str = secrets.GROQ_MODEL
    
    # === Memory / Embedding ===
    embedding_model: str = secrets.EMBEDDING_MODEL
    memory_top_k: int = secrets.MEMORY_TOP_K
    chroma_collection_name: str = secrets.CHROMA_COLLECTION

    # === Query Extraction (RAG Optimization) ===
    enable_query_extraction: bool = getattr(secrets, 'ENABLE_QUERY_EXTRACTION', True)
    query_extraction_groq_model: str = getattr(secrets, 'QUERY_EXTRACTION_GROQ_MODEL', 'llama-3.1-8b-instant')
    query_extraction_ollama_model: str = getattr(secrets, 'QUERY_EXTRACTION_OLLAMA_MODEL', 'llama3.2:1b')

    # === Generation ===
    max_tokens: int = secrets.MAX_TOKENS
    temperature: float = secrets.TEMPERATURE
    stream: bool = secrets.STREAM
    
    # === Chain of Thought ===
    # Aktiviert den inneren Monolog - CHAPiE denkt erst nach, dann antwortet
    chain_of_thought: bool = getattr(secrets, 'CHAIN_OF_THOUGHT', True)
    
    # === System ===
    debug: bool = secrets.DEBUG


# === Globale Settings-Instanzen ===
settings = Settings()


def get_active_model() -> str:
    """Gibt das aktive Modell basierend auf dem Provider zurueck."""
    if settings.llm_provider == LLMProvider.GROQ:
        return settings.groq_model
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
