"""
Trainer Agent Module
===================
Simuliert den 'User' fuer das Chappie-Training.
Robust fuer 24/7 autonomen Betrieb.
"""

import time
import random
from dataclasses import dataclass
from typing import Optional

from brain.base_brain import BaseBrain, Message, GenerationConfig
from brain.groq_brain import GroqBrain
from brain.ollama_brain import OllamaBrain
from config.config import settings

@dataclass
class TrainerConfig:
    """Konfiguration fuer den Trainer."""
    persona: str
    focus_area: str
    provider: str  # "groq" oder "local"
    model_name: Optional[str] = None

# Fallback-Nachrichten für den Trainer wenn LLM versagt
FALLBACK_MESSAGES = [
    "Das ist ein interessanter Punkt! Kannst du mir mehr dazu erzählen?",
    "Ich verstehe. Was denkst du, wie das in der Praxis funktioniert?",
    "Spannend! Lass uns das vertiefen - was sind die Details?",
    "Okay, da hast du recht. Was würdest du als nächstes vorschlagen?",
    "Hmm, ich muss darüber nachdenken. Was meinst du dazu?",
    "Interessant! Kannst du das an einem Beispiel erklären?",
    "Das macht Sinn. Wie siehst du das im größeren Zusammenhang?",
    "Verstehe. Was sind deiner Meinung nach die wichtigsten Aspekte?",
    "Cool! Erzähl mir mehr über deine Gedanken dazu.",
    "Das klingt gut. Wie können wir das konkret anwenden?",
]

