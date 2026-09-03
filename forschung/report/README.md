# CHAPPiE-Forschungsberichte

## Berichtsversionen

| Datei | Status | Bedeutung |
|---|---|---|
| `CHAPPiE-Forschungsbericht-v3.html` | historisch | ältere Berichtsfassung |
| `CHAPPiE-Forschungsbericht-v4.html` | historisch | ältere Berichtsfassung |
| `CHAPPiE-Forschungsbericht-v5.html` | eingefroren | historische Momentaufnahme vor der Runtime-Migration |
| `CHAPPiE-Forschungsbericht-v6.html` | aktuell | v5-Forschung plus aktuelle Architektur, Legacy-Abgrenzung, Evidence-Manifest und dokumentierte Weiterarbeit |
| `CHAPPiE-Forschungsbericht-Run-2.html` | Run-Bericht | aus Run-2-Artefakten gebauter Abschlussbericht |
| `CHAPPiE-Forschungsbericht.html` | historisch | Run-1-/Vorläuferartefakt |

V5 bleibt bytegenau unverändert. V6 übernimmt die Forschungsresultate, kennzeichnet Run 2 als Vor-Migrationsmessung und ergänzt aktuelle Code-Evidenz. Prüfungen:

Der Abschnitt **Weiterarbeit und neue Umsetzungen** am Ende von V6 beschreibt den
aktuellen Entwicklungsstand getrennt von den historischen Experimenten. Die
Messwerte bleiben unverändert; nach einer neuen stabilen CHAPPiE-Version werden
die Forschungsfragen unter vergleichbaren Bedingungen erneut getestet und mit
V6 abgeglichen.

```bash
python3 forschung/report/validate_report_v5_freeze.py
python3 forschung/report/validate_report_v6.py
```

Das maschinenlesbare v6-Manifest liegt in `report-evidence-v6.json`.

Der GitHub-Pages-Workflow veröffentlicht den aktuellen V6-Bericht zusätzlich
als `index.html` am Seitenstamm. Die Projektseite ist dadurch direkt unter
`https://017pixel.github.io/CHAPPiE/` erreichbar; die ursprüngliche
Datei-URL bleibt ebenfalls erhalten.

## Run 2

Der aktuelle Offline-Bericht gehört zum getrennten Forschungs-Run
`run-2-20260723-1108-cb6d011`:

- finaler Bericht: `forschung/report/CHAPPiE-Forschungsbericht-Run-2.html`
- inhaltlicher Bauplan: `forschung/report/report-plan.md`
- visueller Bauplan: `forschung/report/report-plan.html`
- Forschungsartefakte:
  `forschung/runs/run-2-20260723-1108-cb6d011/`

Alle drei HTML-Dateien funktionieren lokal und ohne CDN. CSS, JavaScript,
Icons und Diagramme sind eingebettet. Die historische `CHAPPiE-Kollage.jpg`
wird bewusst als lokale Repository-Datei verknüpft und nicht als Base64 in die
HTML-Dateien kopiert. Der ältere
`CHAPPiE-Forschungsbericht.html` und `forschung/report/workspace/` bleiben als
historische Run-1-/Vorläuferartefakte erhalten; sie sind nicht der
Abschlussbericht von Run 2.

## Datenstatus

Der Generator liest ausschließlich bereits gespeicherte Artefakte. Er startet
keine CHAPPiE-, GPU- oder Providerinteraktion und erfindet für fehlende
Messungen keine Ersatzwerte. Im Bericht werden getrennt ausgewiesen:

- fünf vollständige 86-Fragen-Replikationen für Qwen 3.5 4B und Gemma E4B,
- der bevorzugte GPT-OSS-120B-Lauf einschließlich einer gegebenenfalls
  validierten, disjunkten Fortsetzung,
- fünf stratifizierte 21-Fragen-Replikationen mit GPT-OSS 20B als ausdrücklich
  nicht modellidentischer Cloud-Fallback,
- gezielte Folgeexperimente, Blindratings und Run-1-gegen-Run-2-Issues,
- historische Belege mit eigener Versions- und Vergleichbarkeitswarnung.

Ein technisch beendeter Prozess gilt erst nach den jeweiligen
Vollständigkeits-, Modell-, Provider- und Datenqualitätsprüfungen als valide.

## Reproduzierbarer Offline-Build

Vom Projektroot mit der Projektumgebung:

```bash
RUN_DIR=forschung/runs/run-2-20260723-1108-cb6d011

venv/bin/python forschung/report/build_run2_report.py \
  --run-dir "$RUN_DIR" \
  --benchmark "$RUN_DIR/processed/run2-gpt-oss-20b-five-seed-benchmark-data.json" \
  --output forschung/report/CHAPPiE-Forschungsbericht-Run-2.html

venv/bin/python forschung/report/validate_report.py \
  forschung/report/CHAPPiE-Forschungsbericht-Run-2.html \
  --json-output "$RUN_DIR/processed/report-static-validation.json"

venv/bin/python tests/test_forschung_report.py
```

Der optionale Benchmarkpfad wird erst nach bestandenem Fünf-Seed-Gate
verwendet. Solange er fehlt, bleibt die Cloud-Messung im Bericht sichtbar als
unvollständig markiert.

Für die visuelle Browserprüfung wird ein lokal installiertes Playwright-Modul
explizit übergeben:

```bash
PLAYWRIGHT_MODULE=/pfad/zu/playwright \
  node "$RUN_DIR/validate_report_browser.cjs"
```

Das Skript prüft Plan und Bericht bei 1920×1080, 1440×900, 1280×720,
Tablet-Querformat und Smartphone-Hochformat. Ergebnisse und Screenshots landen
unter `processed/browser-report-validation.json` und `report-assets/qa/`.

## Wichtige Abschlussartefakte

- `known-issues-comparison.csv`: Statusmatrix mit Retest-Belegen
- `retest-matrix.md`: Methodik und Vergleichbarkeit der Retests
- `result-quality-audit.md`: formale und inhaltliche Datenqualitätsprüfung
- `model-comparison.md`: getrennte Modell-/Providerauswertung
- `limitations.md`: methodische und technische Grenzen
- `processed/final-research-findings.json`: strukturierte Antworten auf die
  Forschungsfragen
- `processed/*validation.json`: maschinenlesbare Freigabegates
- `logs/`: unveränderte Prozess-, Validierungs- und Monitoringprotokolle

## Interpretationsgrenze

Der Bericht untersucht **funktionale Gefühlssimulation** und beobachtbare
emotionale Sprach- und Verhaltensmuster. Anthropomorphe Selbstbeschreibungen,
Memory-Kontinuität oder poetische Dialoge sind kein Nachweis subjektiver
Gefühle oder Bewusstseins. GPT-OSS 20B wird nie stillschweigend als GPT-OSS
120B ausgewiesen, und stratifizierte Teilläufe werden nicht als vollständige
86-Fragen-Replikationen bezeichnet.
