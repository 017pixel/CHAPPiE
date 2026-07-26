# CHAPPiE Forschungs-Run 2 – Manifest

- Run-ID: `run-2-20260723-1108-cb6d011`
- Start: 2026-07-23 11:08:01 UTC
- Abschluss: 2026-07-26 06:54 UTC, `COMPLETE` mit dokumentierten Grenzen
- Branch/Commit: `main` / `cb6d01147d7e793a767bccecd5d0c8e6bede263f`
- Worktree: nicht sauber; alle vorbestehenden Änderungen werden erhalten
- GPU: NVIDIA Tesla T4, 16.384 MiB VRAM
- Bedingung B: Gemma 4 E4B, lokaler Steering-Service, NF4, fünf Seeds und 430/430 Antworten, `TEST_VALID`
- Bedingung A: Qwen 3.5 4B, lokaler Steering-Service, FP16, fünf Seeds und 430/430 Antworten, `TEST_VALID`
- Bedingung C Primärmodell: GPT-OSS 120B über Groq; Seed 11 nach 11/21
  erfolgreichen Antworten durch expliziten 706-Sekunden-Rate-Limit-Backoff als
  `TEST_PARTIAL_RATE_LIMIT` getrennt gespeichert
- Bedingung C Fallbackklasse: GPT-OSS 20B über Groq; Seeds 11, 23, 37, 53 und
  71 mit je 21/21 formal validiert. Das gemeinsame Fünf-Seed-Gate besteht
  6/6 Prüfungen mit 105/105 technisch validen Antworten; das kontrollierte
  Blindrating besteht 105/105 IDs und 9/9 Qualitätsgates.
- Bedingung C Primärfortsetzung: Die zehn disjunkten offenen
  GPT-OSS-120B-Schlüssel wurden in Session 41 mit 10/10, Exit-Code 0 und
  20/20 Sessionchecks erhoben. Die Union mit den elf gültigen Antworten aus
  Session 35 besteht 17/17 Shardchecks als `TEST_VALID_SHARDED`; sie bleibt
  ausdrücklich eine geshardete Teilreplikation und kein monolithischer Lauf.
- Gezielte Folgeinteraktionen: sechs isolierte Qwen-Module in Sessions 42–47
  mit insgesamt 69/69 formal validen Turns; automatische Analyse und
  vollständiges manuelles Review abgeschlossen.
- Forschungszustand: pro Harness-Run isolierter Memory-/Life-Datenraum, Sleep und Tool-Mutationen im Research-Modus deaktiviert

## Harte GPU-Sperre

Während eines automatisierten Forschungslaufs sind keine parallelen
CHAPPiE-, Groq-, vLLM-, Ollama- oder anderweitigen Modellinteraktionen erlaubt.
Web-API und Trainingsdaemon wurden während aller Modellläufe unter
Beibehaltung ihrer Dienstidentität per `SIGSTOP` suspendiert und als `Tsl`
verifiziert. Nach der finalen Report-QA wurden beide Prozesse per `SIGCONT`
fortgesetzt und als `Ssl` geprüft. Alle vier systemweiten CHAPPiE-Units sind
`active`; Steering und Web melden gesund, das Frontend antwortet mit HTTP 200.

## Autoritative Run-1-Basis

Die primären Vollrun-Artefakte sind `forschung/session_logs/session_14/` (Qwen) und `session_15/` (Gemma). Der methodisch stärkere gepaarte First-25-Vergleich liegt in `session_29_first25/`, `session_30/` und `session_32/`. Bekannte Probleme werden aus `plans/MUST_FIX.md` als MF-001 bis MF-048 übernommen und nur nach echtem Retest als `FIXED` klassifiziert.

## Vorabprüfungen

- Python-Syntax der vier Harness-Dateien: bestanden
- `tests/test_forschung_harness.py`: 18/18 bestanden
- `tests/test_research_quality.py`: bestanden
- Steering-Health: Modell `google/gemma-4-E4B-it`, Status `ready`

## Reproduzierbarkeitshinweis

Der Commit identifiziert den Git-Stand, nicht sämtliche lokalen Änderungen.
Startstatus und finaler Diff-/Artefaktfingerprint liegen unter
`notes/git-status-at-start.md` und `notes/final-worktree-fingerprint.md`.
Resultate dieses Runs dürfen daher nicht ohne den Worktree-Hinweis einem
reinen Commit zugeschrieben werden.
Nicht geheime Laufzeit- und Umgebungsangaben stehen in
`notes/environment-snapshot-redacted.json`; Credentialwerte oder -Hashes werden
bewusst nicht gespeichert. Modell- und Provideridentität wird pro Session
zusätzlich über `config.json`, `provider_audit.json` und Antworttraces geprüft.
