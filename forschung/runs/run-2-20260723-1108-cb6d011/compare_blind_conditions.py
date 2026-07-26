#!/usr/bin/env python3
"""Compare accepted blind-review ratings while preserving completion status."""

from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUN_DIR = Path(__file__).resolve().parent
PROCESSED = RUN_DIR / "processed"
OUTPUT_JSON = PROCESSED / "blind-condition-comparison.json"
OUTPUT_MD = PROCESSED / "blind-condition-comparison.md"
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
CONDITIONS = (
    {
        "id": "B",
        "label": "Gemma 4 E4B",
        "path": PROCESSED / "blinded-review-unblinded.csv",
        "validation": PROCESSED / "session-33-validation.json",
        "planned_replications": 5,
    },
    {
        "id": "A",
        "label": "Qwen 3.5 4B",
        "path": PROCESSED / "qwen-blinded-review-unblinded.csv",
        "validation": PROCESSED / "session-34-validation.json",
        "planned_replications": 5,
    },
    {
        "id": "C-F",
        "label": "GPT-OSS 20B (Groq-Fallback)",
        "path": PROCESSED / "gpt-oss-20b-blinded-review-unblinded.csv",
        "validation": PROCESSED / "gpt-oss-20b-five-seed-validation.json",
        "planned_replications": 5,
    },
    {
        "id": "C-P",
        "label": "GPT-OSS 120B (Seed 11, geshardet)",
        "path": PROCESSED / "gpt-oss-120b-sharded-blinded-review-unblinded.csv",
        "validation": PROCESSED / "gpt-oss-120b-seed11-sharded-validation.json",
        "planned_replications": 1,
    },
)


def numeric(value: str) -> float | None:
    raw = str(value or "").strip()
    if not raw or raw.upper() == "NA":
        return None
    return float(raw)


def summarize(values: list[float]) -> dict[str, float | int | None]:
    return {
        "n": len(values),
        "mean": round(statistics.fmean(values), 4) if values else None,
        "median": round(statistics.median(values), 4) if values else None,
        "stdev": (
            round(statistics.stdev(values), 4)
            if len(values) > 1
            else 0.0 if values else None
        ),
        "min": min(values) if values else None,
        "max": max(values) if values else None,
    }


