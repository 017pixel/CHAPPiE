"""
Trainer Agent Module
=====================
Simuliert einen User-Agenten der CHAPPiE trainiert.
Unterstützt dynamisches Curriculum mit mehreren Themen und Zeiten.
"""

import time
import json
import os
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Optional, Union, Dict, Any

from rich.console import Console

import logging
log = logging.getLogger(__name__)

# Imports für LLM Backend
from config.config import settings, get_active_model, LLMProvider
from brain import get_brain
from brain.ollama_brain import OllamaBrain
from brain.base_brain import Message, GenerationConfig

console = Console()


@dataclass
class CurriculumItem:
    """Ein einzelnes Thema im Lehrplan."""
    topic: str
    duration_minutes: Union[int, str]  # int oder "infinite"
    
    def get_duration(self) -> Optional[int]:
        """Gibt die Dauer in Minuten zurück, None für infinite."""
        if self.duration_minutes == "infinite":
            return None
        return int(self.duration_minutes)


@dataclass
class TrainerConfig:
    """
    Konfiguration für den Trainer Agent.
    
    Unterstützt:
    - Einfache focus_area (Rückwärtskompatibilität)
    - Curriculum mit mehreren Themen und Zeiten
    """
    persona: str = "Kritischer User"
    
    # Neues Curriculum-System: Liste von Themen mit Dauer
    curriculum: List[CurriculumItem] = field(default_factory=list)
    
    # Legacy: Einzelnes Focus Area (wird zu Curriculum konvertiert)
    focus_area: str = ""
    
    # Timeout nach X Sekunden ohne Antwort
    timeout_seconds: int = 60
    
    def __post_init__(self):
        """Konvertiert focus_area zu curriculum falls nötig."""
        if self.focus_area and not self.curriculum:
            # Legacy-Support: Konvertiere einzelnes Focus zu Curriculum
            self.curriculum = [CurriculumItem(topic=self.focus_area, duration_minutes="infinite")]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrainerConfig":
        """Erstellt TrainerConfig aus einem Dictionary."""
        curriculum = []
        if "curriculum" in data:
            for item in data["curriculum"]:
                curriculum.append(CurriculumItem(
                    topic=item.get("topic", "Allgemeinwissen"),
                    duration_minutes=item.get("duration_minutes", "infinite")
                ))
        
        return cls(
            persona=data.get("persona", "Kritischer User"),
            curriculum=curriculum,
            focus_area=data.get("focus_area", ""),
            timeout_seconds=data.get("timeout_seconds", 60)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary für JSON-Speicherung."""
        return {
            "persona": self.persona,
            "curriculum": [
                {"topic": item.topic, "duration_minutes": item.duration_minutes}
                for item in self.curriculum
            ],
            "timeout_seconds": self.timeout_seconds
        }


class TrainerAgent:
    """
    Ein KI-Agent, der CHAPPiE trainiert.
    
    Features:
    - Dynamisches Curriculum mit automatischem Themenwechsel
    - Fallback auf lokales Modell bei API-Limits
    - Robuste Fehlerbehandlung mit Fallback-Antworten
    """
    
    def __init__(self, config: TrainerConfig):
        """
        Initialisiert den Trainer Agent.
        
        Args:
            config: TrainerConfig mit Persona und Curriculum
        """
        self.config = config
        
        # Curriculum Tracking
        self.current_topic_index = 0
        self.topic_start_time = datetime.now()
        
        # Fallback Counter für robuste Antworten
        self._fallback_counter = 0
        self.MAX_FALLBACK_BEFORE_LOCAL = 3
        
        # Brain initialisieren (eigenes Brain für den Trainer)
        self.brain = get_brain()
        self._is_local = settings.llm_provider == LLMProvider.OLLAMA
        
        msg = f"TrainerAgent initialisiert: Persona='{config.persona}'"
        console.print(f"[cyan]{msg}[/cyan]")
        log.info(msg)
        
        if self.config.curriculum:
            topics = [item.topic for item in self.config.curriculum]
            log.info(f"Curriculum geladen: {len(topics)} Themen: {topics}")
    
    def get_current_focus(self) -> str:
        """
        Gibt das aktuelle Fokus-Thema zurück.
        Wechselt automatisch zum nächsten Thema wenn die Zeit abgelaufen ist.
        
        Returns:
            Das aktuelle Thema als String
        """
        if not self.config.curriculum:
            return "Allgemeinwissen & Smalltalk"
        
        current_item = self.config.curriculum[self.current_topic_index]
        duration = current_item.get_duration()
        
        # Wenn infinite, bleibe beim Thema
        if duration is None:
            return current_item.topic
        
        # Prüfe ob Zeit abgelaufen
        elapsed = datetime.now() - self.topic_start_time
        elapsed_minutes = elapsed.total_seconds() / 60
        
        if elapsed_minutes >= duration:
            # Wechsle zum nächsten Thema
            old_topic = current_item.topic
            self.current_topic_index += 1
            
            # Falls alle Themen durch, bleibe beim letzten
            if self.current_topic_index >= len(self.config.curriculum):
                self.current_topic_index = len(self.config.curriculum) - 1
                log.info(f"Alle Themen abgeschlossen. Bleibe bei: {self.config.curriculum[self.current_topic_index].topic}")
            else:
                new_topic = self.config.curriculum[self.current_topic_index].topic
                self.topic_start_time = datetime.now()
                
                log.info(f"=== THEMEN-WECHSEL: '{old_topic}' -> '{new_topic}' ===")
                console.print(f"[bold yellow]📚 Themen-Wechsel: {old_topic} → {new_topic}[/bold yellow]")
        
        return self.config.curriculum[self.current_topic_index].topic
    
    def get_curriculum_status(self) -> str:
        """Gibt einen formatierten Status des Curriculums zurück."""
        if not self.config.curriculum:
            return "Kein Curriculum definiert"
        
        total = len(self.config.curriculum)
        current = self.current_topic_index + 1
        topic = self.get_current_focus()
        
        return f"Thema {current}/{total}: {topic}"
    
    def _build_system_prompt(self) -> str:
        """
        Baut den System-Prompt für den Trainer.
        
        Returns:
            Dynamischer System-Prompt mit aktuellem Fokus
        """
        current_focus = self.get_current_focus()
        
        return f"""Du bist ein Trainingspartner für eine KI namens CHAPPiE.
Deine Persona: {self.config.persona}
Aktueller Trainings-Fokus: {current_focus}

DEINE AUFGABE:
- Führe ein natürliches Gespräch mit CHAPPiE
- Stelle Fragen zum aktuellen Fokus-Thema
- Reagiere auf CHAPPiEs Antworten mit Folgefragen oder neuen Inputs  
- Sei {self.config.persona.lower()} in deinen Reaktionen
- Gib auch mal kritisches Feedback wenn CHAPPiEs Antwort schwach ist

WICHTIGE REGELN:
- Antworte IMMER auf Deutsch
- Schreibe 1-3 Sätze pro Nachricht (keine langen Texte)
- Bleibe beim aktuellen Fokus-Thema
- Sei abwechslungsreich - wiederhole dich nicht
- Wenn CHAPPiE gut antwortet, gib positives Feedback UND stelle eine neue Frage

Du antwortest direkt als User, OHNE Meta-Kommentare wie "Als Trainer würde ich..."
"""
    
    def generate_reply(self, chappie_response: str, conversation_history: List[dict]) -> str:
        """
        Generiert eine Trainer-Antwort auf CHAPPiEs letzte Nachricht.
        
        Args:
            chappie_response: Die letzte Antwort von CHAPPiE
            conversation_history: Die bisherige Konversation
            
        Returns:
            Die Trainer-Antwort
        """
        system_prompt = self._build_system_prompt()
        
        # Nachrichten für LLM vorbereiten
        messages = [Message(role="system", content=system_prompt)]
        
        # History konvertieren (begrenzt auf letzte 10 für Context)
        recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
        for msg in recent_history:
            # Im Trainer-Kontext: user = CHAPPiE, assistant = Trainer
            # Wir invertieren die Rollen für den Trainer
            role = "assistant" if msg["role"] == "user" else "user"
            messages.append(Message(role=role, content=msg["content"]))
        
        # CHAPPiEs letzte Antwort (als "user" für den Trainer)
        messages.append(Message(role="user", content=chappie_response))
        
        # Generierung mit Error Handling
        try:
            gen_config = GenerationConfig(
                max_tokens=300,  # Kurze Trainer-Antworten
                temperature=0.8,  # Etwas kreativ
                stream=False
            )
            
            response = self.brain.generate(messages, config=gen_config)
            
            # Validierung
            if not response or len(response.strip()) < 5:
                self._fallback_counter += 1
                log.warning(f"Trainer Antwort zu kurz, Fallback #{self._fallback_counter}")
                return self._get_fallback_response()
            
            # Prüfe auf API-Fehler
            if isinstance(response, str) and "fehler" in response.lower():
                self._fallback_counter += 1
                log.error(f"API Fehler in Trainer: {response}")
                return self._get_fallback_response()
            
            # Erfolg - Reset Fallback Counter
            self._fallback_counter = 0
            return response.strip()
            
        except Exception as e:
            self._fallback_counter += 1
            log.error(f"Fehler bei Trainer-Generierung: {e}")
            return self._get_fallback_response()
    
    def _get_fallback_response(self) -> str:
        """
        Gibt eine Fallback-Antwort zurück wenn die Generierung fehlschlägt.
        Wechselt zu lokalem Modell nach zu vielen Fehlern.
        """
        if self._fallback_counter >= self.MAX_FALLBACK_BEFORE_LOCAL:
            self.switch_to_local()
        
        # Thema-basierte Fallback-Fragen
        focus = self.get_current_focus()
        fallbacks = [
            f"Interessant. Erzähl mir mehr über {focus}.",
            f"Was denkst du generell über {focus}?",
            f"Kannst du das näher erklären?",
            f"Hmm, das verstehe ich nicht ganz. Was meinst du genau?",
            f"Okay, und wie hängt das mit {focus} zusammen?",
            f"Spannend! Gibt es dazu ein konkretes Beispiel?",
        ]
        
        import random
        return random.choice(fallbacks)
    
    def switch_to_local(self) -> bool:
        """
        Wechselt den Trainer auf ein lokales Modell (Ollama).
        
        Returns:
            True wenn gewechselt wurde, False wenn bereits lokal
        """
        if self._is_local:
            return False
        
        log.info("Trainer wechselt auf lokales Modell...")
        console.print("[yellow]Trainer wechselt auf lokales Modell (Ollama)...[/yellow]")
        
        try:
            self.brain = OllamaBrain(model=settings.ollama_model)
            self._is_local = True
            self._fallback_counter = 0
            
            log.info(f"Trainer läuft jetzt lokal mit {settings.ollama_model}")
            console.print(f"[green]Trainer läuft jetzt lokal mit {settings.ollama_model}[/green]")
            return True
            
        except Exception as e:
            log.error(f"Fehler beim Wechsel auf lokal: {e}")
            return False
    
    def reset_fallback_counter(self):
        """Setzt den Fallback-Counter zurück."""
        self._fallback_counter = 0


def load_training_config(config_path: str = None) -> TrainerConfig:
    """
    Lädt die Training-Konfiguration aus einer JSON-Datei.
    
    Args:
        config_path: Pfad zur Konfigurationsdatei
        
    Returns:
        TrainerConfig Objekt
    """
    if config_path is None:
        # Standard-Pfad im Projekt-Root
        from config.config import PROJECT_ROOT
        config_path = os.path.join(PROJECT_ROOT, "training_config.json")
    
    if not os.path.exists(config_path):
        log.info(f"Keine Konfiguration gefunden bei {config_path}, nutze Defaults")
        return TrainerConfig()
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        config = TrainerConfig.from_dict(data)
        log.info(f"Konfiguration geladen: {config.persona}, {len(config.curriculum)} Themen")
        return config
        
    except Exception as e:
        log.error(f"Fehler beim Laden der Konfiguration: {e}")
        return TrainerConfig()


def save_training_config(config: TrainerConfig, config_path: str = None):
    """
    Speichert die Training-Konfiguration in eine JSON-Datei.
    
    Args:
        config: Die zu speichernde Konfiguration
        config_path: Zielpfad für die Datei
    """
    if config_path is None:
        from config.config import PROJECT_ROOT
        config_path = os.path.join(PROJECT_ROOT, "training_config.json")
    
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, ensure_ascii=False, indent=2)
        
        log.info(f"Konfiguration gespeichert nach {config_path}")
        
    except Exception as e:
        log.error(f"Fehler beim Speichern der Konfiguration: {e}")
