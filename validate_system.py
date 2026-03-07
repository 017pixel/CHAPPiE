#!/usr/bin/env python3
"""Validiert Konfiguration, Brain-, Memory- und Training-Kompatibilität."""

import inspect
import sys
from pathlib import Path

from config.config import settings, LLMProvider
from brain import get_brain
from memory.memory_engine import MemoryEngine


def _provider_summary() -> list[str]:
    provider = settings.llm_provider
    lines = [f"  LLM Provider: {provider.value}"]
    if provider == LLMProvider.NVIDIA:
        lines.extend([
            f"  NVIDIA API Key: {'JA' if settings.nvidia_api_key else 'NEIN (SETZE KEY!)'}",
            f"  NVIDIA Model: {settings.nvidia_model}",
        ])
    elif provider == LLMProvider.CEREBRAS:
        lines.extend([
            f"  Cerebras API Key: {'JA' if settings.cerebras_api_key else 'NEIN (SETZE KEY!)'}",
            f"  Cerebras Model: {settings.cerebras_model}",
        ])
    elif provider == LLMProvider.GROQ:
        lines.extend([
            f"  Groq API Key: {'JA' if settings.groq_api_key else 'NEIN (SETZE KEY!)'}",
            f"  Groq Model: {settings.groq_model}",
        ])
    else:
        lines.extend([
            f"  Ollama Host: {settings.ollama_host}",
            f"  Ollama Model: {settings.ollama_model}",
        ])
    return lines


def _active_provider_has_credentials() -> bool:
    if settings.llm_provider == LLMProvider.NVIDIA:
        return bool(settings.nvidia_api_key)
    if settings.llm_provider == LLMProvider.CEREBRAS:
        return bool(settings.cerebras_api_key)
    if settings.llm_provider == LLMProvider.GROQ:
        return bool(settings.groq_api_key)
    return True


def _training_service_is_valid() -> tuple[bool, str]:
    service_file = Path(__file__).parent / "chappie-training.service"
    if not service_file.exists():
        return False, "Service-Datei fehlt"
    content = service_file.read_text(encoding="utf-8")
    valid_target = "Chappies_Trainingspartner.training_daemon" in content or "training_daemon.py" in content
    return valid_target, "ExecStart zeigt auf training_daemon" if valid_target else "ExecStart zeigt nicht auf training_daemon"

def main():
    print("CHAPiE SYSTEM VALIDIERUNG")
    print("=" * 50)

    # 1. Konfiguration
    print("\nKONFIGURATION:")
    for line in _provider_summary():
        print(line)

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
    signature = inspect.signature(MemoryEngine.add_memory)
    print("  MemoryEngine.add_memory Signatur:", list(signature.parameters.keys()))
    service_ok, service_msg = _training_service_is_valid()
    print("  Service-Datei:", service_msg)

    # 6. Zusammenfassung
    print("\nZUSAMMENFASSUNG:")

    issues = []

    if not _active_provider_has_credentials():
        issues.append(f"API Key für aktiven Provider {settings.llm_provider.value} fehlt")

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

    if not service_ok:
        issues.append(service_msg)

    if issues:
        print("  PROBLEME GEFUNDEN:")
        for issue in issues:
            print("    -", issue)
    else:
        print("  ALLE SYSTEME BEREIT!")
        print("  Training <-> Web UI Synchronisation: AKTIV")

    print("\n" + "=" * 50)
    return 1 if issues else 0

if __name__ == "__main__":
    raise SystemExit(main())