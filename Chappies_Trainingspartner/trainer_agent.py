"""
Trainer Agent Module
===================
Simuliert den 'User' fuer das Chappie-Training.
"""

import time
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

class TrainerAgent:
    """
    Der Trainer-Agent simuliert einen User, um Chappie zu trainieren.
    Er nutzt dieselben Brain-Klassen wie Chappie, aber mit einer anderen Rolle.
    """

    def __init__(self, config: TrainerConfig):
        self.config = config
        self.brain = self._init_brain()
        
    def _init_brain(self) -> BaseBrain:
        """Initialisiert das gewaehlte Brain fuer den Trainer."""
        if self.config.provider == "groq":
            # Nutze konfiguriertes Modell oder Default
            model = self.config.model_name or settings.groq_model
            return GroqBrain(model=model)
        else:
            # Local / Ollama
            model = self.config.model_name or settings.ollama_model
            return OllamaBrain(model=model)

    def generate_reply(self, chappie_response: str, conversation_history: list[dict]) -> str:
        """
        Generiert eine Antwort auf Chappies Nachricht.
        
        Args:
            chappie_response: Die letzte Nachricht von Chappie
            conversation_history: Der bisherige Verlauf
            
        Returns:
            Die Antwort des Trainers (als User simuliert)
        """
        import logging
        log = logging.getLogger(__name__)
        
        # Retry-Logik für Trainer
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            retry_count += 1
            try:
                # System-Prompt bauen
                system_prompt = (
                    f"Du bist ein Trainings-Partner für eine KI namens Chappie.\n"
                    f"DEINE ROLLE: {self.config.persona}\n"
                    f"TRAININGS-FOKUS: {self.config.focus_area}\n\n"
                    f"AUFGABE: Führe eine Konversation mit Chappie. Simuliere einen User.\n"
                    f"Achte besonders auf den Trainings-Fokus.\n"
                    f"Antworte direkt als User, ohne Meta-Kommentare wie 'Als Trainer sage ich...'."
                )

                messages = [Message(role="system", content=system_prompt)]
                
                # History anhaengen (wir muessen die Rollen fuer den Trainer umdrehen!)
                # Chappie (assistant) ist fuer den Trainer der "User" (bzw. Gesprächspartner)
                # Und der Trainer selbst ist "assistant" im Kontext seines eigenen Brains,
                # spielt aber die Rolle des Users.
                
                # Vereinfachung: Wir geben dem Trainer einfach den Verlauf.
                # Er weiss durch den System-Prompt, wer er ist.
                
                for msg in conversation_history:
                    # Wir mappen Chappie zu 'user' (Input für Trainer) und Trainer zu 'assistant' (Output vom Trainer)
                    # damit das LLM des Trainers den Kontext versteht.
                    role = "user" if msg["role"] == "assistant" else "assistant"
                    messages.append(Message(role=role, content=msg["content"]))
                    
                # Aktuelle Nachricht von Chappie (wenn vorhanden)
                if chappie_response:
                     messages.append(Message(role="user", content=chappie_response))

                # Generieren
                gen_config = GenerationConfig(
                    max_tokens=200, # Reduziert für Rate-Limits (vorher 500)
                    temperature=0.8, # Etwas kreativer/variabler
                    stream=False
                )
                
                log.info(f"Trainer Agent: Generiere Antwort... (Versuch {retry_count}/{max_retries}, {len(messages)} Messages)")
                response = self.brain.generate(messages, config=gen_config)
                
                if not isinstance(response, str):
                    log.warning(f"Trainer Agent: Kein String zurueckbekommen, konvertiere: {type(response)}")
                    response = str(response)
                
                if not response or response.strip() == "":
                    log.warning(f"Trainer Agent: LEERE Antwort erhalten (Versuch {retry_count}/{max_retries})!")
                    if retry_count < max_retries:
                        time.sleep(3)  # Kurz warten vor Retry
                        continue
                    else:
                        log.error("Trainer Agent: Alle Retrys fehlgeschlagen")
                        return ""
                
                log.info(f"Trainer Agent: Antwort erfolgreich ({len(response)} Zeichen): {response[:50]}...")
                return response
                
            except Exception as e:
                log.error(f"Trainer Agent Exception (Versuch {retry_count}/{max_retries}): {e}", exc_info=True)
                if retry_count < max_retries:
                    time.sleep(3)  # Kurz warten vor Retry
                    continue
                else:
                    log.error("Trainer Agent: Alle Retrys fehlgeschlagen")
                    raise
        
        log.error("Trainer Agent: Max retries erreicht ohne Antwort")
        return ""

    def switch_to_local(self):
        """Wechselt den Trainer auf das lokale Modell (Fallback bei RPD-Limit)."""
        if self.config.provider == 'local':
            return False  # Bereits lokal
        
        original_provider = self.config.provider
        self.config.provider = 'local'
        self.config.model_name = settings.ollama_model
        self.brain = self._init_brain()
        return True

    def get_provider_info(self) -> str:
        """Gibt den aktuellen Provider zurück."""
        return self.config.provider

