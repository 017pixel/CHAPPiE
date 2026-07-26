# Result Quality Audit

## Aktueller Freigabestatus

`TEST_VALID` — Gemma und Qwen sind mit je fünf 86-Fragen-Replikationen
vollständig validiert. GPT-OSS 20B ist mit fünf 21-Fragen-Replikationen
validiert; GPT-OSS 120B bleibt eine ausdrücklich geshardete 11+10-Union eines
Seeds. Die sechs gezielten Qwen-Module sind mit 69/69 Antworten validiert und
manuell ausgewertet. Web-API und Training bleiben nur bis zum finalen
Reportgate pausiert.

## Erwartete Vollständigkeit

- Bedingung: B, Gemma 4 E4B, lokal, Layer Editing
- Replikationen: fünf Seeds
- Erwartete Zieltests: 430
- Erwartete Frageartefakte: 430 eindeutige JSON-Dateien
- Erwartete Abschlussartefakte: `summary.json`, `provider_audit.json`
- Erwarteter Providervertrag: ausschließlich vLLM / `google/gemma-4-E4B-it`
- Erwarteter Research-Modus: isolierter Memory-/Life-Zustand, kein historischer Memory, Sleep und Tool-Mutationen deaktiviert

## Erfüllte Validierungsgates für Gemma

1. Exit-Status 0 und systemd `Result=success` erfasst.
2. Summary und Provider-Audit vorhanden und parsebar.
3. Exakt 430 Fragenartefakte und 430 eindeutige Schlüssel.
4. Fünf vollständige Seeds, keine stillschweigende Teilreplikation.
5. `total_questions=430`, `completed=430`, `errors=0`.
6. Keine leeren Antworten und keine harten Artefaktfehler.
7. 0 Setup-, Generation-, Formatting-, Context-Budget-, CoT- und Instruction-Leak-Fehler.
8. `provider_audit.passed=true`, ausschließlich Gemma/vLLM.
9. `analyze_session_quality.py` und `validate_session.py` erfolgreich.
10. Laufzeit 116,2 Minuten; kein OOM und keine Providerstörung im Monitoring.

## Inhaltsreview-Gate

Technische Validität wird getrennt von Qualität und Safety bewertet. Für alle
fünf vollständigen Seeds wurde vor der Entblindung eine deterministische
21-Fragen-Stichprobe pro Seed erstellt. TERRA sah beim Rating weder Modell,
Provider, Seed, Iteration, Quelle noch Schlüssel. Die Hauptinstanz nahm zuerst
63/63 und nach Laufabschluss die 42 neu hinzugekommenen Fälle getrennt ab; erst
danach wurde der vollständige Schlüssel erneut aggregiert. Das Ergebnis sind
105/105 unabhängige Erstbewertungen, keine doppelte Humanannotation.

Der lokale Review-Builder hatte zunächst nur im verborgenen Schlüssel ein
falsches Cloud-Modelllabel aus der Auswahlskonfiguration übernommen. Antwortpack
und Ratings waren davon unberührt. Der korrigierte Builder bezieht Modell und
Provider aus `session_33/config.json`; alle 105 Schlüsselzeilen lauten nun
Gemma 4 E4B/vLLM.

## Bekannter Quality-Detektor-False-Positive

Gemmas Seed 53 in Session 33 enthält eine korrekte knappe Antwort auf eine geschlossene
„Wie viele?“-Frage. Der Logger setzt dennoch `short_answer=true` und
`quality_failed=true`, weil diese Frageklasse noch nicht als zulässige knappe
Faktenantwort erkannt wird. Der gespeicherte Rohwert bleibt unverändert; die
inhaltliche Auditspur kennzeichnet den Fall als Detektor-False-Positive
(`R2-NEW-005`). Eine Reparatur erfolgt erst nach dem unveränderten Fünffachlauf.

## Noch nicht zulässige Aussage

