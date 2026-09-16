"""Request-local wall-clock spans, shared by synchronous and streamed turns."""

from __future__ import annotations
from functools import wraps
import time


def timed_call(owner, name, function, *args, **kwargs):
    started = time.perf_counter()
    try:
        return function(*args, **kwargs)
    finally:
        spans = getattr(owner, "_turn_timings", None)
        if isinstance(spans, dict):
            spans[name] = spans.get(name, 0.0) + (time.perf_counter() - started) * 1000


def measured(name):
    def decorate(function):
        @wraps(function)
        def call(owner, *args, **kwargs):
            return timed_call(owner, name, function, owner, *args, **kwargs)

        return call

    return decorate


def timed_stream(owner, iterable):
    started = time.perf_counter()
    first = True
    try:
        for item in iterable:
            if first and item:
                spans = getattr(owner, "_turn_timings", None)
                if isinstance(spans, dict):
                    spans["generation_ttft_ms"] = (time.perf_counter() - started) * 1000
                first = False
            yield item
    finally:
        spans = getattr(owner, "_turn_timings", None)
        if isinstance(spans, dict):
            spans["generation_ms"] = (
                spans.get("generation_ms", 0) + (time.perf_counter() - started) * 1000
            )


def attach_timings(owner, result, started):
    spans = getattr(owner, "_turn_timings", {}) or {}
    result.setdefault("timing", {}).update(
        {key: round(value, 3) for key, value in spans.items()}
    )
    result["timing"]["total_ms"] = round((time.perf_counter() - started) * 1000, 3)
    # A synchronous provider does not expose its first token timestamp.
    result["timing"].setdefault("generation_ttft_ms", None)
    turn = getattr(owner, "_active_turn", None)
    if turn is not None:
        result["runtime_settings"] = turn.runtime_settings.to_dict()
        result["session_id"] = turn.session_id
        result["turn_id"] = turn.turn_id
    return result
