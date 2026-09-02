"""Regression tests for measured answer throughput."""

import os
import sys
from unittest.mock import MagicMock

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

for module_name in (
    "chromadb",
    "chromadb.config",
    "ollama",
    "openai",
    "sentence_transformers",
):
    sys.modules.setdefault(module_name, MagicMock())

from web_infrastructure.backend_wrapper import calculate_generation_timing  # noqa: E402


def test_buffered_provider_chunk_uses_complete_generation_window():
    timing = calculate_generation_timing(
        total_gen_ms=14010,
        answer_tokens=65,
        reasoning_tokens=120,
        ttft_ms=14000,
    )

    assert timing["answer_time_ms"] == 10
    assert timing["rate_duration_ms"] == 14010
    assert timing["tokens_per_second"] == 4.6
    assert timing["rate_basis"] == "answer_tokens_over_total_generation"


def test_regular_stream_rate_stays_based_on_measured_total_time():
    timing = calculate_generation_timing(5000, answer_tokens=100, ttft_ms=500)

    assert timing["ttft_ms"] == 500
    assert timing["answer_time_ms"] == 4500
    assert timing["tokens_per_second"] == 20.0


def test_empty_answer_has_zero_rate():
    timing = calculate_generation_timing(14000, answer_tokens=0, ttft_ms=14000)

    assert timing["rate_duration_ms"] == 0
    assert timing["tokens_per_second"] == 0.0


if __name__ == "__main__":
    test_buffered_provider_chunk_uses_complete_generation_window()
    test_regular_stream_rate_stays_based_on_measured_total_time()
    test_empty_answer_has_zero_rate()
    print("OK: generation timing uses the complete measured window")
