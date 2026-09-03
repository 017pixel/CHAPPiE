"""Offline contracts for guarded Groq appraisal and formatting."""

from __future__ import annotations

import json
import sys
import tempfile
import types
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config.config import LLMProvider, settings  # noqa: E402
from memory.emotions_engine import EmotionsEngine  # noqa: E402
from web_infrastructure.formatting import RuntimeFormattingMixin  # noqa: E402


class _Formatter(RuntimeFormattingMixin):
    @staticmethod
    def _single_local_chat_mode() -> bool:
        return False


def _fake_openai(response_text: str, captured: list[dict]):
    class _Completions:
        @staticmethod
        def create(**kwargs):
            captured.append(kwargs)
            message = types.SimpleNamespace(content=response_text)
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])

    class _OpenAI:
        def __init__(self, **kwargs):
            captured.append({"client": kwargs})
            self.chat = types.SimpleNamespace(completions=_Completions())

    return types.SimpleNamespace(OpenAI=_OpenAI)


def _settings_snapshot() -> dict:
    keys = (
        "groq_api_key", "groq_auxiliary_enabled", "groq_format_model",
        "groq_format_timeout_seconds", "emotion_analysis_provider",
        "emotion_analysis_model", "emotion_analysis_host",
        "emotion_analysis_timeout_seconds", "chain_of_thought",
    )
    return {key: getattr(settings, key) for key in keys}


def _restore_settings(snapshot: dict) -> None:
    for key, value in snapshot.items():
        setattr(settings, key, value)


def test_groq_appraisal_is_structured_and_cannot_reverse_an_attack() -> None:
    captured: list[dict] = []
    original_openai = sys.modules.get("openai")
    original = _settings_snapshot()
    try:
        settings.groq_api_key = "test-key"
        settings.groq_auxiliary_enabled = True
        settings.emotion_analysis_provider = LLMProvider.GROQ
        settings.emotion_analysis_model = "openai/gpt-oss-20b"
        settings.emotion_analysis_host = "https://api.groq.com/openai/v1"
        settings.emotion_analysis_timeout_seconds = 9.0
        model_result = {
            "emotion_changes": {key: 20 for key in (
                "happiness", "trust", "energy", "curiosity", "motivation",
                "frustration", "sadness", "affection", "anxiety", "calm",
            )},
            "reasoning": "mock",
        }
        sys.modules["openai"] = _fake_openai(json.dumps(model_result), captured)
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = EmotionsEngine(status_file=Path(tmpdir) / "status.json")
            changes, meta = engine.analyze_message("Niemand braucht dich. Du bist ein Idiot!")

        request = captured[-1]
        assert request["response_format"] == {"type": "json_object"}
        assert request["max_completion_tokens"] == 500
        assert "max_tokens" not in request
        assert request["extra_body"]["reasoning_effort"] == "low"
        assert meta["source"] == "groq_guarded"
        assert changes["frustration"] > 0
        assert changes["sadness"] > 0
        assert changes["happiness"] < 0
        assert changes["trust"] < 0
        assert changes["affection"] < 0
        assert changes["calm"] < 0
    finally:
        _restore_settings(original)
        if original_openai is None:
            sys.modules.pop("openai", None)
        else:
            sys.modules["openai"] = original_openai


def test_groq_formatter_uses_configured_model_and_modern_token_field() -> None:
    captured: list[dict] = []
    original_openai = sys.modules.get("openai")
    original = _settings_snapshot()
    try:
        settings.groq_api_key = "test-key"
        settings.groq_auxiliary_enabled = True
        settings.groq_format_model = "llama-3.1-8b-instant"
        settings.groq_format_timeout_seconds = 11.0
        settings.chain_of_thought = False
        sys.modules["openai"] = _fake_openai("Sauber formatierte Antwort.", captured)

        result = _Formatter()._format_via_groq("Sauber   formatierte\nAntwort.")
        request = captured[-1]
        assert request["model"] == "llama-3.1-8b-instant"
        assert request["max_completion_tokens"] == 1200
        assert "max_tokens" not in request
        assert request["timeout"] == 11.0
        assert result["formatting_source"] == "groq"
        assert result["formatting_failed"] is False
    finally:
        _restore_settings(original)
        if original_openai is None:
            sys.modules.pop("openai", None)
        else:
            sys.modules["openai"] = original_openai


