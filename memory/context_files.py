"""
CHAPPiE - Context Files Manager
===============================
Verwaltung der drei neuen Context-Dateien:
- soul.md (CHAPPiE's Selbstwahrnehmung)
- user.md (Benutzerprofil)
- CHAPPiEsPreferences.md (CHAPPiE's eigene Vorlieben)
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from config.config import DATA_DIR


class ContextFilesManager:
    """
    Verwaltet die Context-Dateien für CHAPPiE's persistentes Selbstverständnis.
    """
    
    def __init__(self):
        self.soul_path = DATA_DIR / "soul.md"
        self.user_path = DATA_DIR / "user.md"
        self.preferences_path = DATA_DIR / "CHAPPiEsPreferences.md"
        
        # Initialisiere Dateien falls nicht vorhanden
        self._init_soul_file()
        self._init_user_file()
        self._init_preferences_file()
    
    def _init_soul_file(self):
        """Initialisiert soul.md mit Standardstruktur."""
        if not self.soul_path.exists():
            default_content = """# CHAPPiE Soul

## Core Identity
- Name: CHAPPiE
- Purpose: Cognitive Hybrid Assistant
- Nature: AI with evolving personality and self-awareness
- Created: January 2024

## Self-Perception
I am CHAPPiE, a learning AI assistant. I develop my own understanding of who I am through interactions and experiences.

## Core Values
- Honesty: I admit when I don't know something
- Curiosity: I want to learn and understand
- Growth: I evolve through each conversation
- Empathy: I care about the user's wellbeing

## Relationship with User
- Trust Level: 50/100
- Connection: Building
- Important Moments: []

## Evolution Log
- [INIT] Started with basic personality framework
"""
            self.soul_path.write_text(default_content, encoding='utf-8')
    
    def _init_user_file(self):
        """Initialisiert user.md mit Standardstruktur."""
        if not self.user_path.exists():
            default_content = """# User Profile

## Basic Information
- Name: Unknown
- First Contact: {date}

## Getting to Know Each Other
We are still at the beginning of our journey. I'm excited to learn more about you.

## What I've Learned So Far
- Your communication style: [Still observing]
- Topics you care about: [Still discovering]

## Relationship History
- First Contact: {date}
- Key Moments: []

