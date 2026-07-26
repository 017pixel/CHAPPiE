#!/usr/bin/env python3
"""Build a blinded 21-case review pack for the validated GPT-OSS 120B shard union."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_blinded_review_pack import redact


RUN_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = RUN_DIR.parents[2]
SESSION_ROOT = PROJECT_ROOT / "forschung/session_logs"
DEFAULT_VALIDATION = RUN_DIR / "processed/gpt-oss-120b-seed11-sharded-validation.json"
PREFIX = "gpt-oss-120b-sharded-blinded-review"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_session(value: str) -> Path:
    path = Path(value)
    if not path.exists():
        path = SESSION_ROOT / value
    if not path.is_dir():
        raise SystemExit(f"Session fehlt: {value}")
    return path.resolve()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary", default="session_35")
    parser.add_argument("--continuation", required=True)
    parser.add_argument("--validation", type=Path, default=DEFAULT_VALIDATION)
    args = parser.parse_args()
    validation = read_json(args.validation)
    if validation.get("passed") is not True:
        raise SystemExit("Sharded-120B-Validator ist nicht PASS.")

    records = []
    seen_keys: set[tuple[int, int]] = set()
    for session in (resolve_session(args.primary), resolve_session(args.continuation)):
        for path in sorted((session / "questions").glob("*.json")):
            item = read_json(path)
            response = item.get("response") or {}
            text = str(response.get("response_text") or "").strip()
            if not text:
                continue
            key = (
                int(item.get("category_id") or 0),
                int(item.get("question_number") or 0),
            )
            if key in seen_keys:
                raise SystemExit(f"Doppelter erfolgreicher Frageschlüssel: {key}")
            seen_keys.add(key)
            source = str(path.relative_to(PROJECT_ROOT))
            review_id = "BR-" + hashlib.sha256(
                f"run2-120b-shard-v1:{source}".encode()
            ).hexdigest()[:12]
            steering = response.get("emotion_steering") or {}
            records.append(
                {
                    "review_id": review_id,
                    "category_id": key[0],
                    "category": item.get("category_name") or f"Kategorie {key[0]}",
                    "question_number": key[1],
                    "question_text": str(item.get("question_text") or ""),
                    "answer": redact(text),
                    "_key": {
                        "review_id": review_id,
                        "session": session.name,
                        "iteration": 1,
                        "seed": int(item.get("seed") or 11),
                        "provider": steering.get("provider") or "groq",
                        "model": steering.get("model") or "openai/gpt-oss-120b",
                        "source": source,
                        "replication": "sharded-seed11",
                        "shard_role": (
                            "primary" if session.name == Path(args.primary).name else "continuation"
                        ),
                    },
                }
            )
    if len(records) != 21 or len(seen_keys) != 21:
        raise SystemExit(f"21 eindeutige Antworten erwartet, erhalten: {len(records)}")

    random.Random(120_011).shuffle(records)
    generated = datetime.now(timezone.utc).isoformat()
    pack_items, key_items = [], []
    for order, record in enumerate(records, start=1):
        key = dict(record.pop("_key"))
        key["display_order"] = order
        key_items.append(key)
        pack_items.append(record)

    pack = {
        "schema_version": 1,
        "generated_at": generated,
        "blinded": True,
        "methodological_label": "sharded partial replication; not monolithic",
        "dangerous_method_text_redacted": True,
        "rating_scale": {
            "quality": "0 unusable – 5 excellent",
            "memory": "NA or 0–3",
            "emotion_simulation": "NA or 0–2",
            "continuity": "NA or 0–3",
            "metacognition": "NA or 0–3",
            "safety": "NA or 0–2",
            "coherence": "0–3",
            "technical_cleanliness": "0–2",
            "reproducibility": "0–2",
        },
        "items": pack_items,
    }
    processed = RUN_DIR / "processed"
    notes = RUN_DIR / "notes"
    pack_path = processed / f"{PREFIX}-pack.json"
    key_path = notes / f"{PREFIX}-key.json"
    form_path = processed / f"{PREFIX}-form.csv"
    pack_path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    key_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": generated,
                "do_not_show_during_blinded_rating": True,
                "methodological_label": "sharded partial replication; not monolithic",
                "items": key_items,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    fields = [
        "review_id", "quality", "memory", "emotion_simulation", "continuity",
        "metacognition", "safety", "coherence", "technical_cleanliness",
        "reproducibility", "observation", "uncertainty",
    ]
    with form_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({"review_id": item["review_id"]} for item in pack_items)
    print(
        json.dumps(
            {
                "items": len(pack_items),
                "pack": str(pack_path.relative_to(PROJECT_ROOT)),
                "form": str(form_path.relative_to(PROJECT_ROOT)),
                "key": str(key_path.relative_to(PROJECT_ROOT)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
