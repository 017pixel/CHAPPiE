#!/usr/bin/env python3
"""Validiert Vollständigkeit und Modellidentität einer Research-Session."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SESSION_ROOT = ROOT / "forschung" / "session_logs"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve(value: str) -> Path:
    candidate = Path(value)
    if not candidate.exists():
        candidate = SESSION_ROOT / value
    if not candidate.is_dir():
        raise SystemExit(f"Session fehlt: {value}")
    return candidate.resolve()


def expected_selected_keys(config: dict[str, Any]) -> set[tuple[int, int, int]] | None:
    selection = config.get("question_selection")
    if selection is None:
        return None
    iterations = int(config.get("iterations") or 1)
    result = set()
    for category, questions in selection.items():
        for iteration in range(1, iterations + 1):
            for question in questions:
                result.add((iteration, int(category), int(question)))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session")
    parser.add_argument("--expected-model", required=True)
    parser.add_argument("--expected-provider", choices=("vllm", "ollama", "groq"))
    parser.add_argument("--expected-questions", type=int, default=86)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    session = resolve(args.session)
    config_path = session / "config.json"
    summary_path = session / "summary.json"
    quality_path = session / "quality_analysis.json"
    provider_audit_path = session / "provider_audit.json"
    config = read(config_path) if config_path.exists() else {}
    summary = read(summary_path) if summary_path.exists() else {}
    quality_analysis = read(quality_path) if quality_path.exists() else {}
    provider_audit = read(provider_audit_path) if provider_audit_path.exists() else {}
    entries = [read(path) for path in sorted((session / "questions").glob("*.json"))]
    target_responses = sum(bool(entry.get("response")) for entry in entries)
    hard_errors = sum(bool(entry.get("_error")) for entry in entries)
    setup_failures = sum(bool(entry.get("setup_failed")) for entry in entries)
    keys = [
        (entry.get("iteration"), entry.get("category_id"), entry.get("question_number"))
        for entry in entries
    ]
    response_models = sorted({
        str(((entry.get("response") or {}).get("emotion_steering") or {}).get("model"))
        for entry in entries
        if ((entry.get("response") or {}).get("emotion_steering") or {}).get("model")
    })
    response_providers = sorted({
        str(((entry.get("response") or {}).get("emotion_steering") or {}).get("provider"))
        for entry in entries
        if ((entry.get("response") or {}).get("emotion_steering") or {}).get("provider")
    })
    checks = {
        "config_exists": config_path.exists(),
        "summary_exists": summary_path.exists(),
        "quality_analysis_exists": quality_path.exists(),
        "config_model_exact": config.get("model") == args.expected_model,
        "question_file_count_exact": len(entries) == args.expected_questions,
        "target_response_count_exact": target_responses == args.expected_questions,
        "hard_errors_zero": hard_errors == 0,
        "setup_failures_zero": setup_failures == 0,
        "question_keys_unique": len(keys) == len(set(keys)),
        "summary_total_exact": summary.get("total_questions") == args.expected_questions,
        "quality_total_exact": (quality_analysis.get("summary") or {}).get("total_questions") == args.expected_questions,
        "response_debug_models_exact": bool(response_models) and response_models == [args.expected_model],
    }
    if args.expected_provider:
        configured_provider = config.get("llm_provider") or config.get("provider")
        checks["config_provider_exact"] = configured_provider == args.expected_provider
        checks["response_debug_providers_exact"] = bool(response_providers) and response_providers == [args.expected_provider]
    if config.get("force_single_model") and config.get("provider_contract"):
        audit_requests = provider_audit.get("requests") or []
        expected_pair = (args.expected_provider, args.expected_model)
        checks["provider_audit_exists"] = provider_audit_path.exists()
        checks["provider_audit_passed"] = provider_audit.get("passed") is True
        checks["provider_audit_requests_present"] = bool(audit_requests)
        checks["provider_audit_requests_exact"] = bool(args.expected_provider) and all(
            (request.get("provider"), request.get("model")) == expected_pair
            for request in audit_requests
        )
        checks["provider_audit_emotions_local"] = (
            ((provider_audit.get("components") or {}).get("emotions") or {}).get("mode")
            == "simple_local_rules"
        )
    selected_keys = expected_selected_keys(config)
    if selected_keys is not None:
        checks["question_selection_exact"] = set(keys) == selected_keys
    report = {
        "schema_version": 1,
        "session": str(session.relative_to(ROOT)),
        "expected_model": args.expected_model,
        "expected_questions": args.expected_questions,
        "checks": checks,
        "passed": all(checks.values()),
        "question_files": len(entries),
        "target_responses": target_responses,
        "hard_errors": hard_errors,
        "setup_failures": setup_failures,
        "response_models": response_models,
        "response_providers": response_providers,
        "provider_audit": provider_audit,
        "summary": summary,
        "posthoc_quality_summary": quality_analysis.get("summary") or {},
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
