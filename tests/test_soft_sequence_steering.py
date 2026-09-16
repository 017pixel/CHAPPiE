"""Actual logit transformations, bounds and conditional phrase behavior."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import torch
from brain.steering.sequence_processor import SoftSequenceLogitsProcessor


class Tokenizer:
    all_special_ids = [0, 9]
    eos_token_id = 9

    def encode(self, text, **kwargs):
        return {"word": [2], "pair": [3, 4], "eos": [9]}[text.strip()]


def processor(**overrides):
    spec = {
        "concept": "test",
        "start_token": 0,
        "end_token": 3,
        "max_logit_bias": 1.0,
        "token_candidates": [{"text": "word", "weight": 1}],
        "phrase_candidates": [{"text": "pair", "weight": 0.5}],
    }
    spec.update(overrides)
    return SoftSequenceLogitsProcessor([spec], Tokenizer(), 2, [9])


def test_free_generation_and_window():
    proc = processor()
    logits = torch.zeros(1, 10)
    logits[0, 8] = 100
    original = logits.clone()
    first = proc(torch.tensor([[5, 5]]), logits)
    assert first[0, 2] == 1
    assert first[0, 3] == 0  # A phrase must be started by the model.
    assert first.argmax() == 8  # Candidate is a suggestion.
    assert first[0, 9] == logits[0, 9]
    assert torch.equal(logits, original)
    later = proc(torch.tensor([[5, 5, 1]]), logits)
    assert 0 < later[0, 2] < first[0, 2]
    expired = proc(torch.tensor([[5, 5, 1, 1, 1]]), logits)
    assert torch.equal(expired, logits)


def test_phrase_and_special_tokens():
    proc = processor(token_candidates=[{"text": "eos", "weight": 1}])
    logits = torch.zeros(1, 10)
    continuation = proc(torch.tensor([[5, 5, 3]]), logits)
    assert continuation[0, 4] > 0
    assert continuation[0, 9] == 0
    # Prompt suffix alone must not trigger a continuation.
    untouched = proc(torch.tensor([[5, 3]]), logits)
    assert torch.equal(untouched, logits)


def test_invalid_configuration_and_batch():
    for spec in (
        {"end_token": 0},
        {"max_logit_bias": float("nan")},
        {"decay": "unknown"},
        {"token_candidates": [{"text": "word", "weight": -1}]},
    ):
        try:
            processor(**spec)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Invalid spec accepted: {spec}")
    proc = processor(max_logit_bias=900)
    actual = proc(torch.tensor([[5, 5], [6, 6]]), torch.zeros(2, 10))
    assert actual.max() <= 1.5
    assert actual[0, 2] == actual[1, 2]


if __name__ == "__main__":
    test_free_generation_and_window()
    test_phrase_and_special_tokens()
    test_invalid_configuration_and_batch()
    print("Soft sequence contracts passed")
