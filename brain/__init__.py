"""
CHAPiE Brain Module - LLM Backend Abstraction.

Nutze get_brain() für automatische Backend-Auswahl basierend auf secrets.py.
"""
from .base_brain import BaseBrain, Message, GenerationConfig
from .ollama_brain import OllamaBrain
from .groq_brain import GroqBrain
from .cerebras_brain import CerebrasBrain
from .nvidia_brain import NVIDIABrain
from .deep_think import DeepThinkEngine, DeepThinkStep

from config.config import settings, LLMProvider


def get_brain() -> BaseBrain:
    """
    Factory-Funktion: Gibt das konfigurierte Brain zurück.
    
    Wählt automatisch basierend auf LLM_PROVIDER in secrets.py:
    - "ollama" → OllamaBrain (lokal)
    - "groq" → GroqBrain (cloud)
    - "cerebras" → CerebrasBrain (cloud, high-speed)
    - "nvidia" → NVIDIABrain (cloud, DeepSeek/GLM/Llama)
    
    Returns:
        Initialisiertes Brain-Objekt
    """
    if settings.llm_provider == LLMProvider.GROQ:
        return GroqBrain()
    elif settings.llm_provider == LLMProvider.CEREBRAS:
        return CerebrasBrain()
    elif settings.llm_provider == LLMProvider.NVIDIA:
        return NVIDIABrain()
    else:
        return OllamaBrain()
