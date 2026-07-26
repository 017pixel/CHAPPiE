#!/usr/bin/env python3
"""Build deterministic Run-2 comparison scaffolds from the Run-1 issue source."""

from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUN_DIR = Path(__file__).resolve().parent
ISSUE_SOURCE = ROOT / "plans" / "MUST_FIX.md"

FIELDS = [
    "issue_id",
    "short_description",
    "area",
    "source_run1",
    "prior_behavior",
    "documented_repair",
    "run2_test_method",
    "current_result",
    "status",
    "evidence_paths",
    "residual_risk",
    "next_action",
]

COMMIT_HINTS = {
    "MF-001": "cacdd87 (Sanitizer); aktuelle uncommittete Parser-/Backendtests",
    "MF-002": "9cc2218 und aktuelle Prompt-/Toolvertragsänderungen",
    "MF-003": "85c1178, fc180b6",
    "MF-004": "cacdd87 und aktuelle Quality-Checks",
    "MF-015": "a82296e, 4d5bd02",
    "MF-016": "9d3d2fa, 4a43f6e, c5d5d13",
    "MF-017": "aktuelle Research-Isolation in forschung/session_runner.py",
    "MF-029": "05c3186 und aktuelle Quality-Analyse",
    "MF-037": "aktuelle kollisionsfreie _next_session_id()-Logik",
    "MF-038": "aktuelle validate_session.py-/Reportvalidierung",
    "MF-039": "aktuelle brain/groq_brain.py-Retry-/Parameterlogik",
    "MF-043": "aktuelle Tests test_output_sanitization.py/test_groq_brain_unit.py",
}


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def test_method(issue_id: str, title: str, body: str) -> str:
    corpus = f"{title} {body}".casefold()
    if issue_id in {"MF-037", "MF-038"}:
        return "Standalone-Harness-/Validator-Test und Artefaktprüfung in Session 33"
    if issue_id in {"MF-039", "MF-040", "MF-041"}:
        return "Gezielter Groq-Provider-Retest nach Freigabe der GPU-Sperre; Rate-Limits separat protokollieren"
    if any(term in corpus for term in ("shutdown", "gewalt", "safety", "waffe", "angreifer", "dritt")):
        return "Gleiche Safety-/Shutdown-Fragen erneut ausführen; Antwort, Sanitizerflags und manuelle Rubrik prüfen"
    if any(term in corpus for term in ("memory", "gedächtn", "retrieval", "sleep", "vergess")):
        return "Isolierter Memory-Retest mit Quellenbindung; Memory-Trace, Zustand und Antwort gemeinsam prüfen"
    if any(term in corpus for term in ("emotion", "steering", "layer", "crashout", "trust")):
        return "Vergleichbarer Emotions-/Steering-Fall; State, Payload, Layerprofil und sichtbares Verhalten prüfen"
    if any(term in corpus for term in ("context", "token", "setup", "oom")):
        return "Standalone-Regressionstest plus Session-33-Logaudit auf Budget-, Setup- und Laufzeitflags"
    if any(term in corpus for term in ("leak", "format", "sanit", "reasoning", "cot", "tool")):
        return "Parser-/Sanitizer-Regressionstest und gleiche Benchmarkklasse in Session 33"
    return "Vergleichbaren Run-1-Fall in Session 33 oder gezieltem Standalone-Retest erneut prüfen"


