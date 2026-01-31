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
            description="Bereinigt abgelaufene (>24h) Einträge aus dem Kurzzeitgedächtnis. "
                       "Dies wird normalerweise automatisch gemacht, kann aber manuell ausgelöst werden.",
            handler=self._handle_cleanup_daily_info,
            parameters={
                "type": "object",
                "properties": {}
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
        timestamp = stm.add_info(content, importance=importance, category=category)
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
        infos = stm.get_relevant_infos(query=query)

        if not infos:
            return "Keine Einträge im Kurzzeitgedächtnis."

        lines = ["Kurzzeitgedächtnis-Einträge:"]
        for timestamp, importance, category, content in infos:
            lines.append(f"- [{importance}] [{category}] {content[:60]}{'...' if len(content) > 60 else ''}")

        return "\n".join(lines)

    def _handle_cleanup_daily_info(self) -> str:
        """Bereinigt abgelaufene Einträge."""
        from memory.short_term_memory import get_short_term_memory

        stm = get_short_term_memory()
        count = stm.cleanup_expired()
        return f"✓ Bereinigung abgeschlossen: {count} abgelaufene Einträge entfernt."


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
