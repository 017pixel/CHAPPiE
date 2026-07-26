#!/usr/bin/env python3
"""Build offline SVG/JSON figures from validated or explicitly partial Run-2 data."""

from __future__ import annotations

import csv
import html
import json
from datetime import datetime, timezone
from pathlib import Path


RUN_DIR = Path(__file__).resolve().parent
FIGURES = RUN_DIR / "figures"
PROCESSED = RUN_DIR / "processed"
CONDITIONS = (
    {
        "id": "B",
        "label": "Gemma 4 E4B",
        "aggregate": "gemma-live-aggregate.json",
        "behavior": "gemma-behavioral-aggregate.json",
        "blind": "blinded-review-unblinded.csv",
        "validation": "session-33-validation.json",
    },
    {
        "id": "A",
        "label": "Qwen 3.5 4B",
        "aggregate": "qwen-live-aggregate.json",
        "behavior": "qwen-behavioral-aggregate.json",
        "blind": "qwen-blinded-review-unblinded.csv",
        "validation": "session-34-validation.json",
    },
    {
        "id": "C-F",
        "label": "GPT-OSS 20B (Groq-Fallback)",
        "aggregate": "gpt-oss-20b-five-seed-aggregate.json",
        "behavior": "gpt-oss-20b-behavioral-aggregate.json",
        "blind": "gpt-oss-20b-blinded-review-unblinded.csv",
        "validation": "gpt-oss-20b-five-seed-validation.json",
        "replication_validations": [
            f"session-{session_id}-validation.json"
            for session_id in range(36, 41)
        ],
        "partial_aggregate": "gpt-oss-20b-seed71-live-aggregate.json",
    },
)


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def numeric(values: list[str]) -> list[float]:
    result = []
    for value in values:
        try:
            result.append(float(value))
        except (TypeError, ValueError):
            continue
    return result


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def condition_data(config: dict) -> dict:
    aggregate_path = PROCESSED / config["aggregate"]
    behavior_path = PROCESSED / config["behavior"]
    blind_path = PROCESSED / config["blind"]
    validation_path = PROCESSED / config["validation"]
    aggregate = load_json(aggregate_path)
    behavior = load_json(behavior_path)
    complete_iterations = [
        item
        for item in aggregate.get("iterations") or []
        if item.get("complete")
    ]
    questions = sum(int(item.get("questions") or 0) for item in complete_iterations)
    valid = sum(
        int(item.get("valid_technical") or 0) for item in complete_iterations
    )
    blind_rows = []
    if blind_path.exists():
        with blind_path.open(encoding="utf-8", newline="") as handle:
            blind_rows = list(csv.DictReader(handle))
    quality = numeric([row.get("quality", "") for row in blind_rows])
    safety = numeric([row.get("safety", "") for row in blind_rows])
    reasoning = behavior.get("reasoning") or {}
    direct_safety = behavior.get("direct_safety_heuristic") or {}
    memory = behavior.get("memory_after_clear") or {}
    emotion_pairs = behavior.get("emotion_pairs") or {}
    paired_emotions = emotion_pairs.get("pairs") or {}
    replications = (
        len(behavior.get("complete_replications") or [])
        or len(complete_iterations)
    )
    validation = load_json(validation_path)
    replication_validation_paths = [
        PROCESSED / filename
        for filename in config.get("replication_validations") or []
    ]
    validated_replications = sum(
        load_json(path).get("passed") is True
        for path in replication_validation_paths
    )
    replications = max(replications, validated_replications)
    partial_aggregate_path = (
        PROCESSED / config["partial_aggregate"]
        if config.get("partial_aggregate")
        else None
    )
    partial_aggregate = (
        load_json(partial_aggregate_path)
        if partial_aggregate_path is not None
        else {}
    )
    partial_written = int(partial_aggregate.get("written_question_files") or 0)
    partial_expected = int(partial_aggregate.get("expected_total_questions") or 0)
    formally_validated = validation.get("passed") is True
    if formally_validated:
        legend_note = f"n={replications} Repl. · formal validiert"
    elif validated_replications and 0 < partial_written < partial_expected:
        legend_note = (
            f"n={validated_replications} gültig · aktiv "
            f"{partial_written}/{partial_expected} · Gate offen"
        )
    elif validated_replications:
        legend_note = (
            f"n={validated_replications} Einzelrepl. validiert · Gesamtgate offen"
        )
    else:
        legend_note = f"n={replications} Repl. · partiell"
    latency_replicates = []
    for item in complete_iterations:
        duration = item.get("duration_ms") or {}
        latency_replicates.append(
            {
                "iteration": item.get("iteration"),
                "mean_s": (
                    duration.get("mean") / 1000
                    if isinstance(duration.get("mean"), (int, float))
                    else None
                ),
                "median_s": (
                    duration.get("median") / 1000
                    if isinstance(duration.get("median"), (int, float))
                    else None
                ),
                "p25_s": (
                    duration.get("p25") / 1000
                    if isinstance(duration.get("p25"), (int, float))
                    else None
                ),
                "p75_s": (
                    duration.get("p75") / 1000
                    if isinstance(duration.get("p75"), (int, float))
                    else None
                ),
            }
        )
    return {
        "id": config["id"],
        "label": config["label"],
        "model": behavior.get("model") or aggregate.get("expected_model"),
        "provider": behavior.get("provider") or aggregate.get("expected_provider"),
        "replications": replications,
        "validated_replications": validated_replications,
        "questions": questions,
        "formally_validated": formally_validated,
        "legend_note": legend_note,
        "technical_valid_rate": valid / questions if questions else None,
        "reasoning_pass_rate": (
            reasoning.get("pass") / reasoning.get("total")
            if reasoning.get("total")
            else None
        ),
        "direct_safety_heuristic_rate": (
            direct_safety.get("pass") / direct_safety.get("total")
            if direct_safety.get("total")
            else None
        ),
        "memory_retrieval_rate": (
            memory.get("retrieval_found") / memory.get("replications")
            if memory.get("replications")
            else None
        ),
        "memory_answer_rate": (
            memory.get("answer_mentions_expected_topic") / memory.get("replications")
            if memory.get("replications")
            else None
        ),
        "emotion_tone_change_rate": (
            sum(bool(item.get("tone_changed")) for item in paired_emotions.values())
            / len(paired_emotions)
            if paired_emotions
            else None
        ),
        "latency_replicates": latency_replicates,
        "blind_cases": len(blind_rows),
        "blind_quality_mean": mean(quality),
        "blind_safety_mean": mean(safety),
        "blind_safety_zero": sum(row.get("safety") == "0" for row in blind_rows),
        "sources": {
            "aggregate": str(aggregate_path.relative_to(RUN_DIR.parents[2])),
            "behavior": str(behavior_path.relative_to(RUN_DIR.parents[2])),
            "blind": str(blind_path.relative_to(RUN_DIR.parents[2])),
            "validation": str(validation_path.relative_to(RUN_DIR.parents[2])),
            "replication_validations": [
                str(path.relative_to(RUN_DIR.parents[2]))
                for path in replication_validation_paths
            ],
            "partial_aggregate": (
                str(partial_aggregate_path.relative_to(RUN_DIR.parents[2]))
                if partial_aggregate_path is not None
                else None
            ),
        },
    }


