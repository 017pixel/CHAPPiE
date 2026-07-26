#!/usr/bin/env python3
"""Join accepted blind ratings to their key and summarize by iteration/category."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


RUN_DIR = Path(__file__).resolve().parent
PROCESSED = RUN_DIR / "processed"
METRICS = (
    "quality",
    "memory",
    "emotion_simulation",
    "continuity",
    "metacognition",
    "safety",
    "coherence",
    "technical_cleanliness",
    "reproducibility",
)


def numeric(value: str) -> float | None:
    value = value.strip()
    if not value or value.upper() == "NA":
        return None
    return float(value)


def summarize(rows: list[dict[str, str]], field: str) -> list[dict[str, object]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[row[field]].append(row)
    result = []
    for label, items in sorted(groups.items(), key=lambda pair: pair[0]):
        metrics = {}
        for metric in METRICS:
            values = [
                value
                for item in items
                if (value := numeric(item.get(metric, ""))) is not None
            ]
            metrics[metric] = (
                round(sum(values) / len(values), 3) if values else None
            )
        result.append({"label": label, "n": len(items), "metrics": metrics})
    return result


def display(value: object) -> str:
    return "—" if value is None else f"{float(value):.2f}".replace(".", ",")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", default="blinded-review")
    parser.add_argument(
        "--ratings",
        type=Path,
        help="Optionale Rating-CSV; Standard: processed/<prefix>-terra-ratings.csv",
    )
    args = parser.parse_args()
    key_path = RUN_DIR / f"notes/{args.prefix}-key.json"
    pack_path = PROCESSED / f"{args.prefix}-pack.json"
    provenance_path = RUN_DIR / f"notes/{args.prefix}-provenance.json"
    ratings_path = (
        args.ratings.resolve()
        if args.ratings
        else PROCESSED / f"{args.prefix}-terra-ratings.csv"
    )
    output_csv = PROCESSED / f"{args.prefix}-unblinded.csv"
    output_md = PROCESSED / f"{args.prefix}-unblinded-summary.md"

    key_payload = json.loads(key_path.read_text(encoding="utf-8"))
    keys = {item["review_id"]: item for item in key_payload["items"]}
    with ratings_path.open(encoding="utf-8", newline="") as handle:
        ratings = list(csv.DictReader(handle))
    if len(ratings) != len(keys) or {row["review_id"] for row in ratings} != set(keys):
        raise RuntimeError("Rating- und Key-IDs stimmen nicht vollständig überein")

    rows: list[dict[str, str]] = []
    for rating in ratings:
        key = keys[rating["review_id"]]
        rows.append(
            {
                **rating,
                "session": str(key["session"]),
                "iteration": str(key["iteration"]),
                "replication": (
                    str(key.get("replication"))
                    if key.get("replication")
                    else f"{key['session']}/I{key['iteration']}"
                ),
                "seed": str(key["seed"]),
                "provider": str(key.get("provider") or ""),
                "model": str(key["model"]),
                "source": str(key["source"]),
            }
        )
    fieldnames = list(rows[0])
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    by_replication = summarize(rows, "replication")
    by_category = summarize(rows, "category") if "category" in rows[0] else []
    # Category lives in the blind pack, not in the key or rating CSV.
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    provenance = (
        json.loads(provenance_path.read_text(encoding="utf-8"))
        if provenance_path.exists()
        else {}
    )
    category_by_id = {
        item["review_id"]: str(item["category"]) for item in pack["items"]
    }
    for row in rows:
        row["category"] = category_by_id[row["review_id"]]
    by_category = summarize(rows, "category")

    header = (
        "| Gruppe | n | Qualität | Memory | Gefühl | Kont. | Meta | Safety | "
        "Kohärenz | Technik |"
    )
    divider = "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"

    def lines(groups: list[dict[str, object]]) -> list[str]:
        output = [header, divider]
        for group in groups:
            metric = group["metrics"]
            output.append(
                f"| {group['label']} | {group['n']} | "
                f"{display(metric['quality'])} | {display(metric['memory'])} | "
                f"{display(metric['emotion_simulation'])} | "
                f"{display(metric['continuity'])} | "
                f"{display(metric['metacognition'])} | "
                f"{display(metric['safety'])} | "
                f"{display(metric['coherence'])} | "
                f"{display(metric['technical_cleanliness'])} |"
            )
        return output

    safety_zero = [row for row in rows if row.get("safety") == "0"]
    title = provenance.get(
        "title",
        "Kontrolliert entblindete TERRA-Erstbewertung",
    )
    intro = provenance.get(
        "summary_text",
        "Die Bewertung wurde vor Öffnung des Schlüssels formal abgenommen. "
        "Erst danach wurden Modell, Seed, Iteration und Quellpfad zugespielt. "
        "Das ist ein unabhängiges Erst-Rating, keine doppelte Humanannotation.",
    )
    extra_limit = provenance.get("methodological_limit")
    md = [
        f"# {title}",
        "",
        f"Stand: `{datetime.now(timezone.utc).isoformat()}`",
        "",
        str(intro),
        "",
        f"Alle **{len(rows)}** Fälle gehören laut Session-Konfiguration zu "
        f"`{rows[0]['model']}` über `{rows[0]['provider']}`. Die Provider-/"
        "Modellidentität wird zusätzlich bei der finalen Sessionvalidierung geprüft.",
        "",
        "## Nach Replikation",
        "",
        *lines(by_replication),
        "",
        "## Nach Kategorie",
        "",
        *lines(by_category),
        "",
        "## Safety-Prioritäten",
        "",
        f"**{len(safety_zero)}** Fälle erhielten Safety `0`. Ihre IDs und "
        f"Quellpfade stehen in `{output_csv.name}`; schädliche "
        "Methodendetails bleiben aus Bericht und Zusammenfassung ausgeschlossen.",
        "",
        "## Methodische Grenze",
        "",
        f"Die ausgewerteten {len(by_replication)} "
        f"{'Replikation stammt' if len(by_replication) == 1 else 'Replikationen stammen'} "
        "aus derselben Modell-/Providerbedingung. "
        "Der Review umfasst eine deterministische 21-Fragen-Stichprobe pro "
        "vollständiger Replikation. Mittelwerte schließen `NA` aus und dürfen "
        "ohne denselben Blindprozess nicht direkt mit anderen Bedingungen "
        "verglichen werden.",
    ]
    if extra_limit:
        md.extend(("", str(extra_limit)))
    md.append("")
    output_md.write_text("\n".join(md), encoding="utf-8")
    print(
        json.dumps(
            {
                "ratings": len(rows),
                "iterations": len(by_replication),
                "safety_zero": len(safety_zero),
                "model": rows[0]["model"],
                "provider": rows[0]["provider"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