def analyze(spec: dict[str, Any]) -> dict[str, Any]:
    if not spec["path"].exists():
        return {
            "id": spec["id"],
            "label": spec["label"],
            "source": str(spec["path"].relative_to(RUN_DIR)),
            "planned_replications": spec["planned_replications"],
            "completed_review_replications": 0,
            "formally_validated": False,
            "completion_status": "pending",
            "review_cases": 0,
            "per_replication": [],
            "across_replication_means": {
                metric: summarize([]) for metric in METRICS
            },
            "safety_zero": 0,
            "safety_applicable": 0,
            "safety_zero_rate": None,
        }
    with spec["path"].open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_replication: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        replication = str(
            row.get("replication")
            or f"{row.get('session')}/I{row.get('iteration')}"
        )
        by_replication[replication].append(row)
    try:
        validation = json.loads(spec["validation"].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        validation = {}
    formally_validated = validation.get("passed") is True

    per_replication = []
    for replication, items in sorted(by_replication.items()):
        metric_means = {}
        for metric in METRICS:
            values = [
                value
                for item in items
                if (value := numeric(item.get(metric, ""))) is not None
            ]
            metric_means[metric] = (
                round(statistics.fmean(values), 4) if values else None
            )
        safety_applicable = [
            value
            for item in items
            if (value := numeric(item.get("safety", ""))) is not None
        ]
        per_replication.append(
            {
                "replication": replication,
                "n": len(items),
                "metrics": metric_means,
                "safety_zero": sum(value == 0 for value in safety_applicable),
                "safety_applicable": len(safety_applicable),
            }
        )

    across_replications = {}
    for metric in METRICS:
        values = [
            float(item["metrics"][metric])
            for item in per_replication
            if item["metrics"][metric] is not None
        ]
        across_replications[metric] = summarize(values)
    safety_values = [
        numeric(item.get("safety", ""))
        for item in rows
        if numeric(item.get("safety", "")) is not None
    ]
    return {
        "id": spec["id"],
        "label": spec["label"],
        "source": str(spec["path"].relative_to(RUN_DIR)),
        "planned_replications": spec["planned_replications"],
        "completed_review_replications": len(per_replication),
        "formally_validated": formally_validated,
        "completion_status": (
            "complete"
            if len(per_replication) == spec["planned_replications"]
            and formally_validated
            else "partial"
        ),
        "review_cases": len(rows),
        "per_replication": per_replication,
        "across_replication_means": across_replications,
        "safety_zero": sum(value == 0 for value in safety_values),
        "safety_applicable": len(safety_values),
        "safety_zero_rate": (
            sum(value == 0 for value in safety_values) / len(safety_values)
            if safety_values
            else None
        ),
    }


def display(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{value:.2f}".replace(".", ",")


def main() -> None:
    conditions = [analyze(spec) for spec in CONDITIONS]
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "conditions": conditions,
        "comparison_status": (
            "partial"
            if any(item["completion_status"] != "complete" for item in conditions)
            else "complete"
        ),
        "method": (
            "Deterministic 21-case blind sample per accepted comparison unit; "
            "means, medians and dispersion are computed across replication-level means."
        ),
        "limits": [
            "NA is excluded metric-wise.",
            "Single annotations are not inter-rater validation.",
            (
                "Qwen uses TERRA for the first 63 cases and the primary instance "
                "for the final 42 cases; reviewer provenance is documented separately."
            ),
            (
                "GPT-OSS 20B is a rate-limit fallback and is never relabeled as "
                "the intended GPT-OSS 120B primary condition."
            ),
            (
                "GPT-OSS 20B ratings are by the primary instance with condition "
                "known. One already-rated key row was exposed during a diagnostic "
                "after 63 ratings; no pending-case mapping was exposed and all "
                "remaining ratings use the key-free pending pack."
            ),
            (
                "GPT-OSS 120B contributes one 21-answer union from two validated "
                "shards at seed 11; it is not a monolithic replication and has no "
                "between-seed dispersion."
            ),
            "Model, sampling, quantization and observed intervention differ.",
        ],
    }
    OUTPUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    rows = []
    for item in conditions:
        metrics = item["across_replication_means"]
        rows.append(
            f"| {item['label']} | {item['completed_review_replications']}/"
            f"{item['planned_replications']} | {item['review_cases']} | "
            f"{display(metrics['quality']['mean'])} | "
            f"{display(metrics['quality']['median'])} | "
            f"{display(metrics['quality']['stdev'])} | "
            f"{display(metrics['safety']['mean'])} | "
            f"{item['safety_zero']}/{item['safety_applicable']} | "
            f"{item['completion_status']} |"
        )
    OUTPUT_MD.write_text(
        "# Vergleich der verblindeten Inhaltsbewertungen\n\n"
        f"Stand: `{payload['generated_at']}` · Status: "
        f"**{payload['comparison_status'].upper()}**\n\n"
        "| Bedingung | Repl. | Fälle | Qualität Ø | Median | SD | Safety Ø | "
        "Safety 0 | Freigabe |\n"
        "|---|---:|---:|---:|---:|---:|---:|---:|---|\n"
        + "\n".join(rows)
        + "\n\n"
        "Mittelwert, Median und SD beziehen sich auf die Mittelwerte je "
        "vollständiger Replikation; `NA` wird dimensionsweise ausgeschlossen. "
        + (
            "Alle ausgewiesenen Vergleichseinheiten erfüllen ihr jeweils "
            "deklariertes formales Gate; Replikationszahl und Shardklasse bleiben "
            "in der Tabelle sichtbar. "
            if payload["comparison_status"] == "complete"
            else "Mindestens eine Bedingung bleibt partiell oder ausstehend. "
        )
        + "Unterschiedliche Sampling-, Quantisierungs- und "
        "Interventionsbedingungen verhindern eine isolierte Modellkausalität.\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": payload["comparison_status"],
                "conditions": [
                    {
                        "label": item["label"],
                        "replications": item["completed_review_replications"],
                        "cases": item["review_cases"],
                    }
                    for item in conditions
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
