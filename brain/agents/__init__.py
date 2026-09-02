"""Lazy compatibility namespace for the historical Brain Pipeline v1 agents.

The current runtime does not import these agents. They remain available for
historical research and compatibility tests without being loaded eagerly.
"""

from importlib import import_module
from typing import Any


_EXPORTS = {
    "BaseAgent": ("base_agent", "BaseAgent"),
    "AgentResult": ("base_agent", "AgentResult"),
    "SensoryCortexAgent": ("sensory_cortex", "SensoryCortexAgent"),
    "AmygdalaAgent": ("amygdala", "AmygdalaAgent"),
    "HippocampusAgent": ("hippocampus", "HippocampusAgent"),
    "PrefrontalCortexAgent": ("prefrontal_cortex", "PrefrontalCortexAgent"),
    "BasalGangliaAgent": ("basal_ganglia", "BasalGangliaAgent"),
    "NeocortexAgent": ("neocortex", "NeocortexAgent"),
    "MemoryAgent": ("memory_agent", "MemoryAgent"),
    "BrainOrchestrator": ("orchestrator", "BrainOrchestrator"),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = _EXPORTS[name]
    value = getattr(import_module(f"{__name__}.{module_name}"), attribute_name)
    globals()[name] = value
    return value

__all__ = [
    "BaseAgent",
    "AgentResult",
    "SensoryCortexAgent",
    "AmygdalaAgent",
    "HippocampusAgent",
    "PrefrontalCortexAgent",
    "BasalGangliaAgent",
    "NeocortexAgent",
    "MemoryAgent",
    "BrainOrchestrator",
]
