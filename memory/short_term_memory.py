"""
CHAPiE - Short-Term Memory Manager
===================================
Managt die Daily Info Markdown-Datei für das Kurzzeitgedächtnis.

Features:
- Speichert Infos temporär (24h TTL)
- Automatische ChromaDB-Indexierung für RAG-Suche
- Automatische Bereinigung abgelaufener Einträge
"""

from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
import re
import json

from config.config import settings, PROJECT_ROOT, DATA_DIR


class ShortTermMemory:
    """
    Managt die Daily Info Markdown-Datei mit ChromaDB-Duplikat.
    """

    def __init__(self, memory_engine=None):
        """
        Initialisiert das Kurzzeitgedächtnis.

        Args:
            memory_engine: Optional - MemoryEngine Instanz für RAG-Indexierung
        """
        self.memory_engine = memory_engine
        self.daily_info_path = Path(settings.daily_info_path)
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Erstellt die Datei wenn sie nicht existiert."""
        if not self.daily_info_path.exists():
            self._create_default_file()

    def _create_default_file(self):
        """Erstellt die Standard Daily Info Datei."""
        timestamp = datetime.now().isoformat()
        content = f"""# CHAPiE Daily Information
> Automatisch generiert - Letzte Aktualisierung: {timestamp}

---

## Aktuelle Session
- **Start:** {timestamp}
- **User:** Unbekannt

## Tages-Infos
> Hier werden wichtige Infos aus dem Chat temporär gespeichert (max 24h)
> Diese Infos werden automatisch in ChromaDB indexiert für RAG-Suche

### Aktuell Relevant
_(Keine Einträge - CHAPI wird hier wichtige Informationen während des Tages sammeln)_

**Format:** `[TIMESTAMP] [IMPORTANCE] [CATEGORY] content`

**Kategorien:**
- `user` - Informationen über den User
- `context` - Gesprächskontext
- `reminder` - Erinnerungen/Aufgaben
- `system` - System-relevante Infos

---

## Konsolidierungs-Log
| Datum | Events | Bereinigt |
|-------|--------|-----------|
|       |        |           |

---

