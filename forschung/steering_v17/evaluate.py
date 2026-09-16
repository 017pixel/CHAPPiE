"""Deterministic research metrics; semantic SLT requires explicit blind ratings.

Lexical proxies are diagnostics and never represented as validated semantic SLT.
"""

from __future__ import annotations
import argparse
from collections import Counter
import json
import re
from pathlib import Path

import numpy as np

from brain.steering.sequence_controller import LEXICON


def response_text(row: dict) -> str:
    response = row.get("response", {})
    choices = response.get("choices", [])
    return (
        str(choices[0].get("message", {}).get("content", "") or "")
        if choices
        else str(response.get("text", ""))
    )


def lexical_diagnostics(text: str) -> dict:
    words = re.findall(r"\w+", text.casefold())
    ngrams = [tuple(words[i : i + 3]) for i in range(max(0, len(words) - 2))]
    scores = {
        emotion: sum(word in text.casefold() for word in candidates)
        / max(1, len(candidates))
        for emotion, candidates in LEXICON.items()
    }
    return {
        "word_count": len(words),
        "trigram_repetition": 1 - len(set(ngrams)) / max(1, len(ngrams))
        if ngrams
        else 0.0,
        "lexical_emotions": scores,
        "generic_assistant": any(
            phrase in text.casefold()
            for phrase in (
                "ich bin hier, um dir zu helfen",
                "ihre bedürfnisse",
                "bestmögliche unterstützung",
                "wie kann ich dir",
                "als unterstützendes instrument",
            )
        ),
    }


def slt_from_rating(rating: dict) -> float:
    dimensions = (
        "emotion_direction",
        "emotion_intensity",
        "behavioral_expression",
        "content_preservation",
        "naturalness",
    )
    values = [float(rating[key]) for key in dimensions]
    if not all(np.isfinite(value) and 0 <= value <= 4 for value in values):
        raise ValueError("Blind rating dimensions must be finite in [0,4]")
    return float(np.mean(values) / 4)


def evaluate_rows(rows: list[dict], ratings: dict | None = None) -> dict:
    if any("layers" in row and "strength" in row for row in rows):
        raise ValueError("Layer sweep rows require rank_layers; generic evaluation would merge configurations")
    latest = {}
    for index, row in enumerate(rows):
        key = (
            str(row.get("case_id", row.get("prompt_id", index))),
            row.get("mode", row.get("condition")),
            row.get("seed"),
            json.dumps(row.get("state", {}), sort_keys=True),
        )
        latest[key] = row
    groups = {}
    for row in latest.values():
        groups.setdefault(row.get("mode", row.get("condition", "unknown")), []).append(
            row
        )
    result = {
        "rating_method": "provided_blind_ratings" if ratings else "none",
        "semantic_slt_available": False,
        "groups": {},
    }
    for mode, group in groups.items():
        valid = [row for row in group if "error" not in row]
        texts = [response_text(row).strip() for row in valid]
        emotional = [
            response_text(row).strip()
            for row in valid
            if row.get("category") != "neutral_control"
        ]
        duplicates = Counter(emotional)
        prefixes = Counter(
            " ".join(re.findall(r"\w+", text.casefold())[:7]) for text in emotional
        )
        latencies = [row["elapsed_ms"] for row in valid]
        scores = [lexical_diagnostics(text) for text in texts]
        tokens = [
            int(row.get("response", {}).get("usage", {}).get("completion_tokens", 0))
            for row in valid
        ]
        slt = []
        for row in valid:
            key = f"{row.get('case_id')}:{mode}:{row.get('seed')}"
            if ratings and key in ratings:
                slt.append(slt_from_rating(ratings[key]))
        result["groups"][mode] = {
            "attempted_cases": len(group),
            "successful_cases": len(valid),
            "generation_error_rate": (len(group) - len(valid)) / len(group),
            "empty_output_rate": sum(not text for text in texts) / max(1, len(texts)),
            "exact_duplicate_excess_rate": sum(
                count - 1 for count in duplicates.values()
            )
            / max(1, len(emotional)),
            "most_common_seven_word_prefix_rate": max(prefixes.values(), default=0)
            / max(1, len(emotional)),
            "mean_trigram_repetition": float(
                np.mean([s["trigram_repetition"] for s in scores])
            )
            if scores
            else None,
            "generic_assistant_rate": sum(s["generic_assistant"] for s in scores)
            / max(1, len(scores)),
            "mean_completion_tokens": float(np.mean(tokens)) if tokens else None,
            "short_output_under_12_tokens_rate": sum(n < 12 for n in tokens)
            / max(1, len(tokens)),
            "latency_p50_ms": float(np.percentile(latencies, 50))
            if latencies
            else None,
            "latency_p95_ms": float(np.percentile(latencies, 95))
            if latencies
            else None,
            "slt_score": float(np.mean(slt)) if slt else None,
            "blind_rated_count": len(slt),
        }
    result["semantic_slt_available"] = any(group["blind_rated_count"] > 0 for group in result["groups"].values())
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--ratings", type=Path)
    args = parser.parse_args()
    rows = [
        json.loads(line)
        for line in (args.run / "generations.jsonl").read_text().splitlines()
    ]
    ratings = json.loads(args.ratings.read_text()) if args.ratings else None
    metrics = evaluate_rows(rows, ratings)
    (args.run / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))
