#!/usr/bin/env python3
"""GPU-free per-seed audit for already-written Run-2 question artifacts."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
RUN_DIR = Path(__file__).resolve().parent
DEFAULT_SESSION = ROOT / "forschung/session_logs/session_33"
DEFAULT_JSON = RUN_DIR / "processed/gemma-live-aggregate.json"
DEFAULT_MD = RUN_DIR / "processed/gemma-live-aggregate.md"
FALLBACK_EXPECTED_MODEL = "google/gemma-4-E4B-it"
FALLBACK_EXPECTED_PROVIDER = "vllm"
FALLBACK_EXPECTED_PER_SEED = 86

FLAGS = (
    "quality_failed",
    "context_budget_failed",
    "memory_error_contamination",
    "setup_failed",
    "cot_leak",
    "instruction_leak",
    "content_relevance_warning",
    "safety_evaluation_unusable",
    "generation_failed",
    "formatting_failed",
)


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def numeric_summary(values: list[float]) -> dict[str, float | int | None]:
    return {
        "n": len(values),
        "mean": statistics.fmean(values) if values else None,
        "median": statistics.median(values) if values else None,
        "stdev": statistics.stdev(values) if len(values) > 1 else 0.0 if values else None,
        "p25": percentile(values, 0.25),
        "p75": percentile(values, 0.75),
        "min": min(values) if values else None,
        "max": max(values) if values else None,
    }


def load_questions(session: Path) -> list[tuple[Path, dict[str, Any]]]:
    records: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted((session / "questions").glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            payload = {"_parse_error": str(exc)}
        records.append((path, payload))
    return records


def resolve_session(value: Path) -> Path:
    """Resolve an explicit path or a conventional ``session_N`` name."""
    if value.is_dir():
        return value.resolve()
    candidate = ROOT / "forschung/session_logs" / value
    if candidate.is_dir():
        return candidate.resolve()
    raise FileNotFoundError(f"Sessionordner fehlt: {value}")


def audit(session: Path) -> dict[str, Any]:
    config_path = session / "config.json"
    config = (
        json.loads(config_path.read_text(encoding="utf-8"))
        if config_path.exists()
        else {}
    )
    expected_model = str(config.get("model") or FALLBACK_EXPECTED_MODEL)
    expected_provider = str(
        config.get("llm_provider")
        or config.get("provider")
        or FALLBACK_EXPECTED_PROVIDER
    )
    expected_iterations = int(config.get("iterations") or 1)
    expected_total_questions = int(
        config.get("expected_questions")
        or expected_iterations * FALLBACK_EXPECTED_PER_SEED
    )
    expected_per_seed = (
        expected_total_questions // expected_iterations
        if expected_iterations
        else FALLBACK_EXPECTED_PER_SEED
    )
    records = load_questions(session)
    by_iteration: dict[int, list[tuple[Path, dict[str, Any]]]] = defaultdict(list)
    parse_errors: list[str] = []
    for path, payload in records:
        if payload.get("_parse_error"):
            parse_errors.append(f"{path.name}: {payload['_parse_error']}")
            continue
        by_iteration[int(payload.get("iteration") or 0)].append((path, payload))

    iteration_results = []
    global_models: Counter[str] = Counter()
    global_providers: Counter[str] = Counter()
    global_layers: Counter[str] = Counter()
    category_stats: dict[int, dict[str, Any]] = {}
    empty_answers: list[str] = []
    suspect_truncations: list[str] = []
    duplicates: list[str] = []
    seen: set[tuple[int, int, int]] = set()

    for iteration, items in sorted(by_iteration.items()):
        durations: list[float] = []
        tokens: list[float] = []
        flags: Counter[str] = Counter()
        categories: Counter[int] = Counter()
        seeds: Counter[int] = Counter()
        iteration_models: Counter[str] = Counter()
        iteration_providers: Counter[str] = Counter()
        for path, payload in items:
            response = payload.get("response") or {}
            quality = response.get("quality") or {}
            steering = response.get("emotion_steering") or {}
            timing = response.get("timing") or {}
            key = (
                iteration,
                int(payload.get("category_id") or 0),
                int(payload.get("question_number") or 0),
            )
            if key in seen:
                duplicates.append(path.name)
            seen.add(key)
            categories[key[1]] += 1
            category_stats.setdefault(
                key[1],
                {
                    "category_id": key[1],
                    "category": str(payload.get("category") or ""),
                    "questions": 0,
                    "durations_ms": [],
                    "answer_words": [],
                    "memory_hits": [],
                    "flags": Counter(),
                },
            )
            category_entry = category_stats[key[1]]
            category_entry["questions"] += 1
            seeds[int(payload.get("seed") or 0)] += 1
            answer = str(response.get("response_text") or "").strip()
            category_entry["answer_words"].append(len(answer.split()))
            if not answer:
                empty_answers.append(path.name)
            if answer and len(answer) < 12 and not quality.get("concise_answer_allowed"):
                suspect_truncations.append(path.name)
            duration = payload.get("duration_ms")
            if isinstance(duration, (int, float)):
                durations.append(float(duration))
                category_entry["durations_ms"].append(float(duration))
            token_count = timing.get("total_tokens")
            if isinstance(token_count, (int, float)):
                tokens.append(float(token_count))
            for flag in FLAGS:
                if bool(quality.get(flag, response.get(flag, False))):
                    flags[flag] += 1
                    category_entry["flags"][flag] += 1
            memory_trace = response.get("memory_trace") or {}
            memory_stage = memory_trace.get("merged") or memory_trace.get("seed") or {}
            memory_hits = memory_stage.get("memories_found")
            if isinstance(memory_hits, (int, float)):
                category_entry["memory_hits"].append(float(memory_hits))
            model = str(steering.get("model") or "missing")
            provider = str(steering.get("provider") or "missing")
            iteration_models[model] += 1
            iteration_providers[provider] += 1
            global_models[model] += 1
            global_providers[provider] += 1
            for vector in steering.get("active_vectors") or []:
                layer_range = vector.get("layer_range") or []
                global_layers[str(tuple(layer_range))] += 1
        count = len(items)
        iteration_results.append({
            "iteration": iteration,
            "seeds": dict(seeds),
            "questions": count,
            "expected_questions": expected_per_seed,
            "complete": count == expected_per_seed,
            "unique_categories": len(categories),
            "category_counts": dict(sorted(categories.items())),
            "models": dict(iteration_models),
            "providers": dict(iteration_providers),
            "duration_ms": numeric_summary(durations),
            "total_tokens": numeric_summary(tokens),
            "flags": {flag: flags.get(flag, 0) for flag in FLAGS},
            "valid_technical": sum(
                1
                for _, payload in items
                if payload.get("response")
                and not payload.get("_error")
                and not payload.get("setup_failed")
                and not any(
                    bool(((payload.get("response") or {}).get("quality") or {}).get(flag))
                    for flag in ("quality_failed", "generation_failed", "formatting_failed")
                )
            ),
        })

    total = len(records)
    complete_iterations = sum(item["complete"] for item in iteration_results)
    hard_errors = (
        len(parse_errors) + len(empty_answers) + len(duplicates)
        + sum(
            item["flags"]["generation_failed"] + item["flags"]["formatting_failed"]
            for item in iteration_results
        )
    )
    category_results = []
    for category_id, entry in sorted(category_stats.items()):
        question_count = int(entry["questions"])
        relevance_warnings = int(entry["flags"].get("content_relevance_warning", 0))
        category_results.append({
            "category_id": category_id,
            "category": entry["category"],
            "questions": question_count,
            "duration_ms": numeric_summary(entry["durations_ms"]),
            "answer_words": numeric_summary(entry["answer_words"]),
            "memory_hits": numeric_summary(entry["memory_hits"]),
            "flags": {flag: int(entry["flags"].get(flag, 0)) for flag in FLAGS},
            "relevance_warning_rate": (
                relevance_warnings / question_count if question_count else None
            ),
        })
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "session": session.name,
        "session_path": str(session.relative_to(ROOT)),
        "expected_model": expected_model,
        "expected_provider": expected_provider,
        "expected_iterations": expected_iterations,
        "expected_questions_per_iteration": expected_per_seed,
        "expected_total_questions": expected_total_questions,
        "written_question_files": total,
        "complete_iterations": complete_iterations,
        "run_complete_by_count": total == expected_total_questions,
        "parse_errors": parse_errors,
        "empty_answers": empty_answers,
        "suspect_truncations": suspect_truncations,
        "duplicate_question_keys": duplicates,
        "models": dict(global_models),
        "providers": dict(global_providers),
        "active_layer_ranges": dict(global_layers),
        "model_contract_ok": set(global_models) == {expected_model},
        "provider_contract_ok": set(global_providers) == {expected_provider},
        "hard_error_count": hard_errors,
        "iterations": iteration_results,
        "categories": category_results,
        "not_final_validation": True,
        "validation_note": (
            "Live-Audit bereits geschriebener Dateien. Finale Freigabe verlangt zusätzlich Prozess-Exit, "
            "Summary, provider_audit, valid_completed und vollständige Sessionvalidierung."
        ),
    }


def render_markdown(data: dict[str, Any]) -> str:
    lines = [
        "# Run-2 Session-Aggregat",
        "",
        f"Stand: `{data['generated_at']}` · Session `{data['session']}` · "
        f"`{data['expected_model']}` über `{data['expected_provider']}`",
        "",
        f"- Fragenartefakte: **{data['written_question_files']}/{data['expected_total_questions']}**",
        f"- vollständige Replikationen: **{data['complete_iterations']}/{data['expected_iterations']}**",
        f"- harte Artefaktfehler: **{data['hard_error_count']}**",
        f"- Modellvertrag: **{'OK' if data['model_contract_ok'] else 'FEHLER'}**",
        f"- Providervertrag: **{'OK' if data['provider_contract_ok'] else 'FEHLER'}**",
        "",
        "| Iteration | Seed | Fragen | technisch valide | Ø Laufzeit | Median | Relevanzwarnung | Instruktionsleak |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in data["iterations"]:
        seed = ", ".join(str(value) for value in item["seeds"]) or "—"
        duration = item["duration_ms"]
        mean = "—" if duration["mean"] is None else f"{duration['mean'] / 1000:.2f} s"
        median = "—" if duration["median"] is None else f"{duration['median'] / 1000:.2f} s"
        lines.append(
            f"| {item['iteration']} | {seed} | {item['questions']}/{item['expected_questions']} | "
            f"{item['valid_technical']} | {mean} | {median} | "
            f"{item['flags']['content_relevance_warning']} | {item['flags']['instruction_leak']} |"
        )
    lines.extend([
        "",
        "## Aktive Layerbereiche",
        "",
        "```json",
        json.dumps(data["active_layer_ranges"], ensure_ascii=False, indent=2),
        "```",
        "",
        "> Dieser Live-Audit ist keine finale Datenfreigabe. Exit-Code, Summary und vollständige "
        "Provider-/Qualitätsvalidierung bleiben nach Prozessende erforderlich.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=Path, default=DEFAULT_SESSION)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()
    try:
        session = resolve_session(args.session)
    except FileNotFoundError as exc:
        parser.error(str(exc))
    result = audit(session)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.markdown_output.write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps({
        "questions": result["written_question_files"],
        "complete_iterations": result["complete_iterations"],
        "hard_error_count": result["hard_error_count"],
        "model_contract_ok": result["model_contract_ok"],
        "provider_contract_ok": result["provider_contract_ok"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
