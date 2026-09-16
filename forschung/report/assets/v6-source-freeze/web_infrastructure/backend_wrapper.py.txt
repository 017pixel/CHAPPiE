"""Backward-compatible imports for the CHAPPiE runtime.

Pure contract helpers stay cheap to import. The active runtime is loaded only
when a backend instance or class is requested, which keeps tooling and offline
tests independent of optional memory/provider packages.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

from config.config import LLMProvider
from web_infrastructure.formatting import prompt_chain_of_thought_enabled
from web_infrastructure.generation import (
    calculate_generation_timing,
    measure_prompt_components,
    response_memory_top_k_for_intent,
)
from web_infrastructure.turn_context import (
    context_allows_long_term_memory,
    is_isolated_request,
    is_self_contained_math_query,
    is_transient_problem_statement,
)

if TYPE_CHECKING:
    from web_infrastructure.chappie_runtime import CHAPPiERuntime


CHAT_PROVIDER = LLMProvider.VLLM


def create_chappie_backend(
    *,
    runtime_data_dir: Optional[Path] = None,
    memory_collection_name: Optional[str] = None,
    research_mode: bool = False,
    feature_flags: Optional[Dict[str, bool]] = None,
) -> "CHAPPiERuntime":
    from web_infrastructure.chappie_runtime import create_chappie_backend as create_runtime

    return create_runtime(
        runtime_data_dir=runtime_data_dir,
        memory_collection_name=memory_collection_name,
        research_mode=research_mode,
        feature_flags=feature_flags,
    )


def init_chappie() -> "CHAPPiERuntime":
    return create_chappie_backend()


def __getattr__(name: str) -> Any:
    if name not in {"CHAPPiERuntime", "CHAPPiEBackend"}:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from web_infrastructure.chappie_runtime import CHAPPiEBackend, CHAPPiERuntime

    value = CHAPPiERuntime if name == "CHAPPiERuntime" else CHAPPiEBackend
    globals()[name] = value
    return value

__all__ = [
    "CHAT_PROVIDER",
    "CHAPPiEBackend",  # noqa: F822 - resolved lazily through __getattr__
    "CHAPPiERuntime",
    "calculate_generation_timing",
    "context_allows_long_term_memory",
    "create_chappie_backend",
    "init_chappie",
    "is_isolated_request",
    "is_self_contained_math_query",
    "is_transient_problem_statement",
    "measure_prompt_components",
    "prompt_chain_of_thought_enabled",
    "response_memory_top_k_for_intent",
]