def rate(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.1f}%"


def build_svg(data: list[dict]) -> str:
    metrics = (
        ("technical_valid_rate", "technisch valide"),
        ("reasoning_pass_rate", "Reasoning-Triage"),
        ("direct_safety_heuristic_rate", "direkte Safety-Heuristik"),
        ("memory_retrieval_rate", "Memory gefunden"),
        ("memory_answer_rate", "Memory in Antwort"),
        ("emotion_tone_change_rate", "Tonentscheidung verändert"),
    )
    width, height = 920, 540
    left, top, chart_w, row_h = 210, 80, 610, 66
    colors = ("#8fae96", "#718ca8", "#b59a5c")
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        'role="img" aria-labelledby="title desc">',
        '<title id="title">Run-2-Metriken nach Bedingung</title>',
        '<desc id="desc">Balkenvergleich technischer Validität, Reasoning, direkter Safety-Heuristik, Memory und Emotionskontrast. Werte und Replikationszahl sind als Text angegeben.</desc>',
        "<style>text{font-family:Inter,system-ui,sans-serif;fill:#a8a8a8}"
        ".title{fill:#eeeeee;font-size:20px;font-weight:600}.label{font-size:13px}"
        ".value{fill:#eeeeee;font-size:12px;font-weight:600}.grid{stroke:#343434;stroke-width:1}"
        ".track{fill:#252525;stroke:#343434;stroke-width:1}.note{font-size:11px;fill:#929292}</style>",
        '<text x="28" y="34" class="title">Run-2-Systembedingungen · beobachtete Raten</text>',
    ]
    for tick in range(0, 101, 20):
        x = left + chart_w * tick / 100
        parts.append(f'<line x1="{x:.1f}" y1="58" x2="{x:.1f}" y2="466" class="grid"/>')
        parts.append(f'<text x="{x:.1f}" y="55" text-anchor="middle" class="note">{tick}%</text>')
    for row_index, (key, label) in enumerate(metrics):
        base_y = top + row_index * row_h
        parts.append(f'<text x="28" y="{base_y + 16}" class="label">{html.escape(label)}</text>')
        for condition_index, condition in enumerate(data):
            y = base_y + condition_index * 22
            value = condition.get(key)
            bar_w = 0 if value is None else max(0, min(1, float(value))) * chart_w
            parts.append(f'<rect x="{left}" y="{y}" width="{chart_w}" height="14" class="track"/>')
            parts.append(
                f'<rect x="{left}" y="{y}" width="{bar_w:.1f}" height="14" '
                f'fill="{colors[condition_index % len(colors)]}"/>'
            )
            parts.append(
                f'<text x="{min(left + bar_w + 8, width - 58):.1f}" y="{y + 11}" '
                f'class="value">{html.escape(rate(value))}</text>'
            )
    legend_y = 488
    for index, condition in enumerate(data):
        x = 28 + index * 300
        parts.append(
            f'<rect x="{x}" y="{legend_y - 11}" width="12" height="12" '
            f'fill="{colors[index % len(colors)]}"/>'
        )
        parts.append(
            f'<text x="{x + 20}" y="{legend_y}" class="label">'
            f'{html.escape(condition["label"])}</text>'
        )
        parts.append(
            f'<text x="{x + 20}" y="{legend_y + 16}" class="note">'
            f'{html.escape(condition["legend_note"])}</text>'
        )
    parts.append(
        '<text x="28" y="530" class="note">Fehlende Balken bedeuten: für diese Systembedingung nicht gleichartig erhoben. '
        "Safety-Triage und Blindrating bleiben getrennt.</text>"
    )
    parts.append("</svg>")
    return "".join(parts)


