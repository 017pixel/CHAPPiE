"""Bounded lexical logit bias, with conditional phrase continuation."""

from __future__ import annotations

import math
from typing import Any

import torch
from transformers import LogitsProcessor


class SoftSequenceLogitsProcessor(LogitsProcessor):
    def __init__(
        self,
        specs: list[dict[str, Any]],
        tokenizer: Any,
        prompt_length: int,
        eos_token_ids: list[int],
        bias_cap: float = 1.5,
    ):
        self.prompt_length = prompt_length
        self.forbidden = set(eos_token_ids) | set(
            getattr(tokenizer, "all_special_ids", [])
        )
        self.specs = []
        self.telemetry = {
            "processor_count": 1,
            "invocations": 0,
            "biased_steps": 0,
            "max_applied_bias": 0.0,
            "eos_biased": False,
            "concepts": [],
        }
        for spec in specs:
            start, end = int(spec.get("start_token", 0)), int(spec.get("end_token", 24))
            bias = float(spec.get("max_logit_bias", 1.5))
            decay = spec.get("decay", "exponential")
            if not 0 <= start < end <= 256 or not math.isfinite(bias) or bias < 0:
                raise ValueError("Invalid soft sequence window or bias")
            if decay not in ("exponential", "linear", "constant"):
                raise ValueError("Unknown soft sequence decay")
            candidates = []
            for key in ("token_candidates", "phrase_candidates"):
                for candidate in spec.get(key, []):
                    text = str(candidate.get("text", "")).strip()
                    weight = float(candidate.get("weight", 1.0))
                    if not math.isfinite(weight) or not 0 <= weight <= 1:
                        raise ValueError(
                            "Candidate weight must be finite and between zero and one"
                        )
                    if not text or len(text.split()) > 4:
                        raise ValueError(
                            "Soft candidates must be short words or phrases"
                        )
                    # Both word-boundary tokenizations; never bias special IDs.
                    for prefix in ("", " "):
                        ids = tokenizer.encode(prefix + text, add_special_tokens=False)
                        if (
                            not ids
                            or len(ids) > 12
                            or any(i in self.forbidden for i in ids)
                        ):
                            continue
                        entry = (tuple(ids), weight, key == "phrase_candidates")
                        if entry not in candidates:
                            candidates.append(entry)
            self.specs.append((start, end, min(bias_cap, bias), decay, candidates))
            self.telemetry["concepts"].append(
                {
                    "concept": spec.get("concept"),
                    "start_token": start,
                    "end_token": end,
                    "max_logit_bias": min(bias_cap, bias),
                    "decay": decay,
                }
            )
        self.bias_cap = bias_cap

    def __call__(
        self, input_ids: torch.LongTensor, scores: torch.FloatTensor
    ) -> torch.FloatTensor:
        self.telemetry["invocations"] += 1
        step = input_ids.shape[-1] - self.prompt_length
        if not any(start <= step < end for start, end, *_ in self.specs):
            return scores
        result = scores.clone()
        changed = False
        for batch in range(input_ids.shape[0]):
            generated = input_ids[batch, self.prompt_length :].tolist()
            biases: dict[int, float] = {}
            for start, end, bias, decay, candidates in self.specs:
                if not start <= step < end:
                    continue
                fraction = (step - start) / (end - start)
                scale = (
                    math.exp(-3 * fraction)
                    if decay == "exponential"
                    else 1 - fraction
                    if decay == "linear"
                    else 1
                )
                for ids, weight, conditional in candidates:
                    token = None if conditional else ids[0]
                    for length in range(min(len(ids) - 1, len(generated)), 0, -1):
                        if tuple(generated[-length:]) == ids[:length]:
                            token = ids[length]
                            break
                    if (
                        token is not None
                        and token not in self.forbidden
                        and 0 <= token < scores.shape[-1]
                    ):
                        # Overlapping concepts cannot multiply the maximum bias.
                        biases[token] = max(
                            biases.get(token, 0.0), bias * weight * scale
                        )
            for token, amount in biases.items():
                if amount > 0:
                    result[batch, token] += min(self.bias_cap, amount)
                    changed = True
                    self.telemetry["max_applied_bias"] = max(
                        self.telemetry["max_applied_bias"], min(self.bias_cap, amount)
                    )
        if changed:
            self.telemetry["biased_steps"] += 1
        return result
