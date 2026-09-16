"""Immutable per-turn settings, with central defaults and strict patch validation."""

from dataclasses import asdict, dataclass, fields
from typing import Any

from brain.steering.modes import SteeringMode
from config.config import settings


@dataclass(frozen=True)
class SessionRuntimeSettings:
    memory_enabled: bool
    steering_enabled: bool
    steering_mode: str
    live_enabled: bool

    @classmethod
    def from_mapping(cls, data: dict[str, Any] | None = None):
        known = {field.name for field in fields(cls)}
        values = {**settings.runtime_defaults, **{key: value for key, value in (data or {}).items() if key in known}}
        cls.validate_patch(values)
        return cls(**values)

    @staticmethod
    def validate_patch(values: dict[str, Any]) -> None:
        allowed = {"memory_enabled", "steering_enabled", "steering_mode", "live_enabled"}
        if set(values) - allowed:
            raise ValueError("Unknown session runtime setting")
        for key, value in values.items():
            if key == "steering_mode":
                SteeringMode(value)
            elif type(value) is not bool:
                raise ValueError(f"{key} requires a boolean")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def effective_mode(self) -> str:
        return self.steering_mode if self.steering_enabled else "off"
