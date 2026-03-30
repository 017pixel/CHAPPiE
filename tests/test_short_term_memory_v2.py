import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import memory.short_term_memory_v2 as stm_module


class ShortTermMemoryV2Tests(unittest.TestCase):
    def test_active_entries_sort_by_importance_then_recency(self):
        with TemporaryDirectory() as tmp_dir:
            original_data_dir = stm_module.DATA_DIR
            stm_module.DATA_DIR = Path(tmp_dir)
            try:
                memory = stm_module.ShortTermMemoryV2(memory_engine=None, ttl_hours=24)
                memory.entries = [
                    stm_module.ShortTermEntry(
                        id="normal-new",
                        content="normal new",
                        category="chat",
                        importance="normal",
                        created_at="2026-03-30T11:00:00+00:00",
                        expires_at="2026-03-31T11:00:00+00:00",
                    ),
                    stm_module.ShortTermEntry(
                        id="high-old",
                        content="high old",
                        category="chat",
                        importance="high",
                        created_at="2026-03-30T09:00:00+00:00",
                        expires_at="2026-03-31T09:00:00+00:00",
                    ),
                    stm_module.ShortTermEntry(
                        id="high-new",
                        content="high new",
                        category="chat",
                        importance="high",
                        created_at="2026-03-30T12:00:00+00:00",
                        expires_at="2026-03-31T12:00:00+00:00",
                    ),
                    stm_module.ShortTermEntry(
                        id="low-new",
                        content="low new",
                        category="chat",
                        importance="low",
                        created_at="2026-03-30T13:00:00+00:00",
                        expires_at="2026-03-31T13:00:00+00:00",
                    ),
                ]

                ordered_ids = [entry.id for entry in memory.get_active_entries()]
            finally:
                stm_module.DATA_DIR = original_data_dir

        self.assertEqual(ordered_ids, ["high-new", "high-old", "normal-new", "low-new"])

    def test_active_entries_skip_migrated_and_expired_rows(self):
        with TemporaryDirectory() as tmp_dir:
            original_data_dir = stm_module.DATA_DIR
            stm_module.DATA_DIR = Path(tmp_dir)
            try:
                memory = stm_module.ShortTermMemoryV2(memory_engine=None, ttl_hours=24)
                memory.entries = [
                    stm_module.ShortTermEntry(
                        id="active",
                        content="keep me",
                        category="chat",
                        importance="normal",
                        created_at="2099-03-30T10:00:00+00:00",
                        expires_at="2099-03-31T10:00:00+00:00",
                    ),
                    stm_module.ShortTermEntry(
                        id="expired",
                        content="expired",
                        category="chat",
                        importance="high",
                        created_at="2020-03-30T10:00:00+00:00",
                        expires_at="2020-03-31T10:00:00+00:00",
                    ),
                    stm_module.ShortTermEntry(
                        id="migrated",
                        content="migrated",
                        category="chat",
                        importance="high",
                        created_at="2099-03-30T11:00:00+00:00",
                        expires_at="2099-03-31T11:00:00+00:00",
                        migrated=True,
                    ),
                ]

                ordered_ids = [entry.id for entry in memory.get_active_entries()]
            finally:
                stm_module.DATA_DIR = original_data_dir

        self.assertEqual(ordered_ids, ["active"])


if __name__ == "__main__":
    unittest.main()
