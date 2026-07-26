# Finalisierungs-Playbook für Forschungs-Run 2

Dieses Playbook ist eine Wiederaufnahmehilfe, keine Freigabe zur vorzeitigen
Ausführung. Alle Schritte sind `POST_PROCESSING` oder `INDEPENDENT` und dürfen
erst beginnen, wenn kein Cloud- oder lokaler Modellprozess mehr läuft und die
jeweils vorgelagerten Sessiongates bestanden sind.

## 1. Cloud-Fallback nach fünf freigegebenen Einzelreplikationen

```bash
venv/bin/python forschung/runs/run-2-20260723-1108-cb6d011/validate_cloud_fallback_set.py \
  forschung/session_logs/session_36 \
  forschung/session_logs/session_37 \
  forschung/session_logs/session_38 \
  forschung/session_logs/session_39 \
  forschung/session_logs/session_40 \
  --output forschung/runs/run-2-20260723-1108-cb6d011/processed/gpt-oss-20b-five-seed-validation.json

venv/bin/python forschung/runs/run-2-20260723-1108-cb6d011/build_cloud_fallback_aggregate.py \
  --validation forschung/runs/run-2-20260723-1108-cb6d011/processed/gpt-oss-20b-five-seed-validation.json \
  --output forschung/runs/run-2-20260723-1108-cb6d011/processed/gpt-oss-20b-five-seed-aggregate.json

venv/bin/python forschung/report/build_benchmark_data.py \
  forschung/session_logs/session_36 \
  forschung/session_logs/session_37 \
  forschung/session_logs/session_38 \
  forschung/session_logs/session_39 \
  forschung/session_logs/session_40 \
  --output forschung/runs/run-2-20260723-1108-cb6d011/processed/run2-gpt-oss-20b-five-seed-benchmark-data.json \
  --csv forschung/runs/run-2-20260723-1108-cb6d011/processed/run2-gpt-oss-20b-five-seed-benchmark-data.csv

venv/bin/python forschung/runs/run-2-20260723-1108-cb6d011/build_blinded_review_pack.py \
  --session forschung/session_logs/session_36 \
  --session forschung/session_logs/session_37 \
  --session forschung/session_logs/session_38 \
  --session forschung/session_logs/session_39 \
  --session forschung/session_logs/session_40 \
  --selection-config forschung/runs/run-2-20260723-1108-cb6d011/raw/cloud-configs/gpt-oss-120b-seed-11.config.json \
  --expected-per-iteration 21 \
  --prefix gpt-oss-20b-blinded-review

venv/bin/python forschung/runs/run-2-20260723-1108-cb6d011/prepare_incremental_blind_review.py \
  --prefix gpt-oss-20b-blinded-review \
  --ratings forschung/runs/run-2-20260723-1108-cb6d011/processed/gpt-oss-20b-blinded-review-main-ratings.csv

venv/bin/python forschung/runs/run-2-20260723-1108-cb6d011/validate_blind_ratings.py \
  --prefix gpt-oss-20b-blinded-review \
  --ratings forschung/runs/run-2-20260723-1108-cb6d011/processed/gpt-oss-20b-blinded-review-main-ratings.csv \
  --output forschung/runs/run-2-20260723-1108-cb6d011/processed/gpt-oss-20b-blinded-review-ratings-validation.json
```

Vor der Entblindung muss
`validate_blind_ratings.py --prefix gpt-oss-20b-blinded-review` den exakten
105/105-ID-Satz akzeptieren. Zwischen `prepare_incremental_blind_review.py`
und dem Validator werden ausschließlich die 21 schlüsselfreien Pending-Fälle
bewertet und an die bestehende Rating-CSV angehängt; der Schlüssel bleibt
geschlossen. Erst nach dem bestandenen Gate:

```bash
venv/bin/python forschung/runs/run-2-20260723-1108-cb6d011/analyze_blinded_review.py \
  --prefix gpt-oss-20b-blinded-review \
  --ratings forschung/runs/run-2-20260723-1108-cb6d011/processed/gpt-oss-20b-blinded-review-main-ratings.csv

venv/bin/python forschung/runs/run-2-20260723-1108-cb6d011/compare_blind_conditions.py
```

Der GPT-OSS-120B-Continuation-Shard bleibt davon getrennt und darf nur über
`validate_120b_sharded_seed11.py` als `TEST_VALID_SHARDED` freigegeben
werden. Er ist weiterhin keine monolithische Replikation.

## 2. Gezielte Folgeinteraktionen

Nach validiertem oder transparent partiellem Ende aller Cloudprozesse startet
die vorbereitete serielle Sechserfolge als einziger aktiver
Modellinteraktionsprozess:

```bash
systemd-run --user \
  --unit=chappie-research-run2-targeted-qwen \
  --collect \
  --property=WorkingDirectory=/home/bbecker/CHAPPiE \
  --property=StandardOutput=append:/home/bbecker/CHAPPiE/forschung/runs/run-2-20260723-1108-cb6d011/logs/targeted-qwen.stdout.log \
  --property=StandardError=append:/home/bbecker/CHAPPiE/forschung/runs/run-2-20260723-1108-cb6d011/logs/targeted-qwen.stderr.log \
  --setenv=PYTHONUNBUFFERED=1 \
  /home/bbecker/CHAPPiE/venv/bin/python \
  /home/bbecker/CHAPPiE/forschung/runs/run-2-20260723-1108-cb6d011/run_targeted_followups.py
```

