"""
CHAPPiE - Short-Term Memory V2
==============================
Überarbeitetes Short-Term Memory mit:
- JSON-basierter Speicherung
- Timestamp-basiertem TTL
- Automatischer Migration nach 24h (einzelne Einträge)
- Kategorien: user, system, context, chat, dream
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


class ShortTermMemoryV2:
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
    
    def _load_entries(self):
        """Lädt Einträge aus JSON-Datei."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.entries = [
                        ShortTermEntry(**entry) 
                        for entry in data.get('entries', [])
                    ]
            except Exception as e:
                print(f"[ShortTermV2] Fehler beim Laden: {e}")
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
            print(f"[ShortTermV2] Fehler beim Speichern: {e}")
    
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
    
    def get_active_entries(self, category: str = None, 
                          query: str = None) -> List[ShortTermEntry]:
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
            
            if category and entry.category != category:
                continue
            
            if query and query.lower() not in entry.content.lower():
                continue
            
            active.append(entry)
        
        importance_order = {"high": 0, "normal": 1, "low": 2}
        active.sort(key=lambda e: (
            importance_order.get(e.importance, 1),
            e.created_at
        ), reverse=True)
        
        return active
    
    def migrate_expired_entries(self) -> int:
        """
        Migriert abgelaufene Einträge ins Langzeitgedächtnis (einzeln!).
        
        Returns:
            Anzahl migrierter Einträge
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
                    
                if now > expires:
                    try:
                        self.memory_engine.add_memory(
                            content=entry.content,
                            role="system",
                            mem_type="short_term_migration",
                            label=f"{entry.category}_{entry.importance}",
                            source="short_term_memory"
                        )
                        entry.migrated = True
                        migrated_count += 1
                    except Exception as e:
                        print(f"[ShortTermV2] Migration fehlgeschlagen für {entry.id}: {e}")
            except (ValueError, TypeError) as e:
                print(f"[ShortTermV2] Fehler beim Parsen von expires_at: {e}")
        
        if migrated_count > 0:
            self._save_entries()
            print(f"[ShortTermV2] {migrated_count} Einträge migriert")
        
        return migrated_count
    
    def get_formatted_for_prompt(self, query: str = None) -> str:
        """
        Formatiert aktive Einträge für den Prompt.
        
        Args:
            query: Optionaler Filter
            
        Returns:
            Formatierter String
        """
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


_short_term_memory_v2 = None
_short_term_memory_lock = None

def _get_lock():
    global _short_term_memory_lock
    if _short_term_memory_lock is None:
        import threading
        _short_term_memory_lock = threading.Lock()
    return _short_term_memory_lock


def get_short_term_memory_v2(memory_engine: MemoryEngine = None) -> ShortTermMemoryV2:
    """Gibt die ShortTermMemoryV2 Instanz zurück (Thread-Safe Singleton)."""
    global _short_term_memory_v2
    with _get_lock():
        if _short_term_memory_v2 is None:
            _short_term_memory_v2 = ShortTermMemoryV2(memory_engine=memory_engine)
        return _short_term_memory_v2
