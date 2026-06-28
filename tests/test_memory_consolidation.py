"""
Umfassende Tests fuer die Memory-Konsolidierung.

Testet:
1. SleepPhase._consolidate_memories - STM-Migration, LTM-Merging
2. SleepPhase._merge_similar_ltm_entries - Ahnlichkeits-Merging
3. SleepPhase._apply_forgetting_curve - Vergessenskurve mit skip_ids-Schutz
4. ShortTermMemory.migrate_expired_entries - Hochpriorisierte Eintraege
5. ShortTermMemory._detect_role - Rollenerkennung
6. Integration: Schlafphase schuetzt frische Eintraege vor Vergessen
"""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from memory.sleep_phase import SleepPhaseHandler
from memory.short_term_memory import ShortTermMemory, ShortTermEntry, get_short_term_memory


class MockMemory:
    def __init__(self, id=None, content="", role="user", timestamp="", mem_type="interaction",
                 relevance_score=0.5, label="original"):
        self.id = id or f"mem-{hash(content) % 10000}"
        self.content = content
        self.role = role
        self.timestamp = timestamp
        self.mem_type = mem_type
        self.relevance_score = relevance_score
        self.label = label


class SleepPhaseConsolidationTests(unittest.TestCase):
    """Kern-Tests fuer die Konsolidierungs-Pipeline."""

    def setUp(self):
        self.handler = SleepPhaseHandler()
        # Leere den decay_manager state
        self.handler.config["consolidation"]["batch_size"] = 10
        self.handler.config["consolidation"]["min_memory_age_hours"] = 0

    def test_consolidate_memories_migrates_stm(self):
        """STM-Migration: abgelaufene Eintraege werden ins LTM verschoben."""
        mock_engine = MagicMock()
        mock_engine.get_recent_memories.return_value = []

        mock_stm = MagicMock()
        mock_stm.migrate_expired_entries.return_value = 3

        result = self.handler._consolidate_memories(
            mock_engine, self.handler.config["consolidation"],
            short_term_memory=mock_stm,
        )

        self.assertEqual(result["stm_migrated"], 3)
        self.assertEqual(result["total_consolidated"], 3)

    def test_consolidate_memories_merges_similar_ltm(self):
        """LTM-Merging: aehnliche Eintraege werden zusammengefasst."""
        now = datetime.now().isoformat()
        old = (datetime.now() - timedelta(hours=3)).isoformat()

        memories = [
            MockMemory(id="a1", content="Ich mag Pizza und Pasta sehr gerne", timestamp=old,
                       mem_type="interaction", label="original"),
            MockMemory(id="a2", content="Ich mag Pizza und Nudeln total", timestamp=now,
                       mem_type="interaction", label="original"),
            MockMemory(id="a3", content="Heute ist das Wetter wirklich schoen", timestamp=old,
                       mem_type="interaction", label="original"),
        ]

        mock_engine = MagicMock()
        mock_engine.get_recent_memories.return_value = memories

        mock_stm = MagicMock()
        mock_stm.migrate_expired_entries.return_value = 0

        result = self.handler._consolidate_memories(
            mock_engine, self.handler.config["consolidation"],
            short_term_memory=mock_stm,
        )

        mock_engine.delete_memories.assert_called()
        self.assertGreaterEqual(result["ltm_merged"], 1)

    def test_consolidate_memories_does_not_merge_unique_entries(self):
        """Einzelne Eintraege ohne Ahnlichkeit bleiben erhalten."""
        now = datetime.now().isoformat()

        memories = [
            MockMemory(id="b1", content="Python ist eine Programmiersprache", timestamp=now,
                       mem_type="interaction", label="original"),
            MockMemory(id="b2", content="Ich wohne in Berlin", timestamp=now,
                       mem_type="interaction", label="original"),
            MockMemory(id="b3", content="Mein Lieblingsessen ist Sushi", timestamp=now,
                       mem_type="interaction", label="original"),
        ]

        mock_engine = MagicMock()
        mock_engine.get_recent_memories.return_value = memories
        mock_stm = MagicMock()
        mock_stm.migrate_expired_entries.return_value = 0

        result = self.handler._consolidate_memories(
            mock_engine, self.handler.config["consolidation"],
            short_term_memory=mock_stm,
        )

        mock_engine.delete_memories.assert_not_called()
        self.assertEqual(result["ltm_merged"], 0)

    def test_consolidate_memories_protects_fresh_entries(self):
        """Frisch konsolidierte Eintraege landen in protected_ids."""
        now = datetime.now().isoformat()

        memories = [
            MockMemory(id="c1", content="Wiederholtes Thema Kubernetes", timestamp=now,
                       mem_type="interaction", label="original"),
            MockMemory(id="c2", content="Wiederholtes Thema Kubernetes Deployment", timestamp=now,
                       mem_type="interaction", label="original"),
        ]

        mock_engine = MagicMock()
        mock_engine.get_recent_memories.return_value = memories
        mock_stm = MagicMock()
        mock_stm.migrate_expired_entries.return_value = 0

        result = self.handler._consolidate_memories(
            mock_engine, self.handler.config["consolidation"],
            short_term_memory=mock_stm,
        )

        # Der behaltene Eintrag sollte in protected_ids sein
        self.assertIn("protected_ids", result)
        self.assertGreater(len(result["protected_ids"]), 0)

    def test_forgetting_curve_respects_skip_ids(self):
        """Vergessenskurve ueberspringt geschuetzte IDs."""
        mock_engine = MagicMock()
        protected_id = "protected-001"
        protected_mem = MockMemory(id=protected_id, content="protected entry",
                                   mem_type="short_term_migration")
        normal_mem = MockMemory(id="normal-001", content="old memory",
                                timestamp=(datetime.now() - timedelta(days=30)).isoformat())

        mock_engine.get_recent_memories.return_value = [protected_mem, normal_mem]
        mock_engine.get_memory_count.return_value = 2

        result = self.handler._apply_forgetting_curve(
            mock_engine, skip_ids=[protected_id]
        )

        self.assertEqual(result["memories_protected"], 1)
        self.assertEqual(result["memories_processed"], 1)

    def test_full_consolidation_pipeline(self):
        """Integration: Komplette Pipeline laeuft ohne Fehler durch."""
        mock_engine = MagicMock()
        mock_engine.get_recent_memories.return_value = []
        mock_engine.get_memory_count.return_value = 0

        mock_stm = MagicMock()
        mock_stm.migrate_expired_entries.return_value = 1

        with patch("memory.sleep_phase.get_life_simulation_service") as mock_life:
            mock_life.return_value.process_sleep_cycle.return_value = {
                "dream_replay": ["Traumtest"],
                "replay_state": {"summary": "Test"},
                "life_snapshot": {},
            }

            result = self.handler.execute_sleep_phase(
                memory_engine=mock_engine,
                short_term_memory=mock_stm,
            )

        self.assertIn("consolidation", result)
        self.assertIn("forgetting", result)
        self.assertIn("energy_restored", result)
        self.assertIn("emotional_recovery", result)
        self.assertIn("duration_seconds", result)
        self.assertGreaterEqual(result["consolidation"]["total_consolidated"], 1)