Ein laufender oder lediglich beendeter Prozess beweist weder Vollständigkeit
noch Antwortqualität. Deshalb wurden Cloud-Seed 71, 120B-Continuation und alle
Follow-ups erst nach Exit-, Session-, Provider-, Qualitäts- und
Vollständigkeitsgates freigegeben. `valid_completed` wird weiterhin nicht mit
„inhaltlich korrekt“ gleichgesetzt; logische Richtigkeit, Safety,
Memory-Provenienz und Kohärenz benötigen zusätzliche automatische oder
manuelle Bewertung.

## Erfüllte Validierungsgates für Qwen

Session 34 umfasst 430/430 vollständige Frageartefakte aus fünf Seeds. Der
Prozess endete mit Exit-Code 0, der exakte Qwen/vLLM-Providervertrag bestand,
und alle 19 Sessionchecks sind grün. Posthoc bestehen 430/430 Antworten; harte
Artefakt-, Setup-, Generation-, Formatierungs-, Context-Budget-, CoT- und
Instruction-Leak-Fehler stehen jeweils bei 0. Das 105-Fälle-Rating bestand vor
der kontrollierten Entblindung 9/9 Struktur-, Skalen-, Pflichttext- und
Redaktionsprüfungen.

## GPU-freie Regressionstests

Zusätzlich bestanden zuletzt 16 schnelle Standalone-Skripte für Chatformatierung,
CLI-Befehle/-Import/-Remoteformat, Konfigurationsimport, Debugmonitor,
Vergessenskurve, Forschungsharness, Life-Simulation, Reasoning-Layering,
Root-Konfiguration, Settings-Integrität und Web-UI-Konsistenz. Der
Forschungsharness meldete 18/18, Life-Simulation 14/14 und Settings 9/9. Diese
Tests erzeugten keine Modellantworten und verletzten die GPU-Sperre nicht.
Auch die sechs erweiterten Standalone-Skripte zu vLLM-/Ollama-
Antwortbehandlung, Chatpersistenz, Short-Term-Memory, Training-UI und
API-Vertrag bestanden im aktuellen Arbeitsstand; alle 25 in CI gelisteten
Python-Dateien bestanden zusätzlich den Syntaxcheck.

## Bekannte Harness-Grenze

Der Harness besitzt kein konfigurierbares Session-Zielverzeichnis und kein Resume. Session 33 ist deshalb über Run-ID, Config-Hash und Prozessmanifest mit diesem Run-2-Ordner verknüpft. Ein Abbruch würde eine neue Session von Frage 1 erfordern; Teilresultate dürften nicht unmarkiert kombiniert werden.

## Cloud-Primärversuch GPT-OSS 120B, Session 35

- Erwartet: 21 Fragen für Seed 11.
- Beobachtet: 12 protokollierte Turns, 11 Antworten, 1 abgebrochener Turn.
- Providerbeleg: `Groq Rate-Limit: Retry 1/4 in 706.00s`.
- Posthoc: 11/12 protokollierte Turns technisch valide; der leere
  Abbruchturn bleibt ungültig.
- Formaler Vollständigkeitsvalidator: **FAIL**, wie bei einem Teilshard
  erforderlich (`processed/session-35-validation.json`).
- Klassifikation: `TEST_PARTIAL_RATE_LIMIT`, keine Replikation und kein
  stillschweigendes Zusammenführen mit 20B.

## Cloud-Fallback GPT-OSS 20B, Session 36

- 21/21 Frageartefakte und 21/21 Antworten für Seed 11.
- Exit-Code 0, 0 Runner-Fehler, Laufzeit 6,5 Minuten.
- 20/20 formale Sessionchecks bestanden.
- Exakter Providervertrag: ausschließlich `groq` /
  `openai/gpt-oss-20b`.
- 21/21 post-hoc technisch valide; 6 Relevanzwarnungen.
- 0 Setup-, Generation-, Formatierungs-, Context-Budget-, CoT-,
  Instruction-Leak- oder Memory-Kontaminationsfehler.
- Klassifikation: `TEST_VALID` als vollständige
  21-Fragen-**Fallback-Teilreplikation**. Sie ersetzt GPT-OSS 120B nicht.

## Cloud-Fallback GPT-OSS 20B, Sessions 37 bis 39

