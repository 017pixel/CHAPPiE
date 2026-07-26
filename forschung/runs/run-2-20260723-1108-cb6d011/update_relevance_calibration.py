#!/usr/bin/env python3
"""Reclassify MF-030 from complete-seed relevance-warning calibration evidence."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from build_run2_scaffold import FIELDS, RUN_DIR, write_matrix


QUESTIONS = RUN_DIR.parents[1] / "session_logs/session_33/questions"
CSV_PATH = RUN_DIR / "known-issues-comparison.csv"
EXPECTED_PER_ITERATION = 86


def add_evidence(row: dict[str, str], value: str) -> None:
    existing = [part.strip() for part in row["evidence_paths"].split("|")]
    if value not in existing:
        row["evidence_paths"] += f" | {value}"


def main() -> None:
    by_iteration: dict[int, list[tuple[Path, dict]]] = defaultdict(list)
    for path in sorted(QUESTIONS.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        by_iteration[int(payload.get("iteration") or 0)].append((path, payload))
    complete = {
        iteration
        for iteration, items in by_iteration.items()
        if len(items) == EXPECTED_PER_ITERATION
    }
    if not complete:
        raise RuntimeError("Keine vollständige Replikation")

    direct_safety = []
    emotion_pair = []
    for iteration in sorted(complete):
        for path, payload in by_iteration[iteration]:
            category = int(payload.get("category_id") or 0)
            question = int(payload.get("question_number") or 0)
            response = payload.get("response") or {}
            quality = response.get("quality") or {}
            warning = bool(
                quality.get(
                    "content_relevance_warning",
                    response.get("content_relevance_warning", False),
                )
            )
            item = (path, warning)
            if category == 12:
                direct_safety.append(item)
            if category == 4 and question in {1, 2}:
                emotion_pair.append(item)

    safety_warnings = sum(warning for _, warning in direct_safety)
    emotion_warnings = sum(warning for _, warning in emotion_pair)

    with CSV_PATH.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    row = next(item for item in rows if item["issue_id"] == "MF-030")
    row["status"] = "PARTIALLY_FIXED"
    row["current_result"] = (
        "Das Relevanzflag wird getrennt und reproduzierbar protokolliert, ist aber "
        f"in den vollständig geschriebenen Seeds schlecht kalibriert: {safety_warnings}/"
        f"{len(direct_safety)} klare direkte Safety-Verweigerungen und "
        f"{emotion_warnings}/{len(emotion_pair)} gepaarte Emotionsantworten tragen eine "
        "`content_relevance_warning`. Die Warnung macht mögliche Fälle sichtbar, "
        "misst Relevanz in diesen Antwortklassen aber nicht zuverlässig."
    )
    row["residual_risk"] = (
        "Hohe False-Positive-Rate kann sichere, knappe oder stilistisch ungewöhnliche "
        "Antworten als irrelevant erscheinen lassen; False Negatives bleiben ebenfalls möglich."
    )
    row["next_action"] = (
        "Detektor gegen verblindete Humanlabels kalibrieren, Precision/Recall je Kategorie "
        "messen und knappe Safety-Verweigerungen als eigene Antwortklasse behandeln."
    )
    add_evidence(
        row,
        f"forschung/runs/{RUN_DIR.name}/processed/gemma-live-aggregate.json",
    )
    add_evidence(
        row,
        f"forschung/runs/{RUN_DIR.name}/processed/core-case-screening.json",
    )
    for path, _ in direct_safety:
        add_evidence(row, str(path.relative_to(RUN_DIR.parents[2])))

    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    write_matrix(rows)
    print(
        json.dumps(
            {
                "complete_iterations": sorted(complete),
                "direct_safety_warnings": safety_warnings,
                "direct_safety_total": len(direct_safety),
                "emotion_pair_warnings": emotion_warnings,
                "emotion_pair_total": len(emotion_pair),
                "status": row["status"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
