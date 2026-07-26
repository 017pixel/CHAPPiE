#!/usr/bin/env python3
"""Read Groq's current model catalog once without starting a completion."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brain.groq_brain import GroqBrain


EXCLUDED_SPECIALIST_TERMS = (
    "audio",
    "embed",
    "guard",
    "moderation",
    "playai",
    "speech",
    "tts",
    "whisper",
)


def candidate_class(model_id: str) -> str:
    normalized = model_id.lower()
    if any(term in normalized for term in EXCLUDED_SPECIALIST_TERMS):
        return "excluded_specialist"
    if "compound" in normalized:
        return "excluded_orchestrator"
    return "text_chat_candidate_requires_manual_review"


def compact_model_record(model) -> dict:
    raw = model.model_dump() if hasattr(model, "model_dump") else {}
    model_id = str(raw.get("id") or getattr(model, "id", ""))
    return {
        "id": model_id,
        "active": raw.get("active"),
        "context_window": raw.get("context_window"),
        "max_completion_tokens": raw.get("max_completion_tokens"),
        "owned_by": raw.get("owned_by"),
        "classification": candidate_class(model_id),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="List current Groq models once; no chat/completion request is sent."
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    brain = GroqBrain()
    if not getattr(brain, "_is_initialized", False):
        parser.error("Groq client is not initialized; no valid API key is configured.")

    response = brain.client.models.list()
    records = sorted(
        (compact_model_record(item) for item in response.data),
        key=lambda item: item["id"],
    )
    payload = {
        "schema_version": 1,
        "queried_at": datetime.now(timezone.utc).isoformat(),
        "provider": "groq",
        "request_type": "models.list",
        "completion_started": False,
        "selection_policy": (
            "Specialist, moderation, audio, embedding and orchestrator models are "
            "excluded. Remaining IDs are only candidates and require manual review "
            "for chat support, context, prompt contract and quota before use."
        ),
        "models": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "models": len(records),
                "text_chat_candidates": sum(
                    row["classification"] == "text_chat_candidate_requires_manual_review"
                    for row in records
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