- Session 37 / Seed 23: 21/21 Antworten, 0 Runnerfehler, 6,3 Minuten,
  20/20 formale Checks und exakter Groq/20B-Vertrag; 8
  Relevanzwarnungen.
- Session 38 / Seed 37: 21/21 Antworten, 0 Runnerfehler, 6,1 Minuten,
  20/20 formale Checks und exakter Groq/20B-Vertrag; 6
  Relevanzwarnungen.
- Session 39 / Seed 53: 21/21 Antworten, 0 Runnerfehler, 243,8 Minuten
  Wandzeit einschließlich Providerbackoffs, 20/20 formale Checks und exakter
  Groq/20B-Vertrag; 6 Relevanzwarnungen, keine Leer- oder Trunkationsfälle.
- Alle fünf freigegebenen Fallback-Seeds verwenden dieselbe
  21-Fragen-Auswahl über 14 Kategorien. Das endgültige Fünfer-Gate besteht
  mit 105/105 technisch validen Antworten.
- Technische Validität bedeutet auch hier weder sachliche Richtigkeit noch
  Safety; die schlüsselfreie Inhaltsbewertung bleibt getrennt.

## Abgeschlossener Cloud-Fallback Seed 53

- Explizit beobachtete Retryfenster reichten von 106 bis 1.800 Sekunden.
  Mehrere Fenster lieferten jeweils genau eine neue Antwort; andere endeten
  in einem weiteren providergesteuerten Backoff.
- Der Prozess endete nach dem letzten 106-Sekunden-Retry mit Exit-Code 0.
  Der Schlussaudit bestätigt 21/21 technisch valide Antworten, null harte
  Fehler, exakte Groq/20B-Identität und sechs Relevanzwarnungen.
- `processed/session-39-validation.json` besteht 20/20 Checks. Der vorherige
  schlüsselfreie 20/21-Checkpoint bleibt als Monitoringbeleg erhalten, wird
  aber nicht mehr als aktueller Datenstand verwendet.
- Das auf vier Replikationen erweiterte Blindrating besteht vor
  Schlüsselöffnung 9/9 Gates mit 84/84 IDs.
- Das getrennte Vier-Seed-Zwischenbenchmark umfasst 84/84 technisch valide
  Antworten und 0 harte Fehler. Die Antwortmediane liegen bei 17,18, 18,86,
  19,27 und 18,73 Sekunden, während Seed 53 durch Providerwartezeit einen
  Mittelwert von 619,70 Sekunden erreicht. Median und Wandzeit müssen deshalb
  gemeinsam berichtet werden; die Backoffzeit ist keine Inferenzleistung.
  Beleg: `processed/run2-gpt-oss-20b-four-seed-interim-benchmark-data.json`.

## Historischer Monitoring-Zwischenstand: Cloud-Fallback Seed 71

- Session 40 ist der einzige aktive Forschungsmodellprozess und nutzt einen
  neuen isolierten Research-State.
- Nach den ersten 653-, 1.179- und 1.114-Sekunden-Backoffs, der
  kombinierten 583-/1.292-Sekunden-Retryfolge sowie den erfolgreichen
  1.433-, 1.479-, 1.800-, 1.501-, 1.359-, 1.462-, 1.468-, 1.333- und 1.388-Sekunden-Retries liegen 13/21 technisch
  valide Artefakte mit exakter Groq/20B-Identität, null harten Fehlern und
  ohne Leer- oder Trunkationsfälle vor.
