"""
CHAPiE - vLLM Brain
===================
LLM-Backend für vLLM (lokale GPU-Beschleunigung).

Perfekt für:
- Lokales Hosting von massiven Modellen (z.B. Qwen 3.5 122B)
- Geringe Latenz bei lokaler GPU
- Volle Kontrolle über Steering-Vektoren

Benoetigt: vLLM Server laufend (Standard: http://localhost:8000/v1)
"""

from typing import Generator, Optional, Any, Dict
from openai import OpenAI

from .base_brain import BaseBrain, Message, GenerationConfig
from config.config import settings


class VLLMBrain(BaseBrain):
    """
    LLM-Backend für vLLM Server.
    
    Nutzt das OpenAI-kompatible API-Interface von vLLM.
    Unterstützt Activation Steering über 'extra_body'.
    """
    
    def __init__(self, model: Optional[str] = None, url: Optional[str] = None):
        """
        Initialisiert das vLLM-Backend.
        
        Args:
            model: Modellname (default: aus config.py)
            url: vLLM Server URL (default: aus config.py)
        """
        self.url = url or settings.vllm_url
        model_name = model or settings.vllm_model
        super().__init__(model_name)
        
        # OpenAI Client für vLLM (lokal, meist kein Key nötig)
        self.client = OpenAI(
            base_url=self.url,
            api_key="none"  # vLLM braucht meist keinen echten Key
        )
        self._is_initialized = True
        
        print(f"vLLM Brain initialisiert")
        print(f"   Lokal verbunden: {self.url}")
        print(f"   Modell: {self.model}")
    
    def generate(
        self,
        messages: list[Message],
        config: Optional[GenerationConfig] = None
    ) -> Generator[str, None, None] | str:
        """
        Generiert eine Antwort mit vLLM.
        """
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
        
        # Steering / Extra Körper hinzufügen
        extra_body = config.extra_body or {}
        
        if config.stream:
            return self._stream_generate(openai_messages, config, extra_body)
        else:
            return self._sync_generate(openai_messages, config, extra_body)
    
    def _stream_generate(
        self,
        messages: list[dict],
        config: GenerationConfig,
        extra_body: Dict[str, Any]
    ) -> Generator[str, None, None]:
        """Streaming-Generierung."""
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                stream=True,
                extra_body=extra_body
            )
            
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            yield f"\nvLLM Fehler: {str(e)}"
    
    def _sync_generate(
        self, 
        messages: list[dict], 
        config: GenerationConfig,
        extra_body: Dict[str, Any]
    ) -> str:
        """Synchrone Generierung."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                stream=False,
                extra_body=extra_body
            )
            return response.choices[0].message.content
            
        except Exception as e:
            return f"vLLM Fehler: {str(e)}"
    
    def is_available(self) -> bool:
        """Prueft ob vLLM bereit ist."""
        try:
            # Schneller Check ob der Port offen ist
            import requests
            r = requests.get(f"{self.url}/models", timeout=2)
            return r.status_code == 200
        except:
            return False
    
    def get_model_info(self) -> dict:
        """Gibt Modell-Informationen zurueck."""
        return {
            "name": self.model,
            "provider": "vllm",
            "local": True,
            "url": self.url
        }
