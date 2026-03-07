"""Gezielte Regressionstests für Provider-Switching und Berliner Life-Zeit."""

import os
import sys
from datetime import datetime

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from config.config import LLMProvider, USER_SETTINGS_PATH, settings
from brain.response_parser import looks_like_model_error
from life.service import LifeSimulationService


TRACKED_SETTINGS = (
    "llm_provider",
    "intent_provider",
    "query_extraction_provider",
    "_needs_reload",
)


def _backup_settings_state():
    file_exists = USER_SETTINGS_PATH.exists()
    file_content = USER_SETTINGS_PATH.read_text(encoding="utf-8") if file_exists else None
    values = {name: getattr(settings, name) for name in TRACKED_SETTINGS}
    return file_exists, file_content, values


def _restore_settings_state(file_exists, file_content, values):
    for name, value in values.items():
        setattr(settings, name, value)
    if file_exists:
        USER_SETTINGS_PATH.write_text(file_content, encoding="utf-8")
    elif USER_SETTINGS_PATH.exists():
        USER_SETTINGS_PATH.unlink()


def test_provider_switch_resets_old_followers_to_auto():
    backup = _backup_settings_state()
    try:
        settings.llm_provider = LLMProvider.CEREBRAS
        settings.intent_provider = LLMProvider.CEREBRAS
        settings.query_extraction_provider = LLMProvider.CEREBRAS

        settings.update_from_ui(
            llm_provider="ollama",
            intent_provider="cerebras",
            query_extraction_provider="cerebras",
        )

        assert settings.llm_provider == LLMProvider.OLLAMA
        assert settings.intent_provider is None
        assert settings.query_extraction_provider is None
    finally:
        _restore_settings_state(*backup)


class _FixedBerlinLifeService(LifeSimulationService):
    def _get_berlin_now(self):
        return datetime(2026, 3, 7, 19, 14, tzinfo=self.BERLIN_TZ)


def test_life_snapshot_uses_berlin_time():
    service = _FixedBerlinLifeService()
    service._state.last_updated = ""
    service._sync_clock_to_berlin()
    snapshot = service.get_snapshot()

    assert snapshot["clock"]["minute_of_day"] == (19 * 60 + 14)
    assert snapshot["clock"]["phase"] == "exploration"
    assert snapshot["clock"]["timezone"] == "Europe/Berlin"
    assert "19:14" in snapshot["clock"]["phase_label"]


def test_model_error_detection_catches_sticky_provider_errors_and_empty_responses():
    assert looks_like_model_error("Cerebras Fehler: Error 404 model not found") is True
    assert looks_like_model_error("   ") is True
    assert looks_like_model_error("Hallo Benjamin, schön dich zu sehen.") is False


if __name__ == "__main__":
    test_provider_switch_resets_old_followers_to_auto()
    test_life_snapshot_uses_berlin_time()
    test_model_error_detection_catches_sticky_provider_errors_and_empty_responses()
    print("OK: runtime switching and Berlin clock regression tests passed")

