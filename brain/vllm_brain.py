"""
CHAPiE - vLLM Brain
===================
LLM-Backend fuer einen OpenAI-kompatiblen lokalen GPU-Server.

Perfekt fuer:
- Lokales Hosting von Qwen-Modellen
- Geringe Latenz bei lokaler GPU
- Lokalen Steering-/OpenAI-kompatiblen Transport

Benoetigt: lokaler OpenAI-kompatibler Server laufend (Standard: http://localhost:8000/v1)
"""

from typing import Generator, Optional, Any, Dict
from openai import OpenAI

from .base_brain import BaseBrain, Message, GenerationConfig
from config.config import settings


class VLLMBrain(BaseBrain):
    """
    LLM-Backend fuer einen OpenAI-kompatiblen lokalen Server.

    Nutzt ein OpenAI-kompatibles API-Interface.
    Unterstuetzt Activation Steering ueber 'extra_body'.
    """

    def __init__(self, model: Optional[str] = None, url: Optional[str] = None):
        """
        Initialisiert das lokale OpenAI-kompatible Backend.

        Args:
            model: Modellname (default: aus config.py)
            url: Server URL (default: aus config.py)
        """
        self.url = url or settings.vllm_url
        model_name = model or settings.vllm_model
        super().__init__(model_name)

        # OpenAI Client fuer den lokalen Server (meist kein Key noetig)
        self.client = OpenAI(
            base_url=self.url,
            api_key="none"  # lokaler Server braucht keinen echten Key
        )
        self._is_initialized = True
        print("Lokales OpenAI-Brain initialisiert")
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

        # Steering / provider-spezifische Parameter
        extra_body = self._prepare_extra_body(config.extra_body)

        if config.stream:
            return self._stream_generate(openai_messages, config, extra_body)
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

            emitted_text = False
            reasoning_chars = 0

            for chunk in stream:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta
                content = self._normalize_content(getattr(delta, "content", None))
                if content:
                    emitted_text = True
                    yield content
                    continue

                reasoning = self._extract_reasoning_content(delta)
                reasoning_chars += len(reasoning)

            if not emitted_text:
                if reasoning_chars > 0:
                    yield (
                        "\nvLLM Fehler: Stream lieferte nur reasoning_content ohne finale Antwort. "
                        "Setze chat_template_kwargs.enable_thinking=false oder erhoehe MAX_TOKENS."
                    )
                else:
                    yield "\nvLLM Fehler: Stream lieferte keinen Text."

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

            choices = getattr(response, "choices", None) or []
            if not choices:
                return "vLLM Fehler: API lieferte keine choices."

            first_choice = choices[0]
            message = getattr(first_choice, "message", None)
            content = self._normalize_content(getattr(message, "content", None))
            reasoning = self._extract_reasoning_content(message)
            if content and reasoning:
                return self._format_reasoning_response(reasoning, answer=content)
            if content:
                return content

            finish_reason = getattr(first_choice, "finish_reason", "unknown")
            if reasoning:
                return self._format_reasoning_response(reasoning, answer="CHAPPiE schweigt...")

            tool_calls = getattr(message, "tool_calls", None)
            if tool_calls:
                return (
                    "vLLM Fehler: Modell lieferte Tool-Calls ohne Textantwort "
                    f"(finish_reason={finish_reason})."
                )

            return f"vLLM Fehler: Leere Modellantwort (finish_reason={finish_reason})."

        except Exception as e:
            return f"vLLM Fehler: {str(e)}"

    def _prepare_extra_body(self, extra_body: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Bereitet provider-spezifische Optionen vor."""
        payload = dict(extra_body or {})

        # Qwen3.5 neigt im Thinking-Mode zu reasoning-only Antworten ohne message.content.
        # Standardmaessig deaktivieren, ausser der Aufrufer setzt es explizit.
        if self.model.lower().startswith("qwen/qwen3.5"):
            chat_kwargs = payload.get("chat_template_kwargs")
            if not isinstance(chat_kwargs, dict):
                chat_kwargs = {}
            chat_kwargs.setdefault("enable_thinking", False)
            payload["chat_template_kwargs"] = chat_kwargs

        return payload

    @staticmethod
    def _format_reasoning_response(reasoning: str, answer: str) -> str:
        cleaned_reasoning = (reasoning or "").strip()
        cleaned_answer = (answer or "CHAPPiE schweigt...").strip()
        return f"<model_reasoning>\n{cleaned_reasoning}\n</model_reasoning>\n\n{cleaned_answer}"

    @staticmethod
    def _normalize_content(value: Any) -> str:
        """Normalisiert verschiedene Content-Formate auf String."""
        if isinstance(value, str):
            return value.strip()

        if isinstance(value, list):
            parts: list[str] = []
            for item in value:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text") or item.get("content") or ""
                    if isinstance(text, str):
                        parts.append(text)
            return "".join(parts).strip()

        return ""

    def _extract_reasoning_content(self, message_like: Any) -> str:
        """Extrahiert reasoning_content robust aus OpenAI/vLLM-Objekten."""
        if message_like is None:
            return ""

        direct = self._normalize_content(getattr(message_like, "reasoning_content", None))
        if direct:
            return direct

        if hasattr(message_like, "model_dump"):
            try:
                dumped = message_like.model_dump()
            except Exception:
                dumped = {}
            for key in ("reasoning_content", "reasoning", "reasoningContent"):
                reasoning = self._normalize_content(dumped.get(key))
                if reasoning:
                    return reasoning

        if isinstance(message_like, dict):
            for key in ("reasoning_content", "reasoning", "reasoningContent"):
                reasoning = self._normalize_content(message_like.get(key))
                if reasoning:
                    return reasoning

        return ""

    def is_available(self) -> bool:
        """Prueft ob vLLM bereit ist."""
        try:
            import requests

            api_url = self.url.rstrip("/")
            root_url = api_url[:-3] if api_url.endswith("/v1") else api_url
            for candidate in (f"{root_url}/health", f"{api_url}/models"):
                try:
                    response = requests.get(candidate, timeout=5)
                    if response.status_code == 200:
                        return True
                except Exception:
                    continue
            return False
        except Exception:
            return False

    def get_model_info(self) -> dict:
        """Gibt Modell-Informationen zurueck."""
        return {
            "name": self.model,
            "provider": "vllm",
            "local": True,
            "url": self.url
        }
