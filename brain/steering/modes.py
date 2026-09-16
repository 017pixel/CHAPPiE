"""Ablation modes shared by runtime, API and research."""

from enum import Enum


class SteeringMode(str, Enum):
    OFF = "off"
    ACTIVATION = "activation"
    SEQUENCE = "sequence"
    COMBINED = "combined"

    @property
    def activation(self) -> bool:
        return self in (self.ACTIVATION, self.COMBINED)

    @property
    def sequence(self) -> bool:
        return self in (self.SEQUENCE, self.COMBINED)
