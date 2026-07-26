#!/usr/bin/env python3
"""Validate the Run-1/Run-2 issue matrix contract without model access."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


RUN_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = RUN_DIR.parents[2]
CSV_PATH = RUN_DIR / "known-issues-comparison.csv"
MATRIX_PATH = RUN_DIR / "retest-matrix.md"
OUTPUT_PATH = RUN_DIR / "processed/issue-matrix-validation.json"
FIELDS = (
    "issue_id",
    "short_description",
    "area",
    "source_run1",
    "prior_behavior",
    "documented_repair",
    "run2_test_method",
    "current_result",
    "status",
    "evidence_paths",
    "residual_risk",
    "next_action",
)
STATUSES = {
    "FIXED",
    "PARTIALLY_FIXED",
    "STILL_PRESENT",
    "REGRESSED",
    "NOT_RETESTED",
    "NOT_COMPARABLE",
    "NEW_ISSUE",
}
EVIDENCE_PATH_PREFIXES = (
    "forschung/",
    "tests/",
    "plans/",
    "brain/",
    "config/",
    "memory/",
    "life/",
    "web_infrastructure/",
    "docs/",
    "frontend/",
    "api/",
    "scripts/",
    "README",
    "CHANGELOG",
    "AGENTS",
)


def extra_column_rows(rows: list[dict]) -> dict[str, list[str]]:
    """Return CSV rows that DictReader parsed beyond the declared header."""
    return {
        str(row.get("issue_id", "<unknown>")): [
            str(value) for value in (row.get(None) or [])
        ]
        for row in rows
        if row.get(None)
    }


def existing_evidence_paths(value: str) -> list[str]:
    """Return explicit, project-relative evidence segments that exist."""
    existing: list[str] = []
    for part in str(value or "").split("|"):
        raw = part.strip().rstrip(".,;").strip("`")
        if not raw.startswith(EVIDENCE_PATH_PREFIXES):
            continue
        candidate, separator, suffix = raw.rpartition(":")
        if separator and suffix.isdigit():
            raw = candidate
        if (PROJECT_ROOT / raw).exists():
            existing.append(raw)
    return existing


def main() -> None:
    with CSV_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        header = tuple(reader.fieldnames or ())

    markdown = MATRIX_PATH.read_text(encoding="utf-8")
    checks: list[dict[str, object]] = []

    def check(name: str, passed: bool, detail: object) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    ids = [row.get("issue_id", "") for row in rows]
    mf_rows = [row for row in rows if re.fullmatch(r"MF-\d{3}", row["issue_id"])]
    new_rows = [
        row for row in rows if re.fullmatch(r"R2-NEW-\d{3}", row["issue_id"])
    ]
    status_counts = Counter(row.get("status", "") for row in rows)
    matrix_statuses = {
        issue_id: status
        for issue_id, status in re.findall(
            r"\|\s*((?:MF|R2-NEW)-\d{3})\s*\|.*?\|\s*`([A-Z_]+)`\s*\|",
            markdown,
        )
    }

    check("header_exact", header == FIELDS, list(header))
    check("row_count", len(rows) >= 48, len(rows))
    check("ids_unique", len(ids) == len(set(ids)), len(set(ids)))
    check("known_issue_count", len(mf_rows) == 48, len(mf_rows))
    check("new_issue_count", len(new_rows) >= 1, len(new_rows))
    check(
        "all_ids_well_formed",
        len(mf_rows) + len(new_rows) == len(rows),
        ids,
    )
    check(
        "all_required_fields_present",
        all(all(str(row.get(field, "")).strip() for field in FIELDS) for row in rows),
        "12/12 fields required per row",
    )
    extras = extra_column_rows(rows)
    check(
        "no_extra_columns",
        not extras,
        extras,
    )
    check(
        "statuses_allowed",
        set(status_counts) <= STATUSES,
        dict(status_counts),
    )
    check(
        "new_issue_status_contract",
        all(row["status"] == "NEW_ISSUE" for row in new_rows)
        and all(row["status"] != "NEW_ISSUE" for row in mf_rows),
        [row["issue_id"] for row in new_rows],
    )
    check(
        "fixed_rows_have_retest_result",
        all(
            row["current_result"].strip()
            and "ausstehend" not in row["current_result"].casefold()
            and row["evidence_paths"].strip()
            for row in rows
            if row["status"] == "FIXED"
        ),
        [row["issue_id"] for row in rows if row["status"] == "FIXED"],
    )
    rows_without_existing_evidence = [
        row["issue_id"]
        for row in rows
        if not existing_evidence_paths(row.get("evidence_paths", ""))
    ]
    check(
        "at_least_one_existing_evidence_path_per_row",
        not rows_without_existing_evidence,
        rows_without_existing_evidence,
    )
    check(
        "markdown_covers_all_rows",
        set(matrix_statuses) == set(ids),
        {
            "missing": sorted(set(ids) - set(matrix_statuses)),
            "extra": sorted(set(matrix_statuses) - set(ids)),
        },
    )
    check(
        "markdown_statuses_match_csv",
        all(matrix_statuses.get(row["issue_id"]) == row["status"] for row in rows),
        {
            row["issue_id"]: {
                "csv": row["status"],
                "markdown": matrix_statuses.get(row["issue_id"]),
            }
            for row in rows
            if matrix_statuses.get(row["issue_id"]) != row["status"]
        },
    )

    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "resource_class": "INDEPENDENT",
        "passed": all(item["passed"] for item in checks),
        "checks": checks,
        "status_counts": dict(status_counts),
    }
    OUTPUT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "checks": len(checks),
                "status_counts": report["status_counts"],
                "output": str(OUTPUT_PATH),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
