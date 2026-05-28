"""
CHAPiE - Groq Brain
====================
LLM-Backend für Groq Cloud API.

Groq bietet:
- Extrem schnelle Inferenz (LPU-beschleunigt)
- Zugang zu Llama, Qwen, GPT-OSS Modellen
- OpenAI-kompatible API

Benötigt: Groq API Key (https://console.groq.com/keys)
"""

from typing import Generator, Optional
from openai import OpenAI

from .base_brain import BaseBrain, Message, GenerationConfig
from .groq_limits import get_groq_limiter
from config.config import settings


class GroqBrain(BaseBrain):
    """
    LLM-Backend für Groq Cloud API.

    Groq nutzt eine OpenAI-kompatible API mit eigenem Endpoint.
    Unterstützt Streaming für flüssige Token-Ausgabe.
    """

    BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, 'groq_api_key', '')
        model_name = model or getattr(settings, 'groq_model', 'llama-3.3-70b-versatile')
        super().__init__(model_name)

        if self._is_missing_key(self.api_key):
            print("WARNUNG: Groq Brain - Kein API-Key konfiguriert!")
            print("   Trage deinen Key in CHAPPIE_CONFIG.json ein")
            self._is_initialized = False
            return

        try:
            self.client = OpenAI(
                base_url=self.BASE_URL,
                api_key=self.api_key,
                timeout=30.0,
            )
            self._is_initialized = True

            print(f"Groq Brain initialisiert")
            print(f"   Cloud API verbunden ({self.BASE_URL})")
            print(f"   Modell: {self.model}")
        except Exception as e:
            print(f"FEHLER bei Groq-Initialisierung: {e}")
            self._is_initialized = False

    def generate(
        self,
        messages: list[Message],
        config: Optional[GenerationConfig] = None
    ) -> Generator[str, None, None] | str:
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

        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        if config.stream:
            return self._stream_generate(openai_messages, config)
        else:
            return self._sync_generate(openai_messages, config)

    @staticmethod
    def _is_missing_key(api_key: str) -> bool:
        normalized = (api_key or "").strip()
        return not normalized or normalized.startswith("DEIN_") or not normalized.startswith("gsk_")

    @staticmethod
    def _estimate_request_tokens(messages: list[dict], config: GenerationConfig) -> int:
        text = "\n".join(str(message.get("content", "")) for message in messages)
        return get_groq_limiter().estimate_tokens(text) + int(config.max_tokens or 0)

    def _claim_quota(self, messages: list[dict], config: GenerationConfig) -> Optional[str]:
        allowed, reason = get_groq_limiter().can_start(self._estimate_request_tokens(messages, config))
        return None if allowed else reason

    def _stream_generate(
        self,
        messages: list[dict],
        config: GenerationConfig
    ) -> Generator[str, None, None]:
        try:
            quota_error = self._claim_quota(messages, config)
            if quota_error:
                yield f"\nGroq Fehler: Rate-Limit erreicht ({quota_error})"
                return

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
        try:
            quota_error = self._claim_quota(messages, config)
            if quota_error:
                return f"Groq Fehler: Rate-Limit erreicht ({quota_error})"

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
        return self._is_initialized

    def get_model_info(self) -> dict:
        return {
            "name": self.model,
            "provider": "groq",
            "local": False,
            "api_configured": bool(self.api_key)
        }

    def list_models(self) -> list[str]:
        if not self._is_initialized:
            return []

        try:
            models = self.client.models.list()
            return [m.id for m in models.data]
        except Exception:
            return list(GROQ_MODELS.keys())


# === Verfügbare Groq Modelle ===
GROQ_MODELS = {
    "llama-3.1-8b-instant": "Llama 3.1 8B - Sehr schnell & günstig",
    "llama-3.3-70b-versatile": "Llama 3.3 70B - Starkes Reasoning",
    "openai/gpt-oss-120b": "GPT-OSS 120B - Hochwertige Formatierung",
    "openai/gpt-oss-20b": "GPT-OSS 20B - Extrem schnell",
    "qwen/qwen3-32b": "Qwen3 32B - Gutes Reasoning",
    "meta-llama/llama-4-scout-17b-16e-instruct": "Llama 4 Scout 17B - Vision & Text",
}


# === Test-Funktion ===
if __name__ == "__main__":
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    console.print(Panel("Groq Brain Test", style="bold blue"))

    brain = GroqBrain()

    console.print(f"\n[cyan]1. Prüfe Verfügbarkeit...[/cyan]")
    if brain.is_available():
        console.print("   Groq API ist erreichbar!")

        models = brain.list_models()
        console.print(f"   Verfügbare Modelle: {len(models)}")
        for model in models[:5]:
            console.print(f"      - {model}")

        console.print(f"\n[cyan]2. Test-Generierung (Streaming)...[/cyan]")

        messages = [
            Message(role="system", content="Du bist ein hilfreicher Assistent. Antworte kurz auf Deutsch."),
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
            console.print("   Trage deinen API-Key in CHAPPIE_CONFIG.json ein")
        else:
            console.print("   Prüfe deine Internetverbindung oder den API-Key")
