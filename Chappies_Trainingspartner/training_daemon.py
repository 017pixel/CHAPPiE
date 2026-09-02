"""
Training Daemon - Headless Version
==================================
Autonomer Training-Modus fuer 24/7 Betrieb.
Keine Interaktion, nur Logging.

USAGE:
  python training_daemon.py          # Setzt vorheriges Training fort
  python training_daemon.py --neu    # Startet NEUES Training (interaktiv)
  python training_daemon.py --fokus "Thema"  # Neues Training mit Fokus
"""

import sys
import os
import logging
import argparse
import signal
from logging.handlers import RotatingFileHandler
from typing import Optional

import json
from pathlib import Path

# Force UTF-8 encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Ensure project root is in path (WICHTIG: Muss VOR den Imports passieren)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.config import LEGACY_TRAINING_CONFIG_PATH, TRAINING_CONFIG_PATH  # noqa: E402

from Chappies_Trainingspartner.trainer_agent import TrainerAgent, TrainerConfig  # noqa: E402
from Chappies_Trainingspartner.training_loop import TrainingLoop  # noqa: E402
from config.prompts import TRAINING_START_PROMPT  # noqa: E402

def setup_logging():
    """Setup logging to file for headless operation."""
    # systemd opens its StandardOutput target before dropping privileges and
    # can therefore recreate a root-owned project-root log. Keep the daemon's
    # application log in its writable, isolated runtime directory instead.
    log_dir = Path(PROJECT_ROOT) / "data" / "training_runtime"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = str(log_dir / "training_daemon.log")

    root_logger = logging.getLogger('')
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    root_logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding='utf-8',
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Also log to console for systemd (simple format)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(console)
    
    # Rich console output auch enable (falls verfügbar)
    try:
        from rich.logging import RichHandler
        rich_handler = RichHandler(rich_tracebacks=True, show_time=False, show_path=False)
        rich_handler.setLevel(logging.INFO)
        root_logger.addHandler(rich_handler)
    except ImportError:
        logging.warning("Rich nicht installiert - verwende Standard-Console-Output")


def install_signal_handlers(loop_holder: dict):
    """Installiert Signal-Handler für graceful shutdown."""

    def _handle_shutdown(signum, _frame):
        logging.warning(f"Shutdown-Signal empfangen: {signum}")
        loop = loop_holder.get("loop")
        if loop is not None:
            loop.stop()

    for signal_name in ("SIGTERM", "SIGINT"):
        sig = getattr(signal, signal_name, None)
        if sig is not None:
            signal.signal(sig, _handle_shutdown)


def get_interactive_config() -> dict:
    """Interaktive Abfrage fuer neues Training."""
    print("\n" + "=" * 60)
    print("    NEUES CHAPPIE TRAINING STARTEN")
    print("=" * 60)
    print()
    
    # Persona
    print("Welche Rolle soll der Trainer einnehmen?")
    print("Beispiele: Ein kritischer User, Ein freundlicher Mentor, Ein neugieriger Student")
    persona = input("Trainer-Persona: ").strip()
    if not persona:
        persona = "Ein kritischer aber fairer Nutzer"
    print()
    
    # Fokus-Bereich
    print("Worauf soll der Trainer beim Training achten?")
    print("Beispiele: Logisches Denken, Emotionale Intelligenz, Technisches Wissen")
    focus_area = input("Trainings-Fokus: ").strip()
    if not focus_area:
        focus_area = "Allgemeines Wissen und Konversation"
    print()
    
    # Provider
    print("Welchen LLM-Provider nutzen? (local/groq)")
    provider = input("Provider [local]: ").strip().lower()
    if provider not in ["local", "groq"]:
        provider = "local"
    print()
    
    # Model (optional)
    print("Welches Modell? (Enter fuer Default)")
    model_name: Optional[str] = input("Modell [Standard]: ").strip() or None
    print()
    
    # Start-Prompt
    print("Erste Nachricht an Chappie (wie soll das Training starten)?")
    print("Beispiel: Hallo Chappie, erklaer mir bitte...")
    start_prompt = input("Start-Prompt: ").strip()
    if not start_prompt:
        start_prompt = TRAINING_START_PROMPT
    
    return {
        "persona": persona,
        "focus_area": focus_area,
        "provider": provider,
        "model_name": model_name,
        "start_prompt": start_prompt
    }


