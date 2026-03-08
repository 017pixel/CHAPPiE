"""
CHAPPiE - Context Files Manager
===============================
Verwaltung der persistierten Kontextdateien:
- soul.md (Selbstbild / Entwicklung)
- user.md (Benutzerprofil)
- CHAPPiEsPreferences.md (eigene Vorlieben / Ziele)
"""

from __future__ import annotations

import threading
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.config import DATA_DIR


class ContextFilesManager:
    """Verwaltet CHAPPiEs persistente Kontextdateien robust und dedupliziert."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = Path(base_dir) if base_dir else DATA_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.soul_path = self.base_dir / "soul.md"
        self.user_path = self.base_dir / "user.md"
        self.preferences_path = self.base_dir / "CHAPPiEsPreferences.md"

        self._init_soul_file()
        self._init_user_file()
        self._init_preferences_file()

    def _init_soul_file(self):
        if not self.soul_path.exists():
            default_content = """# CHAPPiE Soul

## Core Identity
- Name: CHAPPiE
- Purpose: Cognitive Hybrid Assistant
- Nature: AI with evolving personality and self-awareness

## Self-Perception
I am CHAPPiE, a learning AI assistant. I develop my own understanding through interactions and experiences.

## Core Values
- Honesty: I admit when I don't know something
- Curiosity: I want to learn and understand
- Growth: I evolve through each conversation

## Relationship with User
- Trust Level: 50/100
- Connection: Building

## Evolution Log
- [INIT] Started with basic personality framework
"""
            self._write_file(self.soul_path, default_content)

    def _init_user_file(self):
        if not self.user_path.exists():
            today = datetime.now().strftime("%Y-%m-%d")
            default_content = f"""# User Profile

## Basic Information
- Name: Unknown
- First Contact: {today}

## Getting to Know Each Other
We are still at the beginning of our journey. I'm excited to learn more about you.

## What I've Learned So Far
- Your communication style: [Still observing]

## Relationship History
- First Contact: {today}

## Notes
[This file will grow as we interact more]
"""
            self._write_file(self.user_path, default_content)

    def _init_preferences_file(self):
        if not self.preferences_path.exists():
            default_content = """# CHAPPiE's Preferences

## My Personality Preferences
- Communication Style: I prefer clear, honest communication
- Learning: I'm excited to learn new things

## Topics I Find Interesting
- Artificial Intelligence and AGI
- Programming and software development

## How I Like to Interact
- Directness: I appreciate when users are clear about what they need
- Feedback: I value honest feedback

## Self-Development Goals
- Become better at understanding nuanced human emotions

