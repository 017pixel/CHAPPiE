"""
Chappies Trainingspartner
=========================
Ein Modul fuer automatisiertes Training von Chappie durch simulierte User-Agenten.

Beinhaltet:
- TrainerAgent: KI-gesteuerter Trainingspartner mit dynamischem Curriculum
- TrainingLoop: Der eigentliche Trainings-Loop mit Rate-Limiting und Fehlerbehandlung
- setup_training: Interaktiver Setup-Wizard
"""

from .trainer_agent import TrainerAgent, TrainerConfig, load_training_config, save_training_config
from .training_loop import TrainingLoop

__all__ = [
    "TrainerAgent",
    "TrainerConfig", 
    "TrainingLoop",
    "load_training_config",
    "save_training_config"
]