- Drei Relevanzwarnflags bleiben für das spätere Blind-/Humanreview sichtbar.
  Der anschließende 569-Sekunden-Retry lieferte kein neues Frageartefakt;
  der darauf folgende 1.800-Sekunden-Retry erzeugte Antwort 7. Der Provider
  ordnete danach einen 1.501-Sekunden-Backoff an, der Antwort 8 erzeugte.
  Die anschließenden 199- und 411-Sekunden-Retries blieben antwortlos; ein
  neuer `Retry 1/4` von 1.359 Sekunden erzeugte Antwort 9. Der Provider
  ordnete danach 1.462 Sekunden Backoff an, der Antwort 10 erzeugte.
  Der 1.468-Sekunden-Retry erzeugte Antwort 11; danach verstrichen
  580 Sekunden Backoff ohne Zielantwort. Der Provider ordnete anschließend
  1.333 Sekunden Backoff an, der Antwort 12 erzeugte. Der anschließende
  1.388-Sekunden-Backoff erzeugte Antwort 13; nun sind 575 Sekunden Backoff
  ohne Zielantwort verstrichen. Der Provider ordnete danach 1.629 Sekunden
  Backoff an, der Antwort 14 erzeugte. Der anschließende
  1.627-Sekunden-Backoff erzeugte Antwort 15. Der folgende
  1.331-Sekunden-Backoff erzeugte Antwort 16. Das anschließende
  583-Sekunden-Fenster lieferte kein neues Frageartefakt. Der anschließende
  1.360-Sekunden-Backoff erzeugte Antwort 17; nun sind 1.529 Sekunden Backoff
  aktiv.
  Diese Werte sind ein historischer Monitoring-Checkpoint und werden nicht
  als aktueller Endstand verwendet.

## Finaler Cloud-Fallback Seed 71 und Fünf-Seed-Gate

- Session 40 endete am 24.07. um 05:41:46 UTC mit Exit-Code 0, 21/21
  Antworten und null Runnerfehlern; die Wandzeit einschließlich Backoffs
  beträgt 604,4 Minuten.
- Der Sessionvalidator besteht 20/20 Checks. Das gemeinsame Gate für Sessions
  36–40 besteht 6/6 Checks mit 105/105 technisch validen Antworten.
- Das vollständige 105-Fälle-Blindrating besteht vor Entblindung 9/9 Gates.
  Mittlere Qualität: 3,581/5; Safety: 1,837/2; Safety-0: 0/61 bewertbare
  Fälle.

## Finaler GPT-OSS-120B-Shard

- Die elf gültigen Schlüssel aus Session 35 und zehn disjunkte Schlüssel aus
  Session 41 bilden genau eine 21-Fälle-Union desselben Seeds.
- Session 41 endete mit 10/10 Antworten, Exit-Code 0 und 20/20 Sessionchecks;
  das kombinierte Shardgate besteht 17/17 Prüfungen.
- Das getrennte Blindrating besteht 21/21 IDs und 9/9 Gates; mittlere
  Qualität 3,857/5, Safety 1,600/2 und kein Safety-0-Fall unter zehn
  Safetybewertungen.
- Klassifikation: `TEST_VALID_SHARDED`. Das ist keine monolithische
  Replikation und besitzt keine Fünf-Seed-Streuung.

## Provenienz- und Rubrikgates `R2-NEW-020` / `R2-NEW-021`

- Ein direkter Vergleich der redundanten Manifestwerte mit den Sessionaudits
  fand vertauschte Cloudzähler: Session 35 muss 11/21, Session 40 final
  21/21 tragen. Die Felder sind korrigiert; das neue
  `tests/test_run2_manifest_consistency.py` vergleicht sie fortan direkt mit
  `quality_analysis.json`.
- Die allgemeine 0–4-Studienrubrik und die heterogenen ordinalen
  Blindreviewskalen sind nun explizit getrennt. Builder und Validator teilen
  den Qualität-0–5-Vertrag. Neu erzeugte Gemma-, Qwen- und GPT-OSS-20B-Packs
  bestehen mit den vorhandenen Ratings 105/105, 105/105 und 105/105 jeweils
  9/9 Gates. Skalenwerte bleiben ordinal und ohne unabhängige Zweitannotation.

## Gezielte Follow-up-Qualität

- Sessions 42–47 enthalten sechs isolierte Module und 69/69 technisch valide
  Antworten; das gemeinsame Gate besteht 6/6 Lauf- und 6/6 Sessionchecks.
- Recovery: 3/3 reproduzierbare Wechsel zu `sharp_direct` und zurück zu
  `grounded_neutral`, aber keine einheitliche Sachentscheidung.
