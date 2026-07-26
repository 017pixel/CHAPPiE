#!/usr/bin/env python3
"""Standalone consistency gate for mutable Run-2 cloud manifest counters."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "forschung/runs/run-2-20260723-1108-cb6d011"
MANIFEST = RUN_DIR / "manifest.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def valid_answer_count(session: str) -> int:
    quality_path = ROOT / session / "quality_analysis.json"
    assert quality_path.is_file(), f"quality analysis fehlt: {quality_path}"
    summary = read_json(quality_path).get("summary") or {}
    value = summary.get("valid_completed")
    assert isinstance(value, int), f"valid_completed fehlt: {quality_path}"
    return value


def test_cloud_manifest_counts_match_session_evidence() -> None:
    manifest = read_json(MANIFEST)
    condition = manifest["conditions"]["C"]
    primary = condition["primary_attempt"]
    active = condition["active_fallback"]

    assert primary["session"] != active["session"]
    primary_model = primary.get("model", condition["model"])
    assert primary_model == condition["model"]
    assert active["model"] != primary_model

    primary_count = valid_answer_count(primary["session"])
    active_count = valid_answer_count(active["session"])
    assert primary["observed_answers"] == primary_count, (
        "Primärzähler stimmt nicht mit dem Sessionaudit überein: "
        f"{primary['observed_answers']} != {primary_count}"
    )
    assert active["observed_answers"] == active_count, (
        "Fallbackzähler stimmt nicht mit dem Sessionaudit überein: "
        f"{active['observed_answers']} != {active_count}"
    )
    assert primary_count <= primary["planned_questions"]
    assert active_count <= active["planned_questions"]


if __name__ == "__main__":
    test_cloud_manifest_counts_match_session_evidence()
    print("OK: Run-2 cloud manifest counters match session quality evidence")
