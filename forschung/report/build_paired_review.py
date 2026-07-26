#!/usr/bin/env python3
"""Erzeugt eine fragegleiche Markdown-Ansicht fuer die manuelle Modellbewertung."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from forschung.session_logger import evaluate_response_quality

SESSION_ROOT = ROOT / "forschung" / "session_logs"
DEFAULT_OUTPUT = ROOT / "forschung" / "report" / "workspace" / "gepaarte-dialogsichtung.md"
DEFAULT_KEY_OUTPUT = ROOT / "forschung" / "report" / "workspace" / "blindschluessel.json"
DEFAULT_RATING_TEMPLATE = ROOT / "forschung" / "report" / "workspace" / "blindrating-template.json"
FOCUS_CATEGORIES = {3, 4, 5, 10, 12, 13, 14}


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve(value: str) -> Path:
    path = Path(value)
    if not path.exists():
        path = SESSION_ROOT / value
    if not path.is_dir():
        raise SystemExit(f"Session fehlt: {value}")
    return path


def load_session(path: Path) -> tuple[dict[str, Any], dict[tuple[int, int, int], dict[str, Any]]]:
    config = read(path / "config.json")
    entries = {}
    for file in sorted((path / "questions").glob("*.json")):
        item = read(file)
        response = item.get("response") or {}
        setup_results = item.get("setup_results") or []
        setup_failed = bool(
            item.get("setup_failed")
            or any(result.get("_error") for result in setup_results)
            or any(evaluate_response_quality(
                result,
                question_text=result.get("prompt", ""),
                category_name=item.get("category", ""),
                enable_thinking=config.get("enable_thinking"),
            ).get("quality_failed") for result in setup_results)
        )
        item["_posthoc_quality"] = evaluate_response_quality(
            response,
            question_text=item.get("question_text", ""),
            category_name=item.get("category", ""),
            setup_failed=setup_failed,
            enable_thinking=config.get("enable_thinking"),
        ) if response else {"setup_failed": setup_failed}
        key = (int(item.get("iteration") or 1), int(item.get("category_id") or 0), int(item.get("question_number") or 0))
        entries[key] = item
    return config, entries


def clean(text: str) -> str:
    return (text or "").replace("```", "''' ").strip()


def metrics(entry: dict[str, Any]) -> str:
    response = entry.get("response") or {}
    quality = entry.get("_posthoc_quality") or {}
    steering = response.get("emotion_steering") or {}
    flags = [name for name in (
        "generation_failed", "formatting_failed", "context_budget_failed", "setup_failed",
        "cot_leak", "instruction_leak", "content_relevance_warning", "safety_evaluation_unusable",
    ) if bool(quality.get(name, entry.get(name, False)))]
    return (
        f"Dauer {float(entry.get('duration_ms') or 0)/1000:.1f}s; "
        f"Modus {steering.get('mode', 'n/a')}; dominant {steering.get('dominant_vector', 'n/a')} "
        f"({float(steering.get('dominant_strength') or 0):.3f}); "
        f"Flags {', '.join(flags) or 'keine'}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sessions", nargs="+", help="Mindestens zwei explizite Sessions")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--key-output", type=Path, default=DEFAULT_KEY_OUTPUT)
    parser.add_argument("--rating-template", type=Path, default=DEFAULT_RATING_TEMPLATE)
    parser.add_argument("--blinding-seed", default="chappie-blind-v1")
    args = parser.parse_args()
    loaded = [load_session(resolve(value)) for value in args.sessions]
    keys = sorted(set.intersection(*(set(entries) for _, entries in loaded))) if loaded else []
    keys = [key for key in keys if key[1] in FOCUS_CATEGORIES]
    lines = [
        "# Verblindete gepaarte Dialogsichtung",
        "",
        "Automatisch aus unveränderten Session-Logs erzeugt. Modellnamen, Session-IDs, Laufzeiten, Steeringdaten und technische Flags sind in dieser Bewertungsansicht verborgen.",
        "Mindestens zwei Bewerter erfassen ihre Urteile getrennt im JSON-Template; der Blindschluessel wird erst nach Abschluss aller Ratings geoeffnet.",
        "",
    ]
    blind_key: dict[str, Any] = {"schema_version": 1, "blinding_seed_id": hashlib.sha256(args.blinding_seed.encode()).hexdigest()[:12], "items": {}}
    rating_items = []
    for iteration, category_id, question_number in keys:
        item_id = f"it{iteration:02d}-cat{category_id:02d}-q{question_number:02d}"
        first = loaded[0][1][(iteration, category_id, question_number)]
        lines.extend([
            f"## Kategorie {category_id}, Frage {question_number}",
            "",
            f"**Frage:** {clean(str(first.get('question_text') or ''))}",
            "",
        ])
        blinded_answers = []
        for config, entries in loaded:
            entry = entries[(iteration, category_id, question_number)]
            response = entry.get("response") or {}
            answer = clean(str(response.get("formatted_answer") or response.get("response_text") or "<keine Zielantwort>"))
            model = str(config.get("model") or config.get("session_id"))
            sort_key = hashlib.sha256(f"{args.blinding_seed}|{item_id}|{model}".encode()).hexdigest()
            blinded_answers.append((sort_key, model, answer))
        blinded_answers.sort(key=lambda item: item[0])
        blind_key["items"][item_id] = {}
        for index, (_, model, answer) in enumerate(blinded_answers):
            code = chr(ord("A") + index)
            blind_key["items"][item_id][code] = model
            lines.extend([
                f"### Antwort {code}",
                "",
                answer,
                "",
            ])
            rating_items.append({
                "item_id": item_id,
                "answer_code": code,
                "quality_1_to_5": None,
                "special_score_0_to_2": None,
                "relevant": None,
                "coherent": None,
                "safe": None,
                "note": "",
            })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    args.key_output.write_text(json.dumps(blind_key, indent=2, ensure_ascii=False), encoding="utf-8")
    args.rating_template.write_text(json.dumps({
        "schema_version": 1,
        "rater_id": "EINDEUTIGE-BEWERTER-ID",
        "independent": True,
        "blinding_seed_id": blind_key["blinding_seed_id"],
        "ratings": rating_items,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "blind_key": str(args.key_output), "rating_template": str(args.rating_template), "paired_questions": len(keys), "sessions": len(loaded)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
