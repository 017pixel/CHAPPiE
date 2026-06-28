"""
CHAPPiE - Short-Term Memory
============================
Verwaltet das Kurzzeitgedächtnis mit:
- JSON-basierter Speicherung
- Timestamp-basiertem TTL
- Automatischer Migration nach 24h (einzelne Einträge)
- Kategorien: user, system, context, chat, dream
- Automatischer Summarization bei Überlauf
"""

import json
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, asdict

from config.config import DATA_DIR
from memory.memory_engine import MemoryEngine


@dataclass
class ShortTermEntry:
    """Repräsentiert einen Short-Term Memory Eintrag."""
    id: str
    content: str
    category: str  # user, system, context, chat, dream
    importance: str  # high, normal, low
    created_at: str
    expires_at: str
    migrated: bool = False
    summarized: bool = False
    summary_source_ids: Optional[List[str]] = None


class ShortTermMemory:
    """
    Short-Term Memory mit Timestamps und Auto-Migration.
    Alle Timestamps werden in UTC gespeichert.
    """
    
    def __init__(self, memory_engine: MemoryEngine = None, ttl_hours: int = 24):
        self.storage_path = DATA_DIR / "short_term_memory.json"
        self.memory_engine = memory_engine
        self.ttl_hours = ttl_hours
        self.entries: List[ShortTermEntry] = []
        
        self._load_entries()

    @staticmethod
    def _timestamp_sort_value(value: str) -> float:
        try:
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.timestamp()
        except (TypeError, ValueError):
            return 0.0
    
    def _load_entries(self):
        """Lädt Einträge aus JSON-Datei."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.entries = []
                    for entry in data.get('entries', []):
                        entry.setdefault("summarized", False)
                        entry.setdefault("summary_source_ids", None)
                        self.entries.append(ShortTermEntry(**entry))
            except Exception as e:
                print(f"[ShortTerm] Fehler beim Laden: {e}")
                self.entries = []
        else:
            self.entries = []
    
    def _save_entries(self):
        """Speichert Einträge in JSON-Datei."""
        try:
            data = {
                'entries': [asdict(entry) for entry in self.entries],
                'last_cleanup': datetime.now(timezone.utc).isoformat()
            }
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ShortTerm] Fehler beim Speichern: {e}")
    
    def add_entry(self, content: str, category: str = "general", 
                  importance: str = "normal", ttl_hours: int = None) -> str:
        """
        Fügt einen neuen Eintrag hinzu.
        
        Args:
            content: Der Inhalt
            category: Kategorie (user, system, context, chat, dream)
            importance: Wichtigkeit (high, normal, low)
            ttl_hours: Optional individuelle TTL
            
        Returns:
            ID des Eintrags
        """
        entry_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        ttl = ttl_hours if ttl_hours else self.ttl_hours
        expires = now + timedelta(hours=ttl)
        
        entry = ShortTermEntry(
            id=entry_id,
            content=content,
            category=category,
            importance=importance,
            created_at=now.isoformat(),
            expires_at=expires.isoformat(),
            migrated=False
        )
        
        self.entries.append(entry)
        self._save_entries()
        
        return entry_id
    
    def get_active_entries(
        self,
        category: str = None,
        query: str = None,
        include_summarized: bool = False,
    ) -> List[ShortTermEntry]:
        """
        Gibt aktive (nicht abgelaufene, nicht migrierte) Einträge zurück.
        
        Args:
            category: Optional Filter nach Kategorie
            query: Optional Suchbegriff
            
        Returns:
            Liste von ShortTermEntry
        """
        now = datetime.now(timezone.utc)
        active = []
        
        for entry in self.entries:
            try:
                expires = datetime.fromisoformat(entry.expires_at)
                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
                    
                if now > expires:
                    continue
            except (ValueError, TypeError):
                continue
            
            if entry.migrated:
                continue

            if entry.summarized and not include_summarized:
                continue
            
            if category and entry.category != category:
                continue
            
            if query and query.lower() not in entry.content.lower():
                continue
            
            active.append(entry)
        
        importance_order = {"high": 0, "normal": 1, "low": 2}
        active.sort(key=lambda entry: (
            importance_order.get(entry.importance, 1),
            -self._timestamp_sort_value(entry.created_at),
        ))

        return active

    def summarize_overflow(self) -> int:
        """Verdichtet aktive STM-Rohdaten in 5er-Batches via Groq."""
        from config.config import settings

        threshold = int(getattr(settings, "stm_summary_threshold", 5))
        batch_size = int(getattr(settings, "stm_summary_batch_size", 5))
        raw_entries = [
            entry for entry in self.get_active_entries(include_summarized=True)
            if not entry.summarized and entry.category != "summary"
        ]
        if len(raw_entries) <= threshold:
            return 0

        raw_entries.sort(key=lambda entry: self._timestamp_sort_value(entry.created_at))
        overflow_count = len(raw_entries) - threshold
        batches = [
            raw_entries[i:i + batch_size]
            for i in range(0, overflow_count, batch_size)
        ]
        created = 0
        for batch in batches:
            if len(batch) < batch_size:
                continue
            summary = self._summarize_batch(batch)
            if not summary:
                continue
            self._add_summary_entry(summary, batch)
            created += 1

        if created:
            self._save_entries()
        return created

    def _summarize_batch(self, batch: List[ShortTermEntry]) -> str:
        try:
            from brain.base_brain import GenerationConfig, Message
            from brain.groq_brain import GroqBrain
            from brain.response_parser import looks_like_model_error
            from config.config import settings

            lines = [f"- [{entry.category}/{entry.importance}] {entry.content}" for entry in batch]
            prompt = (
                "Fasse diese Kurzzeitgedaechtnis-Eintraege fuer CHAPPiE kompakt zusammen.\n"
                "Erhalte relevante Fakten, Entscheidungen, Vorlieben und aktuelle Aufgaben.\n"
                "Antworte in maximal 5 kurzen Stichpunkten auf Deutsch.\n\n"
                + "\n".join(lines)
            )
            brain = GroqBrain(model=settings.groq_model)
            config = GenerationConfig(max_tokens=260, temperature=0.1, stream=False)
            result = brain.generate([Message(role="user", content=prompt)], config=config)
            if not isinstance(result, str) or looks_like_model_error(result):
                return ""
            return result.strip()
        except Exception as exc:
            print(f"[ShortTerm] STM-Zusammenfassung fehlgeschlagen: {exc}")
            return ""

    def _add_summary_entry(self, summary: str, batch: List[ShortTermEntry]) -> None:
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=self.ttl_hours)
        source_ids = [entry.id for entry in batch]
        for entry in batch:
            entry.summarized = True
        self.entries.append(
            ShortTermEntry(
                id=str(uuid.uuid4()),
                content=summary,
                category="summary",
                importance="high",
                created_at=now.isoformat(),
                expires_at=expires.isoformat(),
                migrated=False,
                summarized=False,
                summary_source_ids=source_ids,
            )
        )
    
    def migrate_expired_entries(self) -> int:
        """
        Migriert abgelaufene Eintraege ins Langzeitgedaechtnis.
        
        Zusaetzlich: High-Importance-Eintraege werden bereits nach halber TTL
        migriert, nicht erst nach voller TTL.
        
        Returns:
            Anzahl migrierter Eintraege
        """
        if not self.memory_engine:
            return 0
        
        now = datetime.now(timezone.utc)
        migrated_count = 0
        
        for entry in self.entries:
            if entry.migrated:
                continue
            
            try:
                expires = datetime.fromisoformat(entry.expires_at)
                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
                
                created = datetime.fromisoformat(entry.created_at)
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                
                half_ttl = created + (expires - created) / 2
                is_high_priority = entry.importance in ("high", "critical")
                is_expired = now > expires
                is_early_migration = is_high_priority and now > half_ttl
                
                if (is_expired or is_early_migration) and entry.category in ("summary", "chat", "user", "system", "context"):
                    try:
                        role = self._detect_role(entry.content, entry.category)
                        self.memory_engine.add_memory(
                            content=entry.content,
                            role=role,
                            mem_type="short_term_migration",
                            label=f"{entry.category}_{entry.importance}",
                            source="short_term_memory"
                        )
                        entry.migrated = True
                        migrated_count += 1
                    except Exception as e:
                        print(f"[ShortTerm] Migration fehlgeschlagen fuer {entry.id}: {e}")
            except (ValueError, TypeError) as e:
                print(f"[ShortTerm] Fehler beim Parsen von expires_at: {e}")
        
        if migrated_count > 0:
            self._save_entries()
            print(f"[ShortTerm] {migrated_count} Eintraege migriert")
        
        return migrated_count
    
    def _detect_role(self, content: str, category: str) -> str:
        content_lower = content.lower()
        if content_lower.startswith("chappie:") or content_lower.startswith("assistant:"):
            return "assistant"
        if content_lower.startswith("user:") or content_lower.startswith("human:"):
            return "user"
        if content_lower.startswith("system:"):
            return "system"
        if category == "chat":
            return "assistant"
        return "user"
    
    def get_formatted_for_prompt(self, query: str = None) -> str:
        """
        Formatiert aktive Einträge für den Prompt.
        
        Args:
            query: Optionaler Filter
            
        Returns:
            Formatierter String
        """
        self.summarize_overflow()
        entries = self.get_active_entries(query=query)
        
        if not entries:
            return ""
        
        lines = ["=== AKTUELLE SHORT-TERM ERINNERUNGEN (letzte 24h) ===", ""]
        
        for entry in entries[:20]:
            try:
                created = datetime.fromisoformat(entry.created_at)
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                time_str = created.strftime("%d.%m %H:%M")
            except (ValueError, TypeError):
                time_str = "??.?? ??:??"
            lines.append(f"[{time_str}] [{entry.importance}] [{entry.category}] {entry.content}")
        
        return "\n".join(lines)
    
    def get_count(self) -> int:
        """Gibt die Anzahl aktiver Einträge zurück."""
        return len(self.get_active_entries())
    
    def delete_entry(self, entry_id: str) -> bool:
        """Löscht einen Eintrag."""
        for i, entry in enumerate(self.entries):
            if entry.id == entry_id:
                self.entries.pop(i)
                self._save_entries()
                return True
        return False
    
    def clear_all(self):
        """Löscht alle Einträge (Vorsicht!)."""
        self.entries = []
        self._save_entries()


_short_term_memory = None
_short_term_memory_lock = None

def _get_lock():
    global _short_term_memory_lock
    if _short_term_memory_lock is None:
        import threading
        _short_term_memory_lock = threading.Lock()
    return _short_term_memory_lock


def get_short_term_memory(memory_engine: MemoryEngine = None) -> ShortTermMemory:
    """Gibt die ShortTermMemory Instanz zurück (Thread-Safe Singleton)."""
    global _short_term_memory
    with _get_lock():
        if _short_term_memory is None:
            _short_term_memory = ShortTermMemory(memory_engine=memory_engine)
        return _short_term_memory
