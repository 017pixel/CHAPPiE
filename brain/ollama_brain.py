"""
CHAPiE - Ollama Brain
=====================
LLM-Backend fuer lokale Modelle via Ollama.

Perfekt fuer:
- Offline-Nutzung
- Datenschutz (Daten bleiben lokal)
- GPU-Beschleunigung auf deiner RTX 3060

Voraussetzung: Ollama muss laufen (https://ollama.ai)
"""

from typing import Generator, Optional
import ollama
from ollama import Client

from .base_brain import BaseBrain, Message, GenerationConfig
from config.config import settings


class OllamaBrain(BaseBrain):
    """
    LLM-Backend fuer lokale Modelle via Ollama.
    
    Unterstuetzt Streaming fuer fluessige Token-Ausgabe.
    """
    
    def __init__(self, model: Optional[str] = None, host: Optional[str] = None):
        """
        Initialisiert das Ollama-Backend.
        
        Args:
            model: Modellname (default: aus secrets.py)
            host: Ollama Server URL (default: aus secrets.py)
        """
        self.host = host or settings.ollama_host
        model_name = model or settings.ollama_model
        super().__init__(model_name)
        
        # Ollama Client initialisieren
        self.client = Client(host=self.host)
        self._is_initialized = True
        
        print(f"Ollama Brain initialisiert")
        print(f"   Host: {self.host}")
        print(f"   Modell: {self.model}")
    
    def generate(
        self,
        messages: list[Message],
        config: Optional[GenerationConfig] = None
    ) -> Generator[str, None, None] | str:
        """
        Generiert eine Antwort mit Ollama.
        
        Args:
            messages: Chat-Nachrichten
            config: Generierungs-Konfiguration
        
        Returns:
            Generator (streaming) oder String (nicht-streaming)
        """
        if config is None:
            config = GenerationConfig(
                max_tokens=settings.max_tokens,
                temperature=settings.temperature,
                stream=settings.stream
            )
        
        # Konvertiere Messages zu Ollama-Format
        ollama_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        # Optionen fuer Ollama
        options = {
            "temperature": config.temperature,
            "num_predict": config.max_tokens,
        }
        
        if config.stream:
            return self._stream_generate(ollama_messages, options)
        else:
            return self._sync_generate(ollama_messages, options)
    
    def _stream_generate(
        self,
        messages: list[dict],
        options: dict
    ) -> Generator[str, None, None]:
        """Streaming-Generierung - Token fuer Token."""
        try:
            stream = self.client.chat(
                model=self.model,
                messages=messages,
                options=options,
                stream=True
            )
            
            for chunk in stream:
                if chunk and "message" in chunk:
                    content = chunk["message"].get("content", "")
                    if content:
                        yield content
                        
        except Exception as e:
            yield f"\nOllama Fehler: {str(e)}"
    
    def _sync_generate(self, messages: list[dict], options: dict) -> str:
        """Synchrone Generierung - komplette Antwort auf einmal."""
        try:
            response = self.client.chat(
                model=self.model,
                messages=messages,
                options=options,
                stream=False
            )
            return response["message"]["content"]
            
        except Exception as e:
            return f"Ollama Fehler: {str(e)}"
    
    def is_available(self) -> bool:
        """Prueft ob Ollama erreichbar ist."""
        try:
            # Versuche Modell-Liste abzurufen
            self.client.list()
            return True
        except Exception:
            return False
    
    def get_model_info(self) -> dict:
        """Gibt Modell-Informationen zurueck."""
        try:
            models = self.client.list()
            for model in models.get("models", []):
                if self.model in model.get("name", ""):
                    return {
                        "name": model.get("name"),
                        "size": model.get("size"),
                        "modified": model.get("modified_at"),
                        "provider": "ollama",
                        "local": True
                    }
            return {"name": self.model, "provider": "ollama", "local": True}
        except Exception as e:
            return {"error": str(e), "provider": "ollama"}
    
    def list_models(self) -> list[str]:
        """Listet alle verfuegbaren lokalen Modelle."""
        try:
            models = self.client.list()
            return [m.get("name", "") for m in models.get("models", [])]
        except Exception:
            return []
    
    def pull_model(self, model_name: str) -> bool:
        """
        Laedt ein Modell herunter.
        
        Args:
            model_name: Name des Modells (z.B. "llama3:8b")
        
        Returns:
            True wenn erfolgreich
        """
        try:
            print(f"Lade Modell: {model_name}...")
            self.client.pull(model_name)
            print(f"Modell {model_name} geladen!")
            return True
        except Exception as e:
            print(f"Fehler beim Laden: {e}")
            return False


# === Test-Funktion ===
if __name__ == "__main__":
    from rich.console import Console
    from rich.panel import Panel
    from rich.live import Live
    
    console = Console()
    console.print(Panel("Ollama Brain Test", style="bold blue"))
    
    # Brain initialisieren
    brain = OllamaBrain()
    
    # Verfuegbarkeit pruefen
    console.print(f"\n[cyan]1. Pruefe Verfuegbarkeit...[/cyan]")
    if brain.is_available():
        console.print("   Ollama ist erreichbar!")
        
        # Modelle auflisten
        models = brain.list_models()
        console.print(f"   Verfuegbare Modelle: {', '.join(models[:5])}")
        
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
        
        console.print("\n[green]Ollama Brain Test erfolgreich![/green]")
    else:
        console.print("   Ollama ist nicht erreichbar!")
        console.print("   Starte Ollama: ollama serve")