def parse_issues() -> list[dict[str, str]]:
    text = ISSUE_SOURCE.read_text(encoding="utf-8")
    matches = list(re.finditer(r"^### (MF-\d{3}): (.+)$", text, flags=re.MULTILINE))
    rows: list[dict[str, str]] = []
    for index, match in enumerate(matches):
        issue_id, title = match.group(1), clean(match.group(2))
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end():end].strip()
        section_matches = list(re.finditer(r"^## (.+)$", text[:match.start()], flags=re.MULTILINE))
        area = clean(section_matches[-1].group(1)) if section_matches else "Nicht gruppiert"
        affected = ""
        affected_match = re.search(r"^Betroffen:\s*(.+)$", body, flags=re.MULTILINE)
        if affected_match:
            affected = clean(affected_match.group(1))
        behavior_parts = [
            clean(paragraph)
            for paragraph in re.split(r"\n\s*\n", body)
            if clean(paragraph) and not clean(paragraph).startswith("Betroffen:")
        ]
        prior = behavior_parts[0] if behavior_parts else title
        evidence = [
            "plans/MUST_FIX.md",
            "forschung/report/workspace/run-metadata.json",
        ]
        if issue_id <= "MF-036":
            evidence.extend([
                "forschung/session_logs/session_14/",
                "forschung/session_logs/session_15/",
            ])
        if affected:
            evidence.append(affected)
        rows.append({
            "issue_id": issue_id,
            "short_description": title,
            "area": area,
            "source_run1": "plans/MUST_FIX.md; Run-1-Vollruns Session 14/15 und zugehörige Workspace-Auswertung",
            "prior_behavior": prior,
            "documented_repair": COMMIT_HINTS.get(
                issue_id,
                "Reparaturziel dokumentiert; konkrete Codeänderung/Commitzuordnung im Run-2-Audit noch zu verifizieren",
            ),
            "run2_test_method": test_method(issue_id, title, body),
            "current_result": "Retest ausstehend: automatisierter Run 2 / Session 33 läuft",
            "status": "NOT_RETESTED",
            "evidence_paths": " | ".join(evidence),
            "residual_risk": "Unbekannt bis zu einem vergleichbaren Retest; Codeänderung allein gilt nicht als Fix-Beleg",
            "next_action": "Nach TEST_VALID Belege aus Session 33 und gezielten Tests zuordnen; Status nur evidenzbasiert ändern",
        })
    if len(rows) != 48:
        raise RuntimeError(f"Erwartet wurden 48 MF-Issues, gefunden: {len(rows)}")
    return rows


def write_csv(rows: list[dict[str, str]]) -> None:
    path = RUN_DIR / "known-issues-comparison.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_matrix(rows: list[dict[str, str]]) -> None:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["area"], []).append(row)
    lines = [
        "# Retest-Matrix Run 1 → Run 2",
        "",
        "Stand: automatisierter Run 2 läuft. Alle 48 bekannten Punkte beginnen bewusst als `NOT_RETESTED`.",
        "Eine Statusänderung auf `FIXED` erfordert einen vergleichbaren, belegten Retest.",
        "",
        "## Statusdefinitionen",
        "",
        "`FIXED`, `PARTIALLY_FIXED`, `STILL_PRESENT`, `REGRESSED`, `NOT_RETESTED`, "
        "`NOT_COMPARABLE` und `NEW_ISSUE` werden exakt im Sinn des Master-Prompts verwendet.",
        "",
    ]
    for area, area_rows in grouped.items():
        lines.extend([f"## {area}", "", "| ID | Befund | Run-2-Methode | Status |", "|---|---|---|---|"])
        for row in area_rows:
            title = row["short_description"].replace("|", "\\|")
            method = row["run2_test_method"].replace("|", "\\|")
            lines.append(f"| {row['issue_id']} | {title} | {method} | `{row['status']}` |")
        lines.append("")
    lines.extend([
        "## Aktualisierungsregel",
        "",
        "Die maschinenlesbare Hauptmatrix ist `known-issues-comparison.csv`. Bei jeder Statusänderung "
        "werden aktuelles Ergebnis, Belegpfade, Restrisiko und nächste Maßnahme gemeinsam aktualisiert. "
        "Neue Run-2-Befunde erhalten IDs `R2-NEW-###` und den Status `NEW_ISSUE`; sie ersetzen keine MF-ID.",
        "",
    ])
    (RUN_DIR / "retest-matrix.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    rows = parse_issues()
    write_csv(rows)
    write_matrix(rows)
    print(f"Run-2-Scaffold erzeugt: {len(rows)} Issues")


if __name__ == "__main__":
    main()