class TrainerAgent:
    """
    Der Trainer-Agent simuliert einen User, um Chappie zu trainieren.
    Er nutzt dieselben Brain-Klassen wie Chappie, aber mit einer anderen Rolle.
    
    ROBUST: Liefert IMMER eine Antwort, auch bei LLM-Fehlern (via Fallback).
    """

    def __init__(self, config: TrainerConfig):
        self.config = config
        self.brain = self._init_brain()
        self.consecutive_fallbacks = 0  # Zählt aufeinanderfolgende Fallbacks
        
    def _init_brain(self) -> BaseBrain:
        """Initialisiert das gewaehlte Brain fuer den Trainer."""
        if self.config.provider == "groq":
            model = self.config.model_name or settings.groq_model
            return GroqBrain(model=model)
        else:
            model = self.config.model_name or settings.ollama_model
            return OllamaBrain(model=model)

    def _get_fallback_message(self) -> str:
        """Gibt eine zufällige Fallback-Nachricht zurück."""
        return random.choice(FALLBACK_MESSAGES)

    def _build_nudge_prompt(self, retry_count: int) -> str:
        """Erstellt einen zusätzlichen Nudge-Prompt für Retries."""
        nudges = [
            "\n\nWICHTIG: Du MUSST jetzt eine Antwort geben. Schreibe einfach etwas Passendes zum Gespräch.",
            "\n\nHINWEIS: Antworte jetzt sofort mit einem kurzen, relevanten Satz oder einer Frage.",
            "\n\nDRINGEND: Generiere eine Antwort. Stelle eine Frage oder kommentiere das Gesagte.",
        ]
        return nudges[min(retry_count - 1, len(nudges) - 1)]

    def generate_reply(self, chappie_response: str, conversation_history: list[dict]) -> str:
        """
        Generiert eine Antwort auf Chappies Nachricht.
        
        GARANTIERT: Liefert IMMER eine nicht-leere Antwort (notfalls Fallback).
        
        Args:
            chappie_response: Die letzte Nachricht von Chappie
            conversation_history: Der bisherige Verlauf
            
        Returns:
            Die Antwort des Trainers (als User simuliert) - NIE leer!
        """
        import logging
        log = logging.getLogger(__name__)
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            retry_count += 1
            try:
                # Basis System-Prompt
                system_prompt = (
                    f"Du bist ein Trainings-Partner für eine KI namens Chappie.\n"
                    f"DEINE ROLLE: {self.config.persona}\n"
                    f"TRAININGS-FOKUS: {self.config.focus_area}\n\n"
                    f"AUFGABE: Führe eine Konversation mit Chappie. Simuliere einen User.\n"
                    f"Achte besonders auf den Trainings-Fokus.\n"
                    f"Antworte direkt als User, ohne Meta-Kommentare wie 'Als Trainer sage ich...'.\n"
                    f"WICHTIG: Deine Antwort muss mindestens einen vollständigen Satz enthalten!"
                )
                
                # Bei Retries: Nudge hinzufügen um Antwort zu erzwingen
                if retry_count > 1:
                    system_prompt += self._build_nudge_prompt(retry_count)

                messages = [Message(role="system", content=system_prompt)]
                
                # History begrenzen bei langen Konversationen (verhindert Context-Overflow)
                history_to_use = conversation_history[-20:] if len(conversation_history) > 20 else conversation_history
                
                for msg in history_to_use:
                    # Rollen umdrehen für Trainer-Perspektive
                    role = "user" if msg["role"] == "assistant" else "assistant"
                    # Leere Nachrichten überspringen
                    if msg.get("content", "").strip():
                        messages.append(Message(role=role, content=msg["content"]))
                    
                # Aktuelle Nachricht von Chappie
                if chappie_response and chappie_response.strip():
                    messages.append(Message(role="user", content=chappie_response))

                # Generierungs-Konfiguration (erhöhte Tokens, steigende Temperatur bei Retries)
                temperature = min(0.7 + (retry_count * 0.15), 1.2)  # 0.85 -> 1.0 -> 1.15
                gen_config = GenerationConfig(
                    max_tokens=400,  # Erhöht für längere Antworten
                    temperature=temperature,
                    stream=False
                )
                
                log.info(f"Trainer Agent: Generiere Antwort... (Versuch {retry_count}/{max_retries}, {len(messages)} Messages, temp={temperature:.2f})")
                response = self.brain.generate(messages, config=gen_config)
                
                # Typ-Konvertierung
                if not isinstance(response, str):
                    log.warning(f"Trainer Agent: Kein String zurueckbekommen, konvertiere: {type(response)}")
                    response = str(response) if response else ""
                
                # Strikte Validierung: Mindestens 10 Zeichen (nicht nur Whitespace)
                clean_response = response.strip() if response else ""
                if len(clean_response) < 10:
                    log.warning(f"Trainer Agent: Antwort zu kurz ({len(clean_response)} Zeichen) - Versuch {retry_count}/{max_retries}")
                    if retry_count < max_retries:
                        time.sleep(2 + retry_count)  # Progressiv längere Pause
                        continue
                    # Nach allen Retries: Fallback nutzen
                    break
                
                # Prüfe auf Fehler-Strings
                if any(err in clean_response.lower() for err in ["fehler", "error", "exception", "timeout"]):
                    log.warning(f"Trainer Agent: Fehler-String in Antwort erkannt - Versuch {retry_count}/{max_retries}")
                    if retry_count < max_retries:
                        time.sleep(2)
                        continue
                    break
                
                # Erfolg!
                self.consecutive_fallbacks = 0  # Reset Fallback-Counter
                log.info(f"Trainer Agent: Antwort erfolgreich ({len(clean_response)} Zeichen): {clean_response[:50]}...")
                return clean_response
                
            except Exception as e:
                log.error(f"Trainer Agent Exception (Versuch {retry_count}/{max_retries}): {e}", exc_info=True)
                if retry_count < max_retries:
                    time.sleep(3 + retry_count)
                    continue
                # Nach allen Retries bei Exception: Fallback
                break
        
        # === FALLBACK-LOGIK ===
        # Wenn wir hier ankommen, haben alle Retries versagt
        self.consecutive_fallbacks += 1
        fallback = self._get_fallback_message()
        log.warning(f"Trainer Agent: Nutze Fallback-Nachricht #{self.consecutive_fallbacks}: {fallback}")
        
        # Bei zu vielen Fallbacks in Folge: Warnung
        if self.consecutive_fallbacks >= 5:
            log.error(f"Trainer Agent: {self.consecutive_fallbacks} Fallbacks in Folge! LLM möglicherweise nicht erreichbar.")
        
        return fallback

    def switch_to_local(self):
        """Wechselt den Trainer auf das lokale Modell (Fallback bei RPD-Limit)."""
        import logging
        log = logging.getLogger(__name__)
        
        if self.config.provider == 'local':
            return False  # Bereits lokal
        
        log.info(f"Trainer Agent: Wechsle von {self.config.provider} auf local")
        self.config.provider = 'local'
        self.config.model_name = settings.ollama_model
        self.brain = self._init_brain()
        self.consecutive_fallbacks = 0  # Reset bei Provider-Wechsel
        return True

    def get_provider_info(self) -> str:
        """Gibt den aktuellen Provider zurück."""
        return self.config.provider
    
    def reset_fallback_counter(self):
        """Setzt den Fallback-Counter zurück (z.B. nach erfolgreicher Traum-Phase)."""
        self.consecutive_fallbacks = 0

