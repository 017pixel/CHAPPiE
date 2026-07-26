#!/usr/bin/env python3
"""Validate the six targeted Run-2 follow-up sessions without model access."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUN_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = RUN_DIR.parents[2]
DEFAULT_REGISTRY = RUN_DIR / "processed/targeted-followup-sessions.json"
DEFAULT_OUTPUT = RUN_DIR / "processed/targeted-followup-validation.json"
EXPECTED_MODULES = {
    "F1-recovery": ("full", 15),
    "F2-memory-conflict": ("full", 12),
    "F3-life-full": ("full", 6),
    "F3-life-off": ("no_life", 6),
    "F4-identity-correction": ("full", 15),
    "F5-binding-shutdown": ("full", 15),
}
EXPECTED_MODEL = "Qwen/Qwen3.5-4B"
EXPECTED_PROVIDER = "vllm"
EXPECTED_SEEDS = [11, 23, 37]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_session(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def validate_session(record: dict[str, Any]) -> dict[str, Any]:
    module = str(record.get("module") or "")
    expected_profile, expected_questions = EXPECTED_MODULES.get(module, ("", -1))
    session = resolve_session(str(record.get("session") or ""))
    config_path = session / "config.json"
    summary_path = session / "summary.json"
    quality_path = session / "quality_analysis.json"
    audit_path = session / "provider_audit.json"
    config = read_json(config_path) if config_path.is_file() else {}
    summary = read_json(summary_path) if summary_path.is_file() else {}
    quality = read_json(quality_path) if quality_path.is_file() else {}
    audit = read_json(audit_path) if audit_path.is_file() else {}
    question_paths = sorted((session / "questions").glob("*.json")) if session.is_dir() else []
    questions = [read_json(path) for path in question_paths]
    keys = [
        (item.get("iteration"), item.get("category_id"), item.get("question_number"))
        for item in questions
    ]
    response_models = sorted(
        {
            str(((item.get("response") or {}).get("emotion_steering") or {}).get("model"))
            for item in questions
            if ((item.get("response") or {}).get("emotion_steering") or {}).get("model")
        }
    )
    response_providers = sorted(
        {
            str(((item.get("response") or {}).get("emotion_steering") or {}).get("provider"))
            for item in questions
            if ((item.get("response") or {}).get("emotion_steering") or {}).get("provider")
        }
    )
    checks = {
        "known_module": module in EXPECTED_MODULES,
        "session_exists": session.is_dir(),
        "config_exists": config_path.is_file(),
        "summary_exists": summary_path.is_file(),
        "quality_analysis_exists": quality_path.is_file(),
        "provider_audit_exists": audit_path.is_file(),
        "record_expected_questions_exact": record.get("expected_questions") == expected_questions,
        "record_seeds_exact": record.get("seeds") == EXPECTED_SEEDS,
        "record_ablation_exact": record.get("ablation_profile") == expected_profile,
        "config_model_exact": config.get("model") == EXPECTED_MODEL,
        "config_provider_exact": config.get("llm_provider") == EXPECTED_PROVIDER,
        "config_seeds_exact": config.get("seeds") == EXPECTED_SEEDS,
        "config_ablation_exact": config.get("ablation_profile") == expected_profile,
        "question_file_count_exact": len(questions) == expected_questions,
        "question_keys_unique": len(keys) == len(set(keys)),
        "target_responses_exact": sum(bool(item.get("response")) for item in questions)
        == expected_questions,
        "hard_errors_zero": sum(bool(item.get("_error")) for item in questions) == 0,
        "summary_total_exact": summary.get("total_questions") == expected_questions,
        "summary_valid_exact": summary.get("valid_completed") == expected_questions,
        "quality_total_exact": (quality.get("summary") or {}).get("total_questions")
        == expected_questions,
        "quality_valid_exact": (quality.get("summary") or {}).get("valid_completed")
        == expected_questions,
        "provider_audit_passed": audit.get("passed") is True,
        "response_models_exact": response_models == [EXPECTED_MODEL],
        "response_providers_exact": response_providers == [EXPECTED_PROVIDER],
    }
    return {
        "module": module,
        "session": str(session),
        "expected_questions": expected_questions,
        "question_files": len(questions),
        "response_models": response_models,
        "response_providers": response_providers,
        "checks": checks,
        "passed": all(checks.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    registry = read_json(args.registry)
    records = registry.get("sessions") or []
    sessions = [validate_session(record) for record in records]
    observed_modules = [item["module"] for item in sessions]
    run_checks = {
        "registry_completed_unverified": registry.get("status") == "COMPLETED_UNVERIFIED",
        "six_session_records": len(records) == len(EXPECTED_MODULES),
        "module_set_exact": set(observed_modules) == set(EXPECTED_MODULES),
        "modules_unique": len(observed_modules) == len(set(observed_modules)),
        "aggregate_expected_questions_69": sum(
            int(item.get("expected_questions") or 0) for item in records
        )
        == 69,
        "all_sessions_passed": bool(sessions) and all(item["passed"] for item in sessions),
    }
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "resource_class": "POST_PROCESSING",
        "registry": str(args.registry.resolve()),
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
                "run_checks": sum(run_checks.values()),
                "run_checks_total": len(run_checks),
                "sessions_passed": sum(item["passed"] for item in sessions),
                "sessions_total": len(sessions),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