> 💡 **Hinweis:** Einträge älter als 24h werden automatisch bereinigt.
> Wichtige Infos werden dabei von CHAPI selbstständig ins Langzeitgedächtnis überführt.
"""
        with open(self.daily_info_path, "w", encoding="utf-8") as f:
            f.write(content)

    def add_info(self, content: str, importance: str = "normal", category: str = "general") -> str:
        """
        Fügt eine neue Info zum Kurzzeitgedächtnis hinzu.

        Args:
            content: Die Information die gespeichert werden soll
            importance: "high", "normal", "low"
            category: "user", "system", "context", "reminder", "general"

        Returns:
            Timestamp der gespeicherten Info
        """
        timestamp = datetime.now().isoformat()

        # Erstelle den Eintrag
        entry = f"[{timestamp}] [{importance.upper()}] [{category}] {content}\n"

        # 1. Append zur Markdown-Datei
        self._append_to_file(entry)

        # 2. AUCH in ChromaDB indexieren (für RAG-Suche)
        if self.memory_engine:
            try:
                self.memory_engine.add_memory(
                    content=f"[KURZZEIT] [{category}] {content}",
                    role="system",
                    mem_type="short_term",
                    label=importance,
                    source="daily_info"
                )
            except Exception as e:
                print(f"[SHORT-TERM-MEMORY] Warnung: Konnte nicht in ChromaDB speichern: {e}")

        return timestamp

    def _append_to_file(self, entry: str):
        """
        Fügt einen Eintrag zur Daily Info Datei hinzu.
        
        FIX: Platzhalter wird beim ersten Eintrag komplett entfernt,
        danach werden Einträge korrekt nach der Überschrift angehängt.
        """
        try:
            # Finde die "Aktuell Relevant" Sektion und füge dort ein
            with open(self.daily_info_path, "r", encoding="utf-8") as f:
                content = f.read()

            # REGEX FIX: Suche nach dem Platzhalter-Text (verschiedene Varianten)
            placeholder_pattern = r'_\(Keine Einträge[^\)]*\)_\n?'
            
            if re.search(placeholder_pattern, content):
                # Platzhalter gefunden: Komplett durch den neuen Eintrag ersetzen
                content = re.sub(placeholder_pattern, entry + "\n", content, count=1)
            else:
                # Kein Platzhalter mehr: Nach "### Aktuell Relevant" einfügen
                # Verwende Regex um sicher die richtige Stelle zu finden
                section_pattern = r'(### Aktuell Relevant\n)'
                if re.search(section_pattern, content):
                    content = re.sub(
                        section_pattern,
                        f'\\1{entry}\n',
                        content,
                        count=1
                    )
                else:
                    # Fallback: Am Ende des "Tages-Infos" Blocks anhängen
                    content += f"\n{entry}\n"

            # Update timestamp
            timestamp = datetime.now().isoformat()
            content = re.sub(
                r"> Automatisch generiert - Letzte Aktualisierung: .*",
                f"> Automatisch generiert - Letzte Aktualisierung: {timestamp}",
                content
            )

            with open(self.daily_info_path, "w", encoding="utf-8") as f:
                f.write(content)

        except Exception as e:
            print(f"[SHORT-TERM-MEMORY] Fehler beim Schreiben: {e}")

    def get_relevant_infos(self, query: str = None, max_age_hours: int = None) -> List[Tuple[str, str, str, str]]:
        """
        Holt relevante Infos aus dem Kurzzeitgedächtnis.

        Args:
            query: Optionaler Suchbegriff
            max_age_hours: Maximales Alter der Infos (default: 24h aus Settings)

        Returns:
            Liste von Tupeln: (timestamp, importance, category, content)
        """
        if max_age_hours is None:
            max_age_hours = settings.short_term_ttl_hours

        infos = []
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        try:
            with open(self.daily_info_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse alle Einträge
            # FIX: Pattern mit nicht-greedy match und explizit kein Zeilenumbruch
            # Format: [TIMESTAMP] [IMPORTANCE] [CATEGORY] content
            pattern = r'\[([^\]]+)\] \[([^\]]+)\] \[([^\]]+)\] ([^\n]+)'
            for match in re.finditer(pattern, content):
                timestamp_str, importance, category, entry_content = match.groups()

                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    if timestamp > cutoff_time:
                        if query is None or self._matches_query(entry_content, query):
                            infos.append((timestamp_str, importance, category, entry_content))
                except ValueError:
                    # Falls Timestamp nicht geparst werden kann, ignoriere
                    continue

        except Exception as e:
            print(f"[SHORT-TERM-MEMORY] Fehler beim Lesen: {e}")

        # Sortiere nach Zeit (neueste zuerst)
        infos.sort(key=lambda x: x[0], reverse=True)
        return infos

    def _matches_query(self, content: str, query: str) -> bool:
        """Prüft ob der Inhalt zur Query passt (einfache Keyword-Suche)."""
        query_lower = query.lower()
        content_lower = content.lower()

        keywords = re.findall(r'\b\w+\b', query_lower)
        return any(keyword in content_lower for keyword in keywords)

    def cleanup_expired(self) -> int:
        """
        Entfernt Einträge die älter als 24h sind.
        Gibt Anzahl gelöschter Einträge zurück.
        """
        ttl_hours = settings.short_term_ttl_hours
        cutoff_time = datetime.now() - timedelta(hours=ttl_hours)
        cleaned_count = 0

        try:
            with open(self.daily_info_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse und filtere Einträge
            new_entries = []
            pattern = r'\[([^\]]+)\] \[([^\]]+)\] \[([^\]]+)\] (.+)'

            # Finde alle Einträge
            for match in re.finditer(pattern, content):
                timestamp_str, importance, category, entry_content = match.groups()

                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    if timestamp > cutoff_time:
                        # Behalte diesen Eintrag
                        new_entries.append(f"[{timestamp_str}] [{importance}] [{category}] {entry_content}")
                    else:
                        cleaned_count += 1
                except ValueError:
                    # Behalte Einträge mit ungültigem Timestamp
                    new_entries.append(f"[{timestamp_str}] [{importance}] [{category}] {entry_content}")

            # Baue neuen Inhalt
            if cleaned_count > 0:
                new_content = re.sub(
                    r'### Aktuell Relevant\n.*?(?=\n## |\n---\n|$)',
                    f"### Aktuell Relevant\n" + "\n".join(new_entries) + "\n",
                    content,
                    flags=re.DOTALL
                )

                # Update timestamp
                timestamp = datetime.now().isoformat()
                new_content = re.sub(
                    r"> Automatisch generiert - Letzte Aktualisierung: .*",
                    f"> Automatisch generiert - Letzte Aktualisierung: {timestamp}",
                    new_content
                )

                # Log die Bereinigung
                new_content = self._log_cleanup(new_content, cleaned_count)

                with open(self.daily_info_path, "w", encoding="utf-8") as f:
                    f.write(new_content)

        except Exception as e:
            print(f"[SHORT-TERM-MEMORY] Fehler bei Bereinigung: {e}")

        return cleaned_count

    def _log_cleanup(self, content: str, cleaned_count: int) -> str:
        """Loggt die Bereinigung in der Datei."""
        timestamp = datetime.now().isoformat()

        # Finde die Log-Tabelle und füge neuen Eintrag hinzu
        if "| Datum | Events | Bereinigt |" in content:
            content = content.replace(
                "| Datum | Events | Bereinigt |\n|-------|--------|-----------|\n",
                f"| Datum | Events | Bereinigt |\n|-------|--------|-----------|\n| {timestamp} | Automatische Bereinigung | {cleaned_count} |\n",
                1
            )
        else:
            # Fallback: Log am Ende
            content += f"\n{timestamp} - Bereinigt: {cleaned_count} Einträge\n"

        return content

    def get_formatted_for_prompt(self, query: str = None) -> str:
        """
        Formatiert die relevanten Infos für den System-Prompt.

        Args:
            query: Optionaler Suchbegriff

        Returns:
            Formatierter String mit Infos
        """
        infos = self.get_relevant_infos(query=query)

        if not infos:
            return ""

        lines = ["=== KURZZEITGEDÄCHTNIS ==="]
        for timestamp, importance, category, content in infos:
            lines.append(f"[{importance}] {content}")

        return "\n".join(lines)

    def get_count(self) -> int:
        """Gibt die Anzahl der aktuellen Einträge zurück."""
        try:
            with open(self.daily_info_path, "r", encoding="utf-8") as f:
                content = f.read()

            pattern = r'\[[^\]]+\] \[[^\]]+\] \[[^\]]+\] [^\n]+'
            return len(re.findall(pattern, content))

        except Exception:
            return 0


# === Singleton Instance ===
_short_term_memory = None


def get_short_term_memory(memory_engine=None) -> ShortTermMemory:
    """Gibt die Short-Term Memory Instanz zurück (Singleton)."""
    global _short_term_memory
    if _short_term_memory is None:
        _short_term_memory = ShortTermMemory(memory_engine=memory_engine)
    return _short_term_memory
