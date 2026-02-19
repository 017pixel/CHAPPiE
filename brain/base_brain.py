"""
CHAPiE - Brain Base Class
==========================
Abstrakte Basisklasse für alle LLM-Backends.

Ermöglicht einfachen Wechsel zwischen verschiedenen Providern
(Ollama, Groq, etc.) ohne Änderungen am restlichen Code.
"""

from abc import ABC, abstractmethod
from typing import Generator, Optional
from dataclasses import dataclass


@dataclass
class Message:
    """Repräsentiert eine Chat-Nachricht."""
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class GenerationConfig:
    """Konfiguration für Text-Generierung."""
    max_tokens: int = 1024
    temperature: float = 0.7
    stream: bool = True
    stop_sequences: Optional[list[str]] = None


class BaseBrain(ABC):
    """
    Abstrakte Basisklasse für LLM-Backends.
    
    Jedes Backend muss diese Methoden implementieren:
    - generate(): Generiert Text (mit oder ohne Streaming)
    - is_available(): Prüft ob das Backend verfügbar ist
    """
    
    def __init__(self, model: str):
        """
        Initialisiert das Brain.
        
        Args:
            model: Name des zu verwendenden Modells
        """
        self.model = model
        self._is_initialized = False
    
    @abstractmethod
    def generate(
        self,
        messages: list[Message],
        config: Optional[GenerationConfig] = None
    ) -> Generator[str, None, None] | str:
        """
        Generiert eine Antwort basierend auf den Nachrichten.
        
        Args:
            messages: Liste von Chat-Nachrichten (System, User, Assistant)
            config: Generierungs-Konfiguration
        
        Returns:
            Bei stream=True: Generator der Token für Token liefert
            Bei stream=False: Vollständige Antwort als String
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Prüft ob das Backend verfügbar ist.
        
        Returns:
            True wenn das Backend erreichbar und funktional ist
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> dict:
        """
        Gibt Informationen über das aktive Modell zurück.
        
        Returns:
            Dict mit Modell-Informationen
        """
        pass
    
    def build_prompt(self, system: str, memories: str, user_input: str, history: list[dict] = None) -> list[Message]:
        """
        Baut die Nachrichten-Liste für den Chat-Prompt.
        
        Args:
            system: System-Prompt (Persönlichkeit)
            memories: Formatierte Erinnerungen aus dem Memory
            user_input: Aktuelle User-Eingabe
            history: Chat-Verlauf (Liste von Dicts mit 'role' und 'content')
        
        Returns:
            Liste von Message-Objekten
        """
        messages = []
        
        # System-Prompt mit Erinnerungen
        full_system = system
        if memories:
            full_system += f"\n\n{memories}"
        
        messages.append(Message(role="system", content=full_system))
        
        # Chat-Verlauf hinzufügen (wenn vorhanden)
        if history:
            for msg in history:
                messages.append(Message(role=msg["role"], content=msg["content"]))
        
        messages.append(Message(role="user", content=user_input))
        
        return messages
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model='{self.model}')"
