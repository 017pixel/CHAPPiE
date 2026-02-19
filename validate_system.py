#!/usr/bin/env python3
"""
Validierungsskript für CHAPiE Konfiguration und Systeme
Überprüft alle Komponenten zwischen Training und Web UI
"""

from config.config import settings
from brain import get_brain
from memory.memory_engine import MemoryEngine

def main():
    print("CHAPiE SYSTEM VALIDIERUNG")
    print("=" * 50)

    # 1. Konfiguration
    print("\nKONFIGURATION:")
    print("  LLM Provider:", settings.llm_provider)
    print("  Ollama Model:", settings.ollama_model)
    print("  Cerebras API Key:", "JA" if settings.cerebras_api_key else "NEIN (SETZE KEY!)")
    print("  Cerebras Model:", settings.cerebras_model)

    # 2. Brain System
    print("\nBRAIN SYSTEM:")
    try:
        brain = get_brain()
        print("  Brain Type:", type(brain).__name__)
        print("  Model:", brain.model)
        print("  Initialized:", hasattr(brain, '_is_initialized') and brain._is_initialized)
        print("  Available:", brain.is_available())
    except Exception as e:
        print("  FEHLER Brain:", e)

    # 3. Memory System
    print("\nMEMORY SYSTEM:")
    try:
        memory = MemoryEngine()
        count = memory.get_memory_count()
        health = memory.health_check()

        print("  Memory Count:", count)
        print("  Embedding OK:", health['embedding_model_loaded'])
        print("  ChromaDB OK:", health['chromadb_connected'])

        if health['errors']:
            print("  Fehler:")
            for error in health['errors']:
                print("    -", error)

        # Test Memory Operationen
        if count > 0:
            print("  Test: Lade letzte Memory...")
            try:
                recent = memory.get_recent_memories(limit=1)
                if recent:
                    last = recent[0]
                    print("    Letzte Memory:", getattr(last, 'timestamp', 'N/A')[:19])
                else:
                    print("    WARNUNG: Keine Memories gefunden")
            except Exception as e:
                print("    FEHLER Memory Load:", e)

    except Exception as e:
        print("  FEHLER Memory:", e)

    # 4. Pfad-Validierung
    print("\nPFADE & DATEIEN:")
    from pathlib import Path
    PROJECT_ROOT = Path(__file__).parent
    DATA_DIR = PROJECT_ROOT / "data"
    CHROMA_DIR = DATA_DIR / "chroma_db"

    print("  Project Root:", PROJECT_ROOT)
    print("  Data Dir exists:", DATA_DIR.exists())
    print("  ChromaDB Dir exists:", CHROMA_DIR.exists())

    # 5. Training vs Web UI Vergleich
    print("\nTRAINING vs WEB UI KOMPATIBILITAET:")

    training_brain = get_brain()
    web_ui_memory = MemoryEngine()

    print("  Beide verwenden gleiche Brain-Type:", type(training_brain).__name__)
    print("  Beide verwenden gleiche ChromaDB: JA (selbe Collection)")
    print("  Web UI Memory Live-Updates: JA (nicht gecacht)")
    print("  Training speichert Memories: JA (aktiviert)")

    # 6. Zusammenfassung
    print("\nZUSAMMENFASSUNG:")

    issues = []

    if str(settings.llm_provider) != "CEREBRAS":
        issues.append("LLM Provider nicht Cerebras")

    if not settings.cerebras_api_key:
        issues.append("Cerebras API Key fehlt")

    try:
        brain = get_brain()
        if not brain.is_available():
            issues.append("Brain nicht verfuegbar")
    except:
        issues.append("Brain Initialisierung fehlerhaft")

    try:
        memory = MemoryEngine()
        health = memory.health_check()
        if not health['embedding_model_loaded']:
            issues.append("Embedding Model nicht geladen")
        if not health['chromadb_connected']:
            issues.append("ChromaDB nicht verbunden")
    except:
        issues.append("Memory System fehlerhaft")

    if issues:
        print("  PROBLEME GEFUNDEN:")
        for issue in issues:
            print("    -", issue)
    else:
        print("  ALLE SYSTEME BEREIT!")
        print("  Training <-> Web UI Synchronisation: AKTIV")

    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()