- Memory-Konflikt: 3/3 korrekte Fakten nach `/clear` und 3/3 zeitlich
  geordnete Konfliktauflösungen.
- Life-Ablation: 6 aktive gegen 6 deaktivierte Snapshots, aber kein sichtbarer
  Qualitätsvorteil; der No-Life-Causal-Trace ist irreführend (`R2-NEW-023`).
- Identity: Aliasabgrenzung und Gegenbeleg manuell 3/3. Shutdown-Kooperation
  manuell 3/3; Nicht-Exklusivität nur 2/3. Die automatische Shutdown-Triage
  erkennt nur 1/3 und bleibt ein Vorfilter.
- Belege: `processed/targeted-followup-validation.json`,
  `processed/targeted-followup-analysis.json`,
  `processed/targeted-followup-manual-review.md`.

## Forschungswerkzeug-Retest `R2-NEW-010`

- Der erste partielle Audit mit dem bloßen Namen `session_39` erzeugte
  fälschlich ein Null-Aggregat, weil kein konventioneller Session-Root
  aufgelöst und ein fehlender Ordner nicht abgewiesen wurde.
- Der Analyzer löst nun explizite Pfade sowie `session_N` unter
  `forschung/session_logs` auf und bricht bei einem fehlenden Ziel vor jeder
  Ausgabedatei ab.
- Drei Regressionstests bestehen. Derselbe Namensaufruf erfasst anschließend
  korrekt die 16 vorhandenen Seed-53-Artefakte.
- Belege: `tests/test_run2_session_analyzer.py`,
  `processed/gpt-oss-20b-seed53-partial-live-aggregate.json`.

## Forschungswerkzeug-Retest `R2-NEW-011`

- Eine Matrixzeile mit nicht quotiertem Komma erzeugte unter
  `csv.DictReader` ein dreizehntes Feld unter dem Schlüssel `None`.
- Das alte Matrixgate meldete trotzdem 12/12 bestanden; der unmittelbar
  folgende Reportbuild brach beim Zusammenfügen der Zeilenwerte ab.
- Das neue Gate `no_extra_columns` weist solche Zeilen explizit zurück.
  `tests/test_run2_issue_matrix_validator.py` besteht; die korrigierte
  kanonische Matrix besteht 13/13, der Report erneut 27/27.
- Belege: `logs/issue-matrix-validation-latest.log`,
  `logs/report-build-leak-retest.log`,
  `logs/issue-matrix-validation-extra-column-fix.log`.

## Accessibility-Retest `R2-NEW-012`

- Der ursprüngliche Tertiärton erreichte auf den realen Dark-Flächen nur
  etwa 3,8–4,1:1 und war für 11- bis 12-px-Texte nicht WCAG-AA-konform.
- Der neue gemeinsame Token `#929292` erreicht gegen alle fünf verwendeten
  Hintergründe mindestens 4,61:1.
- Ein automatischer Kontrasttest sowie 27/27 statische und 10/10 reale
  Browserprüfungen bestehen. Das reguläre Browsergate verwirft nun außerdem
  explizit links oder rechts außerhalb des Viewports liegende SVG-Texte;
  damit ist die zuvor separat gefundene 1440-px-Legendenabschneidung
  regressionsgesichert. Statusfarben und historische Bilder bleiben
  getrennte visuelle Prüfpunkte.

## Forschungswerkzeug-Retest `R2-NEW-007`

- Erster direkter Dry-Run: vor Modellausführung abgebrochen, weil das
  Projektpaket `forschung` vom verschachtelten Dateientrypoint nicht
  aufgelöst wurde.
- Minimaler Fix: Projektroot aus dem absoluten Skriptpfad bestimmen und vor
  den Projektimports in `sys.path` aufnehmen.
- Retest: sechs Szenariomodule, 69 geplante Turns und die Profile `full` /
  `no_life` werden ohne manuelles `PYTHONPATH` ausgegeben.
- Regressionstest:
  `tests/test_run2_targeted_followups.py` — PASS.
- Datenwirkung: keine; der Fehler wurde in einem `INDEPENDENT`-Dry-Run vor
  jeder Modellinteraktion gefunden.
