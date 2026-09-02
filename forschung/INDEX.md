# Forschungsbestand

Der Forschungsordner bleibt als Evidenzbestand erhalten. Code-Cleanup ist kein
Grund, Sessions oder Messergebnisse zu löschen.

| Bereich | Klasse | Nutzung | Entscheidung |
|---|---|---|---|
| `allignement_tests.py`, `session_runner.py`, `session_logger.py`, `analyze_session_quality.py` | reproduzierbarer Harness-Code | aktiv | behalten und testen |
| `test_fragen.md`, `test_fragen_parser.py` | Testdefinition und Parser | aktiv | behalten und testen |
| `session_logs/` | eingefrorene Session-Evidenz | Berichte und Vergleich | unverändert behalten |
| `runs/` | Run-Artefakte, Validatoren und Messdaten | Run-2-Reproduzierbarkeit | unverändert behalten |
| `report/` | historische und aktuelle Berichte, Builder, Validatoren | Präsentation | nach Status im Report-README verwalten |
| `CHAPPiE-Forschungs-Agent-Master-Prompt.md` | Methodendokument | Referenz | behalten |
| `session_6_reparaturplan.md` | historische Arbeitsnotiz | nicht aktuelle Architektur | behalten, historisch kennzeichnen |

Die getrackte Baseline von Commit `5911242475b3c510be772f3f9068aa651dff65d0`
umfasst 2.906 Dateien: 2.253 unter `session_logs/`, 574 unter `runs/` und 69
unter `report/`. Präsentierbare Berichte dürfen keine Secrets, unbereinigten
lokalen Pfade oder personenbezogenen Rohdaten einbetten. Rohdaten bleiben
getrennt und werden nur über dokumentierte Belegpfade referenziert.

