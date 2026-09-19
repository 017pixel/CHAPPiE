"""
CHAPiE Brain Module - LLM Backend Abstraction.

Nutze get_brain() für automatische Backend-Auswahl basierend auf settings
oder für eine gezielte Provider-/Modellauswahl pro Agent.
"""
from importlib import import_module
from hashlib import sha256
from typing import Optional, Dict, Tuple, Any

from .base_brain import BaseBrain, Message, GenerationConfig

from config.config import settings, LLMProvider, _parse_provider

_brain_cache: Dict[Tuple[str, str], BaseBrain] = {}
_brain_cache_signatures: Dict[Tuple[str, str], Tuple[str, ...]] = {}
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


def _provider_runtime_signature(provider: LLMProvider) -> Tuple[str, ...]:
    """Return the connection settings that are captured by a brain client."""
    if provider == LLMProvider.VLLM:
        return (str(getattr(settings, "vllm_url", "")),)
    if provider == LLMProvider.OLLAMA:
        return (str(getattr(settings, "ollama_host", "")),)
    if provider == LLMProvider.GROQ:
        # Keep the credential out of cache-key/debug representations while
        # still invalidating a client as soon as the configured key changes.
        credential = str(getattr(settings, "groq_api_key", "") or "").encode()
        return (sha256(credential).hexdigest(),)
    return ()


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

    Instanzen werden pro (provider, model)-Kombination gecached. Aendert sich
    die Provider-Verbindung in den Runtime-Settings, wird der alte Client
    verworfen und beim naechsten Aufruf neu erstellt.

    Returns:
        Initialisiertes Brain-Objekt
    """
    effective_provider = _normalize_provider(provider or settings.llm_provider)
    effective_model = model or None
    resolved_model = _resolved_model(effective_provider, effective_model)
    # Keep the historical key shape. The resolved model and connection details
    # live in the signature so settings reloads invalidate model=None calls too.
    cache_key = (effective_provider.value, effective_model or "")
    runtime_signature = (resolved_model, *_provider_runtime_signature(effective_provider))
    cache_hit = (
        cache_key in _brain_cache
        and _brain_cache_signatures.get(cache_key) == runtime_signature
    )

    _brain_request_audit.append({
        "provider": effective_provider.value,
        "model": resolved_model,
        "cache_hit": cache_hit,
    })

    if cache_hit:
        return _brain_cache[cache_key]

    # A stale client may contain an old URL, host or credential. Remove it
    # before constructing the replacement so Settings reloads do not retain
    # obsolete provider clients in the reusable cache.
    _brain_cache.pop(cache_key, None)
    _brain_cache_signatures.pop(cache_key, None)

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
    _brain_cache_signatures[cache_key] = runtime_signature
    return brain
