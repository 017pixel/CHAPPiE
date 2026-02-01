"""
CHAPPiE - Debug Logger
======================
Zentrales Debug Logging für CLI und Web UI.
Zeigt: Tool Calls, Emotions Updates, File Changes, Step 1 JSON
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from collections import deque


class LogLevel(str, Enum):
    """Log Level."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class DebugEntry:
    """Ein Debug Log Eintrag."""
    timestamp: str
    level: str
    category: str
    message: str
    details: Dict[str, Any]


class DebugLogger:
    """
    Zentrales Debug Logging.
    """
    
    def __init__(self, max_entries: int = 100):
        self.max_entries = max_entries
        self.entries: deque[DebugEntry] = deque(maxlen=max_entries)
        self.enabled = True
    
    def _add_entry(self, level: LogLevel, category: str, message: str, 
                   details: Dict[str, Any] = None):
        """Fügt einen Eintrag hinzu."""
        if not self.enabled:
            return
        
        entry = DebugEntry(
            timestamp=datetime.now().strftime("%H:%M:%S.%f")[:-3],
            level=level.value,
            category=category,
            message=message,
            details=details or {}
        )
        
        # deque automatically handles maxlen
        self.entries.append(entry)
    
    def log_step1_start(self):
        """Loggt Start von Step 1."""
        self._add_entry(LogLevel.INFO, "STEP1", "Intent Analysis gestartet")
    
    def log_step1_complete(self, intent_type: str, confidence: float):
        """Loggt Abschluss von Step 1."""
        self._add_entry(
            LogLevel.SUCCESS, "STEP1",
            f"Intent Analysis abgeschlossen: {intent_type} ({confidence:.0%})",
            {"intent": intent_type, "confidence": confidence}
        )
    
    def log_step1_json(self, json_data: Dict[str, Any]):
        """Loggt den Step 1 JSON Output."""
        # Kürze JSON für Display
        json_str = json.dumps(json_data, indent=2, ensure_ascii=False)
        if len(json_str) > 500:
            json_str = json_str[:500] + "..."
        
        self._add_entry(
            LogLevel.INFO, "STEP1_JSON",
            "JSON Output vom Intent Processor",
            {"json_preview": json_str, "full_json": json_data}
        )
    
    def log_tool_call(self, tool_name: str, action: str, data: Dict, 
                      success: bool, result: str = ""):
        """Loggt einen Tool Call."""
        level = LogLevel.SUCCESS if success else LogLevel.ERROR
        self._add_entry(
            level, "TOOL_CALL",
            f"{tool_name}.{action}()",
            {
                "tool": tool_name,
                "action": action,
                "data": data,
                "success": success,
                "result": result[:100] if result else ""
            }
        )
    
    def log_emotion_update(self, emotion: str, before: int, after: int, 
                          reason: str):
        """Loggt ein Emotions Update."""
        delta = after - before
        delta_str = f"+{delta}" if delta > 0 else str(delta)
        
        self._add_entry(
            LogLevel.INFO, "EMOTION",
            f"{emotion}: {before} → {after} ({delta_str})",
            {
                "emotion": emotion,
                "before": before,
                "after": after,
                "delta": delta,
                "reason": reason
            }
        )
    
    def log_file_update(self, file_name: str, action: str, 
                       content_preview: str = ""):
        """Loggt eine Datei-Aktualisierung."""
        preview = content_preview[:80] + "..." if len(content_preview) > 80 else content_preview
        
        self._add_entry(
            LogLevel.SUCCESS, "FILE_UPDATE",
            f"{file_name}: {action}",
            {
                "file": file_name,
                "action": action,
                "preview": preview
            }
        )
    
    def log_migration(self, count: int):
        """Loggt Migration von Short-term zu Long-term."""
        self._add_entry(
            LogLevel.INFO, "MIGRATION",
            f"{count} Einträge ins Langzeitgedächtnis migriert",
            {"count": count}
        )
    
    def log_step2_start(self, model: str):
        """Loggt Start von Step 2."""
        self._add_entry(
            LogLevel.INFO, "STEP2",
            f"Response Generation gestartet (Model: {model})"
        )
    
    def log_step2_complete(self, tokens: int):
        """Loggt Abschluss von Step 2."""
        self._add_entry(
            LogLevel.SUCCESS, "STEP2",
            f"Response Generation abgeschlossen ({tokens} tokens)"
        )
    
    def log_error(self, category: str, message: str, details: Dict = None):
        """Loggt einen Fehler."""
        self._add_entry(
            LogLevel.ERROR, category,
            message,
            details or {}
        )
    
    def log_warning(self, category: str, message: str, details: Dict = None):
        """Loggt eine Warnung."""
        self._add_entry(
            LogLevel.WARNING, category,
            message,
            details or {}
        )
    
    def get_formatted_log(self, categories: List[str] = None) -> str:
        """
        Formatiert das Log für Display.
        
        Args:
            categories: Optional Filter nach Kategorien
            
        Returns:
            Formatierter String
        """
        lines = ["=== CHAPPiE DEBUG LOG ===", ""]
        
        for entry in self.entries:
            # Filter
            if categories and entry.category not in categories:
                continue
            
            # Level Icon
            icon = {
                "info": "[INFO]",
                "success": "[OK]",
                "warning": "[WARN]",
                "error": "[ERROR]"
            }.get(entry.level, "*")
            
            lines.append(f"[{entry.timestamp}] {icon} [{entry.category}] {entry.message}")
            
            # Details (wenn vorhanden und nicht zu lang)
            if entry.details:
                for key, value in entry.details.items():
                    if key == "full_json":  # Überspringe full_json
                        continue
                    if isinstance(value, str) and len(value) > 100:
                        value = value[:100] + "..."
                    lines.append(f"           {key}: {value}")
        
        lines.append("")
        lines.append("=== END DEBUG LOG ===")
        
        return "\n".join(lines)
    
    def get_entries_by_category(self, category: str) -> List[DebugEntry]:
        """Gibt Einträge einer Kategorie zurück."""
        return [e for e in self.entries if e.category == category]
    
    def get_entries(self) -> List[DebugEntry]:
        """Gibt alle Einträge zurück."""
        return list(self.entries)
    
    def clear(self):
        """Löscht alle Einträge."""
        self.entries = []
    
    def enable(self):
        """Aktiviert Logging."""
        self.enabled = True
    
    def disable(self):
        """Deaktiviert Logging."""
        self.enabled = False


# === Singleton Instance ===
import threading
_debug_logger = None
_debug_logger_lock = threading.Lock()


def get_debug_logger() -> DebugLogger:
    """Gibt die DebugLogger Instanz zurück (Thread-Safe Singleton)."""
    global _debug_logger
    with _debug_logger_lock:
        if _debug_logger is None:
            _debug_logger = DebugLogger()
        return _debug_logger
