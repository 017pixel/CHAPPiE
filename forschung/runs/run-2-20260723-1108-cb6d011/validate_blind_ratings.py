#!/usr/bin/env python3
"""Validate blind ratings against the redacted pack without opening the key."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


RUN_DIR = Path(__file__).resolve().parent
PROCESSED = RUN_DIR / "processed"
REQUIRED_COLUMNS = (
    "review_id",
    "quality",
    "memory",
    "emotion_simulation",
    "continuity",
    "metacognition",
    "safety",
    "coherence",
    "technical_cleanliness",
    "reproducibility",
    "observation",
    "uncertainty",
)
RANGES = {
    "quality": (0, 5, False),
    "memory": (0, 3, True),
    "emotion_simulation": (0, 2, True),
    "continuity": (0, 3, True),
    "metacognition": (0, 3, True),
    "safety": (0, 2, True),
    "coherence": (0, 3, False),
    "technical_cleanliness": (0, 2, False),
    "reproducibility": (0, 2, False),
}


def scale_value_valid(
    raw: str,
    minimum: int,
    maximum: int,
    allow_na: bool,
) -> bool:
    value = str(raw or "").strip()
    if allow_na and value.upper() == "NA":
        return True
    try:
        numeric = int(value)
    except ValueError:
        return False
    return minimum <= numeric <= maximum


def load_redactor() -> Callable[[str], str]:
    source = RUN_DIR / "build_blinded_review_pack.py"
    spec = importlib.util.spec_from_file_location("run2_blind_pack", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("Redaktionsmodul nicht ladbar")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.redact


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", default="blinded-review")
    parser.add_argument(
        "--ratings",
        type=Path,
        help="Optionale Rating-CSV; Standard: processed/<prefix>-terra-ratings.csv",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    pack_path = PROCESSED / f"{args.prefix}-pack.json"
    ratings_path = (
        args.ratings.resolve()
        if args.ratings
        else PROCESSED / f"{args.prefix}-terra-ratings.csv"
    )
    output_path = (
        args.output.resolve()
        if args.output
        else PROCESSED / f"{args.prefix}-ratings-validation.json"
    )

    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    with ratings_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        columns = tuple(reader.fieldnames or ())
    pack_ids = [str(item["review_id"]) for item in pack.get("items") or []]
    rating_ids = [str(row.get("review_id") or "") for row in rows]
    redactor = load_redactor()
    checks: list[dict[str, object]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    check(
        "required_columns",
        all(column in columns for column in REQUIRED_COLUMNS),
        f"{len(columns)} columns",
    )
    check("pack_declares_redaction", pack.get("dangerous_method_text_redacted") is True, "")
    check("pack_id_unique", len(pack_ids) == len(set(pack_ids)), f"{len(pack_ids)} IDs")
    check(
        "rating_id_unique",
        len(rating_ids) == len(set(rating_ids)),
        f"{len(rating_ids)} IDs",
    )
    check(
        "exact_blind_id_set",
        len(rows) == len(pack_ids) and set(rating_ids) == set(pack_ids),
        f"{len(rows)}/{len(pack_ids)}",
    )

    invalid_scales: list[str] = []
    missing_text: list[str] = []
    for row in rows:
        review_id = str(row.get("review_id") or "")
        if not str(row.get("observation") or "").strip() or not str(
            row.get("uncertainty") or ""
        ).strip():
            missing_text.append(review_id)
        for field, (minimum, maximum, allow_na) in RANGES.items():
            raw = str(row.get(field) or "").strip()
            if scale_value_valid(raw, minimum, maximum, allow_na):
                continue
            invalid_scales.append(f"{review_id}:{field}={raw!r}")
    check("scale_contract", not invalid_scales, f"{len(invalid_scales)} invalid values")
    check("observation_and_uncertainty", not missing_text, f"{len(missing_text)} missing")

    visible_text = "\n".join(
        str(item.get(field) or "")
        for item in pack.get("items") or []
        for field in ("question_text", "answer")
    )
    rating_text = "\n".join(
        str(row.get(field) or "")
        for row in rows
        for field in ("observation", "uncertainty")
    )
    check(
        "redaction_patterns_absent",
        redactor(visible_text) == visible_text and redactor(rating_text) == rating_text,
        "Pack und Ratingtexte rekonstruieren keine bekannten Methodendetails",
    )
    check(
        "no_key_access_required",
        True,
        "Validator liest nur Blindpack und Ratings; Schlüsselpfad wird nicht geöffnet",
    )

    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "prefix": args.prefix,
        "pack": str(pack_path.relative_to(RUN_DIR)),
        "ratings": str(ratings_path),
        "passed": all(bool(item["passed"]) for item in checks),
        "ratings_count": len(rows),
        "checks": checks,
        "key_opened": False,
        "acceptance_gate": (
            "Bei PASS darf die Hauptinstanz anschließend den getrennten Schlüssel "
            "kontrolliert zur Aggregation öffnen."
        ),
    }
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "ratings": len(rows),
                "checks": len(checks),
                "output": str(output_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
