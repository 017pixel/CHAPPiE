import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime, timezone
import json
from unittest import mock
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Chappies_Trainingspartner import daemon_manager
from Chappies_Trainingspartner.trainer_agent import TrainerConfig
from web_infrastructure.training_ui import _curriculum_to_text, _parse_curriculum_text


class TrainingConfigAndUiTests(unittest.TestCase):
    def test_trainer_config_roundtrip_preserves_runtime_fields(self):
        config = TrainerConfig.from_dict(
            {
                "persona": "Testpersona",
                "curriculum": [{"topic": "Memory", "duration_minutes": 30}],
                "timeout_seconds": 90,
                "start_prompt": "Los geht's",
                "provider": "local",
                "model_name": "qwen-test",
                "sleep_interval_messages": 35,
                "loop_pause_seconds": 1.0,
                "request_pause_seconds": 3.0,
            }
        )

        data = config.to_dict()
        self.assertEqual(data["sleep_interval_messages"], 35)
        self.assertEqual(data["loop_pause_seconds"], 1.0)
        self.assertEqual(data["request_pause_seconds"], 3.0)
        self.assertEqual(data["curriculum"][0]["topic"], "Memory")

    def test_training_ui_curriculum_helpers_parse_and_format(self):
        curriculum = _parse_curriculum_text("Memory | 15\nReasoning | infinite", "Fallback")
        self.assertEqual(
            curriculum,
            [
                {"topic": "Memory", "duration_minutes": 15},
                {"topic": "Reasoning", "duration_minutes": "infinite"},
            ],
        )
        self.assertEqual(_curriculum_to_text(curriculum), "Memory | 15\nReasoning | infinite")

    def test_daemon_manager_normalizes_and_persists_training_config(self):
        with TemporaryDirectory() as tmp_dir:
            original_config_file = daemon_manager.CONFIG_FILE
            daemon_manager.CONFIG_FILE = Path(tmp_dir) / "training_config.json"
            try:
                saved = daemon_manager.save_training_config(
                    {
                        "focus_area": "Autonomie",
                        "sleep_interval_messages": 2,
                        "loop_pause_seconds": -1,
                        "request_pause_seconds": 0,
                        "curriculum": [],
                    }
                )
                loaded = daemon_manager.load_training_config()

                self.assertEqual(saved["sleep_interval_messages"], 5)
                self.assertEqual(loaded["curriculum"][0]["topic"], "Autonomie")
                self.assertEqual(loaded["loop_pause_seconds"], 0.0)
                self.assertEqual(loaded["request_pause_seconds"], 0.5)
            finally:
                daemon_manager.CONFIG_FILE = original_config_file

    def test_daemon_manager_load_training_config_handles_broken_json(self):
        with TemporaryDirectory() as tmp_dir:
            original_config_file = daemon_manager.CONFIG_FILE
            daemon_manager.CONFIG_FILE = Path(tmp_dir) / "training_config.json"
            try:
                daemon_manager.CONFIG_FILE.write_text("{broken", encoding="utf-8")
                loaded = daemon_manager.load_training_config()
            finally:
                daemon_manager.CONFIG_FILE = original_config_file

        self.assertEqual(loaded["focus_area"], daemon_manager.DEFAULT_TRAINING_CONFIG["focus_area"])
        self.assertEqual(loaded["sleep_interval_messages"], 25)

    def test_daemon_manager_snapshot_uses_state_heartbeat_when_available(self):
        with TemporaryDirectory() as tmp_dir:
            original_paths = (
                daemon_manager.PID_FILE,
                daemon_manager.LOG_FILE,
                daemon_manager.STATE_FILE,
                daemon_manager.CONFIG_FILE,
            )
            daemon_manager.PID_FILE = Path(tmp_dir) / "training.pid"
            daemon_manager.LOG_FILE = Path(tmp_dir) / "training_daemon.log"
            daemon_manager.STATE_FILE = Path(tmp_dir) / "training_state.json"
            daemon_manager.CONFIG_FILE = Path(tmp_dir) / "training_config.json"
            try:
                daemon_manager.save_training_config({"focus_area": "Planung"})
                daemon_manager.STATE_FILE.write_text(
                    json.dumps(
                        {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "current_topic": "Planung",
                            "messages_since_dream": 4,
                            "heartbeat": {
                                "loop_count": 8,
                                "memory_count": 17,
                                "total_exchanges": 11,
                            },
                        }
                    ),
                    encoding="utf-8",
                )
                with mock.patch(
                    "Chappies_Trainingspartner.daemon_manager._resolve_daemon_pid",
                    return_value=(1234, [], False),
                ):
                    snapshot = daemon_manager.get_training_snapshot()
            finally:
                (
                    daemon_manager.PID_FILE,
                    daemon_manager.LOG_FILE,
                    daemon_manager.STATE_FILE,
                    daemon_manager.CONFIG_FILE,
                ) = original_paths

        self.assertTrue(snapshot["running"])
        self.assertEqual(snapshot["loops"], 8)
        self.assertEqual(snapshot["memory_count"], 17)
        self.assertEqual(snapshot["current_topic"], "Planung")


if __name__ == "__main__":
    unittest.main()
