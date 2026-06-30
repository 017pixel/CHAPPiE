"""CHAPiE Memory Module - Episodisches Gedaechtnis mit ChromaDB.

The package exposes the historic convenience imports lazily so lightweight
submodules can be used without installing optional runtime dependencies.
"""

from importlib import import_module
from typing import Any


_EXPORTS = {
    "MemoryEngine": "memory_engine",
    "Memory": "memory_engine",
    "EmotionsEngine": "emotions_engine",
    "EmotionalState": "emotions_engine",
    "analyze_sentiment_simple": "emotions_engine",
    "SleepPhaseHandler": "sleep_phase",
    "get_sleep_phase_handler": "sleep_phase",
    "EbbinghausForgettingCurve": "forgetting_curve",
    "MemoryDecayManager": "forgetting_curve",
    "get_forgetting_curve": "forgetting_curve",
    "get_decay_manager": "forgetting_curve",
    "ShortTermMemory": "short_term_memory",
    "ShortTermEntry": "short_term_memory",
    "get_short_term_memory": "short_term_memory",
    "ContextFilesManager": "context_files",
    "get_context_files_manager": "context_files",
}

__all__ = tuple(_EXPORTS)


def __getattr__(name: str) -> Any:
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(f"{__name__}.{module_name}")
    value = getattr(module, name)
    globals()[name] = value
    return value
