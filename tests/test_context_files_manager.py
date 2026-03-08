import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from memory.context_files import ContextFilesManager


class ContextFilesManagerTests(unittest.TestCase):
    def test_context_files_deduplicate_and_cap_reflections(self):
        with TemporaryDirectory() as tmp_dir:
            manager = ContextFilesManager(base_dir=Path(tmp_dir))

            for index in range(20):
                manager.update_preferences({"reflection": f"Reflexion {index}"})
            manager.update_preferences({"reflection": "Reflexion 19"})

            content = manager.get_preferences_context()
            self.assertEqual(content.count("Reflexion 19"), 1)
            self.assertLessEqual(content.count("- ["), 16)
            self.assertNotIn("Reflexion 0", content)

    def test_user_updates_preserve_first_contact_and_remove_placeholders(self):
        with TemporaryDirectory() as tmp_dir:
            manager = ContextFilesManager(base_dir=Path(tmp_dir))

            manager.update_user(
                {
                    "learning": ["Ben arbeitet gern strukturiert.", "Ben arbeitet gern strukturiert."],
                    "key_moment": "Wir haben das autonome Training neu geplant.",
                }
            )

            content = manager.get_user_context()
            self.assertEqual(content.count("Ben arbeitet gern strukturiert."), 1)
            self.assertIn("First Contact:", content)
            self.assertNotIn("[This file will grow as we interact more]", content)


if __name__ == "__main__":
    unittest.main()