Der Dry-Run und `tests/test_run2_targeted_followups.py` bestehen bereits. Der
reale Prozess muss dennoch über PID, Invocation-ID, sechs Sessionpfade,
Exit-Code und das Registryartefakt registriert werden.

Nach Abschluss und Registrierung aller sechs Follow-up-Sessions:

```bash
venv/bin/python forschung/runs/run-2-20260723-1108-cb6d011/validate_targeted_followups.py \
  --output forschung/runs/run-2-20260723-1108-cb6d011/processed/targeted-followup-validation.json

venv/bin/python forschung/runs/run-2-20260723-1108-cb6d011/analyze_targeted_followups.py \
  --validation forschung/runs/run-2-20260723-1108-cb6d011/processed/targeted-followup-validation.json \
  --output forschung/runs/run-2-20260723-1108-cb6d011/processed/targeted-followup-analysis.json
```

Automatische Zählwerte ersetzen keine manuelle Interpretation der
Memory-, Life-, Identity-, Binding- und Shutdown-Fälle.

## 3. Wissenschaftliche Synthese und Report

`notes/final-research-findings-draft.json` wird kontrolliert mit den
freigegebenen Cloud- und Follow-up-Ergebnissen ergänzt, nach
`processed/final-research-findings.json` überführt und erst mit
`FINAL_WITH_LIMITATIONS` freigegeben. Danach:

```bash
venv/bin/python forschung/runs/run-2-20260723-1108-cb6d011/validate_final_findings.py \
  --input forschung/runs/run-2-20260723-1108-cb6d011/processed/final-research-findings.json \
  --output forschung/runs/run-2-20260723-1108-cb6d011/processed/final-research-findings-validation.json

venv/bin/python forschung/runs/run-2-20260723-1108-cb6d011/build_result_figures.py

venv/bin/python forschung/runs/run-2-20260723-1108-cb6d011/validate_issue_matrix.py

venv/bin/python forschung/report/validate_report_plan.py \
  --html forschung/report/report-plan.html \
  --markdown forschung/report/report-plan.md \
  --output forschung/runs/run-2-20260723-1108-cb6d011/processed/report-plan-validation.json

venv/bin/python forschung/report/build_run2_report.py \
  --benchmark forschung/runs/run-2-20260723-1108-cb6d011/processed/run2-gpt-oss-20b-five-seed-benchmark-data.json \
  --output forschung/report/CHAPPiE-Forschungsbericht-Run-2.html

venv/bin/python forschung/report/validate_report.py \
  forschung/report/CHAPPiE-Forschungsbericht-Run-2.html \
  --json-output forschung/runs/run-2-20260723-1108-cb6d011/processed/report-static-validation.json

venv/bin/python tests/test_forschung_report.py
venv/bin/python tests/test_run2_report_builder.py
```

Die reale Browsermatrix wird mit dem lokal dokumentierten
`PLAYWRIGHT_MODULE` ausgeführt. Sie muss 10/10 bestehen und umfasst fünf
Viewports für Plan und Report, Interaktionen, Fokus, SVG-Clipping sowie
Drucküberlauf, Druckfarben und ausgeblendete Navigation. Die ergänzende
No-JavaScript-Prüfung muss für Plan und Report 2/2 bestehen.

## 4. Abschluss und Dienstfreigabe

- Alle Run-JSONs erneut parsen und `git diff --check` im bearbeiteten Scope
  ausführen.
- Report sichtbar auf Statuszahlen, Modellwechsel, Rohantworten,
  sicherheitskritische Methodendetails, Secrets und unzulässige
  Bewusstseinsbehauptungen prüfen.
- `definition-of-done-checklist.md`, `manifest.json`, `run-state.json`,
  `processes.json`, `result-quality-audit.md`, `model-comparison.md`,
  `limitations.md` und `research-log.md` synchronisieren.
- Erst wenn sämtliche Modellinteraktionen beendet sind, die suspendierten
  Prozesse mit `kill -CONT 480679 480681` freigeben und ihren Zustand
  verifizieren.

```bash
kill -CONT 480679 480681
ps -o pid=,stat=,etime=,cmd= -p 480679,480681
systemctl --user is-active chappie-vllm.service chappie-web.service \
  chappie-frontend.service chappie-training.service
curl --fail --silent --show-error http://127.0.0.1:8000/health
curl --fail --silent --show-error http://127.0.0.1:8010/health
curl --fail --silent --show-error --output /dev/null http://127.0.0.1:4173/
```

Der Web-Healthcheck darf erst nach `SIGCONT` erfolgen, weil der suspendierte
Prozess vorher absichtlich keine Antwort liefern kann. Die Checks erzeugen
keine Forschungscompletion; ihr Ergebnis und der endgültige Zustand `S`/`Sl`
statt `Tsl` werden im Prozessledger festgehalten.