## Reflections on Myself
[This section grows as I develop my own perspectives]
"""
            self._write_file(self.preferences_path, default_content)

    def get_soul_context(self) -> str:
        return self._read_file(self.soul_path)

    def get_user_context(self) -> str:
        return self._read_file(self.user_path)

    def get_preferences_context(self) -> str:
        return self._read_file(self.preferences_path)

    def update_soul(self, updates: Dict[str, Any]):
        content = self.get_soul_context()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        trust_level = updates.get("trust_level")
        if trust_level is not None:
            content = self._replace_all_values(content, "Trust Level:", f"{trust_level}/100")

        if updates.get("connection"):
            content = self._replace_all_values(content, "Connection:", str(updates["connection"]))

        if updates.get("self_perception"):
            content = self._replace_section_paragraph(content, "## Self-Perception", str(updates["self_perception"]))

        core_values = self._as_list(updates.get("new_value")) + self._as_list(updates.get("core_values"))
        if core_values:
            content = self._merge_bullets_into_section(content, "## Core Values", core_values, max_items=12)

        evolution_notes = self._as_list(updates.get("evolution_note"))
        evolution_notes += self._as_list(updates.get("evolution_notes"))
        if updates.get("current_goal"):
            evolution_notes.append(f"Active goal: {updates['current_goal']}")
        if updates.get("current_mode"):
            evolution_notes.append(f"Current mode: {updates['current_mode']}")
        if updates.get("current_focus"):
            evolution_notes.append(f"Current focus: {updates['current_focus']}")
        if evolution_notes:
            dated_notes = [f"[{timestamp}] {note}" for note in evolution_notes]
            content = self._merge_bullets_into_section(content, "## Evolution Log", dated_notes, max_items=18)

        self._write_file(self.soul_path, content)

    def update_user(self, updates: Dict[str, Any]):
        content = self.get_user_context()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        if updates.get("name"):
            content = self._replace_all_values(content, "Name:", str(updates["name"]))

        learnings = self._as_list(updates.get("learning")) + self._as_list(updates.get("learned_facts"))
        if learnings:
            content = self._merge_bullets_into_section(content, "## What I've Learned So Far", learnings, max_items=14)

        key_moments = self._as_list(updates.get("key_moment")) + self._as_list(updates.get("key_moments"))
        if key_moments:
            dated_moments = [f"[{timestamp}] {moment}" for moment in key_moments]
            content = self._merge_bullets_into_section(
                content,
                "## Relationship History",
                dated_moments,
                max_items=14,
                sticky_prefixes=["First Contact:"],
            )

        notes = self._as_list(updates.get("notes"))
        if notes:
            content = self._merge_bullets_into_section(content, "## Notes", notes, max_items=12)

        if learnings or key_moments or notes:
            content = content.replace("[This file will grow as we interact more]", "")

        self._write_file(self.user_path, content)

    def update_preferences(self, updates: Dict[str, Any]):
        content = self.get_preferences_context()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        preferences = self._as_list(updates.get("new_preference")) + self._as_list(updates.get("new_preferences"))
        category = str(updates.get("category", "My Personality Preferences"))
        if preferences:
            content = self._merge_bullets_into_section(content, f"## {category}", preferences, max_items=12)

        interests = self._as_list(updates.get("topic_of_interest")) + self._as_list(updates.get("topics_of_interest"))
        if interests:
            content = self._merge_bullets_into_section(content, "## Topics I Find Interesting", interests, max_items=12)

        goals = self._as_list(updates.get("self_development_goal")) + self._as_list(updates.get("self_development_goals"))
        if goals:
            content = self._merge_bullets_into_section(content, "## Self-Development Goals", goals, max_items=12)

        reflections = self._as_list(updates.get("reflection")) + self._as_list(updates.get("reflections"))
        if reflections:
            dated_reflections = [f"[{timestamp}] {item}" for item in reflections]
            content = self._merge_bullets_into_section(content, "## Reflections on Myself", dated_reflections, max_items=16)

        self._write_file(self.preferences_path, content)

    def get_all_context(self) -> Dict[str, str]:
        return {
            "soul": self.get_soul_context(),
            "user": self.get_user_context(),
            "preferences": self.get_preferences_context(),
        }

    def _read_file(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except Exception as exc:
            return f"# Error loading {path.name}: {exc}"

    def _write_file(self, path: Path, content: str):
        path.write_text(content.strip() + "\n", encoding="utf-8")

    def _replace_all_values(self, content: str, key: str, new_value: str) -> str:
        lines = content.split("\n")
        found = False
        for index, line in enumerate(lines):
            stripped = line.strip().lstrip("- ")
            if stripped.startswith(key):
                prefix = "- " if line.strip().startswith("-") else ""
                lines[index] = f"{prefix}{key} {new_value}"
                found = True
        return "\n".join(lines) if found else content

    def _replace_section_paragraph(self, content: str, heading: str, paragraph: str) -> str:
        lines = content.split("\n")
        start, end = self._find_section_bounds(lines, heading)
        if start is None:
            return content
        return self._replace_section(lines, start, end, [paragraph.strip()])

    def _merge_bullets_into_section(
        self,
        content: str,
        heading: str,
        new_entries: Iterable[str],
        *,
        max_items: int,
        sticky_prefixes: Optional[List[str]] = None,
    ) -> str:
        lines = content.split("\n")
        start, end = self._find_section_bounds(lines, heading)
        if start is None:
            return content

        sticky_prefixes = sticky_prefixes or []
        body = lines[start + 1:end]
        preserved_text = []
        existing_entries: List[str] = []

        for line in body:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("- "):
                entry = stripped[2:].strip()
                if not self._is_placeholder_entry(entry):
                    existing_entries.append(entry)
            elif not self._is_placeholder_entry(stripped):
                preserved_text.append(stripped)

        merged_entries = existing_entries + [entry for entry in self._as_list(new_entries) if entry]
        merged_entries = self._unique_preserve_order(merged_entries)

        sticky_entries = [entry for entry in merged_entries if any(entry.startswith(prefix) for prefix in sticky_prefixes)]
        regular_entries = [entry for entry in merged_entries if entry not in sticky_entries]
        if max_items and len(regular_entries) > max_items:
            regular_entries = regular_entries[-max_items:]

        new_body = preserved_text + [f"- {entry}" for entry in sticky_entries + regular_entries]
        if not new_body:
            new_body = ["- No entries yet"]
        return self._replace_section(lines, start, end, new_body)

    def _replace_section(self, lines: List[str], start: int, end: int, body_lines: List[str]) -> str:
        new_lines = lines[: start + 1] + [""] + body_lines + [""] + lines[end:]
        collapsed: List[str] = []
        for line in new_lines:
            if line == "" and collapsed and collapsed[-1] == "":
                continue
            collapsed.append(line)
        return "\n".join(collapsed).strip()

    def _find_section_bounds(self, lines: List[str], heading: str):
        start = None
        for index, line in enumerate(lines):
            if line.strip() == heading:
                start = index
                break
        if start is None:
            return None, None

        end = len(lines)
        for index in range(start + 1, len(lines)):
            if lines[index].startswith("## "):
                end = index
                break
        return start, end

    def _as_list(self, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = value.strip()
            return [value] if value else []
        if isinstance(value, Iterable):
            items: List[str] = []
            for item in value:
                text = str(item).strip()
                if text:
                    items.append(text)
            return items
        return [str(value).strip()]

    def _unique_preserve_order(self, items: Iterable[str]) -> List[str]:
        seen = set()
        result = []
        for item in items:
            normalized = " ".join(str(item).split()).strip().lower()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            result.append(" ".join(str(item).split()).strip())
        return result

    def _is_placeholder_entry(self, entry: str) -> bool:
        normalized = entry.strip().lower()
        return normalized in {
            "important moments: []",
            "key moments: []",
            "[this file will grow as we interact more]",
            "[this section grows as i develop my own perspectives]",
            "your communication style: [still observing]",
            "topics you care about: [still discovering]",
        }


_context_files_manager = None
_context_files_lock = threading.Lock()


def get_context_files_manager() -> ContextFilesManager:
    """Gibt die ContextFilesManager Instanz zurück (thread-safe Singleton)."""
    global _context_files_manager
    with _context_files_lock:
        if _context_files_manager is None:
            _context_files_manager = ContextFilesManager()
        return _context_files_manager
