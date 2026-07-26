#!/usr/bin/env python3
"""GPU-free contract audit for the prepared Run-2 Groq configurations."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUN_DIR = Path(__file__).resolve().parent
CONFIG_DIR = RUN_DIR / "raw/cloud-configs"
OUTPUT_JSON = RUN_DIR / "processed/cloud-config-audit.json"
OUTPUT_MD = RUN_DIR / "processed/cloud-config-audit.md"
EXPECTED_SEEDS = [11, 23, 37, 53, 71]
EXPECTED_MODELS = {
    "primary": "openai/gpt-oss-120b",
    "fallback": "openai/gpt-oss-20b",
}
FORBIDDEN_KEY_PARTS = ("api_key", "apikey", "secret", "token_value")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected_count(config: dict[str, Any]) -> int:
    return sum(
        len(question_numbers)
        for question_numbers in (config.get("question_selection") or {}).values()
    )


def main() -> None:
    manifest_path = CONFIG_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    configured_paths = [RUN_DIR / item for item in manifest.get("configs") or []]
    checks: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    reference_selection: dict[str, list[int]] | None = None

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    check("manifest_config_count", len(configured_paths) == 10, str(len(configured_paths)))
    check("manifest_paths_exist", all(path.is_file() for path in configured_paths), "")

    for path in configured_paths:
        config = json.loads(path.read_text(encoding="utf-8"))
        role = str(config.get("cloud_model_role") or "")
        selection = config.get("question_selection") or {}
        if reference_selection is None:
            reference_selection = selection
        flat_keys = " ".join(str(key).casefold() for key in config)
        seed_values = config.get("seeds") or []
        record = {
            "path": str(path.relative_to(RUN_DIR)),
            "sha256": digest(path),
            "role": role,
            "model": config.get("model"),
            "seed": seed_values[0] if len(seed_values) == 1 else None,
            "selected_questions": selected_count(config),
            "categories": len(selection),
            "contract_ok": all(
                (
                    config.get("llm_provider") == "groq",
                    config.get("model") == EXPECTED_MODELS.get(role),
                    config.get("force_single_model") is True,
                    config.get("formatting_mode") == "local",
                    config.get("enable_thinking") is False,
                    config.get("include_reasoning") is False,
                    config.get("iterations") == 1,
                    config.get("expected_questions") == 21,
                    config.get("completion_class") == "partial_replication",
                    selected_count(config) == 21,
                    set(selection) == {str(value) for value in range(1, 15)},
                    selection == reference_selection,
                    not any(part in flat_keys for part in FORBIDDEN_KEY_PARTS),
                )
            ),
        }
        records.append(record)

    for role, model in EXPECTED_MODELS.items():
        matching = [item for item in records if item["role"] == role]
        check(
            f"{role}_five_configs",
            len(matching) == 5,
            f"{len(matching)} configs for {model}",
        )
        check(
            f"{role}_seed_set",
            sorted(item["seed"] for item in matching) == EXPECTED_SEEDS,
            str(sorted(item["seed"] for item in matching)),
        )
        check(
            f"{role}_model_contract",
            all(item["model"] == model and item["contract_ok"] for item in matching),
            model,
        )

    check(
        "same_stratified_selection",
        len(
            {
                json.dumps(
                    json.loads(path.read_text(encoding="utf-8")).get("question_selection"),
                    sort_keys=True,
                )
                for path in configured_paths
            }
        )
        == 1,
        "identische 21 Fragen über 14 Kategorien",
    )
    check(
        "no_duplicate_hashes_across_roles",
        len({item["sha256"] for item in records}) == len(records),
        "Model/Seed-Metadaten halten jede Config unterscheidbar",
    )

    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "resource_class": "INDEPENDENT",
        "manifest": str(manifest_path.relative_to(RUN_DIR)),
        "passed": all(item["passed"] for item in checks),
        "checks": checks,
        "configs": records,
        "execution_authorized": False,
        "execution_gate": (
            "Konfigurationsaudit erlaubt keine Cloudinteraktion; Start erst nach "
            "validiertem Ende der lokalen automatisierten Bedingungen."
        ),
    }
    OUTPUT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    rows = "\n".join(
        f"| {item['name']} | {'PASS' if item['passed'] else 'FAIL'} | {item['detail']} |"
        for item in checks
    )
    OUTPUT_MD.write_text(
        "# Cloud-Konfigurationsaudit\n\n"
        f"Stand: `{report['generated_at']}` · "
        f"Gesamtstatus: **{'PASS' if report['passed'] else 'FAIL'}**\n\n"
        "| Prüfung | Status | Detail |\n|---|---|---|\n"
        f"{rows}\n\n"
        "> Dieser GPU-freie Audit startet keine Cloudanfrage. Die Ausführung bleibt "
        "bis zum validierten Ende der lokalen automatisierten Bedingungen gesperrt.\n",
        encoding="utf-8",
    )
    print(json.dumps({"passed": report["passed"], "checks": len(checks)}, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
