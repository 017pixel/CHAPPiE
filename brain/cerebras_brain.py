"""
CHAPiE - Cerebras Brain
========================
LLM-Backend für Cerebras Cloud API.

Cerebras bietet:
- Extrem schnelle Inferenz (bis zu 2000+ Token/Sekunde)
- Zugang zu großen Modellen (Llama 3.3 70B, Qwen 3 235B)
- OpenAI-kompatible API

Benötigt: Cerebras API Key (https://cloud.cerebras.ai)
"""

from typing import Generator, Optional
from openai import OpenAI

from .base_brain import BaseBrain, Message, GenerationConfig
from config.config import settings


class CerebrasBrain(BaseBrain):
    """
    LLM-Backend für Cerebras Cloud API.
    
    Cerebras nutzt eine OpenAI-kompatible API mit eigenem Endpoint.
    Unterstützt Streaming für flüssige Token-Ausgabe.
    """
    
    # Cerebras API Base URL
    BASE_URL = "https://api.cerebras.ai/v1"
    
    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialisiert das Cerebras-Backend.
        
        Args:
            model: Modellname (default: aus Settings)
            api_key: Cerebras API Key (default: aus Settings)
        """
        self.api_key = api_key or getattr(settings, 'cerebras_api_key', '')
        model_name = model or getattr(settings, 'cerebras_model', 'llama-3.3-70b')
        super().__init__(model_name)
        
        if not self.api_key:
            print("WARNUNG: Cerebras Brain - Kein API-Key konfiguriert!")
            print("   Trage deinen Key in config/secrets.py ein")
            self._is_initialized = False
            return
        
        # OpenAI-kompatiblen Client mit Cerebras Endpoint initialisieren
        try:
            self.client = OpenAI(
                base_url=self.BASE_URL,
                api_key=self.api_key
            )
            self._is_initialized = True
            
            print(f"Cerebras Brain initialisiert")
            print(f"   Cloud API verbunden ({self.BASE_URL})")
            print(f"   Modell: {self.model}")
        except Exception as e:
            print(f"FEHLER bei Cerebras-Initialisierung: {e}")
            self._is_initialized = False
    
    def generate(
        self,
        messages: list[Message],
        config: Optional[GenerationConfig] = None
    ) -> Generator[str, None, None] | str:
        """
        Generiert eine Antwort mit Cerebras.
        
        Args:
            messages: Chat-Nachrichten
            config: Generierungs-Konfiguration
        
        Returns:
            Generator (streaming) oder String (nicht-streaming)
        """
        if not self._is_initialized:
            error_msg = "FEHLER: Cerebras nicht initialisiert - API-Key fehlt!"
            if config and config.stream:
                def error_gen():
                    yield error_msg
                return error_gen()
            return error_msg
        
        if config is None:
            config = GenerationConfig(
                max_tokens=settings.max_tokens,
                temperature=settings.temperature,
                stream=settings.stream
            )
        
        # Konvertiere Messages zu OpenAI-Format
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        if config.stream:
            return self._stream_generate(openai_messages, config)
        else:
            return self._sync_generate(openai_messages, config)
    
    def _stream_generate(
        self,
        messages: list[dict],
        config: GenerationConfig
    ) -> Generator[str, None, None]:
        """Streaming-Generierung - Token für Token."""
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            yield f"\nCerebras Fehler: {str(e)}"
    
    def _sync_generate(self, messages: list[dict], config: GenerationConfig) -> str:
        """Synchrone Generierung - komplette Antwort auf einmal."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                stream=False
            )
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Cerebras Fehler: {str(e)}"
    
    def is_available(self) -> bool:
        """Prüft ob Cerebras erreichbar ist."""
        if not self._is_initialized:
            return False
        
        try:
            # Kleiner API-Test mit Models-Endpoint
            self.client.models.list()
            return True
        except Exception:
            return False
    
    def get_model_info(self) -> dict:
        """Gibt Modell-Informationen zurück."""
        return {
            "name": self.model,
            "provider": "cerebras",
            "local": False,
            "api_configured": bool(self.api_key)
        }
    
    def list_models(self) -> list[str]:
        """Listet alle verfügbaren Cerebras-Modelle."""
        if not self._is_initialized:
            return []
        
        try:
            models = self.client.models.list()
            return [m.id for m in models.data]
        except Exception:
            # Fallback: Liste bekannter Modelle
            return list(CEREBRAS_MODELS.keys())


# === Verfügbare Cerebras Modelle (Stand: Januar 2026) ===
CEREBRAS_MODELS = {
    "llama-3.3-70b": "Llama 3.3 70B - Leistungsstark & Schnell",
    "llama-3.1-8b": "Llama 3.1 8B - Kompakt & Effizient",
    "qwen-3-32b": "Qwen 3 32B - Alibaba's Modell",
}


# === Test-Funktion ===
if __name__ == "__main__":
    from rich.console import Console
    from rich.panel import Panel
    
    console = Console()
    console.print(Panel("Cerebras Brain Test", style="bold blue"))
    
    # Brain initialisieren
    brain = CerebrasBrain()
    
    # Verfügbarkeit prüfen
    console.print(f"\n[cyan]1. Prüfe Verfügbarkeit...[/cyan]")
    if brain.is_available():
        console.print("   Cerebras API ist erreichbar!")
        
        # Modelle auflisten
        models = brain.list_models()
        console.print(f"   Verfügbare Modelle: {len(models)}")
        for model in models[:5]:
            console.print(f"      - {model}")
        
        # Test-Generierung
        console.print(f"\n[cyan]2. Test-Generierung (Streaming)...[/cyan]")
        
        messages = [
            Message(role="system", content="Du bist ein hilfreicher Assistent. Antworte kurz auf Deutsch."),
            Message(role="user", content="Was ist 2+2? Antworte in einem Satz.")
        ]
        
        console.print("   Antwort: ", end="")
        for token in brain.generate(messages):
            console.print(token, end="")
        console.print()
        
        console.print("\n[green]Cerebras Brain Test erfolgreich![/green]")
    else:
        console.print("   Cerebras ist nicht erreichbar!")
        if not brain.api_key:
            console.print("   Trage deinen API-Key in config/secrets.py ein")
        else:
            console.print("   Prüfe deine Internetverbindung oder den API-Key")
