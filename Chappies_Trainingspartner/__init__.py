"""
Chappies Trainingspartner
=========================
Ein Modul fuer automatisiertes Training von Chappie durch simulierte User-Agenten.

Beinhaltet:
- TrainerAgent: KI-gesteuerter Trainingspartner mit dynamischem Curriculum
- TrainingLoop: Der eigentliche Trainings-Loop mit Rate-Limiting und Fehlerbehandlung
- setup_training: Interaktiver Setup-Wizard
"""

from importlib import import_module
from typing import Any


_EXPORTS = {
    "TrainerAgent": ("trainer_agent", "TrainerAgent"),
    "TrainerConfig": ("trainer_agent", "TrainerConfig"),
    "TrainingLoop": ("training_loop", "TrainingLoop"),
    "load_training_config": ("trainer_agent", "load_training_config"),
    "save_training_config": ("trainer_agent", "save_training_config"),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, symbol_name = _EXPORTS[name]
    value = getattr(import_module(f"{__name__}.{module_name}"), symbol_name)
    globals()[name] = value
    return value

__all__ = [
    "TrainerAgent",
    "TrainerConfig", 
    "TrainingLoop",
    "load_training_config",
    "save_training_config"
]
