"""Modellfreier Regressionstest fuer die Systemvalidierung."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.emotions import EMOTION_ORDER  # noqa: E402
from scripts.validate_system import _training_service_is_valid  # noqa: E402


def test_training_service_is_resolved_from_deploy_directory():
    valid, message = _training_service_is_valid()

    assert valid is True
    assert message == "ExecStart zeigt auf training_daemon"


def test_system_validation_covers_all_emotion_dimensions():
    assert len(EMOTION_ORDER) == 10


if __name__ == "__main__":
    test_training_service_is_resolved_from_deploy_directory()
    test_system_validation_covers_all_emotion_dimensions()
    print("OK: validate_system regression checks")
