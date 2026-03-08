"""Tests fuer robustes vLLM-Response-Handling."""

import os
import sys
from unittest.mock import patch

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from brain.base_brain import GenerationConfig  # noqa: E402
from brain.vllm_brain import VLLMBrain  # noqa: E402


class _FakeMessage:
    def __init__(self, content=None, reasoning_content=None, tool_calls=None):
        self.content = content
        self.reasoning_content = reasoning_content
        self.tool_calls = tool_calls


class _FakeChoice:
    def __init__(self, message, finish_reason="stop"):
        self.message = message
        self.finish_reason = finish_reason


class _FakeResponse:
    def __init__(self, choices):
        self.choices = choices


class _FakeCompletions:
    def __init__(self, response):
        self._response = response

    def create(self, **kwargs):  # noqa: ANN003
        return self._response


class _FakeChat:
    def __init__(self, response):
        self.completions = _FakeCompletions(response)


class _FakeOpenAIClient:
    def __init__(self, response):
        self.chat = _FakeChat(response)


def _make_brain_with_response(response):
    with patch("brain.vllm_brain.OpenAI", return_value=_FakeOpenAIClient(response)):
        return VLLMBrain(model="Qwen/Qwen3.5-9B", url="http://localhost:8000/v1")


def test_sync_generate_returns_content_when_present():
    response = _FakeResponse([_FakeChoice(_FakeMessage(content="Hallo Welt"))])
    brain = _make_brain_with_response(response)
    result = brain._sync_generate([], GenerationConfig(stream=False), {})
    assert result == "Hallo Welt"


def test_sync_generate_reports_reasoning_only_output():
    response = _FakeResponse([
        _FakeChoice(
            _FakeMessage(content=None, reasoning_content="interner gedanke"),
            finish_reason="length",
        )
    ])
    brain = _make_brain_with_response(response)
    result = brain._sync_generate([], GenerationConfig(stream=False), {})
    assert result.startswith("vLLM Fehler:")
    assert "reasoning_content" in result
    assert "finish_reason=length" in result


def test_prepare_extra_body_sets_qwen_thinking_default_false():
    response = _FakeResponse([_FakeChoice(_FakeMessage(content="ok"))])
    brain = _make_brain_with_response(response)
    payload = brain._prepare_extra_body({})
    assert payload["chat_template_kwargs"]["enable_thinking"] is False


def test_prepare_extra_body_respects_explicit_enable_thinking():
    response = _FakeResponse([_FakeChoice(_FakeMessage(content="ok"))])
    brain = _make_brain_with_response(response)
    payload = brain._prepare_extra_body({"chat_template_kwargs": {"enable_thinking": True}})
    assert payload["chat_template_kwargs"]["enable_thinking"] is True


if __name__ == "__main__":
    test_sync_generate_returns_content_when_present()
    test_sync_generate_reports_reasoning_only_output()
    test_prepare_extra_body_sets_qwen_thinking_default_false()
    test_prepare_extra_body_respects_explicit_enable_thinking()
    print("OK: vLLM response handling")
