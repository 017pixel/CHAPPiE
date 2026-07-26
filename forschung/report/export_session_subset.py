#!/usr/bin/env python3
"""Export an exact, independently validatable subset from a research session."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _selected_keys(config: dict) -> set[tuple[int, int, int]]:
    selection = config.get("question_selection") or {}
    iterations = int(config.get("iterations") or 1)
    return {
        (iteration, int(category), int(question))
        for iteration in range(1, iterations + 1)
        for category, questions in selection.items()
        for question in questions
    }


def export_subset(source: Path, destination: Path, subset_config: Path) -> Path:
    config = _read(subset_config)
    wanted = _selected_keys(config)
    if not wanted:
        raise ValueError("Subset-Konfiguration braucht question_selection")
    if destination.exists():
        raise FileExistsError(f"Ziel existiert bereits: {destination}")

    selected: list[tuple[Path, dict]] = []
    for path in sorted((source / "questions").glob("*.json")):
        entry = _read(path)
        key = (int(entry.get("iteration") or 0), int(entry.get("category_id") or 0), int(entry.get("question_number") or 0))
        if key in wanted:
            selected.append((path, entry))
    found = {
        (int(entry["iteration"]), int(entry["category_id"]), int(entry["question_number"]))
        for _, entry in selected
    }
    if found != wanted:
        raise ValueError(f"Subset unvollstaendig: fehlt={sorted(wanted - found)}, unerwartet={sorted(found - wanted)}")

    questions_dir = destination / "questions"
    questions_dir.mkdir(parents=True)
    for path, _ in selected:
        shutil.copy2(path, questions_dir / path.name)

    source_config = _read(source / "config.json")
    config.update({
        "session_id": destination.name,
        "derived_from_session": source.name,
        "derived_from_run_label": source_config.get("run_label"),
        "expected_questions": len(selected),
        "research_role": "validated_session_subset",
    })
    (destination / "config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    errors = sum(bool(entry.get("_error")) for _, entry in selected)
    completed = sum(bool(entry.get("response")) and not entry.get("_error") for _, entry in selected)
    valid = sum(
        bool(entry.get("response"))
        and not entry.get("_error")
        and not entry.get("setup_failed")
        and not (entry.get("response") or {}).get("quality_failed")
        for _, entry in selected
    )
    total_duration = sum(float(entry.get("duration_ms") or 0) for _, entry in selected)
    summary = {
        "session_id": destination.name,
        "derived_from_session": source.name,
        "total_questions": len(selected),
        "completed": completed,
        "valid_completed": valid,
        "errors": errors,
        "iterations": int(config.get("iterations") or 1),
        "categories": [int(item["id"]) for item in config.get("categories", [])],
        "total_duration_ms": round(total_duration),
        "total_duration_min": round(total_duration / 60000, 1),
        "avg_duration_ms": round(total_duration / len(selected)) if selected else 0,
    }
    (destination / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    result = export_subset(args.source, args.destination, args.config)
    print(result)


if __name__ == "__main__":
    main()