def save_config(config_dict: dict, config_path: str):
    """Speichert die Konfiguration."""
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config_dict, f, ensure_ascii=False, indent=2)
    logging.info(f"Konfiguration gespeichert: {config_path}")


def clear_training_state():
    """Loescht den gespeicherten Training-State fuer frischen Start."""
    try:
        from config.config import settings
        state_path = Path(getattr(settings, "training_runtime_directory", Path(PROJECT_ROOT) / "data" / "training_runtime")) / "training_state.json"
    except Exception:
        state_path = Path(PROJECT_ROOT) / "data" / "training_runtime" / "training_state.json"
    if os.path.exists(state_path):
        os.remove(state_path)
        logging.info("Alter Training-State geloescht - starte frisch")


def write_pid_file():
    """Schreibt die PID des aktuellen Prozesses in training.pid."""
    pid_file = os.path.join(PROJECT_ROOT, 'training.pid')
    try:
        with open(pid_file, 'w') as f:
            f.write(str(os.getpid()))
        logging.info(f"PID {os.getpid()} in {pid_file} geschrieben")
    except Exception as e:
        logging.warning(f"Konnte PID-Datei nicht schreiben: {e}")


def remove_pid_file():
    """Entfernt die PID-Datei beim Beenden."""
    pid_file = os.path.join(PROJECT_ROOT, 'training.pid')
    try:
        # A restarting systemd instance can overlap briefly with the old
        # process. Only the owner may remove the PID file; otherwise the old
        # process can erase the new daemon's heartbeat marker.
        owns_pid_file = False
        if os.path.exists(pid_file):
            with open(pid_file, 'r', encoding='utf-8') as handle:
                owns_pid_file = handle.read().strip() == str(os.getpid())
        if owns_pid_file:
            os.remove(pid_file)
            logging.info("PID-Datei entfernt")
    except Exception as e:
        logging.warning(f"Konnte PID-Datei nicht entfernen: {e}")