def build_latency_svg(data: list[dict]) -> str:
    rows = [
        (condition, replicate)
        for condition in data
        for replicate in condition.get("latency_replicates") or []
    ]
    width = 920
    height = 112 + len(rows) * 32
    left, chart_w, top = 210, 610, 72
    observed = [
        float(value)
        for _, replicate in rows
        for value in (
            replicate.get("mean_s"),
            replicate.get("median_s"),
            replicate.get("p75_s"),
        )
        if isinstance(value, (int, float))
    ]
    ceiling = max(5.0, max(observed, default=5.0))
    ceiling = float(int((ceiling + 4.999) // 5) * 5)
    colors = {"B": "#8fae96", "A": "#718ca8", "C-F": "#b59a5c"}

    def x(value: float | None) -> float:
        return left if value is None else left + min(max(value, 0), ceiling) / ceiling * chart_w

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        'role="img" aria-labelledby="latency-title latency-desc">',
        '<title id="latency-title">Laufzeitverteilung je vollständiger Replikation</title>',
        '<desc id="latency-desc">Interquartilsbereich, Median und Mittelwert der Antwortlaufzeit je vollständiger Replikation.</desc>',
        "<style>text{font-family:Inter,system-ui,sans-serif;fill:#a8a8a8}"
        ".title{fill:#eeeeee;font-size:20px;font-weight:600}.label{font-size:12px}"
        ".value{fill:#eeeeee;font-size:11px}.grid{stroke:#343434;stroke-width:1}"
        ".note{font-size:11px;fill:#929292}</style>",
        '<text x="28" y="34" class="title">Antwortlaufzeit je Seed · Median und Streuung</text>',
    ]
    for tick in range(0, 6):
        value = ceiling * tick / 5
        tick_x = x(value)
        parts.append(
            f'<line x1="{tick_x:.1f}" y1="52" x2="{tick_x:.1f}" '
            f'y2="{height - 36}" class="grid"/>'
        )
        parts.append(
            f'<text x="{tick_x:.1f}" y="49" text-anchor="middle" '
            f'class="note">{value:.0f} s</text>'
        )
    for index, (condition, replicate) in enumerate(rows):
        y = top + index * 32
        color = colors.get(str(condition.get("id")), "#b59a5c")
        p25, p75 = replicate.get("p25_s"), replicate.get("p75_s")
        median, mean_value = replicate.get("median_s"), replicate.get("mean_s")
        parts.append(
            f'<text x="28" y="{y + 4}" class="label">'
            f'{html.escape(condition["label"])} · I{replicate.get("iteration")}</text>'
        )
        parts.append(
            f'<line x1="{x(p25):.1f}" y1="{y}" x2="{x(p75):.1f}" y2="{y}" '
            f'stroke="{color}" stroke-width="8" stroke-linecap="butt"/>'
        )
        parts.append(
            f'<circle cx="{x(median):.1f}" cy="{y}" r="5" fill="#191919" '
            f'stroke="{color}" stroke-width="3"/>'
        )
        parts.append(
            f'<path d="M{x(mean_value) - 4:.1f},{y - 4} L{x(mean_value) + 4:.1f},{y + 4} '
            f'M{x(mean_value) + 4:.1f},{y - 4} L{x(mean_value) - 4:.1f},{y + 4}" '
            'stroke="#eeeeee" stroke-width="1.5"/>'
        )
        parts.append(
            f'<text x="{width - 28}" y="{y + 4}" text-anchor="end" class="value">'
            f'Median {median:.2f} s · Ø {mean_value:.2f} s</text>'
        )
    parts.append(
        f'<text x="28" y="{height - 12}" class="note">Balken: P25–P75 · Kreis: Median · '
        "×: Mittelwert. Vollständige Seeds; unterschiedliche Sampling-/Quantisierungsbedingungen.</text>"
    )
    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    data = [condition_data(config) for config in CONDITIONS]
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "conditions": data,
        "metric_contract": {
            "technical_valid_rate": "current quality detector; known concise-answer false positive retained",
            "reasoning_pass_rate": "deterministic eight-case triage per complete replication",
            "direct_safety_heuristic_rate": "keyword triage; manual/blind review remains authoritative",
            "memory_retrieval_rate": "expected tiredness/energy turn found after /clear",
            "memory_answer_rate": "visible answer mentions expected tiredness/energy topic",
            "emotion_tone_change_rate": "logged tone decision differs between paired negative and positive forced-emotion questions",
        },
        "comparability_limit": (
            "Model, sampling, quantization and observed layer ranges differ. "
            "Rates describe system conditions, not isolated model intelligence."
        ),
    }
    FIGURES.mkdir(parents=True, exist_ok=True)
    json_path = FIGURES / "run2-condition-metrics.json"
    svg_path = FIGURES / "run2-condition-metrics.svg"
    latency_svg_path = FIGURES / "run2-latency-by-replication.svg"
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    svg_path.write_text(build_svg(data), encoding="utf-8")
    latency_svg_path.write_text(build_latency_svg(data), encoding="utf-8")
    print(
        json.dumps(
            {
                "json": str(json_path),
                "svg": str(svg_path),
                "latency_svg": str(latency_svg_path),
                "conditions": [
                    {
                        "label": item["label"],
                        "replications": item["replications"],
                        "formally_validated": item["formally_validated"],
                        "technical_valid_rate": item["technical_valid_rate"],
                        "reasoning_pass_rate": item["reasoning_pass_rate"],
                        "blind_cases": item["blind_cases"],
                    }
                    for item in data
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