class ShortTermMemoryMigrationTests(unittest.TestCase):
    """Tests fuer verbesserte STM-Migration."""

    def test_detect_role_chappie_prefix(self):
        """Erkennt CHAPPiE:-Praefix als assistant."""
        with TemporaryDirectory() as tmp_dir:
            import memory.short_term_memory as stm
            mem = stm.ShortTermMemory(memory_engine=None, ttl_hours=24)
            self.assertEqual(mem._detect_role("CHAPPiE: Hallo Welt", "chat"), "assistant")
            self.assertEqual(mem._detect_role("chappie: Hallo Welt", "chat"), "assistant")

    def test_detect_role_user_prefix(self):
        """Erkennt User:-Praefix als user."""
        with TemporaryDirectory() as tmp_dir:
            import memory.short_term_memory as stm
            mem = stm.ShortTermMemory(memory_engine=None, ttl_hours=24)
            self.assertEqual(mem._detect_role("User: Ich bin da", "chat"), "user")
            self.assertEqual(mem._detect_role("user: Hi there", "chat"), "user")

    def test_detect_role_system_prefix(self):
        """Erkennt System:-Praefix als system."""
        with TemporaryDirectory() as tmp_dir:
            import memory.short_term_memory as stm
            mem = stm.ShortTermMemory(memory_engine=None, ttl_hours=24)
            self.assertEqual(mem._detect_role("System: Init complete", "system"), "system")

    def test_detect_role_fallback(self):
        """Fallback: unbekannter Praefix + chat = assistant."""
        with TemporaryDirectory() as tmp_dir:
            import memory.short_term_memory as stm
            mem = stm.ShortTermMemory(memory_engine=None, ttl_hours=24)
            self.assertEqual(mem._detect_role("Hallo wie gehts", "chat"), "assistant")

    def test_migrate_expired_entries_high_importance_early(self):
        """High-Importance-Eintraege werden frueher migriert (halbe TTL)."""
        class MemorySink:
            def __init__(self): self.items = []
            def add_memory(self, **kwargs): self.items.append(kwargs)

        with TemporaryDirectory() as tmp_dir:
            import memory.short_term_memory as stm
            original_data_dir = stm.DATA_DIR
            stm.DATA_DIR = Path(tmp_dir)
            sink = MemorySink()
            try:
                mem = stm.ShortTermMemory(memory_engine=sink, ttl_hours=24)
                now = datetime.now(timezone.utc)
                # created_at 13h in the past -> half-TTL (12h) ist vergangen
                created = now - timedelta(hours=13)
                expires = created + timedelta(hours=24)  # 11h in der Zukunft

                mem.entries = [
                    stm.ShortTermEntry(
                        id="high-prio", content="Wichtige Info", category="chat",
                        importance="high", created_at=created.isoformat(),
                        expires_at=expires.isoformat(),
                    ),
                ]
                moved = mem.migrate_expired_entries()
            finally:
                stm.DATA_DIR = original_data_dir
            self.assertEqual(moved, 1)
            self.assertEqual(len(sink.items), 1)
            self.assertEqual(sink.items[0]["label"], "chat_high")


class SleepPhaseContextUpdateTests(unittest.TestCase):
    """Aktualisiert fuer neue Konsolidierungs-Result-Struktur."""

    def test_context_update_uses_total_consolidated(self):
        handler = SleepPhaseHandler()
        with TemporaryDirectory() as tmp_dir:
            from memory.context_files import ContextFilesManager
            manager = ContextFilesManager(base_dir=Path(tmp_dir))

            result = handler._update_context_files(
                manager,
                {
                    "consolidation": {
                        "total_consolidated": 7,
                        "stm_migrated": 4,
                        "ltm_merged": 3,
                    },
                    "replay_state": {
                        "summary": "Test Zusammenfassung",
                        "themes": ["focus", "stability"],
                    },
                    "dream_replay": ["Traumfragment"],
                    "life_snapshot": {
                        "current_mode": "focused",
                        "active_goal": {"title": "Tests verbessern"},
                        "self_model": {"narrative": "Ich werde praziser."},
                        "relationship": {"trust": 0.75},
                        "attachment_model": {"bond_type": "professional"},
                    },
                },
            )

            self.assertTrue(result["soul_updated"])
            soul = manager.get_soul_context()
            self.assertIn("Tests verbessern", soul)


if __name__ == "__main__":
    unittest.main()
