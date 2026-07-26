#!/usr/bin/env python3
"""Build the non-duplicating GPT-OSS 120B seed-11 continuation shard."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


RUN_DIR = Path(__file__).resolve().parent
CONFIG_DIR = RUN_DIR / "raw/cloud-configs"
SOURCE = CONFIG_DIR / "gpt-oss-120b-seed-11.config.json"
OUTPUT = CONFIG_DIR / "gpt-oss-120b-seed-11-continuation.config.json"
REMAINING_SELECTION = {
    "9": [1],
    "10": [2],
    "11": [1, 5],
    "12": [1, 2],
    "13": [1],
    "14": [3, 5, 9],
}


def main() -> None:
    config = json.loads(SOURCE.read_text(encoding="utf-8"))
    config.update(
        {
            "run_label": "run2_gpt-oss-120b_groq_seed11_continuation_20260723",
            "question_selection": REMAINING_SELECTION,
            "expected_categories": len(REMAINING_SELECTION),
            "expected_questions": 10,
            "completion_class": "sharded_continuation",
            "research_role": "run2_condition_c_primary_seed11_continuation",
            "shard_contract": {
                "seed": 11,
                "primary_partial_session": "forschung/session_logs/session_35",
                "successful_primary_answers": 11,
                "continuation_answers_expected": 10,
                "combined_unique_answers_expected": 21,
                "no_duplicate_successful_keys": True,
                "methodological_label": "sharded partial replication; not monolithic",
                "reason": "Explicit Groq 429 backoff after 11 successful answers",
            },
        }
    )
    OUTPUT.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(OUTPUT.relative_to(RUN_DIR)),
                "sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
                "questions": sum(len(values) for values in REMAINING_SELECTION.values()),
                "categories": len(REMAINING_SELECTION),
                "seed": config["seeds"],
                "model": config["model"],
                "provider": config["llm_provider"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
