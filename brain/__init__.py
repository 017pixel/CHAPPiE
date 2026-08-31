"""
CHAPiE Brain Module - LLM Backend Abstraction.

Nutze get_brain() für automatische Backend-Auswahl basierend auf settings
oder für eine gezielte Provider-/Modellauswahl pro Agent.
"""
from importlib import import_module
from typing import Optional, Dict, Tuple, Any

from .base_brain import BaseBrain, Message, GenerationConfig

from config.config import settings, LLMProvider, _parse_provider

_brain_cache: Dict[Tuple[str, str], BaseBrain] = {}
_brain_request_audit: list[Dict[str, Any]] = []

_EXPORTS = {
    "OllamaBrain": "ollama_brain",
    "GroqBrain": "groq_brain",
    "VLLMBrain": "vllm_brain",
    "DeepThinkEngine": "deep_think",
    "DeepThinkStep": "deep_think",
}

__all__ = (
    "BaseBrain",
    "Message",
    "GenerationConfig",
    "OllamaBrain",
    "GroqBrain",
    "VLLMBrain",
    "DeepThinkEngine",
    "DeepThinkStep",
    "get_brain",
    "get_brain_request_audit",
    "reset_brain_request_audit",
)


def _load_export(name: str) -> Any:
    module_name = _EXPORTS[name]
    module = import_module(f"{__name__}.{module_name}")
    value = getattr(module, name)
    globals()[name] = value
    return value


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return _load_export(name)


def _normalize_provider(provider: Optional[LLMProvider | str]) -> LLMProvider:
    if isinstance(provider, LLMProvider):
        return provider
    parsed = _parse_provider(provider)
    return parsed or LLMProvider.OLLAMA


def _resolved_model(provider: LLMProvider, model: Optional[str]) -> str:
    if model:
        return str(model)
    if provider == LLMProvider.GROQ:
        return str(settings.groq_model)
    if provider == LLMProvider.VLLM:
        return str(settings.vllm_model)
    return str(settings.ollama_model)


def reset_brain_request_audit() -> None:
    """Begin a fresh provider-call audit without touching reusable clients."""
    _brain_request_audit.clear()


def get_brain_request_audit() -> list[Dict[str, Any]]:
    """Return a copy of every brain factory request since the last reset."""
    return [dict(entry) for entry in _brain_request_audit]


def get_brain(provider: Optional[LLMProvider | str] = None, model: Optional[str] = None) -> BaseBrain:
    """
    Factory-Funktion: Gibt das konfigurierte Brain zurueck (gecached).

    Waehlt automatisch basierend auf LLM_PROVIDER in settings:
    - "ollama" → OllamaBrain (lokal)
    - "groq" → GroqBrain (cloud, high-speed)
    - "vllm" → VLLMBrain (lokale GPU-Beschleunigung)

    Instanzen werden pro (provider, model)-Kombination gecached,
    um mehrfache Initialisierungen zu vermeiden.

    Returns:
        Initialisiertes Brain-Objekt
    """
    effective_provider = _normalize_provider(provider or settings.llm_provider)
    effective_model = model or None
    cache_key = (effective_provider.value, effective_model or "")

    _brain_request_audit.append({
        "provider": effective_provider.value,
        "model": _resolved_model(effective_provider, effective_model),
        "cache_hit": cache_key in _brain_cache,
    })

    if cache_key in _brain_cache:
        return _brain_cache[cache_key]

    if effective_provider == LLMProvider.GROQ:
        brain_cls = _load_export("GroqBrain")
        brain = brain_cls(model=model)
    elif effective_provider == LLMProvider.VLLM:
        brain_cls = _load_export("VLLMBrain")
        brain = brain_cls(model=model)
    else:
        brain_cls = _load_export("OllamaBrain")
        brain = brain_cls(model=model)

    _brain_cache[cache_key] = brain
    return brain
