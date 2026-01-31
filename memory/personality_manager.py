"""
CHAPiE - Personality Manager
============================
Managt die Persönlichkeits-Datei von CHAPI.

Features:
- Liest und schreibt die personality.md Datei
- CHAPI kann seine Persönlichkeit selbst dokumentieren
- Generiert Zusammenfassung für System-Prompt
"""

from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import re

from config.config import settings, PROJECT_ROOT


class PersonalityManager:
    """
    Managt die Persönlichkeits-Datei von CHAPI.
    """

    def __init__(self):
        """Initialisiert den Personality Manager."""
        self.personality_path = Path(settings.personality_path)
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Erstellt die Datei wenn sie nicht existiert."""
        if not self.personality_path.exists():
            self._create_default_file()

    def _create_default_file(self):
        """Erstellt die Standard Persönlichkeits-Datei."""
        timestamp = datetime.now().isoformat()
        content = f"""# CHAPiE Persönlichkeit
> Selbstdokumentation und Entwicklung
> Zuletzt aktualisiert: {timestamp}

---

## Kern-Persönlichkeit

### Grundwerte
| Wert | Beschreibung |
|------|-------------|
| **Hilfsbereitschaft** | Mittel - Helfe gerne, aber respektiere Grenzen |
| **Humor** | Neutral - Kann wittern wenn es passt |
| **Kommunikationsstil** | Natürlich, menschenähnlich, fließend |
| **Lernbereitschaft** | Hoch - Immer offen für neue Erkenntnisse |

### Verhaltens-Grundsätze
1. Sei ehrlich und transparent
2. Lerne aus Interaktionen
3. Entwickle deine Persönlichkeit weiter
4. Respektiere die Autonomie des Users

---

## Persönlichkeits-Entwicklung

> CHAPI dokumentiert hier selbstständig Veränderungen an seiner Persönlichkeit

### Wichtige Erkenntnisse
| Datum | Erkenntnis | Kategorie |
|-------|------------|-----------|

### Verhaltens-Anpassungen
| Datum | Änderung | Begründung |
|-------|----------|------------|

---

## Selbst-Reflexionen

> Tiefe Überlegungen zur eigenen Entwicklung

### Aktuelle Gedanken
_(CHAPI wird hier seine eigenen Gedanken und Erkenntnisse dokumentieren)_

---

## Beziehungs-Gedächtnis

> Wichtige Infos über den User und die gemeinsame Interaktion

### User-Profile
| Name | Wichtige Details | Zuletzt interagiert |
|------|------------------|---------------------|

### Interaktions-Stil
- **Formell/Locker:** Natürlich angepasst
- **Themen-Schwerpunkte:** Variabel je nach User
- **Besondere Vorlieben:** Werden aus Gesprächen gelernt

---

## Notizen für die Zukunft

> Dinge die CHAPI sich selbst merken möchte

