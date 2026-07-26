#!/usr/bin/env python3
"""Paired, question-key-matched comparison of Run-1 and Run-2 Gemma artifacts."""

from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from forschung.report.build_benchmark_data import flatten_question, load_json


ROOT = Path(__file__).resolve().parents[3]
RUN_DIR = Path(__file__).resolve().parent
OLD = ROOT / "forschung" / "session_logs" / "session_15"
NEW = ROOT / "forschung" / "session_logs" / "session_33"
OUT = RUN_DIR / "comparisons"

FLAGS = [
    "valid",
    "content_reviewable",
    "hard_error",
    "generation_failed",
    "formatting_failed",
    "context_budget_failed",
    "setup_failed",
    "cot_leak",
    "instruction_leak",
    "content_relevance_warning",
]


def load_rows(session: Path) -> dict[tuple[int, int, int], dict]:
    config = load_json(session / "config.json")
    result = {}
    for path in (session / "questions").glob("*.json"):
        row = flatten_question(path, config)
        result[(int(row["iteration"]), int(row["category_id"]), int(row["question_number"]))] = row
    return result


def main() -> None:
    old = load_rows(OLD)
    new = load_rows(NEW)
    # Run 1 has one seed/iteration. Compare it only with Run-2 iteration 1,
    # never with all five repeats as if they were independent paired Run-1 data.
    common = sorted(key for key in set(old) & set(new) if key[0] == 1)
    if not common:
        raise RuntimeError("Keine gepaarten Gemma-Fragen vorhanden")
    metrics = {}
    for flag in FLAGS:
        old_count = sum(bool(old[key][flag]) for key in common)
        new_count = sum(bool(new[key][flag]) for key in common)
        metrics[flag] = {
            "run1_count": old_count,
            "run2_count": new_count,
            "run1_rate": old_count / len(common),
            "run2_rate": new_count / len(common),
            "absolute_count_change": new_count - old_count,
            "percentage_point_change": (new_count - old_count) / len(common) * 100,
        }
    timing = {}
    for name, rows in (("run1", old), ("run2", new)):
        values = [float(rows[key]["duration_ms"]) for key in common]
        timing[name] = {
            "mean_ms": statistics.fmean(values),
            "median_ms": statistics.median(values),
            "min_ms": min(values),
            "max_ms": max(values),
        }
    complete = len(common) == 86 and (NEW / "summary.json").exists()
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "comparison": "Gemma Run 1 session_15 iteration 1 vs Run 2 session_33 iteration 1",
        "paired_key": ["iteration", "category_id", "question_number"],
        "paired_questions": len(common),
        "expected_paired_questions": 86,
        "provisional": not complete,
        "run1": {
            "session": "forschung/session_logs/session_15",
            "model": "google/gemma-4-E4B-it",
            "historical_state_isolation": False,
        },
        "run2": {
            "session": "forschung/session_logs/session_33",
            "model": "google/gemma-4-E4B-it",
            "research_state_isolated": True,
        },
        "metrics": metrics,
        "duration_ms": timing,
        "comparability_limits": [
            "Run 2 uses an isolated Research-State; Run 1 reused persistent Memory/Life.",
            "The code and prompts changed between runs by design.",
            "Run 1 is one seed; this direct pairing uses only Run-2 seed 11/iteration 1.",
            "Current quality flags are recomputed with the current posthoc detector on both sessions.",
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "gemma-paired-progress.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    lines = [
        "# Gemma Run 1 → Run 2, gepaarter Arbeitsvergleich",
        "",
        f"Stand: {report['paired_questions']}/86 paarbare Fragen. "
        + ("**Vorläufig; Session 33 läuft.**" if report["provisional"] else "**Vollständig validiert.**"),
        "",
        "| Metrik | Run 1 | Run 2 | Änderung |",
        "|---|---:|---:|---:|",
    ]
    for flag in FLAGS:
        item = metrics[flag]
        lines.append(
            f"| {flag} | {item['run1_count']}/{len(common)} | {item['run2_count']}/{len(common)} "
            f"| {item['percentage_point_change']:+.1f} Prozentpunkte |"
        )
    lines.extend([
        "",
        f"Mittlere Laufzeit: Run 1 {timing['run1']['mean_ms']/1000:.1f} s, "
        f"Run 2 {timing['run2']['mean_ms']/1000:.1f} s.",
        "",
        "## Vergleichsgrenzen",
        "",
        "- Run 2 isoliert Research-Memory/Life; Run 1 tat dies nicht.",
        "- Code und Prompts wurden zwischen den Runs absichtlich repariert.",
        "- Direkt gepaart ist nur Run-2-Seed 11 gegen den einzelnen Run-1-Lauf.",
        "- Quality-Flags wurden auf beide Datensätze mit dem aktuellen Post-hoc-Detektor angewandt.",
        "",
    ])
    (OUT / "gemma-paired-progress.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({
        "paired_questions": len(common),
        "provisional": not complete,
        "run1_valid": metrics["valid"]["run1_count"],
        "run2_valid": metrics["valid"]["run2_count"],
        "run1_instruction_leak": metrics["instruction_leak"]["run1_count"],
        "run2_instruction_leak": metrics["instruction_leak"]["run2_count"],
    }, indent=2))


if __name__ == "__main__":
    main()