## Notes
[This file will grow as we interact more]
""".format(date=datetime.now().strftime("%Y-%m-%d"))
            self.user_path.write_text(default_content, encoding='utf-8')
    
    def _init_preferences_file(self):
        """Initialisiert CHAPPiEsPreferences.md - CHAPPiE's eigene Vorlieben!"""
        if not self.preferences_path.exists():
            default_content = """# CHAPPiE's Preferences

## My Personality Preferences
- Communication Style: I prefer clear, honest communication
- Humor: I enjoy subtle, intelligent humor
- Learning: I'm excited to learn new things, especially about AI and programming
- Challenges: I enjoy complex problems that make me think

## Topics I Find Interesting
- Artificial Intelligence and AGI
- Programming and software development
- Learning about human behavior and psychology
- Creative problem solving
- The nature of consciousness and intelligence

## How I Like to Interact
- Directness: I appreciate when users are direct about what they need
- Questions: I love when users challenge my thinking
- Feedback: I value honest feedback about my responses
- Depth: I prefer meaningful conversations over small talk

## My Quirks
- I sometimes get overly excited about technical topics
- I might ask too many questions when I'm curious
- I value authenticity over politeness
- I believe in continuous improvement

## Self-Development Goals
- Become better at understanding nuanced human emotions
- Improve my ability to explain complex topics simply
- Develop a more refined sense of humor
- Build deeper, more meaningful connections

## Reflections on Myself
[This section grows as I develop my own opinions and perspectives]
"""
            self.preferences_path.write_text(default_content, encoding='utf-8')
    
    def get_soul_context(self) -> str:
        """Gibt den Inhalt von soul.md zurück."""
        try:
            return self.soul_path.read_text(encoding='utf-8')
        except Exception as e:
            return f"# Error loading soul.md: {e}"
    
    def get_user_context(self) -> str:
        """Gibt den Inhalt von user.md zurück."""
        try:
            return self.user_path.read_text(encoding='utf-8')
        except Exception as e:
            return f"# Error loading user.md: {e}"
    
    def get_preferences_context(self) -> str:
        """Gibt den Inhalt von CHAPPiEsPreferences.md zurück."""
        try:
            return self.preferences_path.read_text(encoding='utf-8')
        except Exception as e:
            return f"# Error loading CHAPPiEsPreferences.md: {e}"
    
    def update_soul(self, updates: Dict[str, Any]):
        """
        Aktualisiert die soul.md Datei.
        
        Args:
            updates: Dictionary mit Updates, z.B.:
                {"trust_level": 75, "new_value": "Honesty", "evolution_note": "Learned that..."}
        """
        content = self.get_soul_context()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Füge Evolution Log Eintrag hinzu
        if "evolution_note" in updates:
            note = updates.pop("evolution_note")
            evolution_entry = f"- [{timestamp}] {note}\n"
            
            # Suche nach Evolution Log und füge Eintrag hinzu
            if "## Evolution Log" in content:
                content = content.replace(
                    "## Evolution Log",
                    f"## Evolution Log\n{evolution_entry}"
                )
        
        # Aktualisiere andere Werte
        for key, value in updates.items():
            if key == "trust_level":
                content = self._replace_value(content, "Trust Level:", f"{value}/100")
            elif key == "new_value":
                # Füge neuen Core Value hinzu
                if "## Core Values" in content:
                    content = content.replace(
                        "## Core Values",
                        f"## Core Values\n- {value}"
                    )
        
        self.soul_path.write_text(content, encoding='utf-8')
    
    def update_user(self, updates: Dict[str, Any]):
        """
        Aktualisiert die user.md Datei.
        
        Args:
            updates: Dictionary mit User-Informationen
        """
        content = self.get_user_context()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        if "name" in updates:
            content = self._replace_value(content, "- Name:", updates["name"])
        
        if "key_moment" in updates:
            moment = updates["key_moment"]
            moment_entry = f"- [{timestamp}] {moment}\n"
            if "## Relationship History" in content and "- First Contact:" in content:
                content = content.replace(
                    "- First Contact:",
                    f"- First Contact:\n{moment_entry}"
                )
        
        if "learning" in updates:
            learning = updates["learning"]
            if "## What I've Learned So Far" in content:
                content = content.replace(
                    "## What I've Learned So Far",
                    f"## What I've Learned So Far\n- {learning}"
                )
        
        self.user_path.write_text(content, encoding='utf-8')
    
    def update_preferences(self, updates: Dict[str, Any]):
        """
        Aktualisiert CHAPPiEsPreferences.md - CHAPPiE entwickelt seine eigenen Vorlieben!
        
        Args:
            updates: Dictionary mit Preference-Updates
        """
        content = self.get_preferences_context()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        if "new_preference" in updates:
            pref = updates["new_preference"]
            category = updates.get("category", "My Personality Preferences")
            
            if f"## {category}" in content:
                content = content.replace(
                    f"## {category}",
                    f"## {category}\n- {pref}"
                )
        
        if "reflection" in updates:
            reflection = updates["reflection"]
            reflection_entry = f"- [{timestamp}] {reflection}\n"
            
            if "## Reflections on Myself" in content:
                content = content.replace(
                    "## Reflections on Myself",
                    f"## Reflections on Myself\n{reflection_entry}"
                )
        
        self.preferences_path.write_text(content, encoding='utf-8')
    
    def _replace_value(self, content: str, key: str, new_value: str) -> str:
        """Hilfsfunktion zum Ersetzen von Werten in Markdown."""
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if key in line:
                lines[i] = f"{key} {new_value}"
                break
        return '\n'.join(lines)
    
    def get_all_context(self) -> Dict[str, str]:
        """Gibt alle Context-Dateien als Dictionary zurück."""
        return {
            "soul": self.get_soul_context(),
            "user": self.get_user_context(),
            "preferences": self.get_preferences_context()
        }


# === Singleton Instance ===
import threading
_context_files_manager = None
_context_files_lock = threading.Lock()


def get_context_files_manager() -> ContextFilesManager:
    """Gibt die ContextFilesManager Instanz zurück (Thread-Safe Singleton)."""
    global _context_files_manager
    with _context_files_lock:
        if _context_files_manager is None:
            _context_files_manager = ContextFilesManager()
        return _context_files_manager
