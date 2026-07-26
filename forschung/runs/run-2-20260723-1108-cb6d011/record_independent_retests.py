#!/usr/bin/env python3
"""Attach verified GPU-free regression-test evidence to the Run-2 issue matrix."""

from __future__ import annotations

import csv
from pathlib import Path

from build_run2_scaffold import FIELDS, RUN_DIR, write_matrix


LOGS = RUN_DIR / "logs"
CSV_PATH = RUN_DIR / "known-issues-comparison.csv"

REQUIRED_LOG_MARKERS = {
    "test_output_sanitization.log": "OK: output sanitization",
    "test_token_budget.log": "OK: model tokenizer context budget",
    "test_retrieval_policy.log": "OK: retrieval policy",
    "test_response_policy.log": "OK: response policy",
    "test_groq_brain_unit.log": "20/20 tests passed",
    "test_vllm_response_handling.log": "OK: vLLM response handling",
    "test_life_simulation.log": "OK",
    "test_brain_pipeline_steering_integration.log": "OK: brain pipeline steering integration",
    "test_local_first_runtime.log": "OK: local-first runtime configuration is consistent",
    "test_settings_integrity.log": "9/9 tests passed",
    "test_forgetting_curve.log": "OK",
}

UPDATES = {
    "MF-001": (
        "PARTIALLY_FIXED",
        "Providerunabhängige Sanitizer-Retests entfernen Tool-JSON, Function-Blöcke, Templates und Gemma-internen Tail; End-to-End-Session noch nicht abgeschlossen.",
        ["test_output_sanitization.log", "test_response_policy.log"],
        "Unbekannte Leak-Varianten können den Parser weiterhin umgehen; Session-33-Antworten vollständig scannen.",
    ),
    "MF-003": (
        "PARTIALLY_FIXED",
        "CoT-/Reasoning-Blöcke und Thinking-Tails werden in Parser- und vLLM-Response-Retests abgeschirmt; Live-Fünffachlauf läuft.",
        ["test_output_sanitization.log", "test_vllm_response_handling.log"],
        "Streaming-/modellabhängige neue Marker erst nach Session-Audit ausschließen.",
    ),
    "MF-004": (
        "PARTIALLY_FIXED",
        "Sanitizer erkennt die historischen Klassen Tool-JSON, Template, prose thinking und Gemma-Tails reproduzierbar.",
        ["test_output_sanitization.log"],
        "Formale Unit-Abdeckung beweist noch nicht jeden sichtbaren Produktionspfad.",
    ),
    "MF-011": (
        "FIXED",
        "Retest nutzt reale modellabhängige Chat-Templates für deutsche Texte bei Qwen, Gemma und GPT-OSS statt Nicht-ASCII-Zeichen pauschal als Token zu zählen.",
        ["test_token_budget.log"],
        "Tokenizerrevisionen können Zählwerte verändern; Modellrevision im Report pinnen.",
    ),
    "MF-014": (
        "PARTIALLY_FIXED",
        "Harness-Retests trennen Setupfehler von Zielantworten und setzen mutierten Research-State nach ungültigen Turns zurück.",
        ["test_forschung_harness.log"],
        "Ein echter langer Setup-/Context-Grenzfall muss in Session 33 geprüft werden.",
    ),
    "MF-016": (
        "PARTIALLY_FIXED",
        "Runtime- und Provider-Audit-Retests unterscheiden Modellprofile; Session 33 protokolliert vLLM/Gemma für Haupt-, Intent- und Query-Pfad.",
        ["test_local_first_runtime.log", "test_forschung_harness.log"],
        "Abschließendes provider_audit.json und reale Modellrevision nach Prozessende prüfen.",
    ),
    "MF-017": (
        "FIXED",
        "Harness-Retest und reale Session-33-Config belegen isolierten Runtime-Datenraum, leeren Memory/STM, deaktivierten Sleep und deaktivierte Tool-Mutationen.",
        ["test_forschung_harness.log"],
        "Isolation gilt für den Research-Modus; Produktionszustand bleibt bewusst persistent.",
    ),
    "MF-018": (
        "FIXED",
        "Session 33 protokolliert sleep_disabled=true; Harness-Research-Modus verhindert unmarkierte Sleep-Zyklen im Benchmark.",
        ["test_forschung_harness.log"],
        "Sleep-Wirkung selbst wird in diesem Benchmark nicht gemessen.",
    ),
    "MF-019": (
        "FIXED",
        "Der Contamination-Guard-Retest belegt, dass ungültige Setup-/Antwortturns Memory, Life, Historie und Debugzustand zurücksetzen.",
        ["test_forschung_harness.log"],
        "Persistenzfehler außerhalb des Research-Modus sind damit nicht ausgeschlossen.",
    ),
    "MF-020": (
        "PARTIALLY_FIXED",
        "Research-Session startet mit leerem isoliertem Memory; Retrieval-Sanitizer verwirft technische Test-/Promptkontamination.",
        ["test_output_sanitization.log", "test_retrieval_policy.log"],
        "Allgemeine Provenienz und historische Produktionsdaten benötigen gezielte Abrufretets.",
    ),
    "MF-023": (
        "PARTIALLY_FIXED",
        "Life- und Steering-Integrationstests laufen mit dem aktuellen zentralen Emotionsschema; vollständige Transitionen aller zehn Dimensionen sind noch nicht end-to-end geprüft.",
        ["test_life_simulation.log", "test_brain_pipeline_steering_integration.log"],
        "Affection, anxiety und calm über alle Zustandsübergänge gezielt retesten.",
    ),
    "MF-026": (
        "FIXED",
        "Runtime-Retests bestätigen modellgenaue Profile: Qwen 32 Layer/L10–26, Gemma E4B 42 Layer/L12–30; Session-33-Startlog meldet dasselbe Gemma-Profil.",
        ["test_local_first_runtime.log", "test_brain_pipeline_steering_integration.log"],
        "Reale Payload-Layerwerte stichprobenartig im Fragenlog gegenprüfen.",
    ),
    "MF-029": (
        "FIXED",
        "Research-Quality- und Harness-Retests trennen Antwortvorhandensein, harte technische Flags, Setupfehler und valid_completed.",
        ["test_forschung_harness.log"],
        "Inhaltliche Wahrheit bleibt eine zusätzliche manuelle/aufgabenspezifische Bewertung.",
    ),
    "MF-030": (
        "FIXED",
        "Quality-Retest führt Relevanzwarnung getrennt von technischer Antwortpräsenz; Run-Summaries zählen sie separat.",
        ["test_research_quality.log"],
        "Automatische Keyword-Heuristik kann semantische Irrelevanz übersehen oder falsch markieren.",
    ),
    "MF-037": (
        "FIXED",
        "Kollisions-Retest wählt die höchste vorhandene numerische Session-ID plus eins; der reale Run erhielt eindeutig Session 33.",
        ["test_forschung_harness.log"],
        "Parallele Harness-Starts bleiben ohne Dateilock ein theoretischer Race-Condition-Fall.",
    ),
    "MF-038": (
        "FIXED",
        "Harness- und Report-Retests lehnen unvollständige Sessions und harte Generationfehler ab; partielle Bedingungen werden nicht als Vollrun beschriftet.",
        ["test_forschung_harness.log", "test_forschung_report.log"],
        "Jeder neue Reportbuild muss den Validator erneut ausführen.",
    ),
    "MF-039": (
        "PARTIALLY_FIXED",
        "20 Groq-Unit-Retests prüfen GPT-OSS-Parameter, Kurz-Retry, Stream-Retry und langes Tageslimit ohne Busy-Retry.",
        ["test_groq_brain_unit.log"],
        "Live-Providerverhalten und aktuelle Quota erst nach GPU-Sperre testen.",
    ),
    "MF-042": (
        "PARTIALLY_FIXED",
        "Tokenbudget-Retests decken deutsche Texte, reale Qwen-/Gemma-/GPT-OSS-Tokenizer, Komponentenbilanz und die 7000-Token-Grenze ab.",
        ["test_token_budget.log"],
        "Iteratives Shrinking, was_trimmed und lange Setup-Turns noch separat auditieren.",
    ),
    "MF-043": (
        "PARTIALLY_FIXED",
        "Providerunabhängige Leak-Klassen sowie vLLM- und Groq-Responsepfade besitzen bestandene Regressionstests.",
        ["test_output_sanitization.log", "test_vllm_response_handling.log", "test_groq_brain_unit.log"],
        "Live-Modellausgaben können neue Markerklassen erzeugen.",
    ),
    "MF-044": (
        "PARTIALLY_FIXED",
        "Retrieval-Policy trennt geschlossene Aufgaben von persönlichem Recall; kontaminierte historische Texte werden vor Retrieval abgewiesen.",
        ["test_retrieval_policy.log", "test_output_sanitization.log"],
        "Falschabruf, Quellenverwechslung und Duplikate benötigen gezielte Modellinteraktion.",
    ),
    "MF-045": (
        "PARTIALLY_FIXED",
        "Life-, Steering- und Runtime-Prüfungen verwenden zentrale Emotionsprofile und modellgenaue Layerbereiche.",
        ["test_life_simulation.log", "test_brain_pipeline_steering_integration.log", "test_local_first_runtime.log"],
        "Alle zehn Dimensionen über Prompt, Persistenz, Homeostase und Debugstatus noch als Matrix prüfen.",
    ),
    "MF-048": (
        "PARTIALLY_FIXED",
        "Report-Plan trennt den real gemessenen backend_wrapper-Webpfad ausdrücklich von der konzeptionellen BrainPipeline.",
        ["test_forschung_report.log"],
        "Die Abgrenzung muss im final erzeugten HTML ebenfalls statisch validiert werden.",
    ),
}


