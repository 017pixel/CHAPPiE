"""
CHAPiE - vLLM Brain
===================
LLM-Backend fuer einen OpenAI-kompatiblen lokalen GPU-Server.

Perfekt fuer:
- Lokales Hosting von Qwen-Modellen
- Geringe Latenz bei lokaler GPU
- Lokalen Steering-/OpenAI-kompatiblen Transport

Benoetigt: lokaler OpenAI-kompatibler Server laufend (Standard: http://127.0.0.1:8000/v1)
"""

import re
import time
from typing import Generator, Optional, Any, Dict
from openai import OpenAI

from .base_brain import BaseBrain, Message, GenerationConfig
from config.config import get_model_generation_defaults, is_gemma4_model, is_qwen_model, settings


class VLLMBrain(BaseBrain):
    """
    LLM-Backend fuer einen OpenAI-kompatiblen lokalen Server.

    Nutzt ein OpenAI-kompatibles API-Interface.
    Unterstuetzt Activation Steering ueber 'extra_body'.
    """

    MAX_RETRIES = 3
    RETRY_BACKOFF_BASE = 2
    # The local server can briefly queue the lightweight model-list request
    # behind a GPU generation/training request.  Keep the probe tolerant of
    # that queue without making normal failures retry for a long time.
    AVAILABILITY_TIMEOUT_SECONDS = 15

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
        self.default_request_priority = "interactive"
        self._repetition_events: Dict[str, Any] = {}
        self.last_steering_report: Dict[str, Any] = {}
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
            defaults = get_model_generation_defaults(self.model)
            config = GenerationConfig(
                max_tokens=settings.max_tokens,
                temperature=float(settings.temperature if settings.temperature is not None else defaults["temperature"]),
                stream=settings.stream
            )

        # Konvertiere Messages zu OpenAI-Format
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        # Repetition-Events pro Aufruf zuruecksetzen
        self._repetition_events.clear()

        # Steering / provider-spezifische Parameter
        extra_body = self._prepare_extra_body(
            config.extra_body,
            enable_thinking=config.enable_thinking,
        )

        if config.stream:
            return self._stream_generate(openai_messages, config, extra_body)
        return self._sync_generate(openai_messages, config, extra_body)

    _REASONING_CHAR_LIMIT = 3200
    _CHARS_PER_TOKEN_ESTIMATE = 4.2

    @classmethod
    def _reasoning_token_estimate(cls, chars: int) -> int:
        return max(1, round(chars / cls._CHARS_PER_TOKEN_ESTIMATE))

    @staticmethod
    def _normalize_reasoning_text(text: str) -> str:
        """Fuegt Leerzeichen in zusammenhangloses Reasoning ein."""
        result = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        result = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', result)
        result = re.sub(r'([.,!?;:])([A-Za-z])', r'\1 \2', result)
        return result

    @staticmethod
    def _detect_reasoning_loop(accumulated: str, window: int = 180, min_repeat: int = 3, pct_threshold: float = 0.30) -> bool:
        """Erkennt prozentbasiert, ob das Reasoning sich im Kreis dreht.

        Nimmt die letzten `window` Zeichen und prueft, wie oft dieses
        Segment im gesamten Text vorkommt. Wenn >= `min_repeat` mal und
        (Vorkommen * Window) / Gesamtlaenge > `pct_threshold` → Loop.
        """
        total = len(accumulated)
        if total < window * 2:
            return False
        segment = accumulated[-window:]
        count = accumulated.count(segment)
        if count < min_repeat:
            return False
        loop_chars = count * len(segment)
        ratio = loop_chars / total
        return ratio >= pct_threshold

    def _stream_generate(
        self,
        messages: list[dict],
        config: GenerationConfig,
        extra_body: Dict[str, Any]
    ) -> Generator[str, None, None]:
        """Streaming-Generierung mit Reasoning-Yielding, Reasoning-Cap und automatischem Retry bei Connection-Errors."""
        stream = None
        for attempt in range(self.MAX_RETRIES):
            try:
                stream = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=config.max_tokens,
                    temperature=config.temperature,
                    stream=True,
                    seed=config.seed,
                    extra_body={**extra_body, "repetition_penalty": config.repetition_penalty},
                )
                break
            except Exception as conn_err:
                is_connection_error = any(kw in str(conn_err).lower() for kw in ("connection", "connect", "refused", "timeout", "503"))
                if is_connection_error and attempt < self.MAX_RETRIES - 1:
                    wait = self.RETRY_BACKOFF_BASE ** attempt
                    print(f"vLLM Connection Error (Versuch {attempt + 1}/{self.MAX_RETRIES}), warte {wait}s...")
                    time.sleep(wait)
                    continue
                raise RuntimeError(f"vLLM Verbindungsfehler nach {self.MAX_RETRIES} Versuchen: {conn_err}")

        if stream is None:
            raise RuntimeError("vLLM: Konnte keine Verbindung zum Steering-Server herstellen.")

        try:
            emitted_text = False
            reasoning_chars = 0
            accumulated_reasoning = ""
            accumulated_content = ""
            think_opened = False
            reasoning_capped = False

            for chunk in stream:
                self._capture_steering_report(chunk)
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta
                reasoning = self._extract_reasoning_content(delta, strip=False)
                if reasoning and not reasoning_capped:
                    if reasoning_chars >= self._REASONING_CHAR_LIMIT:
                        if think_opened:
                            yield "</think>"
                            think_opened = False
                        reasoning_capped = True
                        self._repetition_events["reasoning_capped"] = {"chars": reasoning_chars, "limit": self._REASONING_CHAR_LIMIT}
                        continue

                    if not think_opened:
                        yield "<think>"
                        think_opened = True
                    normalized_reasoning = self._normalize_reasoning_text(reasoning)
                    accumulated_reasoning += normalized_reasoning
                    reasoning_chars += len(reasoning)

                    if self._detect_reasoning_loop(accumulated_reasoning):
                        if think_opened:
                            yield "</think>"
                            think_opened = False
                        reasoning_capped = True
                        self._repetition_events["reasoning_loop"] = {"chars": reasoning_chars, "last_180": accumulated_reasoning[-180:]}
                        continue

                    yield normalized_reasoning

                    if reasoning_chars >= self._REASONING_CHAR_LIMIT:
                        if think_opened:
                            yield "</think>"
                            think_opened = False
                        reasoning_capped = True
                        self._repetition_events["reasoning_capped"] = {"chars": reasoning_chars, "limit": self._REASONING_CHAR_LIMIT}
                    continue

                content = self._normalize_content(getattr(delta, "content", None), strip=False)
                if content:
                    if think_opened:
                        yield "</think>"
                        think_opened = False
                    accumulated_content += content
                    if self._detect_reasoning_loop(accumulated_content):
                        self._repetition_events["content_loop"] = {"chars": len(accumulated_content), "last_180": accumulated_content[-180:]}
                        yield "\n[REPETITION CUT]"
                        return
                    emitted_text = True
                    yield content
                    continue

            if think_opened:
                yield "</think>"

            if "steering-server fehler:" in accumulated_content.lower():
                raise RuntimeError(accumulated_content.strip())

            if not emitted_text:
                if reasoning_chars > 0:
                    self._repetition_events["no_answer_only_reasoning"] = {"reasoning_chars": reasoning_chars}
                    raise RuntimeError(
                        "vLLM: Stream lieferte nur reasoning_content ohne finale Antwort. "
                        "Setze chat_template_kwargs.enable_thinking=false oder erhoehe MAX_TOKENS."
                    )
                else:
                    raise RuntimeError("vLLM: Stream lieferte keinen Text.")

        except Exception as e:
            raise RuntimeError(f"vLLM Laufzeitfehler: {e}")

    def _sync_generate(
        self,
        messages: list[dict],
        config: GenerationConfig,
        extra_body: Dict[str, Any]
    ) -> str:
        """Synchrone Generierung mit Retry bei Connection-Errors."""
        response = None
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=config.max_tokens,
                    temperature=config.temperature,
                    stream=False,
                    seed=config.seed,
                    extra_body={**extra_body, "repetition_penalty": config.repetition_penalty},
                )
                self._capture_steering_report(response)
                break
            except Exception as conn_err:
                is_connection_error = any(kw in str(conn_err).lower() for kw in ("connection", "connect", "refused", "timeout", "503"))
                if is_connection_error and attempt < self.MAX_RETRIES - 1:
                    wait = self.RETRY_BACKOFF_BASE ** attempt
                    print(f"vLLM Connection Error (Versuch {attempt + 1}/{self.MAX_RETRIES}), warte {wait}s...")
                    time.sleep(wait)
                    continue
                return f"vLLM Fehler: {str(conn_err)}"

        if response is None:
            return "vLLM Fehler: Konnte keine Verbindung zum Steering-Server herstellen."

        try:
            choices = getattr(response, "choices", None) or []
            if not choices:
                return "vLLM Fehler: API lieferte keine choices."

            first_choice = choices[0]
            message = getattr(first_choice, "message", None)
            content = self._normalize_content(getattr(message, "content", None))
            reasoning = self._normalize_reasoning_text(self._extract_reasoning_content(message))
            if content and reasoning:
                return self._format_reasoning_response(reasoning, answer=content)
            if content:
                return content

            finish_reason = getattr(first_choice, "finish_reason", "unknown")
            if reasoning:
                self._repetition_events["no_answer_only_reasoning"] = {"reasoning_chars": len(reasoning)}
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

    def _capture_steering_report(self, response: Any) -> None:
        """Uebernimmt den Laufzeitnachweis des lokalen Steering-Servers."""
        if response is None:
            return
        try:
            if hasattr(response, "model_dump"):
                payload = response.model_dump()
            elif isinstance(response, dict):
                payload = response
            else:
                payload = getattr(response, "__dict__", {})
            report = payload.get("chappie_steering") if isinstance(payload, dict) else None
            if not isinstance(report, dict) and isinstance(payload, dict):
                usage = payload.get("usage")
                if isinstance(usage, dict):
                    report = usage.get("chappie_steering")
            if not isinstance(report, dict):
                extra = getattr(response, "model_extra", None)
                if isinstance(extra, dict):
                    report = extra.get("chappie_steering")
                    if not isinstance(report, dict):
                        usage = extra.get("usage")
                        if isinstance(usage, dict):
                            report = usage.get("chappie_steering")
            if not isinstance(report, dict):
                report = getattr(response, "chappie_steering", None)
            if isinstance(report, dict):
                self.last_steering_report = dict(report)
        except Exception:
            pass

    def _prepare_extra_body(
        self,
        extra_body: Optional[Dict[str, Any]],
        enable_thinking: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Bereitet provider-spezifische Optionen vor.
        
        enable_thinking und Sampling-Defaults werden modell-spezifisch gesetzt.
        """
        payload = dict(extra_body or {})
        payload.setdefault("request_priority", getattr(self, "default_request_priority", "interactive"))
        if "chat_template_kwargs" not in payload:
            payload["chat_template_kwargs"] = {}
        if isinstance(payload["chat_template_kwargs"], dict):
            if is_qwen_model(self.model) or is_gemma4_model(self.model):
                payload["chat_template_kwargs"]["enable_thinking"] = (
                    bool(settings.chain_of_thought)
                    if enable_thinking is None
                    else bool(enable_thinking)
                )
        defaults = get_model_generation_defaults(self.model)
        if "top_p" not in payload:
            payload["top_p"] = float(settings.top_p if settings.top_p is not None else defaults["top_p"])
        if "top_k" not in payload:
            payload["top_k"] = int(settings.top_k if settings.top_k is not None else defaults["top_k"])
        return payload

    @staticmethod
    def _format_reasoning_response(reasoning: str, answer: str) -> str:
        cleaned_reasoning = (reasoning or "").strip()
        cleaned_answer = (answer or "CHAPPiE schweigt...").strip()
        return f"<model_reasoning>\n{cleaned_reasoning}\n</model_reasoning>\n\n{cleaned_answer}"

    @staticmethod
    def _normalize_content(value: Any, *, strip: bool = True) -> str:
        """Normalisiert verschiedene Content-Formate auf String."""
        if isinstance(value, str):
            return value.strip() if strip else value

        if isinstance(value, list):
            parts: list[str] = []
            for item in value:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text") or item.get("content") or ""
                    if isinstance(text, str):
                        parts.append(text)
            joined = "".join(parts)
            return joined.strip() if strip else joined

        return ""

    def _extract_reasoning_content(self, message_like: Any, *, strip: bool = True) -> str:
        """Extrahiert reasoning_content robust aus OpenAI/vLLM-Objekten."""
        if message_like is None:
            return ""

        direct = self._normalize_content(getattr(message_like, "reasoning_content", None), strip=strip)
        if direct:
            return direct

        if hasattr(message_like, "model_dump"):
            try:
                dumped = message_like.model_dump()
            except Exception:
                dumped = {}
            for key in ("reasoning_content", "reasoning", "reasoningContent", "thinking", "thinking_content"):
                reasoning = self._normalize_content(dumped.get(key), strip=strip)
                if reasoning:
                    return reasoning

        if isinstance(message_like, dict):
            for key in ("reasoning_content", "reasoning", "reasoningContent", "thinking", "thinking_content"):
                reasoning = self._normalize_content(message_like.get(key), strip=strip)
                if reasoning:
                    return reasoning

        return ""

    @property
    def repetition_events(self) -> Dict[str, Any]:
        return dict(self._repetition_events)

    def is_available(self) -> bool:
        """Prueft ob vLLM bereit ist."""
        try:
            import requests

            api_url = self.url.rstrip("/")
            root_url = api_url[:-3] if api_url.endswith("/v1") else api_url
            # /health also includes the steering report and can briefly block
            # while a generation is active.  The OpenAI-compatible model list
            # is the cheap readiness probe; health remains the fallback for
            # servers that do not expose /v1/models.
            for candidate in (f"{api_url}/models", f"{root_url}/health"):
                try:
                    response = requests.get(candidate, timeout=self.AVAILABILITY_TIMEOUT_SECONDS)
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
