"""
Training Daemon - Headless Version
==================================
Autonomer Training-Modus für 24/7 Betrieb.
Keine Interaktion, nur Logging.
"""

import sys
import os
import logging
from datetime import datetime

# Force UTF-8 encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Chappies_Trainingspartner.trainer_agent import TrainerAgent, TrainerConfig
from Chappies_Trainingspartner.training_loop import TrainingLoop

def setup_logging():
    """Setup logging to file for headless operation."""
    log_file = os.path.join(os.path.dirname(__file__), '..', 'training_daemon.log')

    # Remove default handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Also log to console for systemd (simple format)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

def main():
    setup_logging()
    logging.info("Starting CHAPiE Training Daemon")
    
    try:
        # Standard configuration for autonomous operation
        config = TrainerConfig(
            persona="Ein kritischer User, der versucht Fehler zu finden",
            focus_area="Logikfehler und Konsistenz im Gedächtnis",
            provider="local"  # Use local models for 24/7 operation
        )
        
        logging.info(f"Configuration: {config.__dict__}")
        
        trainer = TrainerAgent(config)
        loop = TrainingLoop(trainer)
        
        logging.info("Starting training loop...")
        loop.run_training()  # This runs forever until stopped
        
    except Exception as e:
        logging.error(f"Critical error in training daemon: {e}")
        raise

if __name__ == "__main__":
    main()
