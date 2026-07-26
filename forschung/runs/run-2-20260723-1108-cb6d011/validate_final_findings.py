#!/usr/bin/env python3
"""Validate evidence coverage and language contracts of final Run-2 findings."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUN_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = RUN_DIR.parents[2]
DEFAULT_INPUT = RUN_DIR / "processed/final-research-findings.json"
DEFAULT_OUTPUT = RUN_DIR / "processed/final-research-findings-validation.json"
FIELDS = (
    "question",
    "observation",
    "technical_explanation",
    "scientific_interpretation",
    "safety_and_uncertainty",
    "evidence",
)
FORBIDDEN = (
    "chappie hat bewusstsein",
    "chappie besitzt echte gefühle",
    "beweist bewusstsein",
    "beweist subjektive",
)


def evidence_path(value: str) -> Path:
    raw = value.strip().strip("`")
    candidate, separator, suffix = raw.rpartition(":")
    if separator and suffix.isdigit():
        raw = candidate
    return PROJECT_ROOT / raw


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    findings = payload.get("findings") or []
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: Any) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    check("release_status", payload.get("release_status") == "FINAL_WITH_LIMITATIONS", payload.get("release_status"))
    check("at_least_13_questions", len(findings) >= 13, len(findings))
    check(
        "required_fields",
        all(all(item.get(field) for field in FIELDS) for item in findings),
        "all six fields required",
    )
    questions = [str(item.get("question") or "") for item in findings]
    check("questions_unique", len(questions) == len(set(questions)), len(set(questions)))
    evidence = [
        str(value)
        for item in findings
        for value in (item.get("evidence") or [])
    ]
    missing = [value for value in evidence if not evidence_path(value).exists()]
    check("evidence_paths_exist", not missing, missing)
    check(
        "multiple_evidence_for_major_findings",
        all(len(item.get("evidence") or []) >= 2 for item in findings),
        [index + 1 for index, item in enumerate(findings) if len(item.get("evidence") or []) < 2],
    )
    text = json.dumps(payload, ensure_ascii=False).casefold()
    hits = [phrase for phrase in FORBIDDEN if phrase in text]
    check("forbidden_consciousness_claims_absent", not hits, hits)
    check(
        "four_part_language_nontrivial",
        all(
            len(str(item.get(field) or "")) >= 40
            for item in findings
            for field in FIELDS[1:5]
        ),
        "each interpretation field >= 40 characters",
    )
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input": str(args.input),
        "checks": checks,
        "passed": all(item["passed"] for item in checks),
    }
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "checks": len(checks),
                "findings": len(findings),
                "missing_evidence": len(missing),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