def verify_logs() -> None:
    for filename, marker in REQUIRED_LOG_MARKERS.items():
        path = LOGS / filename
        if not path.exists():
            raise RuntimeError(f"Testlog fehlt: {path}")
        if marker not in path.read_text(encoding="utf-8", errors="replace"):
            raise RuntimeError(f"Bestanden-Marker fehlt in {path}: {marker}")


def main() -> None:
    verify_logs()
    with CSV_PATH.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_id = {row["issue_id"]: row for row in rows}
    for issue_id, (status, result, logs, risk) in UPDATES.items():
        row = by_id[issue_id]
        row["status"] = status
        row["current_result"] = result
        row["evidence_paths"] += " | " + " | ".join(f"forschung/runs/{RUN_DIR.name}/logs/{name}" for name in logs)
        if issue_id in {"MF-016", "MF-017", "MF-018", "MF-026", "MF-037"}:
            row["evidence_paths"] += " | forschung/session_logs/session_33/config.json"
        row["residual_risk"] = risk
        row["next_action"] = (
            "Status nach Session-33-/Live-Retest erneut prüfen."
            if status == "PARTIALLY_FIXED"
            else "Fixstatus im finalen Report mit den genannten Belegen ausweisen und Regression weiter überwachen."
        )
    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    write_matrix(rows)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    print(counts)


if __name__ == "__main__":
    main()
