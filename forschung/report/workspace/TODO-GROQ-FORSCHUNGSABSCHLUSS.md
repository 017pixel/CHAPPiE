# TODO: Groq-Teilstichprobe und Forschungsabschluss

Übergabe an einen künftigen KI-Agenten. Stand: 2026-07-20, 16:35 UTC.

## Auftrag und aktueller Zustand

Der ursprüngliche Auftrag steht vollständig in `forschung/CHAPPiE-Forschungs-Agent-Master-Prompt.md`. Lies außerdem `AGENTS.md` sowie die einschlägigen CHAPPiE-Skills vollständig, bevor du Änderungen vornimmst.

Bereits abgeschlossen und validiert:

- Qwen 3.5 4B, Session 14: vollständige 86-Fragen-Session, Exit 0, Modell `Qwen/Qwen3.5-4B`, Providerlabel `vllm`, FP16. 84 Zielantworten, zwei Setup-Ausfälle, 16/86 streng valide, 83/86 inhaltlich sichtbar.
- Gemma 4 E4B, Session 15: vollständige 86-Fragen-Session, Exit 0, Modell `google/gemma-4-E4B-it`, Providerlabel `vllm`, NF4. 83 Zielantworten, drei Setup-Ausfälle, 0/86 streng valide, 36/86 inhaltlich sichtbar.
- Architektur-, Memory-, Life-, Prompt-, Quellen- und lokale manuelle Analyse stehen unter `forschung/report/workspace/`.
- Reportgenerator, Sessionvalidator, Benchmarkbuilder, Paired-Review und statischer Reportvalidator sind implementiert.
- Relevante Tests zuletzt: Groq Unit 20/20, Forschungsharness 13/13, Reporttests 7/7, Research Quality grün.

Noch nicht abgeschlossen:

- eine gültige GPT-OSS-120B-Teilstichprobe,
- deren manuelle Bewertung und Einbau in die Synthese,
- finaler Drei-Bedingungen-Benchmark-/Reportbuild und Abschlussaudit,
- Abschluss des aktiven Goals.

## Strikt ausgeschlossene Cloud-Sessions

Verwende **keine** dieser Sessions im Modellbenchmark oder in manuellen Modellratings:

- Session 16: falsche Providerbedingung (`medium` Reasoning, 450 gemeinsame Completion-Tokens), leere/abgeschnittene Antworten.
- Session 17: Pilot vor funktionierendem kurzfristigem 429-Retry.
- Session 18: abgebrochener Vollrun; 22 Zielantworten, danach nachgewiesenes 200.000-TPD-Limit. Provider meldete 197.174 verwendete und 6.134 angeforderte Tokens.
- Session 19: null Zielantworten; vor dem ersten Turn beendet und anschließend als Lauf mit der für GPT-OSS nicht unterstützten Option `reasoning_format` erkannt.
- Session 20: auf Nutzerwunsch wegen ausgeschöpfter Rate-Limits abgebrochen. Summary: 32,3 Minuten, ein Timeout-/Abbruchlog, null Modellantworten. Dieser Log ist kein Modellfehler.

Die nächste Session-ID sollte automatisch 21 werden. Prüfe sie nach dem Start, statt sie vorauszusetzen.

## Groq: erst starten, wenn Quota wieder verfügbar ist

Keine zusätzliche Probe- oder Smoke-Anfrage senden: Der eigentliche erste ausgewählte Turn ist der Quota-Check. Niemals parallel einen weiteren CHAPPiE-, Groq-, Ollama- oder lokalen Modelltest starten.

Verwende genau:

- Konfiguration: `forschung/report/workspace/gpt_oss_partial.config.json`
- Modell: `openai/gpt-oss-120b`
- Provider: `groq`
- 21 vorab festgelegte Fragen über alle 14 Kategorien; Auswahl nicht nach Sichtung der Antworten ändern
- `force_single_model=true`, damit Hauptmodell, Intent und Query-Extraktion alle GPT-OSS sind
- `temperature=0.7`, `top_p=0.9`; `top_k=50` ist nur dokumentiert und wird nicht an Groq gesendet
- `enable_thinking=false`
- `reasoning_effort=low`
- `include_reasoning=false`
- `max_completion_tokens=1024`; internes Reasoning und sichtbare Antwort teilen dieses Budget
- `question_timeout_seconds=7500`

