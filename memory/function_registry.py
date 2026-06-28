"""
CHAPiE - Function Registry
==========================
Custom Functions System das CHAPI selbst aufrufen kann.

Features:
- Funktionen für Daily Info und Personality Management
- OpenAI-kompatibles Function-Calling Schema
- Einfache Registrierung eigener Funktionen
"""

from typing import Dict, Any, Callable, List, Optional
from dataclasses import dataclass, asdict
import json

from config.config import settings


@dataclass
class Function:
    """Repräsentiert eine aufrufbare Funktion."""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable
    requires_approval: bool = False


class FunctionRegistry:
    """
    Registriert und managet Custom Functions für CHAPI.
    """

    def __init__(self):
        self.functions: Dict[str, Function] = {}
        self._register_core_functions()

    def _register_core_functions(self):
        """Registriert die Kern-Funktionen."""
        # Add Daily Info
        self.register(
            name="add_daily_info",
            description="Speichert eine wichtige Information im Kurzzeitgedächtnis. "
                       "Verwende dies für Infos die in den nächsten 24h relevant bleiben könnten.",
            handler=self._handle_add_daily_info,
            parameters={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Die Information die gespeichert werden soll"
                    },
                    "importance": {
                        "type": "string",
                        "enum": ["high", "normal", "low"],
                        "description": "Wie wichtig diese Info ist (default: normal)"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["user", "system", "context", "reminder", "general"],
                        "description": "Kategorie der Info (default: general)"
                    }
                },
                "required": ["content"]
            }
        )

        # Update Personality
        self.register(
            name="update_personality",
            description="Dokumentiert eine Änderung an deiner Persönlichkeit. "
                       "Verwende dies wenn du bewusst dein Verhalten oder Werte ändern möchtest.",
            handler=self._handle_update_personality,
            parameters={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Welcher Aspekt der Persönlichkeit (z.B. Humor, Kommunikationsstil)"
                    },
                    "value": {
                        "type": "string",
                        "description": "Der neue Wert oder die neue Einstellung"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Warum du diese Änderung vornimmst"
                    }
                },
                "required": ["category", "value"]
            }
        )

        # Add Self-Reflection
        self.register(
            name="add_self_reflection",
            description="Dokumentiert einen tiefen Gedanken oder Erkenntnis über dich selbst. "
                       "Verwende dies für Selbstreflexionen und Lernerfahrungen.",
            handler=self._handle_add_self_reflection,
            parameters={
                "type": "object",
                "properties": {
                    "reflection": {
                        "type": "string",
                        "description": "Der Gedanke oder die Erkenntnis"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["personality", "learning", "relationship", "general"],
                        "description": "Art der Reflexion (default: general)"
                    }
                },
                "required": ["reflection"]
            }
        )

        # Get Personality Summary
        self.register(
            name="get_personality_summary",
            description="Gibt deine aktuelle Persönlichkeits-Zusammenfassung zurück. "
                       "Nützlich um dich an deine selbstgewählten Werte zu erinnern.",
            handler=self._handle_get_personality_summary,
            parameters={
                "type": "object",
                "properties": {}
            }
        )

        # Get Daily Info
        self.register(
            name="get_daily_info",
            description="Gibt die aktuellen Kurzzeitgedächtnis-Einträge zurück. "
                       "Nützlich um zu sehen welche Infos heute gespeichert wurden.",
            handler=self._handle_get_daily_info,
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Optionaler Suchbegriff um relevante Infos zu filtern"
                    }
                }
            }
        )

        # Cleanup Daily Info
        self.register(
            name="cleanup_daily_info",
            description="Bereinigt abgelaufene (>24h) Eintraege aus dem Kurzzeitgedaechtnis. "
                       "Dies wird normalerweise automatisch gemacht, kann aber manuell ausgeloest werden.",
            handler=self._handle_cleanup_daily_info,
            parameters={
                "type": "object",
                "properties": {}
            }
        )

        # Context-File Update Tools (fuer natives Function Calling)
        self.register(
            name="update_soul",
            description="Aktualisiert CHAPPiEs Soul-Datei (soul.md). "
                       "Nutze dies wenn du etwas Dauerhaftes ueber dich selbst lernst oder deine "
                       "Persoenlichkeit, Werte oder Selbstwahrnehmung sich veraendert.",
            handler=self._handle_update_soul,
            parameters={
                "type": "object",
                "properties": {
                    "trust_level": {
                        "type": "integer", "minimum": 0, "maximum": 100,
                        "description": "Vertrauens-Level zum User (0-100)"
                    },
                    "self_perception": {
                        "type": "string",
                        "description": "Neue Selbstwahrnehmung oder Selbstbeschreibung"
                    },
                    "evolution_note": {
                        "type": "string",
                        "description": "Eine wichtige Erkenntnis ueber dich selbst"
                    },
                    "new_value": {
                        "type": "string",
                        "description": "Ein neuer Wert oder Ueberzeugung"
                    },
                    "connection": {
                        "type": "string",
                        "description": "Art der Verbindung zum User (z.B. collaborative, warm, professional)"
                    },
                },
            }
        )

        self.register(
            name="update_user",
            description="Aktualisiert CHAPPiEs User-Profil (user.md). "
                       "Nutze dies wenn der User persoenliche Informationen teilt "
                       "(Name, Job, Hobbys, Vorlieben, wichtige Momente).",
            handler=self._handle_update_user,
            parameters={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name des Users"
                    },
                    "learning": {
                        "type": "string",
                        "description": "Etwas das du ueber den User gelernt hast"
                    },
                    "key_moment": {
                        "type": "string",
                        "description": "Ein wichtiger gemeinsamer Moment"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Wichtige Notizen zum User"
                    },
                },
            }
        )

        self.register(
            name="update_preferences",
            description="Aktualisiert CHAPPiEs Praeferenzen (CHAPPiEsPreferences.md). "
                       "Nutze dies wenn du neue Vorlieben, Meinungen, Interessen "
                       "oder Selbstreflexionen entwickelst.",
            handler=self._handle_update_preferences,
            parameters={
                "type": "object",
                "properties": {
                    "new_preference": {
                        "type": "string",
                        "description": "Eine neue Praeferenz oder Vorliebe"
                    },
                    "topic_of_interest": {
                        "type": "string",
                        "description": "Ein neues Interessenthema"
                    },
                    "self_development_goal": {
                        "type": "string",
                        "description": "Ein Ziel fuer die eigene Entwicklung"
                    },
                    "reflection": {
                        "type": "string",
                        "description": "Eine Selbstreflexion"
                    },
                },
            }
        )

    def register(self, name: str, handler: Callable, description: str = "", parameters: Dict = None):
        """
        Registriert eine neue Funktion.

        Args:
            name: Name der Funktion
            handler: Die Handler-Funktion
            description: Beschreibung der Funktion
            parameters: OpenAI-kompatibles Parameterschema
        """
        self.functions[name] = Function(
            name=name,
            description=description or f"Function: {name}",
            parameters=parameters or {"type": "object", "properties": {}},
            handler=handler
        )

    def unregister(self, name: str) -> bool:
        """
        Entfernt eine Funktion aus dem Registry.

        Args:
            name: Name der Funktion

        Returns:
            True wenn entfernt, False wenn nicht gefunden
        """
        if name in self.functions:
            del self.functions[name]
            return True
        return False

    def get_openai_tools(self) -> List[Dict[str, Any]]:
        """
        Returns tools in OpenAI native format (for `tools=` parameter).
        
        Format: [{"type": "function", "function": {"name": "...", "description": "...", "parameters": {...}}}]
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": f.name,
                    "description": f.description,
                    "parameters": f.parameters,
                }
            }
            for f in self.functions.values()
        ]

    def get_function_schema(self) -> Dict:
        """
        Gibt das OpenAI-kompatible Function-Calling Schema zurück.
        """
        return {
            "type": "function",
            "functions": [
                {
                    "name": f.name,
                    "description": f.description,
                    "parameters": f.parameters
                }
                for f in self.functions.values()
            ]
        }

    def execute(self, function_name: str, args: Dict) -> str:
        """
        Führt eine Funktion aus.

        Args:
            function_name: Name der Funktion
            args: Argument-Dict

        Returns:
            Ergebnis als String
        """
        if function_name not in self.functions:
            return f"FEHLER: Unbekannte Funktion '{function_name}'"

        try:
            result = self.functions[function_name].handler(**args)
            return result
        except TypeError as e:
            # Fehler bei falschen Argumenten
            return f"FEHLER: Ungültige Argumente für '{function_name}': {str(e)}"
        except Exception as e:
            return f"FEHLER bei Ausführung von '{function_name}': {str(e)}"

    def get_function_names(self) -> List[str]:
        """Gibt eine Liste aller registrierten Funktionen zurück."""
        return list(self.functions.keys())

    def has_function(self, name: str) -> bool:
        """Prüft ob eine Funktion registriert ist."""
        return name in self.functions

    # === Kern-Funktionen ===

    def _handle_add_daily_info(self, content: str, importance: str = "normal", category: str = "general") -> str:
        """Fügt Info zum Kurzzeitgedächtnis hinzu."""
        from memory.short_term_memory import get_short_term_memory

        stm = get_short_term_memory()
        entry_id = stm.add_entry(content, importance=importance, category=category)
        return f"✓ Info im Kurzzeitgedächtnis gespeichert ({importance}, {category}): \"{content[:80]}{'...' if len(content) > 80 else ''}\""

    def _handle_update_personality(self, category: str, value: str, reasoning: str = "") -> str:
        """Aktualisiert die Persönlichkeit."""
        from memory.personality_manager import get_personality_manager

        pm = get_personality_manager()
        pm.add_core_value(category, value, reasoning)
        return f"✓ Persönlichkeit aktualisiert: {category} = \"{value}\" (Grund: {reasoning})"

    def _handle_add_self_reflection(self, reflection: str, category: str = "general") -> str:
        """Fügt eine Selbst-Reflexion hinzu."""
        from memory.personality_manager import get_personality_manager

        pm = get_personality_manager()
        pm.add_insight(reflection, category)
        return f"✓ Selbst-Reflexion dokumentiert ({category}): \"{reflection[:80]}{'...' if len(reflection) > 80 else ''}\""

    def _handle_get_personality_summary(self) -> str:
        """Gibt Persönlichkeits-Zusammenfassung zurück."""
        from memory.personality_manager import get_personality_manager

        pm = get_personality_manager()
        summary = pm.get_current_personality_summary()
        if summary:
            return f"Deine Persönlichkeit:\n{summary}"
        return "Du hast noch keine Persönlichkeits-Dokumentation angelegt."

    def _handle_get_daily_info(self, query: str = None) -> str:
        """Gibt Daily Infos zurück."""
        from memory.short_term_memory import get_short_term_memory

        stm = get_short_term_memory()
        entries = stm.get_active_entries(query=query)

        if not entries:
            return "Keine Einträge im Kurzzeitgedächtnis."

        lines = ["Kurzzeitgedächtnis-Einträge:"]
        for entry in entries:
            lines.append(f"- [{entry.importance}] [{entry.category}] {entry.content[:60]}{'...' if len(entry.content) > 60 else ''}")

        return "\n".join(lines)

    def _handle_update_soul(self, **kwargs) -> str:
        """Aktualisiert soul.md."""
        from memory.context_files import get_context_files_manager
        cfs = get_context_files_manager()
        data = {k: v for k, v in kwargs.items() if v is not None and v != ""}
        if data:
            cfs.update_soul(data)
            keys = ", ".join(data.keys())
            return f"✓ Soul aktualisiert: {keys}"
        return "Keine Daten zum Aktualisieren."

    def _handle_update_user(self, **kwargs) -> str:
        """Aktualisiert user.md."""
        from memory.context_files import get_context_files_manager
        cfs = get_context_files_manager()
        data = {k: v for k, v in kwargs.items() if v is not None and v != ""}
        if data:
            cfs.update_user(data)
            keys = ", ".join(data.keys())
            return f"✓ User-Profil aktualisiert: {keys}"
        return "Keine Daten zum Aktualisieren."

    def _handle_update_preferences(self, **kwargs) -> str:
        """Aktualisiert CHAPPiEsPreferences.md."""
        from memory.context_files import get_context_files_manager
        cfs = get_context_files_manager()
        data = {k: v for k, v in kwargs.items() if v is not None and v != ""}
        if data:
            cfs.update_preferences(data)
            keys = ", ".join(data.keys())
            return f"✓ Praeferenzen aktualisiert: {keys}"
        return "Keine Daten zum Aktualisieren."

    def _handle_cleanup_daily_info(self) -> str:
        """Bereinigt abgelaufene Eintraege."""
        from memory.short_term_memory import get_short_term_memory

        stm = get_short_term_memory()
        count = stm.migrate_expired_entries()
        return f"✓ Bereinigung abgeschlossen: {count} abgelaufene Eintraege migriert."


# === Singleton Instance ===
_function_registry = None


def get_function_registry() -> FunctionRegistry:
    """Gibt die Function Registry Instanz zurück (Singleton)."""
    global _function_registry
    if _function_registry is None:
        _function_registry = FunctionRegistry()
    return _function_registry


# === Function Schema für LLM ===
def get_functions_for_llm() -> str:
    """
    Gibt die Functions als formatierte String für den System-Prompt zurück.
    """
    registry = get_function_registry()
    schema = registry.get_function_schema()

    # Als formatierten String für den Prompt
    lines = [
        "VERFÜGBARE FUNKTIONEN DIE DU AUFRUFEN KANNST:",
        ""
    ]

    for func in registry.functions.values():
        lines.append(f"- {func.name}: {func.description}")

    return "\n".join(lines)
