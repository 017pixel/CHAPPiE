"""
CHAPiE - Groq Brain
===================
LLM-Backend fuer Groq Cloud API.

Perfekt fuer:
- Schnelle Inferenz (extrem niedrige Latenz)
- Entwicklung ohne GPU-Last
- Zugriff auf groessere Modelle

Benoetigt: Groq API Key (https://console.groq.com)
"""

from typing import Generator, Optional
from groq import Groq

from .base_brain import BaseBrain, Message, GenerationConfig
from config.config import settings


class GroqBrain(BaseBrain):
    """
    LLM-Backend fuer Groq Cloud API.
    
    Groq bietet extrem schnelle Inferenz durch spezielle Hardware.
    Unterstuetzt Streaming fuer fluessige Token-Ausgabe.
    """
    
    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialisiert das Groq-Backend.
        
        Args:
            model: Modellname (default: aus secrets.py)
            api_key: Groq API Key (default: aus secrets.py)
        """
        self.api_key = api_key or settings.groq_api_key
        model_name = model or settings.groq_model
        super().__init__(model_name)
        
        if not self.api_key:
            print("WARNUNG: Groq Brain - Kein API-Key konfiguriert!")
            print("   Trage deinen Key in config/secrets.py ein")
            self._is_initialized = False
            return
        
        # Groq Client initialisieren
        self.client = Groq(api_key=self.api_key)
        self._is_initialized = True
        
        print(f"Groq Brain initialisiert")
        print(f"   Cloud API verbunden")
        print(f"   Modell: {self.model}")
    
    def generate(
        self,
        messages: list[Message],
        config: Optional[GenerationConfig] = None
    ) -> Generator[str, None, None] | str:
        """
        Generiert eine Antwort mit Groq.
        
        Args:
            messages: Chat-Nachrichten
            config: Generierungs-Konfiguration
        
        Returns:
            Generator (streaming) oder String (nicht-streaming)
        """
        if not self._is_initialized:
            error_msg = "FEHLER: Groq nicht initialisiert - API-Key fehlt!"
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
        
        # Konvertiere Messages zu Groq-Format
        groq_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        if config.stream:
            return self._stream_generate(groq_messages, config)
        else:
            return self._sync_generate(groq_messages, config)
    
    def _stream_generate(
        self,
        messages: list[dict],
        config: GenerationConfig
    ) -> Generator[str, None, None]:
        """Streaming-Generierung - Token fuer Token."""
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
            yield f"\nGroq Fehler: {str(e)}"
    
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
            return f"Groq Fehler: {str(e)}"
    
    def is_available(self) -> bool:
        """Prueft ob Groq bereit ist (kein API-Call, nur Initialisierungs-Check)."""
        return self._is_initialized
    
    def get_model_info(self) -> dict:
        """Gibt Modell-Informationen zurueck."""
        return {
            "name": self.model,
            "provider": "groq",
            "local": False,
            "api_configured": bool(self.api_key)
        }
    
    def list_models(self) -> list[str]:
        """Listet alle verfuegbaren Groq-Modelle."""
        if not self._is_initialized:
            return []
        
        try:
            models = self.client.models.list()
            return [m.id for m in models.data]
        except Exception:
            return []


# === Verfuegbare Groq Modelle (Stand: Januar 2026) ===
GROQ_MODELS = {
    "llama-3.1-8b-instant": "Llama 3.1 8B - Schnell & effizient",
    "llama-3.1-70b-versatile": "Llama 3.1 70B - Leistungsstark",
    "llama-3.2-1b-preview": "Llama 3.2 1B - Ultra-schnell",
    "llama-3.2-3b-preview": "Llama 3.2 3B - Kompakt",
    "mixtral-8x7b-32768": "Mixtral 8x7B - MoE Architektur",
    "gemma2-9b-it": "Gemma 2 9B - Google's Modell",
}


# === Test-Funktion ===
if __name__ == "__main__":
    from rich.console import Console
    from rich.panel import Panel
    
    console = Console()
    console.print(Panel("Groq Brain Test", style="bold blue"))
    
    # Brain initialisieren
    brain = GroqBrain()
    
    # Verfuegbarkeit pruefen
    console.print(f"\n[cyan]1. Pruefe Verfuegbarkeit...[/cyan]")
    if brain.is_available():
        console.print("   Groq API ist erreichbar!")
        
        # Modelle auflisten
        models = brain.list_models()
        console.print(f"   Verfuegbare Modelle: {len(models)}")
        for model in models[:5]:
            console.print(f"      - {model}")
        
        # Test-Generierung
        console.print(f"\n[cyan]2. Test-Generierung (Streaming)...[/cyan]")
        
        messages = [
            Message(role="system", content="Du bist ein hilfreicher Assistent. Antworte kurz."),
            Message(role="user", content="Was ist 2+2? Antworte in einem Satz.")
        ]
        
        console.print("   Antwort: ", end="")
        for token in brain.generate(messages):
            console.print(token, end="")
        console.print()
        
        console.print("\n[green]Groq Brain Test erfolgreich![/green]")
    else:
        console.print("   Groq ist nicht erreichbar!")
        if not brain.api_key:
            console.print("   Trage deinen API-Key in config/secrets.py ein")
        else:
            console.print("   Pruefe deine Internetverbindung")