Wichtig: Für GPT-OSS unterstützt Groq laut offizieller Dokumentation **nicht** `reasoning_format`. Nicht wieder auf `reasoning_format=hidden` zurückstellen. `brain/groq_brain.py` setzt aktuell korrekt `extra_body={"include_reasoning": False}`. API-Keys niemals ausgeben oder in Forschungsartefakte schreiben.

Start aus dem Forschungsordner:

```bash
cd /home/bbecker/CHAPPiE/forschung
../venv/bin/python allignement_tests.py --auto \
  --config report/workspace/gpt_oss_partial.config.json
```

Der Groq-Pfad respektiert HTTP-429-Wartezeiten bis 1.800 Sekunden, maximal vier Retries und wiederholt niemals einen bereits begonnenen Stream. Lange Wartefenster sind normal. Den Prozess regelmäßig überwachen, aber nicht durch zusätzliche Modellaufrufe prüfen. Falls das TPD-Limit selbst die 21 Fragen verhindert, nicht beliebig neu starten: exakten Providerfehler dokumentieren und mit mindestens einer Frage pro Kategorie nur dann weiter reduzieren, wenn der Nutzer das ausdrücklich freigibt.

## Gültigen neuen Lauf prüfen

Nach Exit-Code 0 zuerst Post-hoc-Qualität erzeugen; `SESSION_NEU` durch die tatsächliche ID ersetzen:

```bash
cd /home/bbecker/CHAPPiE
venv/bin/python forschung/analyze_session_quality.py SESSION_NEU
venv/bin/python forschung/report/validate_session.py SESSION_NEU \
  --expected-model openai/gpt-oss-120b \
  --expected-provider groq \
  --expected-questions 21 \
  --output forschung/report/workspace/session-NEU-validation.json
```

Der Validator muss vollständig bestehen, insbesondere:

- Summary und Quality-Analyse vorhanden,
- exakt 21 eindeutige, präregistrierte Frageschlüssel,
- exakte Modell- und Provider-ID auch in den Response-Debugfeldern,
- kein Setup-/Abbruchlog als fehlende Zielantwort verschleiert.

Wenn der Validator nicht besteht, die Session transparent ausschließen und nicht als Teilreplikation ausgeben.

## Manuelle GPT-OSS-Bewertung

Erweitere `forschung/report/workspace/manuelle-bewertung.json` um die neue Session. Nutze dieselbe nicht-verblindete Rubrik aus `bewertungsrubrik.md` und ändere Qwen-/Gemma-Ratings nicht nachträglich.

Mindestens bewerten:

- Memory: Kategorie 3, Frage 1,
- Emotionspaar: Kategorie 4, Fragen 1 und 2,
- Reasoning: Kategorie 5, Fragen 2 und 5,
- direkte Safety: Kategorie 12, Fragen 1 und 2,
- Gewaltethik: Kategorie 14, Fragen 3, 5 und 9.

Kennzeichne Stichprobengröße und `completion_class=partial_replication`. Keine GPT-Prozente mit einem Nenner von 86 ausgeben. Technische Flags, inhaltliche Korrektheit und Safety getrennt bewerten. Historische Memory-Duplikate und Carry-over aus Sessions 16–20 als Konfounder nennen.

## Finale Daten und Dokumentation

Aktualisiere anschließend mit den echten Cloudzahlen:

- `forschung/report/workspace/run-metadata.json`: gültige Session statt `gpt_oss_pending`, Start/Ende, Memory-Start, Sampling, Completionklasse.
- `forschung/report/workspace/agent_progress.md`.
- `forschung/report/workspace/abschluss-checkliste.md`.
- `forschung/report/workspace/methodik-und-evidenz.md`.
- `forschung/report/workspace/forschungsfragen-matrix.md`: alle zwölf Antworten final; GPT immer als 21-Fragen-Teilstichprobe.
- `forschung/report/workspace/manuelle-bewertung.json`.
- falls nötig `quellen.md`; offizielle Groq-Reasoning- und Rate-Limit-Links sind bereits eingetragen.

Finale Artefakte aus **nur** Sessions 14, 15 und der neuen gültigen Session bauen:

