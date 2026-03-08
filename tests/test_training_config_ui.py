import sys
from pathlib import Path
from tempfile import TemporaryDirectory
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


if __name__ == "__main__":
    unittest.main()