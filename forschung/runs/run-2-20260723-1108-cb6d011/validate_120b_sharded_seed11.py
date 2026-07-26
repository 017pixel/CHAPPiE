#!/usr/bin/env python3
"""Validate the two-session GPT-OSS 120B seed-11 shard contract."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUN_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = RUN_DIR.parents[2]
SESSION_ROOT = PROJECT_ROOT / "forschung/session_logs"
TARGET_CONFIG = RUN_DIR / "raw/cloud-configs/gpt-oss-120b-seed-11.config.json"
DEFAULT_OUTPUT = RUN_DIR / "processed/gpt-oss-120b-seed11-sharded-validation.json"
MODEL = "openai/gpt-oss-120b"
PROVIDER = "groq"
CONTROLLED_CONFIG_FIELDS = (
    "temperature",
    "top_p",
    "top_k",
    "include_reasoning",
    "provider_max_completion_tokens",
    "formatting_mode",
    "ablation_profile",
    "force_single_model",
    "enable_thinking",
    "intent_provider",
    "query_extraction_provider",
    "reset_per_category",
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_session(value: str) -> Path:
    candidate = Path(value)
    if not candidate.exists():
        candidate = SESSION_ROOT / value
    if not candidate.is_dir():
        raise SystemExit(f"Session fehlt: {value}")
    return candidate.resolve()


def keys_from_selection(config: dict[str, Any]) -> set[tuple[int, int]]:
    return {
        (int(category), int(question))
        for category, questions in (config.get("question_selection") or {}).items()
        for question in questions
    }


def inspect(session: Path) -> dict[str, Any]:
    config = read_json(session / "config.json")
    summary = read_json(session / "summary.json")
    quality = read_json(session / "quality_analysis.json")
    audit = read_json(session / "provider_audit.json")
    questions = [
        read_json(path) for path in sorted((session / "questions").glob("*.json"))
    ]
    successful = [
        item for item in questions if item.get("response") and not item.get("_error")
    ]
    errors = [item for item in questions if item.get("_error") or not item.get("response")]
    response_pairs = {
        (
            str(((item.get("response") or {}).get("emotion_steering") or {}).get("provider")),
            str(((item.get("response") or {}).get("emotion_steering") or {}).get("model")),
        )
        for item in successful
    }
    return {
        "session": str(session.relative_to(PROJECT_ROOT)),
        "config": config,
        "summary": summary,
        "quality": quality,
        "provider_audit": audit,
        "question_files": len(questions),
        "successful": len(successful),
        "errors": len(errors),
        "successful_keys": {
            (int(item.get("category_id") or 0), int(item.get("question_number") or 0))
            for item in successful
        },
        "all_keys": {
            (int(item.get("category_id") or 0), int(item.get("question_number") or 0))
            for item in questions
        },
        "seeds": sorted(
            {int(item.get("seed")) for item in questions if item.get("seed") is not None}
        ),
        "response_pairs": response_pairs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary", default="session_35")
    parser.add_argument("--continuation", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    primary = inspect(resolve_session(args.primary))
    continuation = inspect(resolve_session(args.continuation))
    target_config = read_json(TARGET_CONFIG)
    target = keys_from_selection(target_config)
    primary_keys = primary["successful_keys"]
    continuation_keys = continuation["successful_keys"]
    combined = primary_keys | continuation_keys
    checks = {
        "primary_model_provider": (
            primary["config"].get("model"),
            primary["config"].get("llm_provider"),
        )
        == (MODEL, PROVIDER),
        "continuation_model_provider": (
            continuation["config"].get("model"),
            continuation["config"].get("llm_provider"),
        )
        == (MODEL, PROVIDER),
        "both_seed_11": primary["seeds"] == [11] and continuation["seeds"] == [11],
        "primary_controlled_settings_match_target": all(
            primary["config"].get(field) == target_config.get(field)
            for field in CONTROLLED_CONFIG_FIELDS
        ),
        "continuation_controlled_settings_match_target": all(
            continuation["config"].get(field) == target_config.get(field)
            for field in CONTROLLED_CONFIG_FIELDS
        ),
        "shards_controlled_settings_identical": all(
            primary["config"].get(field) == continuation["config"].get(field)
            for field in CONTROLLED_CONFIG_FIELDS
        ),
        "both_provider_audits_pass": primary["provider_audit"].get("passed") is True
        and continuation["provider_audit"].get("passed") is True,
        "both_response_contracts_exact": primary["response_pairs"]
        == {(PROVIDER, MODEL)}
        and continuation["response_pairs"] == {(PROVIDER, MODEL)},
        "primary_expected_partial_shape": primary["question_files"] == 12
        and primary["successful"] == 11
        and primary["errors"] == 1,
        "primary_posthoc_valid_11": (
            primary["quality"].get("summary") or {}
        ).get("valid_completed")
        == 11,
        "continuation_expected_shape": continuation["question_files"] == 10
        and continuation["successful"] == 10
        and continuation["errors"] == 0,
        "continuation_summary_valid_10": continuation["summary"].get(
            "valid_completed"
        )
        == 10
        and (continuation["quality"].get("summary") or {}).get("valid_completed")
        == 10,
        "no_duplicate_successful_keys": not (primary_keys & continuation_keys),
        "combined_21_unique_keys": len(combined) == 21,
        "combined_keys_match_original_selection": combined == target,
        "continuation_declares_shard": continuation["config"].get(
            "completion_class"
        )
        == "sharded_continuation",
        "category_state_reset_in_both": primary["config"].get(
            "reset_per_category"
        )
        is True
        and continuation["config"].get("reset_per_category") is True,
    }
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "resource_class": "POST_PROCESSING",
        "classification": "TEST_VALID_SHARDED" if all(checks.values()) else "TEST_PARTIAL",
        "methodological_label": "sharded partial replication; not monolithic",
        "model": MODEL,
        "provider": PROVIDER,
        "seed": 11,
        "checks": checks,
        "passed": all(checks.values()),
        "combined_unique_answers": len(combined),
        "target_answers": len(target),
        "primary": {
            key: value
            for key, value in primary.items()
            if key
            not in {
                "config",
                "summary",
                "quality",
                "provider_audit",
                "successful_keys",
                "all_keys",
                "response_pairs",
            }
        },
        "continuation": {
            key: value
            for key, value in continuation.items()
            if key
            not in {
                "config",
                "summary",
                "quality",
                "provider_audit",
                "successful_keys",
                "all_keys",
                "response_pairs",
            }
        },
        "limit": (
            "The two shards have identical model/provider/seed and reset research "
            "state per category, but a two-session shard is not a monolithic replication."
        ),
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
                "classification": report["classification"],
                "checks_passed": sum(checks.values()),
                "checks_total": len(checks),
                "combined_unique_answers": len(combined),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
