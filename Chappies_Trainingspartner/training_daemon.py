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
from datetime import datetime

import json

# Force UTF-8 encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Ensure project root is in path (WICHTIG: Muss VOR den Imports passieren)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Relative Imports sind robuster als absolute mit explizitem Ordnernamen
try:
    from Chappies_Trainingspartner.trainer_agent import TrainerAgent, TrainerConfig
    from Chappies_Trainingspartner.training_loop import TrainingLoop
except ImportError as e:
    # Fallback: Versuche mit alternativer Schreibweise (Case-Sensitivity auf Linux)
    print(f"Import-Fehler: {e}")
    print("Versuche alternative Import-Methode...")
    from trainer_agent import TrainerAgent, TrainerConfig
    from training_loop import TrainingLoop

def setup_logging():
    """Setup logging to file for headless operation."""
    log_file = os.path.join(PROJECT_ROOT, 'training_daemon.log')

    # Remove default handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        filename=log_file,
        level=logging.DEBUG,  # DEBUG fuer detailliertere Logs
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Also log to console for systemd (simple format)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    
    # Rich console output auch enable (falls verfügbar)
    try:
        from rich.logging import RichHandler
        rich_handler = RichHandler(rich_tracebacks=True, show_time=False, show_path=False)
        rich_handler.setLevel(logging.INFO)
        logging.getLogger('').addHandler(rich_handler)
    except ImportError:
        logging.warning("Rich nicht installiert - verwende Standard-Console-Output")


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
    model_name = input("Modell [Standard]: ").strip()
    if not model_name:
        model_name = None
    print()
    
    # Start-Prompt
    print("Erste Nachricht an Chappie (wie soll das Training starten)?")
    print("Beispiel: Hallo Chappie, erklaer mir bitte...")
    start_prompt = input("Start-Prompt: ").strip()
    if not start_prompt:
        start_prompt = "Hallo Chappie! Lass uns ein Gespraech fuehren."
    
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
    state_path = os.path.join(PROJECT_ROOT, 'training_state.json')
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
        if os.path.exists(pid_file):
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
        config_path = os.path.join(PROJECT_ROOT, 'training_config.json')
        
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
            save_config(config_dict, config_path)
            
            config = TrainerConfig(
                persona=config_dict["persona"],
                focus_area=config_dict["focus_area"]
            )
            start_prompt = config_dict.get("start_prompt", "Hallo Chappie!")
            provider = config_dict["provider"]
            model_name = config_dict.get("model_name")

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
            if os.path.exists(config_path):
                logging.info("Lade Konfiguration aus training_config.json")
                with open(config_path, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    
                config = TrainerConfig(
                    persona=saved_config.get("persona", "Ein kritischer User"),
                    focus_area=saved_config.get("focus_area", "Logikfehler")
                )
                provider = saved_config.get("provider", "local")
                model_name = saved_config.get("model_name")
                start_prompt = saved_config.get("start_prompt", "Hallo Chappie!")
            else:
                logging.warning("Keine training_config.json gefunden! Nutze Defaults.")
                # Fallback configuration
                config = TrainerConfig(
                    persona="Ein kritischer User, der versucht Fehler zu finden",
                    focus_area="Logikfehler und Konsistenz im Gedaechtnis"
                )
                provider = "local"
                model_name = None
                start_prompt = "Hallo Chappie! Lass uns ein Gespraech fuehren."
        
        logging.info(f"Aktive Konfiguration: {config.__dict__}")
        
        from config.config import settings, LLMProvider
        
        if settings.training_use_global_settings:
            logging.info(f"Verwende globale Settings: Provider={settings.llm_provider}")
        else:
            if settings.training_chappie_provider:
                settings.llm_provider = settings.training_chappie_provider
                if settings.training_chappie_model:
                    if settings.llm_provider == LLMProvider.GROQ:
                        settings.groq_model = settings.training_chappie_model
                    elif settings.llm_provider == LLMProvider.CEREBRAS:
                        settings.cerebras_model = settings.training_chappie_model
                    elif settings.llm_provider == LLMProvider.NVIDIA:
                        settings.nvidia_model = settings.training_chappie_model
                    else:
                        settings.ollama_model = settings.training_chappie_model
                logging.info(f"Training-spezifische Settings: Provider={settings.llm_provider}, Modell={settings.training_chappie_model}")
            else:
                if provider == "groq":
                    settings.llm_provider = LLMProvider.GROQ
                    if model_name: settings.groq_model = model_name
                else:
                    settings.llm_provider = LLMProvider.OLLAMA
                    if model_name: settings.ollama_model = model_name
                logging.info(f"Legacy Config Provider={settings.llm_provider}")
              
        logging.info(f"Globale Settings aktualisiert: Provider={settings.llm_provider}")
        
        trainer = TrainerAgent(config)
        loop = TrainingLoop(trainer)
        
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

