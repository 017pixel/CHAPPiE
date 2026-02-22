"""
CHAPiE - NVIDIA Brain
=====================
LLM-Backend fuer NVIDIA NIM API.

NVIDIA NIM bietet:
- Zugriff auf verschiedene Modelle (DeepSeek, GLM, Llama, etc.)
- OpenAI-kompatible API
- Streaming Support

Benötigt: NVIDIA API Key (https://build.nvidia.com)
"""

from typing import Generator, Optional, List
import requests
import json

from .base_brain import BaseBrain, Message, GenerationConfig
from config.config import settings


NVIDIA_MODELS = {
    "z-ai/glm5": "GLM 5 - Z.ai's leistungsstarkes Modell",
    "deepseek-ai/deepseek-v3.1-terminus": "DeepSeek V3.1 Terminus - Reasoning optimiert",
    "moonshotai/kimi-k2.5": "Kimi K2.5 - Moonshot AI",
    "meta/llama-3.3-70b-instruct": "Llama 3.3 70B",
    "meta/llama-3.1-405b-instruct": "Llama 3.1 405B - Groesstes Llama",
    "nvidia/llama-3.1-nemotron-70b": "Nemotron 70B - NVIDIA optimiert",
    "deepseek-ai/deepseek-r1": "DeepSeek R1 - Reasoning",
}


class NVIDIABrain(BaseBrain):
    """
    LLM-Backend fuer NVIDIA NIM API.
    
    NVIDIA NIM nutzt eine OpenAI-kompatible API.
    Unterstuetzt Streaming fuer fluessige Token-Ausgabe.
    """
    
    BASE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
    
    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialisiert das NVIDIA-Backend.
        
        Args:
            model: Modellname (default: aus Settings)
            api_key: NVIDIA API Key (default: aus Settings)
        """
        self.api_key = api_key or getattr(settings, 'nvidia_api_key', '')
        model_name = model or getattr(settings, 'nvidia_model', 'deepseek-ai/deepseek-v3.1-terminus')
        super().__init__(model_name)
        
        if not self.api_key:
            print("WARNUNG: NVIDIA Brain - Kein API-Key konfiguriert!")
            print("   Trage deinen Key in config/secrets.py ein")
            print("   Hole einen Key von: https://build.nvidia.com")
            self._is_initialized = False
            return
        
        self._is_initialized = True
        print(f"NVIDIA Brain initialisiert")
        print(f"   API: {self.BASE_URL}")
        print(f"   Modell: {self.model}")
    
    def generate(
        self,
        messages: List[Message],
        config: Optional[GenerationConfig] = None
    ) -> Generator[str, None, None] | str:
        """
        Generiert eine Antwort mit NVIDIA NIM.
        
        Args:
            messages: Chat-Nachrichten
            config: Generierungs-Konfiguration
        
        Returns:
            Generator (streaming) oder String (nicht-streaming)
        """
        if not self._is_initialized:
            error_msg = "FEHLER: NVIDIA nicht initialisiert - API-Key fehlt!"
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
        
        nvidia_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        if config.stream:
            return self._stream_generate(nvidia_messages, config)
        else:
            return self._sync_generate(nvidia_messages, config)
    
    def _build_headers(self, stream: bool = False) -> dict:
        """Baut die HTTP-Headers fuer NVIDIA API."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "text/event-stream" if stream else "application/json",
            "Content-Type": "application/json"
        }
    
    def _stream_generate(
        self,
        messages: List[dict],
        config: GenerationConfig
    ) -> Generator[str, None, None]:
        """Streaming-Generierung - Token fuer Token."""
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": 1.0,
            "stream": True,
        }
        
        try:
            response = requests.post(
                self.BASE_URL,
                headers=self._build_headers(stream=True),
                json=payload,
                stream=True,
                timeout=120
            )
            
            if response.status_code != 200:
                yield f"\nNVIDIA Fehler: HTTP {response.status_code} - {response.text[:200]}"
                return
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode("utf-8")
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            if "choices" in data and data["choices"]:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
                            
        except requests.exceptions.Timeout:
            yield "\nNVIDIA Fehler: Timeout - Anfrage dauerte zu lange"
        except requests.exceptions.ConnectionError:
            yield "\nNVIDIA Fehler: Verbindungsfehler - Pruefe Internetverbindung"
        except Exception as e:
            yield f"\nNVIDIA Fehler: {str(e)}"
    
    def _sync_generate(self, messages: List[dict], config: GenerationConfig) -> str:
        """Synchrone Generierung - komplette Antwort auf einmal."""
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": 1.0,
            "stream": False,
        }
        
        try:
            response = requests.post(
                self.BASE_URL,
                headers=self._build_headers(stream=False),
                json=payload,
                timeout=120
            )
            
            if response.status_code != 200:
                return f"NVIDIA Fehler: HTTP {response.status_code} - {response.text[:200]}"
            
            data = response.json()
            
            if "choices" in data and data["choices"]:
                return data["choices"][0]["message"]["content"]
            else:
                return f"NVIDIA Fehler: Unerwartete Antwort - {data}"
                
        except requests.exceptions.Timeout:
            return "NVIDIA Fehler: Timeout - Anfrage dauerte zu lange"
        except requests.exceptions.ConnectionError:
            return "NVIDIA Fehler: Verbindungsfehler - Pruefe Internetverbindung"
        except Exception as e:
            return f"NVIDIA Fehler: {str(e)}"
    
    def is_available(self) -> bool:
        """Prueft ob NVIDIA NIM bereit ist (kein API-Call, nur Initialisierungs-Check)."""
        return self._is_initialized
    
    def get_model_info(self) -> dict:
        """Gibt Modell-Informationen zurueck."""
        return {
            "name": self.model,
            "provider": "nvidia",
            "local": False,
            "api_configured": bool(self.api_key),
            "description": NVIDIA_MODELS.get(self.model, "Unbekanntes Modell")
        }
    
    def list_models(self) -> List[str]:
        """Listet alle verfuegbaren NVIDIA-Modelle."""
        return list(NVIDIA_MODELS.keys())


if __name__ == "__main__":
    from rich.console import Console
    from rich.panel import Panel
    
    console = Console()
    console.print(Panel("NVIDIA Brain Test", style="bold green"))
    
    brain = NVIDIABrain()
    
    console.print(f"\n[cyan]1. Pruefe Verfuegbarkeit...[/cyan]")
    if brain.is_available():
        console.print("   NVIDIA NIM API ist erreichbar!")
        
        console.print(f"\n[cyan]2. Verfuegbare Modelle:[/cyan]")
        for model_id, model_desc in NVIDIA_MODELS.items():
            console.print(f"   - {model_id}: {model_desc}")
        
        console.print(f"\n[cyan]3. Test-Generierung (Streaming)...[/cyan]")
        
        messages = [
            Message(role="system", content="Du bist ein hilfreicher Assistent. Antworte kurz auf Deutsch."),
            Message(role="user", content="Was ist 2+2? Antworte in einem Satz.")
        ]
        
        console.print("   Antwort: ", end="")
        for token in brain.generate(messages):
            console.print(token, end="")
        console.print()
        
        console.print("\n[green]NVIDIA Brain Test erfolgreich![/green]")
    else:
        console.print("   NVIDIA NIM ist nicht erreichbar!")
        if not brain.api_key:
            console.print("   Trage deinen API-Key in config/secrets.py ein")
            console.print("   Hole einen Key von: https://build.nvidia.com")
        else:
            console.print("   Pruefe deine Internetverbindung oder den API-Key")
