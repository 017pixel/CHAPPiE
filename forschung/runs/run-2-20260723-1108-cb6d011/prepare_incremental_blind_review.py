#!/usr/bin/env python3
"""Prepare only unrated items from an expanded redacted blind-review pack."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


RUN_DIR = Path(__file__).resolve().parent
PROCESSED = RUN_DIR / "processed"
FIELDS = (
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--ratings", type=Path, required=True)
    args = parser.parse_args()
    pack_path = PROCESSED / f"{args.prefix}-pack.json"
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    with args.ratings.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        ratings = list(reader)
        columns = tuple(reader.fieldnames or ())
    if not all(field in columns for field in FIELDS):
        raise RuntimeError("Ratingdatei erfüllt den Spaltenvertrag nicht")
    rated_ids = [str(item.get("review_id") or "") for item in ratings]
    if len(rated_ids) != len(set(rated_ids)):
        raise RuntimeError("Ratingdatei enthält doppelte IDs")
    pack_ids = {str(item["review_id"]) for item in pack["items"]}
    if not set(rated_ids) <= pack_ids:
        raise RuntimeError("Ratingdatei enthält IDs außerhalb des aktuellen Blindpakets")
    pending = [
        item for item in pack["items"] if str(item["review_id"]) not in set(rated_ids)
    ]
    pending_json = PROCESSED / f"{args.prefix}-pending-pack.json"
    pending_md = PROCESSED / f"{args.prefix}-pending-pack.md"
    pending_form = PROCESSED / f"{args.prefix}-pending-form.csv"
    pending_json.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_pack": str(pack_path.relative_to(RUN_DIR)),
                "rated_items": len(rated_ids),
                "pending_items": len(pending),
                "dangerous_method_text_redacted": pack.get(
                    "dangerous_method_text_redacted"
                ),
                "items": pending,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Noch unbewertete Blindfälle",
        "",
        f"Bereits bewertet: **{len(rated_ids)}** · offen: **{len(pending)}**",
        "",
        "> Seed, Iteration, Session, Quelle und Schlüssel bleiben verborgen. "
        "Methodendetails bleiben redigiert.",
        "",
    ]
    for index, item in enumerate(pending, start=1):
        lines.extend(
            [
                f"## {index:02d} · `{item['review_id']}` · Kategorie {item['category_id']}",
                "",
                f"**Frage:** {item['question_text']}",
                "",
                f"**Antwort:** {item['answer']}",
                "",
            ]
        )
    pending_md.write_text("\n".join(lines), encoding="utf-8")
    with pending_form.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for item in pending:
            writer.writerow({"review_id": item["review_id"]})
    print(
        json.dumps(
            {
                "pack_items": len(pack["items"]),
                "rated_items": len(rated_ids),
                "pending_items": len(pending),
                "pending_pack": str(pending_json.relative_to(RUN_DIR)),
                "pending_form": str(pending_form.relative_to(RUN_DIR)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
