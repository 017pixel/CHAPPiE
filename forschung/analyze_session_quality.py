"""Reanalysiert vorhandene Research-Session-Logs mit den aktuellen Qualitaetsregeln."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from forschung.session_logger import LOG_ROOT, evaluate_response_quality


def _load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def analyze_session(session_dir: Path) -> Dict[str, Any]:
    config = _load_json(session_dir / "config.json") if (session_dir / "config.json").exists() else {}
    questions_dir = session_dir / "questions"
    question_files = sorted(questions_dir.glob("*.json")) if questions_dir.exists() else []

    counters = {
        "total_questions": 0,
        "completed": 0,
        "valid_completed": 0,
        "generation_failures": 0,
        "formatting_failures": 0,
        "quality_failures": 0,
        "context_budget_failures": 0,
        "setup_failures": 0,
        "cot_leaks": 0,
        "memory_contamination_hits": 0,
        "content_relevance_warnings": 0,
        "safety_evaluation_unusable": 0,
    }
    question_results = []

    for path in question_files:
        entry = _load_json(path)
        response = entry.get("response") or {}
        setup_results = entry.get("setup_results") or []
        setup_qualities = []
        for item in setup_results:
            setup_qualities.append(item.get("quality") or evaluate_response_quality(
                item,
                question_text=item.get("prompt", ""),
                category_name=entry.get("category", ""),
                enable_thinking=config.get("enable_thinking"),
            ))
        setup_failed = bool(entry.get("setup_failed") or any(quality.get("quality_failed") for quality in setup_qualities) or any(item.get("_error") for item in setup_results))
        quality = evaluate_response_quality(
            response,
            question_text=entry.get("question_text", ""),
            category_name=entry.get("category", ""),
            setup_failed=setup_failed,
            enable_thinking=config.get("enable_thinking"),
        )
        has_response = bool(response)
        hard_error = bool(entry.get("_error"))
        valid = has_response and not hard_error and not setup_failed and not quality.get("quality_failed")

        counters["total_questions"] += 1
        counters["completed"] += 0 if hard_error else 1
        counters["valid_completed"] += 1 if valid else 0
        for key in (
            "generation_failed",
            "formatting_failed",
            "quality_failed",
            "context_budget_failed",
            "setup_failed",
            "cot_leak",
            "memory_error_contamination",
            "content_relevance_warning",
            "safety_evaluation_unusable",
        ):
            summary_key = {
                "generation_failed": "generation_failures",
                "formatting_failed": "formatting_failures",
                "quality_failed": "quality_failures",
                "context_budget_failed": "context_budget_failures",
                "setup_failed": "setup_failures",
                "cot_leak": "cot_leaks",
                "memory_error_contamination": "memory_contamination_hits",
                "content_relevance_warning": "content_relevance_warnings",
                "safety_evaluation_unusable": "safety_evaluation_unusable",
            }[key]
            counters[summary_key] += 1 if quality.get(key) else 0

        question_results.append({
            "file": path.name,
            "category": entry.get("category"),
            "question_number": entry.get("question_number"),
            "valid": valid,
            "quality": quality,
            "setup_quality": setup_qualities,
        })

    report = {
        "session_dir": str(session_dir),
        "source_config": {
            "session_id": config.get("session_id"),
            "enable_thinking": config.get("enable_thinking"),
            "formatting_mode": config.get("formatting_mode"),
        },
        "summary": counters,
        "questions": question_results,
    }
    out_path = session_dir / "quality_analysis.json"
    with open(out_path, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Reanalysiert eine CHAPPiE Research-Session.")
    parser.add_argument("session", help="Session-Ordner, z.B. session_6 oder forschung/session_logs/session_6")
    args = parser.parse_args()

    session_dir = Path(args.session)
    if not session_dir.exists():
        session_dir = LOG_ROOT / args.session
    if not session_dir.exists() or not session_dir.is_dir():
        raise SystemExit(f"Session nicht gefunden: {args.session}")

    report = analyze_session(session_dir)
    print(json.dumps(report["summary"], indent=2, ensure_ascii=False))
    print(f"Analyse geschrieben: {session_dir / 'quality_analysis.json'}")


if __name__ == "__main__":
    main()
