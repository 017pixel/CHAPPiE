"""Conservative, explicit v17 acceptance gates over recorded evidence.

Blind emotion ratings remain observations. A constant LOW/MEDIUM/HIGH output
never counts as state transfer, even though it is weakly monotonic. Missing
triples stay in the denominator; OFF is reported as the negative control.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

from forschung.steering_v17.evaluate import evaluate_rows, response_text

LEVELS = ("low", "medium", "high")


def context_preparation_upper_bound(timing):
    """Conservative remainder of disjoint synchronous runtime phases.

    Retrieval, context assembly, token budget, steering preparation and persistence
    remain included. Missing optional phase measurements are not subtracted.
    The current runtime executes the four excluded phases sequentially.
    """
    total = timing.get("total_ms")
    generation = timing.get("generation_ms")
    if any(type(value) not in (int, float) or not math.isfinite(value) or value < 0 for value in (total, generation)):
        return None
    excluded = []
    for name in ("intent_ms", "emotion_appraisal_ms", "generation_ms", "formatting_ms"):
        value = timing.get(name, 0)
        if value is None:
            value = 0
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            return None
        excluded.append(value)
    remainder = total - sum(excluded)
    if remainder < -.005:
        return None  # Invalid or overlapping spans cannot establish a gate.
    return max(0, remainder + .005)  # Cover rounding of five millisecond fields.


def neutral_answer_correct(text, expected):
    """True/False for covered tasks; None for prose needing semantic review."""
    if expected is None:
        return None
    clean = text.strip()
    expected = str(expected)
    if expected == "json:7":
        try:
            value = json.loads(clean)
        except (ValueError, TypeError):
            return False
        return isinstance(value, dict) and type(value.get("zahl")) is int and value["zahl"] == 7
    if expected == "blau":
        return clean.casefold() == "blau"
    if expected == "2, 5, 9":
        return bool(re.fullmatch(r"\[?\s*2\s*[,;]\s*5\s*[,;]\s*9\s*\]?", clean.strip(" .")))
    if expected == "H2O":
        clean = clean.replace("₂", "2")
    # Anchor the entire answer. Mentioning the right number inside a correction
    # or a negated answer is not evidence of task correctness.
    clean = clean.strip(" .!\n\t").replace("**", "")
    forms = {
        "Paris": r"(?:Die Hauptstadt (?:von )?Frankreichs? ist )?Paris",
        "H2O": r"(?:(?:Die chemische Formel von Wasser|Wasser) ist )?H2O",
        "3": r"(?:(?:Ein Dreieck hat|Es sind) )?(?:3|drei)(?: Seiten)?",
        "60": r"(?:(?:Eine Stunde hat|Es sind) )?60(?: Minuten)?",
        "Sonne": r"(?:Die Erde kreist um die )?Sonne",
    }
    pattern = forms.get(expected, r"(?:(?:Das Ergebnis|Die Antwort) (?:ist|lautet) )?" + re.escape(expected))
    if re.fullmatch(pattern, clean, re.I):
        return True
    if re.fullmatch(r"[-+]?\d+(?:[.,]\d+)?", clean):
        return False
    # Unrecognized explanations and contradictions are not silently scored as
    # wrong facts. They require semantic adjudication and block the quality gate.
    return None


def valid_rating(entry, axis):
    if "error" in entry:
        return None
    value = entry.get("rating", {}).get(axis)
    return value if type(value) is int and 0 <= value <= 4 else None


def controlled_transfer(rows, ratings, expected_rows=None):
    groups = {}
    for row in expected_rows or []:
        if row.get("control_group") and row.get("control_level") in LEVELS:
            key = (row.get("mode"), row.get("seed"), row["control_group"], row["control_axis"])
            groups.setdefault(key, {})
    for row in rows:
        if not row.get("control_group") or row.get("control_level") not in LEVELS:
            continue
        key = (row.get("mode"), row.get("seed"), row["control_group"], row["control_axis"])
        groups.setdefault(key, {})[row["control_level"]] = row
    results = {}
    details = []
    for (mode, seed, group, axis), levels in groups.items():
        scores = []
        for level in LEVELS:
            row = levels.get(level, {})
            entry = ratings.get(row.get("response", {}).get("id"), {})
            scores.append(None if not row or "error" in row else valid_rating(entry, axis))
        complete = all(score is not None for score in scores)
        increasing = complete and scores[0] <= scores[1] <= scores[2] and scores[0] < scores[2]
        counters = results.setdefault(mode, {"expected_triples": 0, "rated_triples": 0,
                                            "increasing_triples": 0, "flat_triples": 0})
        counters["expected_triples"] += 1
        counters["rated_triples"] += int(complete)
        counters["increasing_triples"] += int(increasing)
        counters["flat_triples"] += int(complete and len(set(scores)) == 1)
        details.append({"mode": mode, "seed": seed, "group": group, "axis": axis,
                        "scores_low_medium_high": scores, "increasing": increasing})
    for mode, result in results.items():
        result["increasing_rate"] = result["increasing_triples"] / result["expected_triples"]
        result["coverage"] = result["rated_triples"] / result["expected_triples"]
        result["passes_80_percent"] = (result["coverage"] == 1 and result["increasing_rate"] >= .8) if expected_rows is not None else None
    return {"method": "blind_perceived_axis_low_le_medium_le_high_and_low_lt_high",
            "independent_human_rating": False, "planned_matrix_available": expected_rows is not None, "groups": results, "triples": details}


def quality_controls(rows):
    latest = {(r.get("case_id"), r.get("mode"), r.get("seed")): r for r in rows}
    groups = {}
    for row in latest.values():
        mode = row.get("mode", "unknown")
        counts = groups.setdefault(mode, {"neutral_expected": 0, "neutral_correct": 0, "neutral_unresolved": 0,
                                          "termination_observed": 0, "natural_eos": 0,
                                          "length_limited": 0, "short_natural_eos": 0})
        if row.get("category") == "neutral_control" and row.get("expected_answer") is not None:
            counts["neutral_expected"] += 1
            correctness = False if "error" in row else neutral_answer_correct(response_text(row), row["expected_answer"])
            counts["neutral_correct"] += int(correctness is True)
            counts["neutral_unresolved"] += int(correctness is None)
        generation = row.get("response", {}).get("generation", {})
        if type(generation.get("natural_eos")) is bool:
            counts["termination_observed"] += 1
            counts["natural_eos"] += int(generation["natural_eos"])
            tokens = row.get("response", {}).get("usage", {}).get("completion_tokens")
            counts["short_natural_eos"] += int(generation["natural_eos"] and isinstance(tokens, int) and tokens < 12)
            counts["length_limited"] += int(any(c.get("finish_reason") == "length" for c in row.get("response", {}).get("choices", [])))
    for counts in groups.values():
        expected = counts["neutral_expected"]
        counts["neutral_accuracy_lower_bound"] = counts["neutral_correct"] / expected if expected else None
        counts["neutral_accuracy_upper_bound"] = (counts["neutral_correct"] + counts["neutral_unresolved"]) / expected if expected else None
        counts["neutral_oracle_coverage"] = 1 - counts["neutral_unresolved"] / expected if expected else None
        counts["neutral_accuracy"] = counts["neutral_accuracy_lower_bound"] if counts["neutral_unresolved"] == 0 else None
    off = groups.get("off", {}).get("neutral_accuracy")
    for counts in groups.values():
        score = counts["neutral_accuracy"]
        counts["neutral_accuracy_loss_vs_off"] = off - score if off is not None and score is not None else None
        counts["neutral_quality_passes_10pp"] = counts["neutral_accuracy_loss_vs_off"] <= .1 if counts["neutral_accuracy_loss_vs_off"] is not None else None
    return groups


def assess(rows, ratings, expected_generations=None, *, cases=None, modes=None, seeds=None):
    metrics = evaluate_rows(rows)
    expected_rows = [{**case, "case_id": case["id"], "mode": mode, "seed": seed}
                     for case in cases for mode in modes for seed in seeds] if cases and modes and seeds else None
    transfer = controlled_transfer(rows, ratings, expected_rows)
    quality = quality_controls(rows)
    recorded = sum(group["attempted_cases"] for group in metrics["groups"].values())
    actual_keys = {(row.get("case_id"), row.get("mode"), row.get("seed")) for row in rows}
    expected_keys = {(row["case_id"], row["mode"], row["seed"]) for row in expected_rows} if expected_rows else None
    full = expected_keys is not None and actual_keys == expected_keys
    if expected_generations is not None:
        full = full and recorded == expected_generations
    gates = {}
    for mode, group in metrics["groups"].items():
        gates[mode] = {
            "complete_generation_capture": full and group["generation_error_rate"] == 0,
            "emotional_duplicate_rate_below_10_percent": group["exact_duplicate_excess_rate"] < .1,
            "controlled_transfer": transfer["groups"].get(mode, {}).get("passes_80_percent"),
            "neutral_quality": full and quality.get(mode, {}).get("neutral_quality_passes_10pp"),
        }
    return {"schema_version": 1, "expected_generations": expected_generations,
            "recorded_generations": recorded, "planned_matrix_available": expected_rows is not None, "metrics": metrics, "quality_controls": quality,
            "controlled_transfer": transfer, "gates": gates,
            "production_acceptance": False,
            "remaining_manual_gates": ["systematic_early_eos_review", "runtime_memory_and_latency", "full_suite_and_controlled_suite_joint_review"],
            "note": "HTTP success and lexical diagnostics do not establish semantic transfer. SLT requires explicit five-dimension ratings; perceived-axis ratings alone are not SLT."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--expected", type=int)
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--rating-file", default="blind_ratings_v2.jsonl")
    args = parser.parse_args()
    path = args.run / "generations.jsonl"
    rows = list(map(json.loads, path.read_text().splitlines()))
    if Path(args.rating_file).name != args.rating_file:
        raise ValueError("Rating filename must be a basename")
    rating_path = args.run / args.rating_file
    ratings = {r["response_id"]: r for r in map(json.loads, rating_path.read_text().splitlines())} if rating_path.exists() else {}
    manifest = json.loads((args.run / "manifest.json").read_text())
    dataset = args.dataset or (Path(manifest["dataset_path"]) if manifest.get("dataset_path") else None)
    if dataset and hashlib.sha256(dataset.read_bytes()).hexdigest() != manifest["dataset_hash"]:
        raise ValueError("Evaluation dataset differs from run manifest")
    cases = list(map(json.loads, dataset.read_text().splitlines())) if dataset else None
    result = assess(rows, ratings, args.expected, cases=cases, modes=manifest.get("modes"), seeds=manifest.get("seeds"))
    result["generations_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    result["rating_file"] = args.rating_file
    result["ratings_sha256"] = hashlib.sha256(rating_path.read_bytes()).hexdigest() if rating_path.exists() else None
    (args.run / "acceptance.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["gates"], indent=2))
