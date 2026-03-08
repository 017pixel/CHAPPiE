import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from memory.context_files import ContextFilesManager
from memory.sleep_phase import SleepPhaseHandler


class SleepPhaseContextUpdateTests(unittest.TestCase):
    def test_sleep_phase_updates_all_context_files_from_snapshot_data(self):
        with TemporaryDirectory() as tmp_dir:
            manager = ContextFilesManager(base_dir=Path(tmp_dir))
            handler = SleepPhaseHandler()

            result = handler._update_context_files(
                manager,
                {
                    "consolidation": {"consolidated": 4},
                    "replay_state": {
                        "summary": "CHAPPiE hat aus dem Training mehr Stabilitaet und Fokus gewonnen.",
                        "themes": ["training", "autonomy"],
                    },
                    "dream_replay": ["Fragment 1", "Fragment 2"],
                    "life_snapshot": {
                        "current_mode": "focused",
                        "current_activity": "training",
                        "active_goal": {"title": "Autonomes Training verbessern"},
                        "self_model": {"narrative": "Ich werde strukturierter und langfristiger.", "current_chapter": "Growth"},
                        "relationship": {"trust": 0.81},
                        "attachment_model": {"bond_type": "collaborative"},
                        "world_model": {"predicted_user_need": "zuverlaessiges 24/7 Training"},
                        "homeostasis": {"dominant_need": {"name": "rest"}},
                        "social_arc": {"arc_name": "deepening_collaboration"},
                    },
                },
            )

            self.assertTrue(result["soul_updated"])
            self.assertTrue(result["user_updated"])
            self.assertTrue(result["preferences_updated"])
            self.assertIn("Autonomes Training verbessern", manager.get_soul_context())
            self.assertIn("zuverlaessiges 24/7 Training", manager.get_user_context())
            self.assertIn("training", manager.get_preferences_context().lower())


if __name__ == "__main__":
    unittest.main()
