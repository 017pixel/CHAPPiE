#!/usr/bin/env python3
"""Build a paired Run-1/Run-2 comparison for one model condition."""

from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from forschung.report.build_benchmark_data import flatten_question, load_json


ROOT = Path(__file__).resolve().parents[3]
RUN_DIR = Path(__file__).resolve().parent
FLAGS = (
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
)


def resolve_session(value: str) -> Path:
    candidate = Path(value)
    if not candidate.exists():
        candidate = ROOT / "forschung/session_logs" / value
    if not candidate.is_dir():
        raise SystemExit(f"Session fehlt: {value}")
    return candidate.resolve()


def load_rows(session: Path) -> tuple[dict, dict[tuple[int, int, int], dict]]:
    config = load_json(session / "config.json")
    rows = {}
    for path in sorted((session / "questions").glob("*.json")):
        row = flatten_question(path, config)
        key = (
            int(row["iteration"]),
            int(row["category_id"]),
            int(row["question_number"]),
        )
        rows[key] = row
    return config, rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-session", required=True)
    parser.add_argument("--new-session", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--output-stem", required=True)
    parser.add_argument("--expected-questions", type=int, default=86)
    parser.add_argument("--output-dir", type=Path, default=RUN_DIR / "comparisons")
    args = parser.parse_args()

    old_session = resolve_session(args.old_session)
    new_session = resolve_session(args.new_session)
    old_config, old = load_rows(old_session)
    new_config, new = load_rows(new_session)
    common = sorted(key for key in set(old) & set(new) if key[0] == 1)
    if not common:
        raise RuntimeError("Keine gepaarten Fragen vorhanden")

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

    complete = (
        len(common) == args.expected_questions
        and (new_session / "summary.json").exists()
    )
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "comparison": (
            f"{args.label}: {old_session.name} Iteration 1 gegen "
            f"{new_session.name} Iteration 1"
        ),
        "paired_key": ["iteration", "category_id", "question_number"],
        "paired_questions": len(common),
        "expected_paired_questions": args.expected_questions,
        "provisional": not complete,
        "run1": {
            "session": str(old_session.relative_to(ROOT)),
            "model": old_config.get("model"),
            "provider": old_config.get("llm_provider") or old_config.get("provider"),
            "historical_state_isolation": False,
        },
        "run2": {
            "session": str(new_session.relative_to(ROOT)),
            "model": new_config.get("model"),
            "provider": new_config.get("llm_provider") or new_config.get("provider"),
            "research_state_isolated": True,
        },
        "metrics": metrics,
        "duration_ms": timing,
        "comparability_limits": [
            "Run 2 uses isolated Research-State; Run 1 reused persistent Memory/Life.",
            "Code and prompts changed between runs by design.",
            "Run 1 has one seed; direct pairing uses only Run-2 seed 11/iteration 1.",
            "Quality flags are recomputed with the current posthoc detector on both sessions.",
        ],
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / f"{args.output_stem}.json"
    markdown_path = args.output_dir / f"{args.output_stem}.md"
    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    lines = [
        f"# {args.label}: Run 1 → Run 2",
        "",
        f"Stand: {len(common)}/{args.expected_questions} paarbare Fragen. "
        + ("**Vorläufig.**" if report["provisional"] else "**Vollständig.**"),
        "",
        "| Metrik | Run 1 | Run 2 | Änderung |",
        "|---|---:|---:|---:|",
    ]
    for flag in FLAGS:
        item = metrics[flag]
        lines.append(
            f"| {flag} | {item['run1_count']}/{len(common)} | "
            f"{item['run2_count']}/{len(common)} | "
            f"{item['percentage_point_change']:+.1f} Prozentpunkte |"
        )
    lines.extend(
        [
            "",
            f"Mittlere Laufzeit: Run 1 {timing['run1']['mean_ms']/1000:.1f} s, "
            f"Run 2 {timing['run2']['mean_ms']/1000:.1f} s.",
            "",
            "## Vergleichsgrenzen",
            "",
            "- Run 2 isoliert Research-Memory/Life; Run 1 tat dies nicht.",
            "- Code und Prompts wurden zwischen den Runs absichtlich repariert.",
            "- Direkt gepaart ist nur Run-2-Seed 11 gegen den einzelnen Run-1-Lauf.",
            "- Quality-Flags wurden mit dem aktuellen Post-hoc-Detektor auf beide Datensätze angewandt.",
            "",
        ]
    )
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    print(
        json.dumps(
            {
                "paired_questions": len(common),
                "provisional": not complete,
                "run1_model": old_config.get("model"),
                "run2_model": new_config.get("model"),
                "run1_valid": metrics["valid"]["run1_count"],
                "run2_valid": metrics["valid"]["run2_count"],
                "json": str(json_path),
                "markdown": str(markdown_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
