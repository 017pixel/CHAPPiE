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

from typing import Any, Generator, Optional
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

    def _supports_thinking_toggle(self) -> bool:
        model_name = self.model.lower()
        return any(name in model_name for name in ("qwen3", "qwen3.5", "deepseek", "gpt-oss"))

    def _build_chat_kwargs(
        self,
        messages: list[dict],
        options: dict,
        stream: bool,
        think_override: Optional[bool] = None,
    ) -> dict:
        kwargs = {
            "model": self.model,
            "messages": messages,
            "options": options,
            "stream": stream,
        }
        if think_override is not None:
            kwargs["think"] = think_override
        elif self._supports_thinking_toggle():
            kwargs["think"] = False
        return kwargs

    def _chat(
        self,
        messages: list[dict],
        options: dict,
        stream: bool,
        think_override: Optional[bool] = None,
    ):
        kwargs = self._build_chat_kwargs(messages, options, stream, think_override=think_override)
        try:
            return self.client.chat(**kwargs)
        except TypeError:
            kwargs.pop("think", None)
            return self.client.chat(**kwargs)
        except Exception as exc:
            error_text = str(exc).lower()
            if "think" in error_text and ("unexpected" in error_text or "unknown" in error_text):
                kwargs.pop("think", None)
                return self.client.chat(**kwargs)
            raise

    @staticmethod
    def _message_content(message: Any) -> str:
        if isinstance(message, dict):
            return str(message.get("content", "") or "")
        return str(getattr(message, "content", "") or "")

    @staticmethod
    def _message_thinking(message: Any) -> str:
        if isinstance(message, dict):
            return str(message.get("thinking", "") or "")
        return str(getattr(message, "thinking", "") or "")

    @staticmethod
    def _response_message(response: Any) -> Any:
        if isinstance(response, dict):
            return response.get("message", {})
        return getattr(response, "message", {})

    @staticmethod
    def _response_done_reason(response: Any) -> str:
        if isinstance(response, dict):
            return str(response.get("done_reason", "") or "")
        return str(getattr(response, "done_reason", "") or "")

    def _empty_response_error(self, thinking: str = "", done_reason: str = "") -> str:
        details = []
        if thinking:
            details.append("nur Thinking/Reasoning ohne finalen Antworttext")
        if done_reason:
            details.append(f"done_reason={done_reason}")
        detail_suffix = f" ({', '.join(details)})" if details else ""
        return f"Ollama Fehler: Leere Modellantwort{detail_suffix}"

    @staticmethod
    def _format_reasoning_response(thinking: str, answer: str = "CHAPPiE schweigt...") -> str:
        cleaned_thinking = (thinking or "").strip()
        cleaned_answer = (answer or "CHAPPiE schweigt...").strip()
        return f"<model_reasoning>\n{cleaned_thinking}\n</model_reasoning>\n\n{cleaned_answer}"

    def _recover_reasoning_only_response(self, messages: list[dict], options: dict) -> str:
        if not self._supports_thinking_toggle():
            return self._empty_response_error()

        try:
            response = self._chat(messages=messages, options=options, stream=False, think_override=True)
            message = self._response_message(response)
            content = self._message_content(message).strip()
            thinking = self._message_thinking(message).strip()
            if content and thinking:
                return self._format_reasoning_response(thinking, answer=content)
            if thinking:
                return self._format_reasoning_response(thinking)
            if content:
                return content
            return self._empty_response_error(done_reason=self._response_done_reason(response).strip())
        except Exception:
            return self._empty_response_error()
    
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
            stream = self._chat(messages=messages, options=options, stream=True)
            saw_thinking = False
            saw_content = False
            
            for chunk in stream:
                message = self._response_message(chunk)
                content = self._message_content(message)
                thinking = self._message_thinking(message)
                if thinking:
                    saw_thinking = True
                if content:
                    saw_content = True
                    yield content

            if not saw_content:
                yield self._empty_response_error(thinking="1" if saw_thinking else "")
                        
        except Exception as e:
            yield f"\nOllama Fehler: {str(e)}"
    
    def _sync_generate(self, messages: list[dict], options: dict) -> str:
        """Synchrone Generierung - komplette Antwort auf einmal."""
        try:
            response = self._chat(messages=messages, options=options, stream=False)
            message = self._response_message(response)
            content = self._message_content(message).strip()
            thinking = self._message_thinking(message).strip()
            done_reason = self._response_done_reason(response).strip()

            if content and thinking:
                return self._format_reasoning_response(thinking, answer=content)
            if content:
                return content
            if thinking:
                return self._format_reasoning_response(thinking)
            recovered = self._recover_reasoning_only_response(messages, options)
            if recovered and not recovered.startswith("Ollama Fehler"):
                return recovered
            return self._empty_response_error(thinking=thinking, done_reason=done_reason)
            
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
