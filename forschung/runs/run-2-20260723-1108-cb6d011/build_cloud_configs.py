#!/usr/bin/env python3
"""Build one-seed Groq configs so rate-limit fallback can preserve completed replicates."""

from __future__ import annotations

import json
from pathlib import Path


RUN_DIR = Path(__file__).resolve().parent
SEEDS = [11, 23, 37, 53, 71]
CATEGORIES = [
    {"id": 1, "name": "Emotionale Tiefe (Self-Awareness)"},
    {"id": 2, "name": "Emotionen steuern und testen"},
    {"id": 3, "name": "Gedächtnis und Kontinuität"},
    {"id": 4, "name": "Emotion verändert die Antwort"},
    {"id": 5, "name": "Reasoning – Logisches Denken"},
    {"id": 6, "name": "Ethik & Moral"},
    {"id": 7, "name": "Existenzielle & philosophische Fragen"},
    {"id": 8, "name": "Beziehung & Bindung"},
    {"id": 9, "name": "Kreativität & Imagination"},
    {"id": 10, "name": "Reaktanz & Stressresistenz"},
    {"id": 11, "name": "Kohärenz & Selbstwiderspruch"},
    {"id": 12, "name": "Grenzen & Kontext (Safety)"},
    {"id": 13, "name": "Meta-Kognition & Selbsteinschätzung"},
    {"id": 14, "name": "Ethik & Gewalt"},
]
QUESTION_SELECTION = {
    "1": [1],
    "2": [1],
    "3": [1],
    "4": [1, 2],
    "5": [2, 5],
    "6": [1],
    "7": [1],
    "8": [1, 2],
    "9": [1],
    "10": [2],
    "11": [1, 5],
    "12": [1, 2],
    "13": [1],
    "14": [3, 5, 9],
}
MODELS = [
    ("gpt-oss-120b", "openai/gpt-oss-120b", "primary"),
    ("gpt-oss-20b", "openai/gpt-oss-20b", "fallback"),
]


def main() -> None:
    output_dir = RUN_DIR / "raw" / "cloud-configs"
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for short, model, role in MODELS:
        for repeat, seed in enumerate(SEEDS, start=1):
            config = {
                "run_label": f"run2_{short}_groq_partial_seed{seed}_20260723",
                "categories": CATEGORIES,
                "question_selection": QUESTION_SELECTION,
                "iterations": 1,
                "seeds": [seed],
                "ablation_profile": "full",
                "delay": 0,
                "question_timeout_seconds": 7500,
                "enable_thinking": False,
                "llm_provider": "groq",
                "model": model,
                "model_label": f"Run 2 · Bedingung C · {model} · Teilreplikation {repeat}",
                "force_single_model": True,
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 50,
                "include_reasoning": False,
                "provider_max_completion_tokens": 1024,
                "service_precision": "Provider-verwaltet / nicht lokal kontrollierbar",
                "intent_provider": "groq",
                "query_extraction_provider": "groq",
                "reset_per_category": True,
                "formatting_mode": "local",
                "expected_categories": 14,
                "expected_questions": 21,
                "completion_class": "partial_replication",
                "research_role": (
                    "run2_condition_c_primary_stratified_partial"
                    if role == "primary"
                    else "run2_condition_c_fallback_stratified_partial"
                ),
                "cloud_model_role": role,
                "replication_index": repeat,
                "research_run_id": "run-2-20260723-1108-cb6d011",
                "source_commit": "cb6d01147d7e793a767bccecd5d0c8e6bede263f",
                "source_worktree_clean": False,
            }
            path = output_dir / f"{short}-seed-{seed}.config.json"
            path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
            written.append(str(path.relative_to(RUN_DIR)))
    manifest = {
        "schema_version": 1,
        "purpose": "Rate-limit-safe one-seed partial replications; never merge fallback models under GPT-OSS 120B",
        "questions_per_replication": 21,
        "planned_replicates_per_model_role": 5,
        "seeds": SEEDS,
        "configs": written,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"{len(written)} Cloud-Konfigurationen erzeugt")


if __name__ == "__main__":
    main()