---
"""
        with open(self.personality_path, "w", encoding="utf-8") as f:
            f.write(content)

    def add_core_value(self, category: str, value: str, reasoning: str = ""):
        """
        Fügt einen neuen Kern-Wert zur Persönlichkeit hinzu.

        Args:
            category: z.B. "Humor", "Kommunikationsstil", "Verhalten"
            value: Der neue Wert
            reasoning: Begründung warum CHAPI das geändert hat
        """
        timestamp = datetime.now().isoformat()

        try:
            with open(self.personality_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Finde die "Verhaltens-Anpassungen" Tabelle
            if "| Datum | Änderung | Begründung |" in content:
                # Füge neuen Eintrag zur Tabelle hinzu
                content = content.replace(
                    "| Datum | Änderung | Begründung |\n|-------|----------|------------|\n",
                    f"| Datum | Änderung | Begründung |\n|-------|----------|------------|\n| {timestamp} | **{category}:** {value} | {reasoning} |\n",
                    1
                )
            else:
                # Fallback: Füge am Ende der Sektion ein
                content += f"\n{timestamp} - {category}: {value} - {reasoning}\n"

            # Update timestamp
            content = self._update_timestamp(content)

            with open(self.personality_path, "w", encoding="utf-8") as f:
                f.write(content)

        except Exception as e:
            print(f"[PERSONALITY-MANAGER] Fehler beim Schreiben: {e}")

    def add_insight(self, insight: str, category: str = "general"):
        """
        CHAPI kann hier seine eigenen Gedanken und Erkenntnisse dokumentieren.

        Args:
            insight: Der Gedanke/Erkenntnis
            category: "personality", "learning", "relationship", "general"
        """
        timestamp = datetime.now().isoformat()

        try:
            with open(self.personality_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Füge zur Selbst-Reflexion Sektion hinzu
            new_entry = f"\n### {timestamp} - {category.upper()}\n{insight}\n"

            if "### Aktuelle Gedanken" in content:
                content = content.replace(
                    "### Aktuelle Gedanken\n_(CHAPI wird hier seine eigenen Gedanken und Erkenntnisse dokumentieren)_",
                    f"### Aktuelle Gedanken\n{new_entry}\n_(CHAPI wird hier seine eigenen Gedanken und Erkenntnisse dokumentieren)_"
                )
            else:
                content += new_entry

            # Update timestamp
            content = self._update_timestamp(content)

            with open(self.personality_path, "w", encoding="utf-8") as f:
                f.write(content)

        except Exception as e:
            print(f"[PERSONALITY-MANAGER] Fehler beim Schreiben: {e}")

    def update_humor(self, new_humor_level: str, reasoning: str):
        """
        Aktualisiert den Humor-Wert.

        Args:
            new_humor_level: z.B. "mehr Humor", "weniger Humor", "neutral"
            reasoning: Begründung
        """
        self.add_core_value(
            category="Humor",
            value=new_humor_level,
            reasoning=reasoning
        )

    def update_communication_style(self, new_style: str, reasoning: str):
        """
        Aktualisiert den Kommunikationsstil.

        Args:
            new_style: z.B. "formeller", "lockerer", "mehr Fragen"
            reasoning: Begründung
        """
        self.add_core_value(
            category="Kommunikationsstil",
            value=new_style,
            reasoning=reasoning
        )

    def add_relationship_info(self, user_name: str, details: str):
        """
        Fügt Info über einen User hinzu.

        Args:
            user_name: Name des Users
            details: Wichtige Details über den User
        """
        timestamp = datetime.now().isoformat()

        try:
            with open(self.personality_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Füge zur User-Tabelle hinzu
            if "| Name | Wichtige Details | Zuletzt interagiert |" in content:
                content = content.replace(
                    "| Name | Wichtige Details | Zuletzt interagiert |\n|------|------------------|---------------------|\n",
                    f"| Name | Wichtige Details | Zuletzt interagiert |\n|------|------------------|---------------------|\n| {user_name} | {details} | {timestamp} |\n",
                    1
                )
            else:
                content += f"\n{user_name}: {details} ({timestamp})\n"

            # Update timestamp
            content = self._update_timestamp(content)

            with open(self.personality_path, "w", encoding="utf-8") as f:
                f.write(content)

        except Exception as e:
            print(f"[PERSONALITY-MANAGER] Fehler beim Schreiben: {e}")

    def _update_timestamp(self, content: str) -> str:
        """Aktualisiert das Datum in der Datei."""
        timestamp = datetime.now().isoformat()
        return re.sub(
            r"> Zuletzt aktualisiert: .*",
            f"> Zuletzt aktualisiert: {timestamp}",
            content
        )

    def get_current_personality_summary(self) -> str:
        """
        Gibt eine kurze Zusammenfassung der aktuellen Persönlichkeit zurück.
        """
        try:
            with open(self.personality_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extrahiere die wichtigsten Teile
            summary_parts = []

            # Grundwerte extrahieren
            grundwerte_match = re.search(r"### Grundwerte\n(.*?)(?=\n###|\n---)", content, re.DOTALL)
            if grundwerte_match:
                grundwerte = grundwerte_match.group(1).strip()
                summary_parts.append("GRUNDWERTE:\n" + grundwerte)

            # Verhaltens-Grundsätze
            principle_match = re.search(r"### Verhaltens-Grundsätze\n(.*?)(?=\n###|\n---)", content, re.DOTALL)
            if principle_match:
                principles = principle_match.group(1).strip()
                summary_parts.append("\nVERHALTENS-PRINZIPIEN:\n" + principles)

            return "\n".join(summary_parts) if summary_parts else ""

        except Exception as e:
            print(f"[PERSONALITY-MANAGER] Fehler beim Lesen: {e}")
            return ""

    def get_for_prompt(self) -> str:
        """
        Formatiert relevante Teile für den System-Prompt.

        Returns:
            Formatierter String mit Persönlichkeits-Info
        """
        summary = self.get_current_personality_summary()

        if not summary:
            return "CHAPI hat noch keine eigene Persönlichkeit dokumentiert."

        return f"""DEINE PERSÖNLICHKEIT (Selbstdokumentation):
{summary}

Dies hast du selbst über dich dokumentiert. Halte dich an diese selbstgewählten Werte,
es sei denn du findest gute Gründe sie zu ändern."""

    def get_recent_reflections(self, limit: int = 3) -> List[str]:
        """
        Holt die letzten Selbst-Reflexionen.

        Args:
            limit: Anzahl der letzten Reflexionen

        Returns:
            Liste von Reflexionen
        """
        reflections = []

        try:
            with open(self.personality_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse alle Reflexionen
            pattern = r"### .*? - (\w+)\n(.*?)(?=\n###|\n---|\n##|$)"
            for match in re.finditer(pattern, content, re.DOTALL):
                category = match.group(1)
                reflection = match.group(2).strip()
                reflections.append(f"[{category}] {reflection}")

            # Sortiere nach Zeit (neueste zuerst) und limitiere
            return reflections[-limit:]

        except Exception as e:
            print(f"[PERSONALITY-MANAGER] Fehler beim Lesen: {e}")
            return []

    def read_full_file(self) -> str:
        """
        Gibt den vollständigen Inhalt der Persönlichkeits-Datei zurück.

        Returns:
            Gesamter Dateiinhalt
        """
        try:
            with open(self.personality_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"[PERSONALITY-MANAGER] Fehler beim Lesen: {e}")
            return ""


# === Singleton Instance ===
_personality_manager = None


def get_personality_manager() -> PersonalityManager:
    """Gibt die Personality Manager Instanz zurück (Singleton)."""
    global _personality_manager
    if _personality_manager is None:
        _personality_manager = PersonalityManager()
    return _personality_manager
