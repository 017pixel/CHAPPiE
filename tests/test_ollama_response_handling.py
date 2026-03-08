"""Tests fuer robustes Ollama-Response-Handling."""

import os
import sys
from unittest.mock import patch

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from brain.base_brain import GenerationConfig  # noqa: E402
from brain.ollama_brain import OllamaBrain  # noqa: E402


class _FakeClient:
    def __init__(self, response, capture_kwargs=False):
        self._response = response
        self.capture_kwargs = capture_kwargs
        self.last_kwargs = None
        self.calls = []

    def chat(self, **kwargs):  # noqa: ANN003
        if self.capture_kwargs:
            self.last_kwargs = kwargs
        self.calls.append(kwargs)
        if isinstance(self._response, list):
            return self._response.pop(0)
        return self._response


def _make_brain(response, model="qwen3.5:9b", capture_kwargs=False):
    fake_client = _FakeClient(response, capture_kwargs=capture_kwargs)
    with patch("brain.ollama_brain.Client", return_value=fake_client):
        brain = OllamaBrain(model=model)
    return brain, fake_client


def test_sync_generate_returns_content_when_present():
    brain, _ = _make_brain({"message": {"content": "Hallo von Ollama"}})
    result = brain.generate([], GenerationConfig(stream=False))
    assert result == "Hallo von Ollama"


def test_sync_generate_reports_reasoning_only_output():
    brain, _ = _make_brain(
        {"message": {"content": "", "thinking": "interner gedanke"}, "done_reason": "stop"}
    )
    result = brain.generate([], GenerationConfig(stream=False))
    assert "CHAPPiE schweigt..." in result
    assert "<model_reasoning>" in result
    assert "interner gedanke" in result


def test_sync_generate_preserves_answer_and_model_reasoning():
    brain, _ = _make_brain(
        {"message": {"content": "fertige antwort", "thinking": "modell denkt"}, "done_reason": "stop"}
    )
    result = brain.generate([], GenerationConfig(stream=False))
    assert "<model_reasoning>" in result
    assert "modell denkt" in result
    assert result.strip().endswith("fertige antwort")


def test_sync_generate_recovers_reasoning_after_empty_first_response():
    brain, fake_client = _make_brain(
        [
            {"message": {"content": "", "thinking": ""}, "done_reason": "stop"},
            {"message": {"content": "", "thinking": "zweiter gedanke"}, "done_reason": "stop"},
        ],
        capture_kwargs=True,
    )
    result = brain.generate([], GenerationConfig(stream=False))
    assert "CHAPPiE schweigt..." in result
    assert "zweiter gedanke" in result
    assert fake_client.calls[0]["think"] is False
    assert fake_client.calls[1]["think"] is True


def test_qwen_models_disable_thinking_by_default():
    brain, fake_client = _make_brain({"message": {"content": "ok"}}, capture_kwargs=True)
    brain.generate([], GenerationConfig(stream=False))
    assert fake_client.last_kwargs["think"] is False


def test_non_thinking_models_do_not_send_think_flag():
    brain, fake_client = _make_brain(
        {"message": {"content": "ok"}},
        model="llama3.2:3b",
        capture_kwargs=True,
    )
    brain.generate([], GenerationConfig(stream=False))
    assert "think" not in fake_client.last_kwargs


if __name__ == "__main__":
    test_sync_generate_returns_content_when_present()
    test_sync_generate_reports_reasoning_only_output()
    test_sync_generate_preserves_answer_and_model_reasoning()
    test_sync_generate_recovers_reasoning_after_empty_first_response()
    test_qwen_models_disable_thinking_by_default()
    test_non_thinking_models_do_not_send_think_flag()
    print("OK: Ollama response handling")