"""Lazy compatibility access to the archived BrainPipeline v1.

The active chat runtime lives in :mod:`web_infrastructure.chappie_runtime`.
This module intentionally keeps the historical imports used by research and
manual compatibility tests without loading the v1 agents during normal brain
or runtime imports.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any


_LEGACY_SOURCE = (
    Path(__file__).resolve().parents[1]
    / "Legacy-Code"
    / "brain-pipeline-v1"
    / "brain_pipeline.py"
)
_legacy_module: ModuleType | None = None

__all__ = ["BrainPipeline", "get_brain_pipeline"]  # noqa: F822 - lazy compatibility export


def _load_legacy_module() -> ModuleType:
    global _legacy_module
    if _legacy_module is not None:
        return _legacy_module

    spec = importlib.util.spec_from_file_location(
        "_chappie_legacy_brain_pipeline_v1",
        _LEGACY_SOURCE,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Legacy BrainPipeline konnte nicht geladen werden: {_LEGACY_SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _legacy_module = module
    return module


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(_load_legacy_module(), name)
    globals()[name] = value
    return value


def get_brain_pipeline() -> Any:
    """Return the archived v1 singleton for compatibility-only callers."""
    return _load_legacy_module().get_brain_pipeline()
