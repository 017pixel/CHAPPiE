"""
CHAPiE Brain Module - LLM Backend Abstraction.

Nutze get_brain() für automatische Backend-Auswahl basierend auf settings
oder für eine gezielte Provider-/Modellauswahl pro Agent.
"""
from typing import Optional, Dict, Tuple

from .base_brain import BaseBrain, Message, GenerationConfig
from .ollama_brain import OllamaBrain
from .groq_brain import GroqBrain
from .vllm_brain import VLLMBrain
from .deep_think import DeepThinkEngine, DeepThinkStep

from config.config import settings, LLMProvider

_brain_cache: Dict[Tuple[str, str], BaseBrain] = {}


def get_brain(provider: Optional[LLMProvider] = None, model: Optional[str] = None) -> BaseBrain:
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
    effective_provider = provider or settings.llm_provider
    effective_model = model or None
    cache_key = (effective_provider.value, effective_model or "")

    if cache_key in _brain_cache:
        return _brain_cache[cache_key]

    if effective_provider == LLMProvider.GROQ:
        brain = GroqBrain(model=model)
    elif effective_provider == LLMProvider.VLLM:
        brain = VLLMBrain(model=model)
    else:
        brain = OllamaBrain(model=model)

    _brain_cache[cache_key] = brain
    return brain
