"""Unit-Tests für CerebrasRateLimiter."""

import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from unittest.mock import MagicMock, patch

for mod in (
    "ollama", "chromadb", "chromadb.config", "requests", "openai",
    "brain.ollama_brain", "brain.groq_brain", "brain.nvidia_brain",
    "brain.brain_pipeline", "brain.steering_api_server",
    "brain.steering_backend", "brain.deep_think", "brain.global_workspace",
    "brain.action_response", "brain.response_parser", "brain.agents",
    "brain.cerebras_brain", "life", "memory", "memory.memory_engine",
    "memory.emotions_engine", "memory.sleep_phase", "memory.forgetting_curve",
    "memory.context_files", "memory.chat_manager", "memory.short_term_memory",
    "memory.short_term_memory_v2", "memory.personality_manager",
    "memory.function_registry", "memory.intent_processor", "memory.debug_logger",
    "sentence_transformers",
):
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

from brain.cerebras_limits import CerebrasRateLimiter, UsageEvent, get_cerebras_limiter
from config.config import settings


def test_estimate_tokens_english():
    assert CerebrasRateLimiter.estimate_tokens("Hello world") == 2
    assert CerebrasRateLimiter.estimate_tokens("") == 1
    assert CerebrasRateLimiter.estimate_tokens(None) == 1


def test_estimate_tokens_german():
    text = "Hallo Benjamin, wie geht es dir heute? Schön dich zu sehen!"
    tokens = CerebrasRateLimiter.estimate_tokens(text)
    assert tokens >= 1
    assert tokens <= len(text)


def test_can_start_within_limits():
    limiter = get_cerebras_limiter()
    with patch.object(settings, "cerebras_requests_per_minute", 100):
        with patch.object(settings, "cerebras_requests_per_hour", 10000):
            with patch.object(settings, "cerebras_requests_per_day", 100000):
                with patch.object(settings, "cerebras_tokens_per_minute", 1000000):
                    with patch.object(settings, "cerebras_tokens_per_hour", 10000000):
                        with patch.object(settings, "cerebras_tokens_per_day", 100000000):
                            allowed, reason = limiter.can_start(100)
                            assert allowed is True
                            assert reason == ""


def test_snapshot_returns_expected_keys():
    limiter = get_cerebras_limiter()
    snap = limiter.snapshot()
    assert "minute" in snap
    assert "hour" in snap
    assert "day" in snap
    for window in snap.values():
        assert "requests" in window
        assert "tokens" in window
        assert "request_limit" in window
        assert "token_limit" in window


def test_limiter_is_singleton():
    a = get_cerebras_limiter()
    b = get_cerebras_limiter()
    assert a is b


def test_limits_read_from_settings():
    limiter = get_cerebras_limiter()
    original_rpm = settings.cerebras_requests_per_minute
    try:
        settings.cerebras_requests_per_minute = 42
        limits = limiter._limits()
        assert limits["minute"][0] == 42
    finally:
        settings.cerebras_requests_per_minute = original_rpm


def test_prune_removes_old_events():
    import time
    limiter = CerebrasRateLimiter()
    old_event = UsageEvent(ts=time.time() - 100000, tokens=100)
    limiter._requests.append(old_event)
    assert len(limiter._requests) == 1
    limiter._prune(time.time())
    assert len(limiter._requests) == 0


def test_can_start_exhausts_request_limit():
    import time
    limiter = CerebrasRateLimiter()
    now = time.time()
    limiter._requests.append(UsageEvent(ts=now, tokens=10))

    with patch.object(settings, "cerebras_requests_per_minute", 0):
        with patch.object(settings, "cerebras_requests_per_hour", 10000):
            with patch.object(settings, "cerebras_requests_per_day", 100000):
                with patch.object(settings, "cerebras_tokens_per_minute", 1000000):
                    with patch.object(settings, "cerebras_tokens_per_hour", 10000000):
                        with patch.object(settings, "cerebras_tokens_per_day", 100000000):
                            allowed, reason = limiter.can_start(10)
                            assert allowed is False
                            assert "request_limit" in reason


if __name__ == "__main__":
    tests = [
        test_estimate_tokens_english,
        test_estimate_tokens_german,
        test_can_start_within_limits,
        test_snapshot_returns_expected_keys,
        test_limiter_is_singleton,
        test_limits_read_from_settings,
        test_prune_removes_old_events,
        test_can_start_exhausts_request_limit,
    ]
    passed = 0
    for test in tests:
        try:
            test()
            print(f"  [OK] {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
    print(f"\n{passed}/{len(tests)} tests passed")
