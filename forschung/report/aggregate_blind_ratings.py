#!/usr/bin/env python3
"""Validate and aggregate two or more independent blinded rating files."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ratings", nargs="+", type=Path)
    parser.add_argument("--blind-key", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    if len(args.ratings) < 2:
        raise SystemExit("Mindestens zwei unabhaengige Ratingdateien sind erforderlich")
    payloads = [read(path) for path in args.ratings]
    rater_ids = [str(payload.get("rater_id") or "") for payload in payloads]
    if any(not value or value == "EINDEUTIGE-BEWERTER-ID" for value in rater_ids) or len(set(rater_ids)) != len(rater_ids):
        raise SystemExit("Jede Ratingdatei braucht eine eindeutige rater_id")
    if not all(payload.get("independent") is True for payload in payloads):
        raise SystemExit("Alle Bewerter muessen independent=true bestaetigen")

    blind_key = read(args.blind_key)
    seed_ids = {payload.get("blinding_seed_id") for payload in payloads}
    if seed_ids != {blind_key.get("blinding_seed_id")}:
        raise SystemExit("Ratingdateien und Blindschluessel gehoeren nicht zusammen")

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for payload in payloads:
        for rating in payload.get("ratings", []):
            key = (str(rating.get("item_id")), str(rating.get("answer_code")))
            if key[0] not in blind_key.get("items", {}) or key[1] not in blind_key["items"][key[0]]:
                raise SystemExit(f"Unbekannter Blindrating-Schluessel: {key}")
            grouped[key].append(rating)

    items = []
    agreements = []
    for (item_id, answer_code), ratings in sorted(grouped.items()):
        if len(ratings) != len(payloads):
            raise SystemExit(f"Unvollstaendige Ratings fuer {item_id}/{answer_code}")
        scores = [int(rating["quality_1_to_5"]) for rating in ratings]
        if any(score < 1 or score > 5 for score in scores):
            raise SystemExit(f"Ungueltiger quality_1_to_5 Score fuer {item_id}/{answer_code}")
        mean = statistics.fmean(scores)
        stddev = statistics.stdev(scores) if len(scores) >= 2 else 0.0
        margin = 1.96 * stddev / math.sqrt(len(scores)) if len(scores) >= 2 else 0.0
        pair_agreement = sum(1 for i in range(len(scores)) for j in range(i + 1, len(scores)) if scores[i] == scores[j])
        pair_total = len(scores) * (len(scores) - 1) // 2
        agreements.append(pair_agreement / pair_total if pair_total else 1.0)
        items.append({
            "item_id": item_id,
            "answer_code": answer_code,
            "model": blind_key["items"][item_id][answer_code],
            "ratings_n": len(scores),
            "quality_mean": round(mean, 4),
            "quality_variance": round(statistics.variance(scores), 4) if len(scores) >= 2 else None,
            "quality_ci95": [round(mean - margin, 4), round(mean + margin, 4)],
            "exact_pairwise_agreement": round(agreements[-1], 4),
        })

    output = {
        "schema_version": 1,
        "rater_count": len(payloads),
        "rater_ids": rater_ids,
        "blind_key_opened_after_rating": True,
        "mean_exact_pairwise_agreement": round(statistics.fmean(agreements), 4) if agreements else None,
        "items": items,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "raters": len(payloads), "items": len(items)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