def main():
    # Argument Parser
    parser = argparse.ArgumentParser(
        description="CHAPiE Training Daemon - Autonomes 24/7 Training",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  python training_daemon.py              # Setzt vorheriges Training fort
  python training_daemon.py --neu        # Startet NEUES Training (interaktiv)
  python training_daemon.py --fokus "Mathematik und Logik"  # Neues Training mit Fokus
  python training_daemon.py --fokus "Emotionen" --persona "Ein einfuehlsamer Freund"
        """
    )
    parser.add_argument('--neu', action='store_true', 
                        help='Startet ein NEUES Training (loescht alten State, fragt interaktiv)')
    parser.add_argument('--fokus', type=str, default=None,
                        help='Trainings-Fokus direkt angeben (impliziert --neu)')
    parser.add_argument('--persona', type=str, default=None,
                        help='Trainer-Persona direkt angeben')
    parser.add_argument('--start', type=str, default=None,
                        help='Start-Prompt fuer das Training')
    
    args = parser.parse_args()
    
    setup_logging()
    
    write_pid_file()
    
    logging.info("=" * 70)
    logging.info("CHAPiE TRAINING DAEMON GESTARTET")
    logging.info("=" * 70)
    
    try:
        config_path = TRAINING_CONFIG_PATH
        
        # === NEUES TRAINING ===
        if args.neu or args.fokus:
            logging.info("NEUES TRAINING wird gestartet...")
            
            if args.fokus:
                # Direkte Angabe via Kommandozeile
                config_dict = {
                    "persona": args.persona or "Ein kritischer aber fairer Nutzer",
                    "focus_area": args.fokus,
                    "provider": "local",
                    "model_name": None,
                    "start_prompt": args.start or "Hallo Chappie! Lass uns ein Gespraech fuehren."
                }
                logging.info(f"Fokus via Kommandozeile: {args.fokus}")
            else:
                # Interaktive Abfrage
                config_dict = get_interactive_config()
            
            # State loeschen und Config speichern
            clear_training_state()
            config_path.parent.mkdir(parents=True, exist_ok=True)
            save_config(config_dict, str(config_path))
            
            config = TrainerConfig.from_dict(config_dict)
            start_prompt = config.start_prompt
            provider = config.provider
            model_name = config.model_name

            print("\n" + "=" * 60)
            print("    TRAINING KONFIGURATION")
            print("=" * 60)
            print(f"  Persona:    {config.persona}")
            print(f"  Fokus:      {config.focus_area}")
            print(f"  Provider:   {provider}")
            print(f"  Start:      {start_prompt}")
            print("=" * 60 + "\n")
            
        # === TRAINING FORTSETZEN ===
        else:
            if not config_path.exists() and LEGACY_TRAINING_CONFIG_PATH.exists():
                config_path = LEGACY_TRAINING_CONFIG_PATH
                logging.info("Lade kompatible Legacy-Konfiguration aus dem Projekt-Root")

            if config_path.exists():
                logging.info("Lade Konfiguration aus %s", config_path)
                with open(config_path, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    
                config = TrainerConfig.from_dict(saved_config)
                provider = config.provider
                model_name = config.model_name
                start_prompt = config.start_prompt
            else:
                logging.warning("Keine Trainingskonfiguration gefunden! Nutze Defaults.")
                # Fallback configuration
                config = TrainerConfig(
                    persona="Ein kritischer User, der versucht Fehler zu finden",
                    focus_area="Logikfehler und Konsistenz im Gedaechtnis"
                )
                provider = config.provider
                model_name = config.model_name
                start_prompt = config.start_prompt
        
        logging.info(f"Aktive Konfiguration: {config.to_dict()}")
        
        from config.config import settings, LLMProvider
        
        if settings.training_use_global_settings:
            logging.info(f"Verwende globale Settings: Provider={settings.llm_provider}")
        else:
            if settings.training_chappie_provider:
                settings.llm_provider = settings.training_chappie_provider
                if settings.training_chappie_model:
                    if settings.llm_provider == LLMProvider.GROQ:
                        settings.groq_model = settings.training_chappie_model
                    elif settings.llm_provider == LLMProvider.VLLM:
                        settings.vllm_model = settings.training_chappie_model
                    else:
                        settings.ollama_model = settings.training_chappie_model
                logging.info(f"Training-spezifische Settings: Provider={settings.llm_provider}, Modell={settings.training_chappie_model}")
            else:
                normalized_provider = (provider or "vllm").lower()
                if normalized_provider == "local":
                    normalized_provider = "vllm"

                if normalized_provider == "groq":
                    settings.llm_provider = LLMProvider.GROQ
                    if model_name:
                        settings.groq_model = model_name
                elif normalized_provider == "ollama":
                    settings.llm_provider = LLMProvider.OLLAMA
                    if model_name:
                        settings.ollama_model = model_name
                else:
                    settings.llm_provider = LLMProvider.VLLM
                    if model_name:
                        settings.vllm_model = model_name
                logging.info(f"Legacy Config Provider={settings.llm_provider}")
              
        logging.info(f"Globale Settings aktualisiert: Provider={settings.llm_provider}")
        
        trainer = TrainerAgent(config)
        loop = TrainingLoop(trainer)
        loop_holder = {"loop": loop}
        install_signal_handlers(loop_holder)
        
        # Bei neuem Training: Start-Prompt uebergeben
        if args.neu or args.fokus:
            logging.info(f"Starte NEUES Training mit Prompt: {start_prompt}")
            loop.run_training(initial_prompt=start_prompt)
        else:
            logging.info("Setze vorheriges Training fort (autonomer 24/7 Betrieb)...")
            loop.run_training()
        
    except KeyboardInterrupt:
        logging.warning("Training durch Keyboard-Interrupt gestoppt")
    except Exception as e:
        logging.error(f"Kritischer Fehler im Training-Daemon: {e}", exc_info=True)
        raise
    finally:
        remove_pid_file()

if __name__ == "__main__":
    main()
