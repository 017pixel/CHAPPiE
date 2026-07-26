#!/usr/bin/env python3
"""Validate a five-seed GPT-OSS 20B fallback set without provider access."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUN_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = RUN_DIR.parents[2]
SESSION_ROOT = PROJECT_ROOT / "forschung/session_logs"
DEFAULT_OUTPUT = RUN_DIR / "processed/gpt-oss-20b-five-seed-validation.json"
EXPECTED_MODEL = "openai/gpt-oss-20b"
EXPECTED_PROVIDER = "groq"
EXPECTED_SEEDS = [11, 23, 37, 53, 71]
EXPECTED_QUESTIONS = 21


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_session(value: str) -> Path:
    candidate = Path(value)
    if not candidate.exists():
        candidate = SESSION_ROOT / value
    if not candidate.is_dir():
        raise SystemExit(f"Session fehlt: {value}")
    return candidate.resolve()


def selected_keys(config: dict[str, Any]) -> set[tuple[int, int]]:
    return {
        (int(category), int(question))
        for category, questions in (config.get("question_selection") or {}).items()
        for question in questions
    }


def inspect_session(session: Path) -> dict[str, Any]:
    config_path = session / "config.json"
    summary_path = session / "summary.json"
    quality_path = session / "quality_analysis.json"
    audit_path = session / "provider_audit.json"
    config = read_json(config_path) if config_path.is_file() else {}
    summary = read_json(summary_path) if summary_path.is_file() else {}
    quality = read_json(quality_path) if quality_path.is_file() else {}
    audit = read_json(audit_path) if audit_path.is_file() else {}
    paths = sorted((session / "questions").glob("*.json"))
    questions = [read_json(path) for path in paths]
    seeds = sorted({int(item.get("seed")) for item in questions if item.get("seed") is not None})
    keys = {
        (int(item.get("category_id") or 0), int(item.get("question_number") or 0))
        for item in questions
    }
    response_pairs = {
        (
            str(((item.get("response") or {}).get("emotion_steering") or {}).get("provider")),
            str(((item.get("response") or {}).get("emotion_steering") or {}).get("model")),
        )
        for item in questions
        if item.get("response")
    }
    checks = {
        "config_exists": config_path.is_file(),
        "summary_exists": summary_path.is_file(),
        "quality_exists": quality_path.is_file(),
        "provider_audit_exists": audit_path.is_file(),
        "model_exact": config.get("model") == EXPECTED_MODEL,
        "provider_exact": config.get("llm_provider") == EXPECTED_PROVIDER,
        "one_seed": len(seeds) == 1,
        "config_seed_matches": seeds == list(config.get("seeds") or []),
        "question_count_exact": len(questions) == EXPECTED_QUESTIONS,
        "selected_key_count_exact": len(keys) == EXPECTED_QUESTIONS,
        "selected_keys_match_config": keys == selected_keys(config),
        "responses_exact": sum(bool(item.get("response")) for item in questions)
        == EXPECTED_QUESTIONS,
        "hard_errors_zero": sum(bool(item.get("_error")) for item in questions) == 0,
        "summary_total_exact": summary.get("total_questions") == EXPECTED_QUESTIONS,
        "summary_completed_exact": summary.get("completed") == EXPECTED_QUESTIONS,
        "summary_valid_exact": summary.get("valid_completed") == EXPECTED_QUESTIONS,
        "quality_valid_exact": (quality.get("summary") or {}).get("valid_completed")
        == EXPECTED_QUESTIONS,
        "provider_audit_passed": audit.get("passed") is True,
        "response_contract_exact": response_pairs
        == {(EXPECTED_PROVIDER, EXPECTED_MODEL)},
    }
    return {
        "session": str(session.relative_to(PROJECT_ROOT)),
        "seed": seeds[0] if len(seeds) == 1 else None,
        "question_files": len(questions),
        "selection": sorted([list(key) for key in keys]),
        "duration_minutes": summary.get("total_duration_min"),
        "checks": checks,
        "passed": all(checks.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sessions", nargs="+")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    sessions = [inspect_session(resolve_session(value)) for value in args.sessions]
    seed_values = sorted(item["seed"] for item in sessions if item["seed"] is not None)
    selections = {
        json.dumps(item["selection"], separators=(",", ":")) for item in sessions
    }
    run_checks = {
        "five_sessions": len(sessions) == 5,
        "five_unique_sessions": len({item["session"] for item in sessions}) == 5,
        "expected_seed_set": seed_values == EXPECTED_SEEDS,
        "identical_stratified_selection": len(selections) == 1,
        "all_sessions_passed": bool(sessions) and all(item["passed"] for item in sessions),
        "aggregate_questions_105": sum(item["question_files"] for item in sessions)
        == 105,
    }
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "resource_class": "POST_PROCESSING",
        "condition_class": "GPT-OSS 20B Groq fallback; not a replacement label for GPT-OSS 120B",
        "expected_model": EXPECTED_MODEL,
        "expected_provider": EXPECTED_PROVIDER,
        "checks": run_checks,
        "sessions": sessions,
        "passed": all(run_checks.values()),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "checks_passed": sum(run_checks.values()),
                "checks_total": len(run_checks),
                "sessions_passed": sum(item["passed"] for item in sessions),
                "sessions_total": len(sessions),
                "seeds": seed_values,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
