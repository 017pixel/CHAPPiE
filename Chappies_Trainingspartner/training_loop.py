"""
Training Loop Module
====================
Steuert den eigentlichen Trainings-Loop zwischen Trainer und Chappie.
Handhabt Threading fuer Unterbrechbarkeit und robuste Rate-Limiting Pause.
"""

import threading
import time
import sys
import os
import json
from datetime import datetime
from typing import Optional, Callable

from rich.console import Console
from rich.panel import Panel
from rich.live import Live

import logging
log = logging.getLogger(__name__)

# Backend Imports (Manuell um Streamlit Dependencies zu vermeiden)
from config.config import settings, get_active_model, PROJECT_ROOT, LLMProvider
from config.prompts import get_system_prompt_with_emotions
from memory.memory_engine import MemoryEngine
from memory.emotions_engine import EmotionsEngine, analyze_sentiment_simple
from memory.chat_manager import ChatManager
from brain import get_brain
from brain.ollama_brain import OllamaBrain
from brain.base_brain import GenerationConfig
from brain.deep_think import DeepThinkEngine

from .trainer_agent import TrainerAgent

console = Console()

class TrainingLoop:
    def __init__(self, trainer: TrainerAgent):
        self.trainer = trainer
        self.stop_flag = threading.Event()
        self.conversation_history = []
        self.messages_since_dream = 0
        self.loop_count = 0
        
        # Chappie Backend Initialisierung (ohne Streamlit Cache)
        msg = "Initialisiere Chappie Backend..."
        print(msg)
        log.info(msg)
        self.memory = MemoryEngine()
        self.emotions = EmotionsEngine()
        self.brain = get_brain()
        data_dir = os.path.join(PROJECT_ROOT, "data")
        self.chat_manager = ChatManager(data_dir)
        self.deep_think_engine = DeepThinkEngine(
            memory_engine=self.memory,
            emotions_engine=self.emotions,
            brain=self.brain
        )
        msg = "Chappie Backend bereit."
        print(msg)
        log.info(msg)

    def _safe_execute(self, func: Callable, *args, **kwargs) -> Optional[str]:
        """
        Führt eine LLM-Funktion sicher aus mit:
        1. 2.5 Sekunden Zwangspause (Rate-Limit Optimierung)
        2. Umfassende Fehlerbehandlung (Context Length, Timeout, RPM, RPD)
        3. Automatische Recovery (Context Reduction, Local Fallback)
        """
        consecutive_errors = 0
        MAX_CONSECUTIVE_ERRORS = 5
        
        while not self.stop_flag.is_set():
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                error_msg = f"Zu viele Fehler in Folge ({consecutive_errors}). Pausiere für 30 Minuten..."
                console.print(f"\n[bold red]🛑 {error_msg}[/bold red]")
                log.error(error_msg)
                # Warte 30 Minuten (unterbrechbar)
                for _ in range(30 * 60):
                    if self.stop_flag.is_set(): return None
                    time.sleep(1)
                    if _ % 60 == 0:
                        log.info(f"Pause läuft: {_//60} Minuten verstrichen")
                consecutive_errors = 0 # Reset nach langer Pause
                console.print("[green]Versuche es erneut nach langer Pause...[/green]")
                log.info("Versuche es erneut nach langer Pause")
            
            time.sleep(2.5)
            
            try:
                response = func(*args, **kwargs)
                
                # Check ob GroqBrain einen Fehler als String zurückgegeben hat
                if isinstance(response, str) and response.strip().startswith("Groq Fehler"):
                    error_msg = response
                    error_type = self._classify_error(error_msg)
                    consecutive_errors += 1
                    log.error(f"API FEHLER: {error_msg} (Type: {error_type})")
                    
                    if error_type == "CONTEXT_LENGTH":
                        console.print(f"\n[bold red]⚠️ Context Length Error![/bold red]")
                        self._reduce_conversation_context()
                        console.print("[yellow]Erneuter Versuch mit reduziertem Context...[/yellow]")
                        log.info("Context reduziert, versuche erneut...")
                        time.sleep(2)
                        continue
                        
                    elif error_type == "TIMEOUT":
                        console.print(f"\n[bold red]⚠️ Timeout/Connection Error![/bold red]")
                        console.print("[yellow]Warte 5 Sekunden vor Retry...[/yellow]")
                        log.warning("Timeout-Error, warte 5 Sekunden...")
                        for _ in range(5):
                            if self.stop_flag.is_set(): return None
                            time.sleep(1)
                        console.print("[green]Setze fort...[/green]")
                        continue
                        
                    elif error_type == "RPM":
                        console.print(f"\n[bold red]⚠️ Rate Limit erreicht! (RPM)[/bold red]")
                        console.print(f"[yellow]Pausiere für 60 Sekunden zum Abkühlen...[/yellow]")
                        log.warning("RPM Rate Limit erreicht, pausiere 60 Sekunden...")
                        for _ in range(60):
                            if self.stop_flag.is_set(): return None
                            time.sleep(1)
                        console.print("[green]Setze fort...[/green]")
                        continue
                        
                    elif error_type == "RPD":
                        console.print(f"\n[bold red]⚠️ Tages-Limit erreicht! (RPD)[/bold red]")
                        console.print(f"[yellow]Wechsle Trainer UND Chappie auf lokale Modelle...[/yellow]")
                        log.warning("RPD Limit erreicht, wechsle auf lokale Modelle...")
                        
                        # 1. Trainer wechseln
                        trainer_switched = self.trainer.switch_to_local()
                        
                        # 2. Chappie wechseln
                        self.switch_chappie_to_local()
                        
                        if trainer_switched:
                            console.print(f"[green]Trainer & Chappie laufen jetzt lokal.[/green]")
                            log.info("Erfolgreich auf lokale Modelle gewechselt")
                            time.sleep(2)
                            continue
                        else:
                            console.print(f"[red]Trainer war bereits lokal. Warte 30s...[/red]")
                            log.info("Trainer bereits lokal, warte 30 Sekunden...")
                            time.sleep(30)
                            continue
                            
                    else:
                        # Anderer API Fehler
                        console.print(f"\n[bold red]⚠️ API Fehler: {error_msg}[/bold red]")
                        console.print("[yellow]Warte 10s bevor Retry...[/yellow]")
                        log.warning(f"Anderer API Fehler: {error_msg}")
                        time.sleep(10)
                        continue
                
                # Erfolgreich
                consecutive_errors = 0 
                return response

            except Exception as e:
                consecutive_errors += 1
                error_msg = str(e)
                error_type = self._classify_error(error_msg)
                log.error(f"Unerwarteter Fehler: {error_msg} (Type: {error_type})")
                
                if error_type == "TIMEOUT":
                    console.print(f"\n[bold red]⚠️ Timeout/Connection Error![/bold red]")
                    console.print("[yellow]Warte 5 Sekunden vor Retry...[/yellow]")
                    for _ in range(5):
                        if self.stop_flag.is_set(): return None
                        time.sleep(1)
                    console.print("[green]Setze fort...[/green]")
                    continue
                else:
                    console.print(f"\n[bold red]⚠️ Unerwarteter Fehler: {e}[/bold red]")
                    time.sleep(5)
                    continue
                
        return None

    def _chappie_process(self, user_input: str) -> str:
        """
        Ein vereinfachter 'process' Loop, aehnlich wie im BackendWrapper,
        aber angepasst fuer CLI.
        """
        # 1. Emotions Analyse
        self.emotions.update_from_sentiment(analyze_sentiment_simple(user_input))
        
        # 2. Memory Search
        memories = self.memory.search_memory(user_input, top_k=settings.memory_top_k)
        memories_for_prompt = self.memory.format_memories_for_prompt(memories)
        
        # 3. Prompt Building
        state = self.emotions.get_state()
        system_prompt = get_system_prompt_with_emotions(
            **state.__dict__,
            use_chain_of_thought=False # CoT fuer Training ggf. zu verbose, wir wollen Interaktion
        )
        
        messages = self.brain.build_prompt(
            system_prompt, 
            memories_for_prompt, 
            user_input, 
            self.conversation_history
        )
        
        # 4. Generierung
        gen_config = GenerationConfig(
            max_tokens=250, # Reduziert für Rate-Limit Optimierung (vorher Settings default)
            temperature=settings.temperature,
            stream=False,
        )
        
        response = self.brain.generate(messages, config=gen_config)
        
        if not isinstance(response, str):
            response = str(response)
            
        # Speichern nur wenn KEIN Fehler
        if not self._is_error_response(response):
            self.memory.add_memory(user_input, role="user")
            self.memory.add_memory(response, role="assistant")
        else:
            console.print(f"[red]Fehler-Antwort nicht im Gedachtnis gespeichert[/red]")
        
        return response

    def run_training(self):
        """Der eigentliche Thread-Loop."""
        
        log.info("=" * 50)
        log.info("TRAINING LOOP GESTARTET")
        log.info("=" * 50)
        
        # Versuche Status zu laden
        self.load_state()
        
        if not self.conversation_history:
            # Start-Nachricht des Trainers (Initial) falls keine History
            first_input = "Hallo Chappie! Bist du bereit für unser Training?"
            current_input = first_input
            
            console.print(Panel(f"[bold blue]TRAINER (User):[/bold blue] {current_input}", border_style="blue"))
            log.info(f"TRAINER: {current_input}")
            
            # Zur History hinzufuegen (User Role fuer Chappie)
            self.conversation_history.append({"role": "user", "content": current_input})
        else:
            # Wiederaufnahme: Letzte Nachricht ermitteln
            last_msg = self.conversation_history[-1]
            msg = f"Wiederaufnahme des Trainings... Letzte Rolle: {last_msg['role']}"
            console.print(Panel(f"[yellow]{msg}[/yellow]", border_style="yellow"))
            log.info(msg)
            
            # Wenn letzte Nachricht vom Trainer (user) war, ist Chappie dran
            # Wenn letzte Nachricht von Chappie (assistant) war, ist Trainer dran
            if last_msg["role"] == "user":
                current_input = last_msg["content"]
            else:
                # Trainer muss auf Chappie reagieren
                current_input = None # Signalisiert, dass wir direkt zum Trainer-Teil springen koennten
                pass
                
        # Wenn wir wiederaufnehmen, müssen wir sicherstellen, dass wir an der richtigen Stelle weitermachen.
        # Der Loop ist: Chappie antwortet auf current_input -> Trainer antwortet auf Chappie.
        
        # Fall 1: Neu (current_input gesetzt) -> Chappie ist dran.
        # Fall 2: Wiederaufnahme, letzte Nachricht war User -> Chappie ist dran (current_input = last_user_msg).
        # Fall 3: Wiederaufnahme, letzte Nachricht war Assistant -> Trainer ist dran.
        
        chappie_response = None # Init für LSP
        skip_chappie_turn = False
        if self.conversation_history:
            if self.conversation_history[-1]["role"] == "assistant":
                skip_chappie_turn = True
                chappie_response = self.conversation_history[-1]["content"]
            else:
                current_input = self.conversation_history[-1]["content"]

        log.info(f"Startparameter: skip_chappie_turn={skip_chappie_turn}, total_messages={len(self.conversation_history)}")

        while not self.stop_flag.is_set():
            try:
                self.loop_count += 1
                log.info(f"--- LOOP {self.loop_count} START ---")
                
                # === CHAPPIE ANTWORTET ===
                if not skip_chappie_turn:
                    log.info("CHAPPIE GENERIERE...")
                    with console.status("[bold green]Chappie denkt nach...[/bold green]", spinner="dots"):
                        # Wrap the actual generation/process logic in a lambda for safe execution
                        chappie_response = self._safe_execute(self._chappie_process, current_input)
                    
                    if not chappie_response: 
                        log.warning("Chappie Antwort leer/war fehlerhaft - breche Loop ab")
                        break # Stop/Error
                    
                    # Prüfe ob es ein Fehler ist
                    if self._is_error_response(chappie_response):
                        log.error(f"FEHLER in Chappie Antwort: {chappie_response}")
                        console.print(f"[red]Fehler-Antwort nicht in History gespeichert: {chappie_response}[/red]")
                        time.sleep(2)
                        continue # Keine History-Update, sofort neuer Versuch
                    
                    console.print(Panel(f"[bold green]CHAPPIE:[/bold green] {chappie_response}", border_style="green"))
                    log.info(f"CHAPPIE: {chappie_response}")
                    
                    # History Update (Assistant Role fuer Chappie)
                    self.conversation_history.append({"role": "assistant", "content": chappie_response})
                    self.save_state() # SAVE
                    log.info(f"State gespeichert: {len(self.conversation_history)} Nachrichten")
                else:
                    log.info("SKIP CHAPPIE (Wiederaufnahme nach Trainer-Antwort)")
                    skip_chappie_turn = False # Nur beim ersten Loop überspringen

                if self.stop_flag.is_set(): 
                    log.info("Stop-Flag gesetzt - breche ab")
                    break

                # === TRAINER REAGIERT ===
                log.info("TRAINER GENERIERE...")
                with console.status("[bold blue]Trainer überlegt...[/bold blue]", spinner="dots"):
                    trainer_response = self._safe_execute(
                        self.trainer.generate_reply, 
                        chappie_response, 
                        self.conversation_history
                    )
                
                if not trainer_response: 
                    log.warning("Trainer Antwort leer - starte Retry (max 3 Versuche)...")
                    retry_count = 0
                    while not trainer_response and retry_count < 3:
                        retry_count += 1
                        time.sleep(2)
                        trainer_response = self._safe_execute(
                            self.trainer.generate_reply, 
                            chappie_response, 
                            self.conversation_history
                        )
                    
                    if not trainer_response:
                        log.error("Trainer Antwort bleibt leer nach Retries - breche Loop ab")
                        break # Stop/Error

                # Prüfe ob es ein Fehler ist
                if self._is_error_response(trainer_response):
                    log.error(f"FEHLER in Trainer Antwort: {trainer_response}")
                    console.print(f"[red]Fehler-Antwort nicht in History gespeichert: {trainer_response}[/red]")
                    time.sleep(2)
                    continue # Keine History-Update, sofort neuer Versuch
                
                console.print(Panel(f"[bold blue]TRAINER (User):[/bold blue] {trainer_response}", border_style="blue"))
                log.info(f"TRAINER: {trainer_response}")
                
                # History Update
                self.conversation_history.append({"role": "user", "content": trainer_response})
                self.messages_since_dream += 2 # +2 Nachrichten (Chappie + Trainer)
                
                # === TRAUM-PHASE CHECK (alle 24 Nachrichten / 12 Paare) ===
                if self.messages_since_dream >= 24:
                    log.info("=== TRAUM-PHASE EINGELEITET ===")
                    console.print(Panel("[bold magenta]🌙 TRAUM-PHASE EINGELEITET[/bold magenta]\nKonsolidiere neue Nachrichten und aktualisiere Langzeit-Kontext...", border_style="magenta"))
                    
                    # 1. Erinnerungen konsolidieren (via Memory Engine)
                    # Dies speichert die Fakten einzeln in ChromaDB
                    summary_result = self._safe_execute(self.memory.consolidate_memories, self.brain)
                    
                    if summary_result:
                        log.info(f"Traum-Phase erfolgreich: {summary_result[:200]}...")
                        # Extrahiere die reine Zusammenfassung für den Kontext (aus dem Log-String falls möglich, 
                        # oder wir nutzen eine saubere Methode)
                        console.print(f"[dim]{summary_result}[/dim]")
                        
                        # 2. Kontext-Management: Ersetze nur die letzen 24 Nachrichten durch die Zusammenfassung
                        # Wir behalten alte Zusammenfassungen, entfernen aber die rohen Interaktionen
                        new_history = []
                        # Behalte nur bestehende Zusammenfassungen (Anker)
                        for msg in self.conversation_history:
                            if msg["role"] == "system" and "[TRAUM-ZUSAMMENFASSUNG]" in msg["content"]:
                                new_history.append(msg)
                        
                        # Neue Zusammenfassung als System-Nachricht hinzufügen
                        # Wir kürzen den Report für den Kontext auf das Wesentliche
                        short_summary = summary_result.split("Verlauf:")[0].strip()
                        
                        new_history.append({
                            "role": "system", 
                            "content": f"[TRAUM-ZUSAMMENFASSUNG]: {short_summary}\nAlle Details wurden als Fakten im Gedächtnis gespeichert."
                        })
                        
                        self.conversation_history = new_history
                        self.messages_since_dream = 0 # Reset Counter
                        log.info("Kontext konsolidiert, Traum-Phase abgeschlossen")
                        console.print("[bold green]✅ Kontext wurde konsolidiert und kompaktiert.[/bold green]")
                    else:
                        log.error("Traum-Phase fehlgeschlagen")
                        console.print("[red]❌ Traum-Phase fehlgeschlagen. Mache normal weiter.[/red]")

                self.save_state() # SAVE
                log.info(f"State gespeichert: {len(self.conversation_history)} Nachrichten, messages_since_dream={self.messages_since_dream}")
                current_input = trainer_response
                log.info(f"--- LOOP {self.loop_count} BEENDET ---\n")
                
                # Zusaetzliche Pause nicht mehr noetig, da safe_execute schon 2.5s hat
                # Aber fuer Lesbarkeit schadet eine kleine Pause nicht
                time.sleep(0.5)
                
            except Exception as e:
                console.print(f"[bold red]Kritischer Fehler im Loop:[/bold red] {e}")
                import traceback
                traceback.print_exc()
                # Bei kritischen Fehlern kurz warten, nicht sofort abbrechen (Autonomie!)
                time.sleep(10)
                # break # Nicht brechen, sondern weitermachen (Autonomie) - ausser es ist KeyboardInterrupt


    def start(self):
        """Startet den Thread und wartet auf Enter."""
        training_thread = threading.Thread(target=self.run_training)
        training_thread.daemon = True # Thread stirbt wenn Main stirbt
        training_thread.start()
        
        return training_thread

    def stop(self):
        """Setzt das Stop-Flag."""
        self.stop_flag.set()

    def switch_chappie_to_local(self):
        """Schaltet Chappie auf das lokale Modell um (z.B. bei API Limit)."""
        if settings.llm_provider == LLMProvider.OLLAMA:
            return # Bereits lokal
            
        console.print("[bold yellow]Schalte Chappie auf lokales Modell um (Ollama)...[/bold yellow]")
        log.info("Wechsle Chappie auf lokales Modell (Ollama)")
        
        # 1. Globale Settings ändern
        settings.llm_provider = LLMProvider.OLLAMA
        settings.ollama_model = settings.ollama_model # Behalte default oder was konfiguriert war
        
        # 2. Brain neu initialisieren
        self.brain = OllamaBrain(model=settings.ollama_model)
        
        # 3. DeepThink neu initialisieren (nutzt das Brain)
        self.deep_think_engine = DeepThinkEngine(
            memory_engine=self.memory,
            emotions_engine=self.emotions,
            brain=self.brain
        )
        msg = f"Chappie läuft jetzt lokal mit {settings.ollama_model}"
        console.print(f"[green]{msg}[/green]")
        log.info(msg)

    def save_state(self):
        """Speichert den aktuellen Trainings-Status in eine JSON-Datei."""
        state = {
            "timestamp": datetime.now().isoformat(),
            "history": self.conversation_history,
            "messages_since_dream": self.messages_since_dream
        }
        try:
            with open("training_state.json", "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            log.debug(f"State gespeichert: {len(self.conversation_history)} Nachrichten")
        except Exception as e:
            console.print(f"[red]Fehler beim Speichern des Status: {e}[/red]")
            log.error(f"Fehler beim Speichern des Status: {e}")

    def load_state(self):
        """Lädt den Trainings-Status falls vorhanden."""
        if not os.path.exists("training_state.json"):
            log.info("Kein vorheriger Trainings-Status gefunden, starte neu")
            return
            
        try:
            console.print("[dim]Lade vorherigen Trainings-Status...[/dim]")
            with open("training_state.json", "r", encoding="utf-8") as f:
                state = json.load(f)
                
            self.conversation_history = state.get("history", [])
            self.messages_since_dream = state.get("messages_since_dream", 0)
            last_save = state.get("timestamp", "Unbekannt")
            msg = f"Status geladen ({len(self.conversation_history)} Nachrichten). Letztes Save: {last_save}"
            console.print(f"[green]{msg}[/green]")
            log.info(msg)
            
        except Exception as e:
            console.print(f"[red]Konnte Status nicht laden: {e}[/red]")
            log.error(f"Status konnte nicht geladen werden: {e}")

    def _reduce_conversation_context(self):
        """Reduziert die Conversation-History auf 50%."""
        original_length = len(self.conversation_history)
        if original_length <= 4:
            return False  # Zu wenig zum Kürzen
        
        new_length = max(4, original_length // 2)
        self.conversation_history = self.conversation_history[-new_length:]
        msg = f"Context reduziert: {original_length} -> {new_length} Nachrichten"
        console.print(f"[yellow]{msg}[/yellow]")
        log.info(msg)
        return True

    def _is_error_response(self, response: str) -> bool:
        """Prüft ob eine Antwort eine Fehlermeldung ist."""
        if not isinstance(response, str):
            return False
        response_lower = response.lower()
        error_indicators = [
            "fehler", "error", "exception",
            "groq fehler", "ollama fehler",
            "429", "500", "timeout", "context",
            "rate limit", "quota", "rpd", "rpm"
        ]
        return any(indicator in response_lower for indicator in error_indicators)

    def _classify_error(self, error_msg: str) -> str:
        """Klassifiziert den Fehler-Typ basierend auf der Fehlermeldung."""
        error_lower = error_msg.lower()
        
        if any(keyword in error_lower for keyword in ["context", "maximum context", "token limit", "too long"]):
            return "CONTEXT_LENGTH"
        elif any(keyword in error_lower for keyword in ["timeout", "connection", "network", "timed out"]):
            return "TIMEOUT"
        elif any(keyword in error_lower for keyword in ["429", "rate limit", "rpm", "rate_limit"]):
            return "RPM"
        elif any(keyword in error_lower for keyword in ["quota", "daily", "rpd", "request per day", "usage limit"]):
            return "RPD"
        else:
            return "OTHER"
