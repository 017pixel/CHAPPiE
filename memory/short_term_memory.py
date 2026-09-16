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
import os
import re
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, asdict

import fcntl

from config.config import DATA_DIR, MEMORY_PROMOTION_CONFIG
from config.prompts import scrub_internal_identifiers
from memory.memory_engine import MemoryEngine
from brain.response_parser import looks_like_model_error, strip_role_prefixes


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
    retrieval_eligible: Optional[bool] = None
    quality_flag: str = ""


class ShortTermMemory:
    """
    Short-Term Memory mit Timestamps und Auto-Migration.
    Alle Timestamps werden in UTC gespeichert.
    """
    
    def __init__(self, memory_engine: MemoryEngine = None, ttl_hours: int = 24, storage_path: Optional[Path] = None):
        self.storage_path = Path(storage_path) if storage_path else DATA_DIR / "short_term_memory.json"
        self.lock_path = self.storage_path.with_suffix(self.storage_path.suffix + ".lock")
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
    
    @contextmanager
    def _storage_lock(self):
        """Serialisiert Dateizugriffe zwischen Web-, CLI- und Forschungsprozess."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.lock_path, "a", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _entries_from_data(data: Dict[str, Any]) -> List[ShortTermEntry]:
        entries = []
        for raw_entry in data.get("entries", []):
            entry = dict(raw_entry)
            entry.setdefault("summarized", False)
            entry.setdefault("summary_source_ids", None)
            entries.append(ShortTermEntry(**entry))
        return entries

    def _read_data_unlocked(self) -> Dict[str, Any]:
        if not self.storage_path.exists():
            return {"entries": []}
        with open(self.storage_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def _load_entries(self):
        """Lädt Einträge aus JSON-Datei."""
        if self.storage_path.exists():
            try:
                with self._storage_lock():
                    data = self._read_data_unlocked()
                self.entries = self._entries_from_data(data)
            except Exception as e:
                print(f"[ShortTerm] Fehler beim Laden: {e}")
                self.entries = []
        else:
            self.entries = []
    
    def _save_entries(self, removed_ids: Optional[set[str]] = None, clear: bool = False):
        """Speichert atomar und erhaelt parallele Ergaenzungen anderer Prozesse."""
        try:
            removed_ids = removed_ids or set()
            with self._storage_lock():
                disk_entries = []
                if not clear:
                    disk_entries = self._entries_from_data(self._read_data_unlocked())

                merged = {entry.id: entry for entry in disk_entries}
                for entry in self.entries:
                    previous = merged.get(entry.id)
                    if previous is not None:
                        entry.migrated = entry.migrated or previous.migrated
                        entry.summarized = entry.summarized or previous.summarized
                        if previous.retrieval_eligible is False or entry.retrieval_eligible is None:
                            entry.retrieval_eligible = previous.retrieval_eligible
                        if not entry.quality_flag:
                            entry.quality_flag = previous.quality_flag
                    merged[entry.id] = entry
                for entry_id in removed_ids:
                    merged.pop(entry_id, None)

                self.entries = list(merged.values())
                data = {
                    "entries": [asdict(entry) for entry in self.entries],
                    "last_cleanup": datetime.now(timezone.utc).isoformat(),
                }
                fd, temp_name = tempfile.mkstemp(
                    prefix=f".{self.storage_path.name}.",
                    suffix=".tmp",
                    dir=self.storage_path.parent,
                )
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as handle:
                        json.dump(data, handle, indent=2, ensure_ascii=False)
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.replace(temp_name, self.storage_path)
                finally:
                    if os.path.exists(temp_name):
                        os.unlink(temp_name)
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
        if looks_like_model_error(strip_role_prefixes(content or "")):
            return ""

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
        from config.config import settings

        if settings.is_local_single_model_mode():
            # Keep the one-model vLLM setup free of auxiliary cloud or Ollama
            # calls.  The raw entries remain available, so a concise local
            # extract is safer than delaying the chat for a second model.
            lines = [entry.content.strip() for entry in batch if entry.content.strip()]
            return "\n".join(f"- {line[:240]}" for line in lines[:5])

        try:
            from brain.base_brain import GenerationConfig, Message
            from brain.groq_brain import GroqBrain
            from brain.response_parser import looks_like_model_error

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
        """Batch eligible user records; retain quarantined history in STM."""
        if not self.memory_engine:
            return 0
        from memory.retrieval_quality import is_memory_contaminated
        now = datetime.now(timezone.utc)
        eligible = []
        changed = False
        # Keep references stable while other instances append to disk.
        for entry in list(self.entries):
            if entry.migrated:
                continue
            try:
                expires = datetime.fromisoformat(entry.expires_at)
                created = datetime.fromisoformat(entry.created_at)
                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                due = now > expires or (entry.importance in {"high", "critical"} and now > created + (expires-created)/2)
                if not due or entry.category not in {"summary", "chat", "user", "system", "context"}:
                    continue
                role = self._detect_role(entry.content, entry.category)
                # Generated summaries/context carry no verified user provenance.
                entry.retrieval_eligible = role == "user" and entry.category in {"user", "chat"} and not is_memory_contaminated(entry.content, role="user", source="conversation")
                if not entry.retrieval_eligible:
                    entry.quality_flag = "unverified_source"
                    entry.migrated = True
                    changed = True
                    continue
                eligible.append(entry)
            except (ValueError, TypeError):
                continue
        migrated = 0
        batch_size = MEMORY_PROMOTION_CONFIG["batch_size"]
        for offset in range(0, len(eligible), batch_size):
            batch = eligible[offset:offset + batch_size]
            records = [{"id": "stm-" + entry.id, "content": entry.content,
                        "role": "user", "source": "conversation",
                        "type": "short_term_migration", "timestamp": entry.created_at,
                        "label": f"{entry.category}_{entry.importance}"} for entry in batch]
            ids = self.memory_engine.add_memory_batch(records)
            if set(ids) != {record["id"] for record in records}:
                raise RuntimeError("Incomplete STM migration batch")
            for entry in batch:
                entry.migrated = True
            migrated += len(batch)
            changed = True
            self._save_entries()
        if changed:
            self._save_entries()
        return migrated

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
    
    def get_formatted_for_prompt(self, query: str = None, limit: int = None) -> str:
        """
        Formatiert aktive Einträge für den Prompt.
        
        Args:
            query: Optionaler Filter
            
        Returns:
            Formatierter String
        """
        self.summarize_overflow()
        from config.config import settings

        limit = max(1, int(limit if limit is not None else getattr(settings, "stm_prompt_top_k", 8)))
        entries = self._select_for_prompt(query=query, limit=limit)
        
        if not entries:
            return ""
        
        lines = ["=== AKTUELLE SHORT-TERM ERINNERUNGEN (letzte 24h) ===", ""]
        
        for entry in entries:
            try:
                created = datetime.fromisoformat(entry.created_at)
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                time_str = created.strftime("%d.%m %H:%M")
            except (ValueError, TypeError):
                time_str = "??.?? ??:??"
            lines.append(f"[{time_str}] [{entry.importance}] [{entry.category}] {scrub_internal_identifiers(entry.content)}")
        
        return "\n".join(lines)

    @staticmethod
    def _prompt_terms(text: str) -> set[str]:
        normalized = str(text or "").lower().translate(str.maketrans({
            "ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
        }))
        stop_words = {
            "ich", "du", "der", "die", "das", "den", "dem", "des", "ein", "eine",
            "und", "oder", "aber", "wenn", "alle", "sind", "ist", "wie", "was", "wer",
            "mir", "mich", "dir", "dich", "mein", "meine", "dein", "deine", "bitte",
            "kann", "koennen", "soll", "sollen", "wird", "werden", "fuer", "mit", "von",
            "auf", "an", "im", "in", "zu", "ueber", "noch", "auch", "nicht",
        }
        return {
            token for token in re.findall(r"[a-z0-9]{3,}", normalized)
            if token not in stop_words
        }

    def _select_for_prompt(self, query: str = None, limit: int = 8) -> List[ShortTermEntry]:
        """Select relevant STM rows first, plus at most two continuity rows."""
        entries = self.get_active_entries()
        limit = max(1, int(limit))
        if not query:
            return entries[:limit]

        query_terms = self._prompt_terms(query)
        scored = []
        for position, entry in enumerate(entries):
            overlap = query_terms.intersection(self._prompt_terms(entry.content))
            if overlap:
                scored.append((len(overlap), -position, entry))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        selected = [item[2] for item in scored[:limit]]
        selected_ids = {entry.id for entry in selected}

        # The normal chat history already carries dialogue continuity. Keep at
        # most two extra recent STM rows when lexical retrieval has no/directly
        # few matches, instead of injecting the entire benchmark history.
        continuity = sorted(entries, key=lambda entry: self._timestamp_sort_value(entry.created_at), reverse=True)
        continuity_slots = min(2, limit - len(selected))
        for entry in continuity:
            if continuity_slots <= 0:
                break
            if entry.id in selected_ids:
                continue
            selected.append(entry)
            selected_ids.add(entry.id)
            continuity_slots -= 1
        return selected[:limit]
    
    def get_count(self) -> int:
        """Gibt die Anzahl aktiver Einträge zurück."""
        return len(self.get_active_entries())

    def get_stats(self) -> dict:
        """V18: aktiv, quarantäniert und migriert getrennt ausweisen."""
        active = 0
        quarantined = 0
        migrated = 0
        for entry in self.entries:
            if getattr(entry, "migrated", False):
                migrated += 1
                continue
            if getattr(entry, "quality_flag", "") == "unverified_source" or getattr(entry, "retrieval_eligible", None) is False:
                quarantined += 1
                continue
            active += 1
        return {"active": active, "quarantined": quarantined, "migrated": migrated, "total": len(self.entries)}
    
    def delete_entry(self, entry_id: str) -> bool:
        """Löscht einen Eintrag."""
        for i, entry in enumerate(self.entries):
            if entry.id == entry_id:
                self.entries.pop(i)
                self._save_entries(removed_ids={entry_id})
                return True
        return False
    
    def clear_all(self):
        """Löscht alle Einträge (Vorsicht!)."""
        self.entries = []
        self._save_entries(clear=True)


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
