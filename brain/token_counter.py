"""Exact, model-specific token counting for prompt budget enforcement."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Iterable


class TokenizerUnavailableError(RuntimeError):
    """Raised when the active model's real tokenizer cannot be loaded."""


def _message_dict(message: Any) -> dict[str, str]:
    if isinstance(message, dict):
        role = message.get("role", "user")
        content = message.get("content", "")
    else:
        role = getattr(message, "role", "user")
        content = getattr(message, "content", "")
    return {"role": str(role or "user"), "content": str(content or "")}


class ModelTokenCounter:
    """Counts the exact tokens emitted by the active model chat template.

    Qwen/Gemma use their cached Hugging Face tokenizer and chat template.
    GPT-OSS uses OpenAI's Harmony renderer, which ships with the Groq client
    environment. There is deliberately no character-count fallback: an
    unavailable tokenizer is an observable runtime error, not a guessed count.
    """

    def __init__(self, model_name: str):
        self.model_name = str(model_name or "").strip()
        if not self.model_name:
            raise TokenizerUnavailableError("Kein aktives Modell fuer Tokenzaehlung angegeben")
        self.kind, self.tokenizer = self._load(self.model_name)

    @staticmethod
    @lru_cache(maxsize=4)
    def _load(model_name: str) -> tuple[str, Any]:
        if "gpt-oss" in model_name.lower():
            try:
                from openai_harmony import HarmonyEncodingName, load_harmony_encoding

                return "harmony", load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)
            except Exception as exc:  # pragma: no cover - environment dependent
                raise TokenizerUnavailableError(
                    f"GPT-OSS Harmony-Tokenizer konnte nicht geladen werden: {exc}"
                ) from exc

        try:
            from transformers import AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                local_files_only=True,
                trust_remote_code=False,
            )
            return "transformers", tokenizer
        except Exception as exc:
            raise TokenizerUnavailableError(
                f"Tokenizer fuer {model_name} ist nicht lokal verfuegbar: {exc}"
            ) from exc

    def count_messages(self, messages: Iterable[Any], *, add_generation_prompt: bool = True) -> int:
        normalized = [_message_dict(message) for message in messages]
        if not normalized:
            return 0

        if self.kind == "harmony":
            from openai_harmony import Conversation, Message as HarmonyMessage, Role

            harmony_messages = []
            for item in normalized:
                try:
                    role = Role(item["role"])
                except ValueError:
                    role = Role.USER
                harmony_messages.append(HarmonyMessage.from_role_and_content(role, item["content"]))
            conversation = Conversation.from_messages(harmony_messages)
            if add_generation_prompt:
                token_ids = self.tokenizer.render_conversation_for_completion(conversation, Role.ASSISTANT)
            else:
                token_ids = self.tokenizer.render_conversation(conversation)
            return len(token_ids)

        try:
            token_ids = self.tokenizer.apply_chat_template(
                normalized,
                tokenize=True,
                add_generation_prompt=add_generation_prompt,
            )
        except TypeError:
            token_ids = self.tokenizer.apply_chat_template(normalized, tokenize=True)
        if isinstance(token_ids, dict) or hasattr(token_ids, "get"):
            token_ids = token_ids.get("input_ids", token_ids)
        if hasattr(token_ids, "numel"):
            return int(token_ids.numel())
        return len(token_ids)

    def count_message(self, message: Any) -> int:
        return self.count_messages([message])

    def count_text(self, text: str) -> int:
        value = str(text or "")
        if not value:
            return 0
        if self.kind == "harmony":
            return len(self.tokenizer.encode(value))
        return len(self.tokenizer.encode(value, add_special_tokens=False))
