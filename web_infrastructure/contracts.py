"""Typed internal contracts for the active CHAPPiE runtime.

The public FastAPI JSON and SSE shapes remain defined at the API boundary.  The
types in this module only make the data exchanged inside the runtime explicit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Literal, Optional, TypedDict
from uuid import uuid4
from config.session_settings import SessionRuntimeSettings


StatusCallback = Callable[[Dict[str, Any]], None]
StreamEventName = Literal["status", "token", "error", "finished"]


@dataclass(frozen=True)
class RuntimeOptions:
    """Construction options shared by the factory and the runtime facade."""

    runtime_data_dir: Any = None
    memory_collection_name: Optional[str] = None
    research_mode: bool = False
    feature_flags: Dict[str, bool] = field(default_factory=dict)


@dataclass(frozen=True)
class TurnContext:
    """Stable input contract used by synchronous and streamed turns."""

    user_input: str
    history: List[Dict[str, Any]]
    debug_mode: bool = False
    status_callback: Optional[StatusCallback] = None
    temporal_context: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    turn_id: str = field(default_factory=lambda: uuid4().hex)
    runtime_settings: SessionRuntimeSettings = field(default_factory=SessionRuntimeSettings.from_mapping)


class ResponseEnvelope(TypedDict, total=False):
    response_text: str
    provider: str
    model: str
    emotions: Dict[str, int]
    emotions_before: Dict[str, int]
    emotions_delta: Dict[str, Any]
    life_snapshot: Dict[str, Any]
    sleep_status: Dict[str, Any]
    debug_entries: List[Dict[str, Any]]
    retry_history: List[Dict[str, Any]]


class StreamEvent(TypedDict, total=False):
    event: StreamEventName
    step: int
    status_text: str
    content: str
    token_type: str
    error: str
    result: ResponseEnvelope