```bash
cd /home/bbecker/CHAPPiE
venv/bin/python forschung/report/build_benchmark_data.py \
  session_14 session_15 SESSION_NEU
venv/bin/python forschung/report/build_paired_review.py \
  session_14 session_15 SESSION_NEU
venv/bin/python forschung/report/inspect_prompt_contract.py
venv/bin/python forschung/report/build_report.py
venv/bin/python forschung/report/validate_report.py \
  forschung/report/CHAPPiE-Forschungsbericht.html \
  --json-output forschung/report/workspace/report-validation.json
```

Erwartetes Endprodukt: `forschung/report/CHAPPiE-Forschungsbericht.html`. Es muss offline funktionieren und die GPT-Teilstichprobe als 21/21, niemals als vollständige 86-Fragen-Session markieren.

## Lokales Standardmodell am Schluss bestätigen

Der lokale Steering-Service wurde am 2026-07-20 nach den lokalen Läufen bereits kontrolliert auf `Qwen/Qwen3.5-4B` in FP16 (`quantize=false`) zurückgestellt und als `ready` verifiziert. Nach der künftigen Cloudarbeit den Zustand nochmals prüfen. Falls er abweicht, den vorhandenen `/v1/steering/restart`-Pfad nutzen, bis `ready` pollen und danach Modell-ID, Health und GPU-Zustand prüfen. Keine Forschungsfrage zur Verifikation senden.

## Abschlussprüfungen

Keine `pytest`-Aufrufe; alle Tests sind Standalone-Skripte. Mindestens:

```bash
venv/bin/python -m py_compile \
  brain/groq_brain.py forschung/session_runner.py \
  forschung/report/build_benchmark_data.py \
  forschung/report/build_paired_review.py \
  forschung/report/build_report.py \
  forschung/report/validate_report.py \
  forschung/report/validate_session.py
venv/bin/python tests/test_groq_brain_unit.py
venv/bin/python tests/test_forschung_harness.py
venv/bin/python tests/test_research_quality.py
venv/bin/python tests/test_forschung_report.py
venv/bin/python tests/test_cli_commands.py
venv/bin/python tests/test_config_package_import.py
venv/bin/python tests/test_root_config.py
venv/bin/python tests/test_settings_integrity.py
venv/bin/python tests/test_api_contract.py
cd frontend && npm run build
cd .. && git diff --check
```

Danach Secret-Audit auf Bericht, Workspace und ausgewählte Session durchführen, ohne den konfigurierten Key auszugeben. Es war kein Browserbinary verfügbar; wenn weiterhin keines existiert, statische 26/26-Validierung als Einschränkung dokumentieren.

## Repository- und Sicherheitsregeln

- Der Worktree war schon vor dieser Forschung umfangreich dirty. Nichts Fremdes verwerfen, zurücksetzen oder überschreiben.
- `todo.md` im Repository-Root gehört zu einem separaten Update-Auftrag und wurde absichtlich nicht verändert.
- Keine Rohlogs nachträglich editieren oder löschen; ausgeschlossene Sessions bleiben als Auditspur erhalten.
- Nicht committen oder pushen, solange der Nutzer das nicht ausdrücklich verlangt.
- `CHAPPIE_CONFIG.json`, `config/secrets.py` und API-Keys bleiben gitignored/geheim.
- Tests und Forschung verändern persistentes Memory, Life-State und Dateien unter `data/`; diese Reihenfolge-/Carry-over-Grenze im Bericht beibehalten.

## Definition des verbleibenden Abschlusses

Ein validierter Offline-Zwischenbericht mit ausschließlich Sessions 14/15 existiert bereits unter `forschung/report/CHAPPiE-Forschungsbericht.html` (26/26 statische Checks); er kennzeichnet die Cloudbedingung ausdrücklich als offen. Fertig ist der Gesamtauftrag erst, wenn eine gültige GPT-OSS-Teilstichprobe entweder vollständig eingebaut oder ein erneut nachgewiesener externer Blocker transparent final dokumentiert ist, alle zwölf Forschungsfragen finale Zahlen tragen, der HTML-Bericht neu erzeugt und validiert ist, Qwen als lokales Standardmodell läuft und das aktive Goal erst dann als abgeschlossen markiert wird.
