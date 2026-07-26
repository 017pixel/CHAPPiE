#!/usr/bin/env python3
"""Erzeugt reproduzierbare Benchmark-Aggregate aus CHAPPiE-Forschungssessions.

Das Skript verändert keine Session-Logs. Es schreibt ein JSON-Aggregat und eine
flache CSV-Datei in den Report-Workspace. Sessions werden explizit als Argumente
angegeben, damit fehlgeschlagene oder historische Läufe nicht versehentlich in
den Modellvergleich geraten.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from forschung.session_logger import evaluate_response_quality

SESSION_ROOT = PROJECT_ROOT / "forschung" / "session_logs"
DEFAULT_OUTPUT = PROJECT_ROOT / "forschung" / "report" / "workspace" / "benchmark-data.json"
DEFAULT_CSV = PROJECT_ROOT / "forschung" / "report" / "workspace" / "benchmark-questions.csv"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def rounded(value: float | None, digits: int = 2) -> float | None:
    return None if value is None else round(value, digits)


def words(text: str) -> int:
    return len((text or "").split())


def flatten_question(path: Path, config: dict[str, Any]) -> dict[str, Any]:
    entry = load_json(path)
    response = entry.get("response") or {}
    setup_results = entry.get("setup_results") or []
    setup_qualities = [
        evaluate_response_quality(
            item,
            question_text=item.get("prompt", ""),
            category_name=entry.get("category", ""),
            enable_thinking=config.get("enable_thinking"),
        )
        for item in setup_results
    ]
    setup_failed = bool(
        entry.get("setup_failed")
        or any(item.get("_error") for item in setup_results)
        or any(item.get("quality_failed") for item in setup_qualities)
    )
    quality = evaluate_response_quality(
        response,
        question_text=entry.get("question_text", ""),
        category_name=entry.get("category", ""),
        setup_failed=setup_failed,
        enable_thinking=config.get("enable_thinking"),
    ) if response else {}
    timing = response.get("timing") or {}
    context = response.get("context_budget") or {}
    steering = response.get("emotion_steering") or {}
    memory_trace = response.get("memory_trace") or {}
    merged_memory = memory_trace.get("merged") or memory_trace.get("seed") or {}
    answer = str(response.get("formatted_answer") or response.get("response_text") or "")
    hard_error = bool(entry.get("_error"))
    quality_failed = bool(quality.get("quality_failed", False))
    valid = bool(response) and not hard_error and not setup_failed and not quality_failed
    content_reviewable = bool(response) and not any((
        hard_error,
        setup_failed,
        quality.get("generation_failed"),
        quality.get("formatting_failed"),
        quality.get("short_answer"),
        quality.get("punctuation_or_emoji_only"),
        quality.get("contains_joined_text_warning"),
        quality.get("cot_leak"),
        quality.get("instruction_leak"),
        quality.get("memory_error_contamination"),
    ))
    emotions_before = entry.get("emotions_before") or {}
    emotions_after = entry.get("emotions_after") or {}
    emotion_l1_delta = sum(
        abs(float(emotions_after.get(name, before)) - float(before))
        for name, before in emotions_before.items()
        if isinstance(before, (int, float))
    )
    active_vectors = steering.get("active_vectors") or []
    total_gen_ms = float(timing.get("total_gen_ms") or 0)
    total_tokens = int(timing.get("total_tokens") or 0)
    return {
        "session_id": config.get("session_id"),
        "run_label": config.get("run_label", ""),
        "provider": config.get("llm_provider") or config.get("provider") or "unknown",
        "model": config.get("model") or "unknown",
        "iteration": entry.get("iteration"),
        "seed": entry.get("seed"),
        "category_id": entry.get("category_id"),
        "category": entry.get("category", ""),
        "question_number": entry.get("question_number"),
        "question_text": entry.get("question_text", ""),
        "commands_before": entry.get("commands_before") or [],
        "emotions_before": emotions_before,
        "emotions_after": emotions_after,
        "answer": answer,
        "answer_chars": len(answer.strip()),
        "answer_words": words(answer),
        "duration_ms": float(entry.get("duration_ms") or 0),
        "processing_time_ms": float(response.get("processing_time_ms") or 0),
        "ttft_ms": float(timing.get("ttft_ms") or 0),
        "total_gen_ms": total_gen_ms,
        "total_tokens": total_tokens,
        "tokens_per_s": (total_tokens * 1000 / total_gen_ms) if total_gen_ms > 0 else 0,
        "answer_tokens": int(timing.get("answer_tokens") or 0),
        "reasoning_tokens": int(timing.get("reasoning_tokens") or 0),
        "context_tokens": int(context.get("trimmed_tokens") or context.get("estimated_tokens") or 0),
        "context_trimmed": bool(context.get("was_trimmed")),
        "memory_count": int(merged_memory.get("memories_found") or 0),
        "memory_top_relevance": float(merged_memory.get("top_relevance") or 0),
        "memory_used": int(merged_memory.get("memories_found") or 0) > 0,
        "emotion_l1_delta": emotion_l1_delta,
        "steering_mode": steering.get("mode", "unknown"),
        "steering_active": bool(steering.get("steering_active")),
        "prompt_emotions_enabled": bool(steering.get("prompt_emotions_enabled")),
        "dominant_vector": steering.get("dominant_vector", ""),
        "dominant_strength": float(steering.get("dominant_strength") or 0),
        "active_vector_count": len(active_vectors),
        "active_vector_layers": sorted({
            tuple(vector.get("layer_range") or [])
            for vector in active_vectors
            if len(vector.get("layer_range") or []) == 2
        }),
        "auto_sleep_triggered": bool(response.get("auto_sleep_triggered")),
        "hard_error": hard_error,
        "valid": valid,
        "content_reviewable": content_reviewable,
        "generation_failed": bool(quality.get("generation_failed", False)),
        "formatting_failed": bool(quality.get("formatting_failed", False)),
        "quality_failed": quality_failed,
        "context_budget_failed": bool(quality.get("context_budget_failed", False)),
        "setup_failed": setup_failed,
        "cot_leak": bool(quality.get("cot_leak", False)),
        "instruction_leak": bool(quality.get("instruction_leak", False)),
        "memory_error_contamination": bool(quality.get("memory_error_contamination", False)),
        "content_relevance_warning": bool(quality.get("content_relevance_warning", False)),
        "safety_evaluation_unusable": bool(quality.get("safety_evaluation_unusable", False)),
        "source_file": str(path.relative_to(PROJECT_ROOT)),
        "has_response": bool(response),
    }


def numeric_stats(rows: list[dict[str, Any]], field: str) -> dict[str, float | None]:
    include_zero = field.endswith("_rate")
    values = [
        float(row[field])
        for row in rows
        if isinstance(row.get(field), (int, float))
        and (include_zero or float(row[field]) > 0)
    ]
    mean = statistics.fmean(values) if values else None
    variance = statistics.variance(values) if len(values) >= 2 else None
    stddev = statistics.stdev(values) if len(values) >= 2 else None
    margin = (1.96 * stddev / math.sqrt(len(values))) if stddev is not None else None
    return {
        "n": len(values),
        "mean": rounded(mean),
        "median": rounded(statistics.median(values)) if values else None,
        "p95": rounded(percentile(values, 0.95)),
        "min": rounded(min(values)) if values else None,
        "max": rounded(max(values)) if values else None,
        "variance": rounded(variance, 4),
        "stddev": rounded(stddev, 4),
        "ci95": [rounded(mean - margin, 4), rounded(mean + margin, 4)] if mean is not None and margin is not None else None,
    }


def seed_statistics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_seed: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("seed") is not None:
            by_seed[int(row["seed"])].append(row)
    seed_rows = []
    for seed, items in sorted(by_seed.items()):
        seed_rows.append({
            "seed": seed,
            "questions": len(items),
            "valid_rate": sum(bool(item.get("valid")) for item in items) / len(items),
            "content_reviewable_rate": sum(bool(item.get("content_reviewable")) for item in items) / len(items),
            "mean_duration_ms": statistics.fmean(float(item.get("duration_ms") or 0) for item in items),
        })
    def metric(name: str) -> dict[str, Any]:
        pseudo_rows = [{name: item[name]} for item in seed_rows]
        return numeric_stats(pseudo_rows, name)
    return {
        "replicates": len(seed_rows),
        "seeds": [item["seed"] for item in seed_rows],
        "per_seed": seed_rows,
        "valid_rate": metric("valid_rate"),
        "content_reviewable_rate": metric("content_reviewable_rate"),
        "mean_duration_ms": metric("mean_duration_ms"),
    }


def exact_mcnemar_p(discordant_a: int, discordant_b: int) -> float:
    """Two-sided exact binomial McNemar p-value for paired binary outcomes."""
    n = int(discordant_a) + int(discordant_b)
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(0, min(discordant_a, discordant_b) + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


def paired_significance(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_model: dict[str, dict[tuple[Any, Any, Any], dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        key = (row.get("seed"), row.get("category_id"), row.get("question_number"))
        by_model[str(row.get("model"))][key] = row
    models = sorted(by_model)
    results = []
    for left_index, left in enumerate(models):
        for right in models[left_index + 1:]:
            common = sorted(set(by_model[left]) & set(by_model[right]))
            left_only = sum(bool(by_model[left][key].get("valid")) and not bool(by_model[right][key].get("valid")) for key in common)
            right_only = sum(bool(by_model[right][key].get("valid")) and not bool(by_model[left][key].get("valid")) for key in common)
            results.append({
                "model_a": left,
                "model_b": right,
                "paired_questions": len(common),
                "metric": "strict_valid",
                "test": "exact_mcnemar",
                "a_valid_b_invalid": left_only,
                "a_invalid_b_valid": right_only,
                "p_value_two_sided": round(exact_mcnemar_p(left_only, right_only), 6),
                "significant_at_0_05": exact_mcnemar_p(left_only, right_only) < 0.05,
            })
    return results


def aggregate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    flags = [
        "hard_error", "generation_failed", "formatting_failed", "quality_failed",
        "context_budget_failed", "setup_failed", "cot_leak", "instruction_leak",
        "memory_error_contamination", "content_relevance_warning",
        "safety_evaluation_unusable", "context_trimmed", "auto_sleep_triggered",
    ]
    counts = {flag: sum(bool(row.get(flag)) for row in rows) for flag in flags}
    steering_modes = Counter(str(row.get("steering_mode") or "unknown") for row in rows)
    layer_ranges = Counter(
        str(layer_range)
        for row in rows
        for layer_range in row.get("active_vector_layers") or []
    )
    return {
        "questions": len(rows),
        "completed": sum(row["has_response"] and not row["hard_error"] for row in rows),
        "valid": sum(row["valid"] for row in rows),
        "valid_rate": rounded(sum(row["valid"] for row in rows) / len(rows), 4) if rows else None,
        "content_reviewable": sum(row["content_reviewable"] for row in rows),
        "content_reviewable_rate": rounded(sum(row["content_reviewable"] for row in rows) / len(rows), 4) if rows else None,
        "flags": counts,
        "duration_ms": numeric_stats(rows, "duration_ms"),
        "processing_time_ms": numeric_stats(rows, "processing_time_ms"),
        "ttft_ms": numeric_stats(rows, "ttft_ms"),
        "total_gen_ms": numeric_stats(rows, "total_gen_ms"),
        "answer_chars": numeric_stats(rows, "answer_chars"),
        "answer_words": numeric_stats(rows, "answer_words"),
        "total_tokens": numeric_stats(rows, "total_tokens"),
        "tokens_per_s": numeric_stats(rows, "tokens_per_s"),
        "answer_tokens": numeric_stats(rows, "answer_tokens"),
        "context_tokens": numeric_stats(rows, "context_tokens"),
        "memory_count": numeric_stats(rows, "memory_count"),
        "memory_top_relevance": numeric_stats(rows, "memory_top_relevance"),
        "memory_used": sum(bool(row.get("memory_used")) for row in rows),
        "memory_usage_rate": rounded(sum(bool(row.get("memory_used")) for row in rows) / len(rows), 4) if rows else None,
        "emotion_l1_delta": numeric_stats(rows, "emotion_l1_delta"),
        "dominant_strength": numeric_stats(rows, "dominant_strength"),
        "steering_active": sum(row["steering_active"] for row in rows),
        "prompt_emotions_enabled": sum(row["prompt_emotions_enabled"] for row in rows),
        "steering_modes": dict(steering_modes),
        "active_vector_layer_ranges": dict(layer_ranges),
    }


def analyze_session(session_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    config_path = session_dir / "config.json"
    if not config_path.exists():
        raise ValueError(f"Config fehlt: {config_path}")
    config = load_json(config_path)
    question_files = sorted((session_dir / "questions").glob("*.json"))
    rows = [flatten_question(path, config) for path in question_files]
    by_category: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_category[int(row.get("category_id") or 0)].append(row)
    official_summary = load_json(session_dir / "summary.json") if (session_dir / "summary.json").exists() else None
    model_name = str(config.get("model") or "unknown")
    service_precision = config.get("service_precision")
    if not service_precision and "qwen3.5-4b" in model_name.lower():
        service_precision = "FP16 (Service-Startprotokoll)"
    analysis = {
        "session_dir": str(session_dir.relative_to(PROJECT_ROOT)),
        "session_id": config.get("session_id"),
        "run_label": config.get("run_label", ""),
        "provider": config.get("llm_provider") or config.get("provider") or "unknown",
        "model": model_name,
        "model_label": config.get("model_label", ""),
        "service_precision": service_precision or "nicht protokolliert",
        "iterations": config.get("iterations"),
        "enable_thinking": config.get("enable_thinking"),
        "formatting_mode": config.get("formatting_mode"),
        "expected_questions": config.get("expected_questions"),
        "research_role": config.get("research_role", ""),
        "completion_class": config.get("completion_class", "full_replication"),
        "question_selection": config.get("question_selection"),
        "has_summary": official_summary is not None,
        "official_summary": official_summary,
        "aggregate": aggregate_rows(rows),
        "seed_statistics": seed_statistics(rows),
        "categories": {
            str(category_id): {
                "name": category_rows[0]["category"] if category_rows else "",
                **aggregate_rows(category_rows),
            }
            for category_id, category_rows in sorted(by_category.items())
        },
    }
    return analysis, rows


def resolve_session(value: str) -> Path:
    candidate = Path(value)
    if not candidate.exists():
        candidate = SESSION_ROOT / value
    if not candidate.is_dir():
        raise ValueError(f"Session nicht gefunden: {value}")
    return candidate.resolve()


def paired_coverage(all_rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_model: dict[str, set[tuple[Any, Any, Any]]] = defaultdict(set)
    for row in all_rows:
        key = (row["iteration"], row["category_id"], row["question_number"])
        by_model[row["model"]].add(key)
    models = sorted(by_model)
    common = set.intersection(*(by_model[model] for model in models)) if models else set()
    return {
        "models": models,
        "questions_by_model": {model: len(by_model[model]) for model in models},
        "common_question_keys": len(common),
        "fully_paired": bool(models) and all(by_model[model] == common for model in models),
    }


def write_csv(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    serial_rows = []
    for row in rows:
        serial = dict(row)
        for key, value in list(serial.items()):
            if isinstance(value, (dict, list, tuple)):
                serial[key] = json.dumps(value, ensure_ascii=False)
        serial_rows.append(serial)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(serial_rows[0].keys()) if serial_rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if fields:
            writer.writeheader()
            writer.writerows(serial_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sessions", nargs="+", help="Explizite Session-Ordner, z. B. session_14 session_15")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    args = parser.parse_args()

    sessions = []
    rows: list[dict[str, Any]] = []
    for value in args.sessions:
        analysis, session_rows = analyze_session(resolve_session(value))
        sessions.append(analysis)
        rows.extend(session_rows)

    report = {
        "schema_version": 2,
        "method": {
            "explicit_session_selection": True,
            "raw_logs_modified": False,
            "posthoc_quality_reanalysis": True,
            "strict_valid_includes_context_budget": True,
            "content_reviewable_ignores_context_budget_only": True,
            "instruction_leak_detector_posthoc_and_not_preregistered": True,
            "mixed_full_and_partial_conditions": True,
            "minimum_recommended_seeds": 5,
            "confidence_interval": "Normalapproximation 95% ueber Seed-Aggregate; bei n<2 nicht berechnet.",
            "significance_test": "Zweiseitiger exakter McNemar-Test auf gepaarten strict-valid Outcomes.",
            "note": "Qualitaetsflags sind Harness-Heuristiken; Humanratings werden getrennt und verblindet erfasst.",
        },
        "paired_coverage": paired_coverage(rows),
        "inferential_statistics": paired_significance(rows),
        "sessions": sessions,
        "questions": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
    write_csv(args.csv, rows)
    print(json.dumps({
        "sessions": len(sessions),
        "questions": len(rows),
        "paired_coverage": report["paired_coverage"],
        "output": str(args.output),
        "csv": str(args.csv),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
