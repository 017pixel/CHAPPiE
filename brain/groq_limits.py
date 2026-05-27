"""Lightweight in-process Groq quota guard."""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Tuple


@dataclass
class UsageEvent:
    ts: float
    tokens: int


class GroqRateLimiter:
    def __init__(self):
        self._lock = threading.Lock()
        self._requests: Deque[UsageEvent] = deque()

    @staticmethod
    def estimate_tokens(text: str) -> int:
        return max(1, int(len(text or "") / 4))

    def _limits(self):
        from config.config import settings
        return {
            "minute": (settings.groq_requests_per_minute, settings.groq_tokens_per_minute, 60),
            "hour": (settings.groq_requests_per_hour, settings.groq_tokens_per_hour, 3600),
            "day": (settings.groq_requests_per_day, settings.groq_tokens_per_day, 86400),
        }

    def _prune(self, now: float) -> None:
        while self._requests and now - self._requests[0].ts > 86400:
            self._requests.popleft()

    def can_start(self, estimated_tokens: int) -> Tuple[bool, str]:
        now = time.time()
        with self._lock:
            self._prune(now)
            for name, (request_limit, token_limit, window) in self._limits().items():
                events = [event for event in self._requests if now - event.ts <= window]
                if len(events) + 1 > request_limit:
                    return False, f"groq_{name}_request_limit"
                if sum(event.tokens for event in events) + estimated_tokens > token_limit:
                    return False, f"groq_{name}_token_limit"
            self._requests.append(UsageEvent(now, estimated_tokens))
            return True, ""

    def snapshot(self) -> dict:
        now = time.time()
        with self._lock:
            self._prune(now)
            return {
                name: {
                    "requests": len([event for event in self._requests if now - event.ts <= window]),
                    "tokens": sum(event.tokens for event in self._requests if now - event.ts <= window),
                    "request_limit": request_limit,
                    "token_limit": token_limit,
                }
                for name, (request_limit, token_limit, window) in self._limits().items()
            }


_limiter = GroqRateLimiter()


def get_groq_limiter() -> GroqRateLimiter:
    return _limiter
