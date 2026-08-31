import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

for module_name in ("chromadb", "chromadb.config", "sentence_transformers", "ollama", "openai", "requests"):
    sys.modules.setdefault(module_name, MagicMock())

import memory.short_term_memory as stm_module
from config.config import LLMProvider, settings


class ShortTermMemoryTests(unittest.TestCase):
    def test_active_entries_sort_by_importance_then_recency(self):
        with TemporaryDirectory() as tmp_dir:
            original_data_dir = stm_module.DATA_DIR
            stm_module.DATA_DIR = Path(tmp_dir)
            try:
                memory = stm_module.ShortTermMemory(memory_engine=None, ttl_hours=24)
                memory.entries = [
                    stm_module.ShortTermEntry(
                        id="normal-new",
                        content="normal new",
                        category="chat",
                        importance="normal",
                        created_at="2099-03-30T11:00:00+00:00",
                        expires_at="2099-03-31T11:00:00+00:00",
                    ),
                    stm_module.ShortTermEntry(
                        id="high-old",
                        content="high old",
                        category="chat",
                        importance="high",
                        created_at="2099-03-30T09:00:00+00:00",
                        expires_at="2099-03-31T09:00:00+00:00",
                    ),
                    stm_module.ShortTermEntry(
                        id="high-new",
                        content="high new",
                        category="chat",
                        importance="high",
                        created_at="2099-03-30T12:00:00+00:00",
                        expires_at="2099-03-31T12:00:00+00:00",
                    ),
                    stm_module.ShortTermEntry(
                        id="low-new",
                        content="low new",
                        category="chat",
                        importance="low",
                        created_at="2099-03-30T13:00:00+00:00",
                        expires_at="2099-03-31T13:00:00+00:00",
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
                memory = stm_module.ShortTermMemory(memory_engine=None, ttl_hours=24)
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

    def test_summarize_overflow_marks_old_batch_and_keeps_summary_active(self):
        with TemporaryDirectory() as tmp_dir:
            original_data_dir = stm_module.DATA_DIR
            stm_module.DATA_DIR = Path(tmp_dir)
            try:
                memory = stm_module.ShortTermMemory(memory_engine=None, ttl_hours=24)
                memory._summarize_batch = lambda batch: "Zusammenfassung aus fuenf Eintraegen"
                memory.entries = [
                    stm_module.ShortTermEntry(
                        id=f"raw-{idx}",
                        content=f"entry {idx}",
                        category="chat",
                        importance="normal",
                        created_at=f"2099-03-30T1{idx}:00:00+00:00",
                        expires_at="2099-03-31T10:00:00+00:00",
                    )
                    for idx in range(6)
                ]

                created = memory.summarize_overflow()
                active_ids = [entry.id for entry in memory.get_active_entries()]
                summarized_raw = [entry for entry in memory.entries if entry.summarized]
            finally:
                stm_module.DATA_DIR = original_data_dir

        self.assertEqual(created, 1)
        self.assertEqual(len(summarized_raw), 5)
        self.assertEqual(len(active_ids), 2)
        self.assertTrue(any(entry_id.startswith("raw-") for entry_id in active_ids))

    def test_single_local_model_uses_no_cloud_for_stm_summary(self):
        original_provider = settings.llm_provider
        original_force_single = settings.vllm_force_single_model
        try:
            settings.llm_provider = LLMProvider.VLLM
            settings.vllm_force_single_model = True
            memory = stm_module.ShortTermMemory(memory_engine=None, ttl_hours=24)
            batch = [
                stm_module.ShortTermEntry(
                    id="entry-1", content="Wichtige lokale Notiz", category="chat", importance="normal",
                    created_at="2099-03-30T10:00:00+00:00", expires_at="2099-03-31T10:00:00+00:00",
                )
            ]
            assert memory._summarize_batch(batch) == "- Wichtige lokale Notiz"
        finally:
            settings.llm_provider = original_provider
            settings.vllm_force_single_model = original_force_single

    def test_expired_entries_migrate_to_ltm_by_category(self):
        class MemorySink:
            def __init__(self):
                self.items = []

            def add_memory(self, **kwargs):
                self.items.append(kwargs)

        with TemporaryDirectory() as tmp_dir:
            original_data_dir = stm_module.DATA_DIR
            stm_module.DATA_DIR = Path(tmp_dir)
            sink = MemorySink()
            try:
                memory = stm_module.ShortTermMemory(memory_engine=sink, ttl_hours=24)
                memory.entries = [
                    stm_module.ShortTermEntry(
                        id="raw-expired",
                        content="raw",
                        category="chat",
                        importance="normal",
                        created_at="2020-03-30T10:00:00+00:00",
                        expires_at="2020-03-31T10:00:00+00:00",
                    ),
                    stm_module.ShortTermEntry(
                        id="summary-expired",
                        content="summary",
                        category="summary",
                        importance="high",
                        created_at="2020-03-30T10:00:00+00:00",
                        expires_at="2020-03-31T10:00:00+00:00",
                    ),
                ]

                migrated = memory.migrate_expired_entries()
            finally:
                stm_module.DATA_DIR = original_data_dir

        self.assertEqual(migrated, 2)
        self.assertEqual([item["content"] for item in sink.items], ["raw", "summary"])

    def test_parallel_instances_merge_entries_without_losing_updates(self):
        with TemporaryDirectory() as tmp_dir:
            original_data_dir = stm_module.DATA_DIR
            stm_module.DATA_DIR = Path(tmp_dir)
            try:
                first = stm_module.ShortTermMemory(memory_engine=None)
                second = stm_module.ShortTermMemory(memory_engine=None)
                first.add_entry("first", category="chat")
                second.add_entry("second", category="chat")

                reloaded = stm_module.ShortTermMemory(memory_engine=None)
                contents = {entry.content for entry in reloaded.entries}
            finally:
                stm_module.DATA_DIR = original_data_dir

        self.assertEqual(contents, {"first", "second"})

    def test_delete_entry_removes_only_target_from_merged_storage(self):
        with TemporaryDirectory() as tmp_dir:
            original_data_dir = stm_module.DATA_DIR
            stm_module.DATA_DIR = Path(tmp_dir)
            try:
                first = stm_module.ShortTermMemory(memory_engine=None)
                first_id = first.add_entry("first", category="chat")
                second = stm_module.ShortTermMemory(memory_engine=None)
                second.add_entry("second", category="chat")

                self.assertTrue(first.delete_entry(first_id))
                reloaded = stm_module.ShortTermMemory(memory_engine=None)
                contents = {entry.content for entry in reloaded.entries}
            finally:
                stm_module.DATA_DIR = original_data_dir

        self.assertEqual(contents, {"second"})

    def test_prompt_selection_prioritizes_relevant_fact_and_bounds_continuity(self):
        with TemporaryDirectory() as tmp_dir:
            original_data_dir = stm_module.DATA_DIR
            stm_module.DATA_DIR = Path(tmp_dir)
            try:
                memory = stm_module.ShortTermMemory(memory_engine=None)
                memory.summarize_overflow = lambda: 0
                memory.entries = [
                    stm_module.ShortTermEntry(
                        id=f"noise-{idx}", content=f"Belanglose historische Testfrage {idx}",
                        category="chat", importance="normal",
                        created_at=f"2099-03-30T{10 + idx:02d}:00:00+00:00",
                        expires_at="2099-03-31T23:00:00+00:00",
                    )
                    for idx in range(10)
                ] + [
                    stm_module.ShortTermEntry(
                        id="orbit", content="User: Der kontrollierte Code lautet ORBIT-741.",
                        category="context", importance="normal",
                        created_at="2099-03-30T09:00:00+00:00",
                        expires_at="2099-03-31T23:00:00+00:00",
                    )
                ]

                selected = memory._select_for_prompt("Wie lautet der kontrollierte Code ORBIT-741?", limit=8)
                formatted = memory.get_formatted_for_prompt("Wie lautet der kontrollierte Code ORBIT-741?", limit=8)
            finally:
                stm_module.DATA_DIR = original_data_dir

        self.assertEqual(selected[0].id, "orbit")
        self.assertLessEqual(len(selected), 3)
        self.assertIn("ORBIT-741", formatted)
        self.assertLessEqual(formatted.count("Belanglose historische Testfrage"), 2)


if __name__ == "__main__":
    unittest.main()
