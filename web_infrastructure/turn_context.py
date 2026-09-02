"""Turn input normalization shared by sync and streaming adapters."""

from __future__ import annotations

import re

from typing import Any, Dict, List, Optional

from web_infrastructure.contracts import StatusCallback, TurnContext



def is_self_contained_math_query(text: str) -> bool:
    """Detect closed arithmetic that must not be influenced by autobiographical RAG."""
    normalized = str(text or "").lower().replace("×", "*").replace("÷", "/")
    number_words = (
        "null|eins|ein|eine|zwei|drei|vier|fuenf|fünf|sechs|sieben|acht|neun|"
        "zehn|elf|zwoelf|zwölf|dreizehn|vierzehn|fuenfzehn|fünfzehn|sechzehn|"
        "siebzehn|achtzehn|neunzehn|zwanzig"
    )
    operand = rf"(?:-?\d+(?:[.,]\d+)?|(?:{number_words}))"
    operator = r"(?:\+|-|\*|/|x|plus|minus|mal|geteilt\s+durch|dividiert\s+durch)"
    return bool(re.search(rf"\b{operand}\s*{operator}\s*{operand}\b", normalized))

def is_transient_problem_statement(text: str) -> bool:
    """Detect a short operational/frustration report without a recall request.

    These turns should still update emotion and life state, but old semantic
    conversation summaries about crashes or system failure are not useful
    evidence for the immediate response.  Explicit questions about a past
    problem do not match and continue to use the normal memory path.
    """
    normalized = str(text or "").casefold()
    return bool(re.search(
        r"(?:\bfunktioniert\s+(?:nicht|nix|nichts)\b|\bgeht\s+nicht\b|"
        r"\balles\s+(?:ist\s+)?kaputt\b|\bkomplett\s+kaputt\b|"
        r"\b(?:total|alles)\s+falsch\b)",
        normalized,
    ))

def context_allows_long_term_memory(requirements: Dict[str, bool] | None) -> bool:
    """Make the Step-1 context contract authoritative for semantic retrieval."""
    return bool((requirements or {}).get("need_long_term_memory", True))

def is_isolated_request(requirements: Dict[str, bool] | None) -> bool:
    keys = (
        "need_soul_context",
        "need_user_context",
        "need_preferences",
        "need_short_term_memory",
        "need_long_term_memory",
    )
    values = requirements or {}
    return not any(bool(values.get(key, True)) for key in keys)

def build_turn_context(
    user_input: str,
    history: Optional[List[Dict[str, Any]]],
    *,
    debug_mode: bool = False,
    status_callback: Optional[StatusCallback] = None,
    temporal_context: Optional[Dict[str, Any]] = None,
) -> TurnContext:
    """Create an isolated request object without changing user text semantics."""

    return TurnContext(
        user_input=str(user_input),
        history=list(history or []),
        debug_mode=bool(debug_mode),
        status_callback=status_callback,
        temporal_context=dict(temporal_context) if temporal_context is not None else None,
    )