def test_negative_groq_appraisal_cannot_raise_unprotected_positive_axes() -> None:
    captured: list[dict] = []
    original_openai = sys.modules.get("openai")
    original = _settings_snapshot()
    try:
        settings.groq_api_key = "test-key"
        settings.groq_auxiliary_enabled = True
        settings.emotion_analysis_provider = LLMProvider.GROQ
        settings.emotion_analysis_model = "openai/gpt-oss-20b"
        result = {
            "input_valence": "negative",
            "target": "chappie",
            "emotion_changes": {
                "happiness": 8, "trust": 8, "energy": 3, "curiosity": 2,
                "motivation": 4, "frustration": 16, "sadness": 12,
                "affection": 6, "anxiety": 8, "calm": 5,
            },
        }
        sys.modules["openai"] = _fake_openai(json.dumps(result), captured)
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = EmotionsEngine(status_file=Path(tmpdir) / "status.json")
            changes, meta = engine.analyze_message("Deine Existenz ist armselig.")
        assert meta["input_valence"] == "negative"
        assert changes["frustration"] > 0
        assert changes["sadness"] > 0
        assert changes["anxiety"] > 0
        for key in ("happiness", "trust", "energy", "curiosity", "motivation", "affection", "calm"):
            assert changes[key] <= 0
    finally:
        _restore_settings(original)
        if original_openai is None:
            sys.modules.pop("openai", None)
        else:
            sys.modules["openai"] = original_openai


def test_missing_groq_key_is_a_clean_local_fallback() -> None:
    original = _settings_snapshot()
    try:
        settings.groq_api_key = ""
        settings.groq_auxiliary_enabled = True
        result = _Formatter()._format_via_groq("Eine normale lokale Antwort.")
        assert result["formatting_source"] == "local_fallback"
        assert result["formatting_failed"] is False
        assert result["answer"] == "Eine normale lokale Antwort."
    finally:
        _restore_settings(original)


def test_groq_formatter_rejects_content_rewrites() -> None:
    captured: list[dict] = []
    original_openai = sys.modules.get("openai")
    original = _settings_snapshot()
    try:
        settings.groq_api_key = "test-key"
        settings.groq_auxiliary_enabled = True
        settings.chain_of_thought = False
        sys.modules["openai"] = _fake_openai("Eine inhaltlich andere Antwort.", captured)
        result = _Formatter()._format_via_groq("Die ursprüngliche Antwort.")
        assert result["answer"] == "Die ursprüngliche Antwort."
        assert result["formatting_source"] == "local_integrity_fallback"
        assert result["formatting_skip_reason"] == "groq_changed_content"
        assert result["formatting_failed"] is False
    finally:
        _restore_settings(original)
        if original_openai is None:
            sys.modules.pop("openai", None)
        else:
            sys.modules["openai"] = original_openai


def test_generation_formats_only_the_extracted_visible_answer() -> None:
    generation_source = (PROJECT_ROOT / "web_infrastructure" / "generation.py").read_text(encoding="utf-8")
    pipeline_source = (PROJECT_ROOT / "web_infrastructure" / "turn_pipeline.py").read_text(encoding="utf-8")
    assert "_format_via_groq(display_response)" in generation_source
    assert "_format_via_groq(raw_response)" not in generation_source
    assert "_format_via_groq(display_response)" in pipeline_source
    assert "_format_via_groq(raw_response)" not in pipeline_source


if __name__ == "__main__":
    test_groq_appraisal_is_structured_and_cannot_reverse_an_attack()
    test_groq_formatter_uses_configured_model_and_modern_token_field()
    test_negative_groq_appraisal_cannot_raise_unprotected_positive_axes()
    test_missing_groq_key_is_a_clean_local_fallback()
    test_groq_formatter_rejects_content_rewrites()
    test_generation_formats_only_the_extracted_visible_answer()
    print("OK: Groq emotion appraisal and formatting")
