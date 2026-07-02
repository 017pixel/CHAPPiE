"""Antwort-Policy fuer kurze lokale Antworten und intentabhaengiges Retrieval."""

import os
import sys
from unittest.mock import MagicMock

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

for mod in ("ollama", "chromadb", "chromadb.config", "requests", "openai", "sentence_transformers"):
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

from config.config import LLMProvider  # noqa: E402
from config.prompts import get_system_prompt_with_emotions  # from config/prompts.py
from web_infrastructure.backend_wrapper import prompt_chain_of_thought_enabled, response_memory_top_k_for_intent  # noqa: E402


def test_casual_chat_uses_twenty_memories_and_other_intents_keep_default():
    assert response_memory_top_k_for_intent("casual_chat", 40) == 20
    assert response_memory_top_k_for_intent("technical_discussion", 40) == 40


def test_local_vllm_does_not_add_long_cot_prompt_block():
    assert prompt_chain_of_thought_enabled(LLMProvider.VLLM, True) is False
    assert prompt_chain_of_thought_enabled(LLMProvider.GROQ, True) is True

    prompt = get_system_prompt_with_emotions(
        include_emotion_status=False,
        use_chain_of_thought=prompt_chain_of_thought_enabled(LLMProvider.VLLM, True),
    )
    assert "## Innerer Monolog" not in prompt
    assert "DEIN AKTUELLER EMOTIONALER STATUS" not in prompt
    assert "kurz und konkret" in prompt


if __name__ == "__main__":
    test_casual_chat_uses_twenty_memories_and_other_intents_keep_default()
    test_local_vllm_does_not_add_long_cot_prompt_block()
    print("OK: response policy")
