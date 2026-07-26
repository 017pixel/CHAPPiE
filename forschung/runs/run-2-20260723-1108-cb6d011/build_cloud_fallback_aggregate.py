#!/usr/bin/env python3
"""Combine validated per-seed GPT-OSS 20B aggregates without reading answer text."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUN_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = RUN_DIR.parents[2]
PROCESSED = RUN_DIR / "processed"
SEEDS = (11, 23, 37, 53, 71)
DEFAULT_VALIDATION = PROCESSED / "gpt-oss-20b-five-seed-validation.json"
DEFAULT_OUTPUT = PROCESSED / "gpt-oss-20b-five-seed-aggregate.json"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def project_path(path: Path) -> str:
    """Return stable project-relative provenance for relative or absolute input."""
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(resolved)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validation", type=Path, default=DEFAULT_VALIDATION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    validation = read_json(args.validation)
    if validation.get("passed") is not True:
        raise SystemExit("Fünf-Seed-Validator ist nicht PASS; kein finales Aggregat.")

    iterations = []
    sources = []
    for replication, seed in enumerate(SEEDS, start=1):
        path = PROCESSED / f"gpt-oss-20b-seed{seed}-live-aggregate.json"
        aggregate = read_json(path)
        source_items = aggregate.get("iterations") or []
        if len(source_items) != 1:
            raise SystemExit(f"Seed {seed}: genau ein Iterationsaggregat erwartet.")
        item = dict(source_items[0])
        if item.get("questions") != 21 or item.get("valid_technical") != 21:
            raise SystemExit(f"Seed {seed}: 21/21 technisch valide erwartet.")
        if set((item.get("seeds") or {}).keys()) != {str(seed)}:
            raise SystemExit(f"Seed {seed}: Seedvertrag stimmt nicht.")
        item["iteration"] = replication
        item["source_session"] = next(
            (
                record.get("session")
                for record in validation.get("sessions", [])
                if record.get("seed") == seed
            ),
            None,
        )
        iterations.append(item)
        sources.append(project_path(path))

    result = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "resource_class": "POST_PROCESSING",
        "condition_class": (
            "GPT-OSS 20B Groq fallback; five stratified 21-question "
            "partial replications; not GPT-OSS 120B"
        ),
        "expected_model": "openai/gpt-oss-20b",
        "expected_provider": "groq",
        "expected_iterations": 5,
        "expected_questions_per_iteration": 21,
        "expected_total_questions": 105,
        "complete_iterations": 5,
        "written_question_files": 105,
        "hard_error_count": 0,
        "run_complete_by_count": True,
        "formal_five_seed_gate": True,
        "iterations": iterations,
        "sources": sources
        + [project_path(args.validation)],
        "methodological_limit": (
            "Five repeated stratified partial replications are not five full "
            "86-question runs and do not replace the GPT-OSS 120B primary condition."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "replications": len(iterations),
                "questions": sum(item["questions"] for item in iterations),
                "technically_valid": sum(
                    item["valid_technical"] for item in iterations
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
