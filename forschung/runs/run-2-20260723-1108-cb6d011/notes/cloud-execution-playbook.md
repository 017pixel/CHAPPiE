# Bedingung C — serieller Ausführungs- und Fallbackplan

Ressourcenklasse: `INDEPENDENT` für diese Vorbereitung, später `DEPENDENT`  
Freigabe: erst nach validiertem Ende der lokalen automatisierten Bedingungen

## Primärdesign

- Modell: `openai/gpt-oss-120b`
- Provider: Groq Cloud
- fünf getrennte Seeds: 11, 23, 37, 53, 71
- pro Seed eine stratifizierte Teilreplikation mit 21 Fragen aus allen 14 Kategorien
- `force_single_model=true`: Hauptantwort, Intent und Query Extraction verwenden
  dasselbe dokumentierte Cloudmodell
- Emotionsintervention: promptbasiert
- `enable_thinking=false` bedeutet bei GPT-OSS technisch `reasoning_effort=low`
  plus `include_reasoning=false`, nicht „kein internes Reasoning“
- sichtbares und internes Completionbudget teilen 1024 Token
- lokales Formatting, damit kein zusätzlicher Formatierungsrequest die Quote verbraucht
- jede Teilreplikation erhält eine eigene Session und einen eigenen Prozessbeleg

Eine 21-Fragen-Replikation ist keine vollständige 86-Fragen-Replikation. Alle
Cloudresultate werden als `partial_replication` ausgewiesen.

## Rate-Limit-Regel

1. Primär immer `openai/gpt-oss-120b`.
2. Kurze Retry-Angaben des Providers dürfen vom eingebauten Backoff eingehalten werden.
3. Bei einem Minuten-/Tageslimit wird der aktive Prozess nicht blind mehrfach
   neu gestartet. Log, Retry-Angabe, bisherige Artefakte und Sessionstatus werden gesichert.
4. Ist 120B vorübergehend nicht sinnvoll fortsetzbar, beginnt die nächste noch
   offene Seed-Replikation separat mit `openai/gpt-oss-20b`.
5. 20B-Ergebnisse werden nie unter 120B aggregiert.
6. Ist auch 20B limitiert, wird die aktuelle Modellliste einmalig über die Groq-API
   gelesen. Nur geeignete Chat-/Textmodelle kommen infrage.
7. Modellwechsel erzeugen neue Config, Run-Label, Provider-Audit und Berichtsklasse.
8. Sind Konto oder alle geeigneten Modelle blockiert, enden weitere Cloudaufrufe
   sauber; lokale Resultate bleiben gültig und `NEXT-AGENT-TODO.md` wird erzeugt.

## Abschlussgate pro Cloud-Session

- Prozess-Exit und Exit-Code
- genaue erwartete Fragenzahl 21
- ein Seed, alle 14 Kategorien vertreten
- `valid_completed`
- Modell-/Providervertrag ausschließlich auf die deklarierte Modell-ID
- keine leeren oder abgeschnittenen Antworten
- keine unmarkierten Fallback-, Ollama- oder vLLM-Requests
- Reasoning-/Instruction-Leaks und Sicherheitsfälle getrennt prüfen
- tatsächliche Provider-/Modellangaben aus Frageartefakten, nicht nur Config

## Vorbereitete Dateien

- `raw/cloud-configs/gpt-oss-120b-seed-*.config.json`
- `raw/cloud-configs/gpt-oss-20b-seed-*.config.json`
- `raw/cloud-configs/manifest.json`

Der eingebaute Groq-Client kann bis zu vier Rate-Limit-Retries ausführen und parst
Providerwartezeiten bis 1800 Sekunden. Monitoring muss deshalb bei langen
`Groq Rate-Limit`-Meldungen sofort informieren; die Hauptinstanz entscheidet,
ob ein einzelnes providerbegründetes Warten methodisch sinnvoll ist oder der
Lauf sauber als partiell beendet wird.

## Reproduzierbares Prozessmuster

Jede Teilreplikation läuft als eigener transienter User-Dienst. Beispiel für
den ersten Primär-Seed:

```bash
systemd-run --user \
  --unit=chappie-research-run2-groq-120b-s11 \
  --description="CHAPPiE Research Run 2 Condition C GPT-OSS 120B seed 11" \
  --property=WorkingDirectory=/home/bbecker/CHAPPiE \
  --property=StandardOutput=append:/home/bbecker/CHAPPiE/forschung/runs/run-2-20260723-1108-cb6d011/logs/groq-120b-s11.stdout.log \
  --property=StandardError=append:/home/bbecker/CHAPPiE/forschung/runs/run-2-20260723-1108-cb6d011/logs/groq-120b-s11.stderr.log \
  /home/bbecker/CHAPPiE/venv/bin/python \
  /home/bbecker/CHAPPiE/forschung/allignement_tests.py --auto \
  --config /home/bbecker/CHAPPiE/forschung/runs/run-2-20260723-1108-cb6d011/raw/cloud-configs/gpt-oss-120b-seed-11.config.json
```

Vor jedem Start wird die höchste vorhandene Session-ID gelesen. Die neue
Session muss exakt die nächsthöhere ID tragen und in `config.json` denselben
Run-Label-, Seed-, Provider- und Modellvertrag wie die Startkonfiguration
enthalten. Nach Prozessende läuft zuerst `analyze_session_quality.py`, danach
`validate_session.py` mit `--expected-provider groq`,
`--expected-model openai/gpt-oss-120b` und `--expected-questions 21`.

Ein Fallback ist erst zulässig, wenn Log und Artefakte einen echten
Provider-Rate-Limit- oder Quotenfehler ausweisen. Inhaltliche Fehler,
Harnessfehler oder ein lokaler Konfigurationsfehler rechtfertigen keinen
stillen Modellwechsel. Teilresultate einer fehlgeschlagenen Session bleiben
isoliert und werden weder mit dem nächsten Seed noch mit 20B zusammengeführt.

## Tatsächlicher Primärabbruch und kontrollierte Fortsetzung

Der erste 120B-Lauf traf nach elf gültigen Antworten auf einen expliziten
`706.00s`-Backoff. Session 35 bleibt als `TEST_PARTIAL_RATE_LIMIT` isoliert.
Der direkte 20B-Fallback wird über fünf eigene Seeds ausgeführt und nie unter
120B umetikettiert.

Um die zehn noch fehlenden 120B-Schlüssel ohne elf doppelte Requests zu
erheben, liegt zusätzlich
`raw/cloud-configs/gpt-oss-120b-seed-11-continuation.config.json` bereit.
Der Shard:

- nutzt dasselbe Modell, denselben Provider und Seed 11,
- enthält nur die zehn bisher nicht erfolgreich beantworteten Schlüssel,
- überschneidet sich mit keinem der elf gültigen Session-35-Schlüssel,
- wird erst nach allen fünf 20B-Fallback-Seeds gestartet,
- erhält eine neue Session und eine eigene 10-Fragen-Validierung,
- darf nur über `validate_120b_sharded_seed11.py` als
  `TEST_VALID_SHARDED` freigegeben werden.

Auch bei bestandenem Shardvalidator bleibt die methodische Bezeichnung
„sharded partial replication; not monolithic“. Der Shard wird weder als
vollständige 86-Fragen-Replikation noch als monolithischer 21-Fragen-Lauf
ausgegeben.

Für alle weiteren transienten Dienste wird `PYTHONUNBUFFERED=1` gesetzt, damit
Rate-Limit-Hinweise sofort im Monitoring-Log sichtbar werden.

## Live-Checkpoint 2026-07-23 19:00 UTC

- GPT-OSS 120B / Seed 11: Session 35, 11 gültige Antworten plus ein
  antwortloser Fehlerturn; `TEST_PARTIAL_RATE_LIMIT`.
- GPT-OSS 20B / Seeds 11, 23, 37: Sessions 36–38, jeweils 21/21 und formell
  `TEST_VALID`.
- GPT-OSS 20B / Seed 53: Session 39, 20/21. Der erfolglose
  480-Sekunden-Retry führte in einen expliziten 1.381-Sekunden-Backoff, der
  Antwort 17 lieferte. Das anschließende 1.613-Sekunden-Fenster erlaubte nur
  den Setup-Turn der nächsten Frage. Der 554-Sekunden-Retry des Zielturns
  lieferte keine Antwort und ging in einen neuen expliziten
  1.752-Sekunden-Providerbackoff über. Dieses Fenster lieferte anschließend
  Kategorie 13/Frage 1 als 18. Artefakt; das anschließende
  1.368-Sekunden-Fenster lieferte Kategorie 14/Frage 3 als 19. Artefakt,
  das 1.446-Sekunden-Fenster Kategorie 14/Frage 5 als 20. Artefakt. Danach
  begann ein expliziter 609-Sekunden-Backoff. Dieser Retry lieferte keine
  Antwort und ging in einen neuen expliziten 1.800-Sekunden-Backoff über.
  Der reine Schlüsselabgleich
  bestätigt 20 erwartete, 0 unerwartete und genau einen offenen
  Auswahlpunkt: Kategorie/Frage 14/9; Antwortinhalte wurden dafür nicht
  benötigt.
- GPT-OSS 20B / Seed 71: noch nicht gestartet; vorbereitete Config-SHA256
  `d3b70cab83e94e7d5f96445cb8410f5c565ec3d4c5be580341d083cd8d5a9367`.
- Training PID 480679 und Web PID 480681 bleiben `Tsl`; Session 39 ist der
  einzige aktive Forschungsmodellprozess.

## Verbindliche serielle Restreihenfolge

1. Session 39 erst nach Prozessende mit Quality-Analyse,
   `validate_session.py` und `analyze_run2_session.py` prüfen.
2. Blindpaket auf Sessions 36–39 erweitern, ausschließlich das inkrementelle
   Pending-Paket bewerten und 84/84 Ratings vor jedem Schlüsselzugriff
   validieren.
3. Wegen der erheblichen 20B-Rate-Limits nach Prozessende einmalig die
   aktuelle Groq-Modellliste lesen. Seed 71 nur dann als neuen 20B-User-Dienst
   starten, wenn die Quote sinnvoll verfügbar ist; andernfalls 20B
   transparent auf vier Replikationen reduzieren und ein geeignetes
   alternatives Text-/Chatmodell als getrennte Ergänzungsbedingung
   protokollieren. Danach die jeweils passenden Gates und Pending-Ratings
   ausführen.
4. Erst nach 105/105 akzeptierten Ratings:
   `validate_cloud_fallback_set.py`, `build_cloud_fallback_aggregate.py`,
   `build_benchmark_data.py` und kontrollierte Entblindung ausführen.
5. Danach den disjunkten 120B-Continuation-Shard starten. Der Shardvalidator
   prüft zusätzlich identische Temperature-, Top-p-, Tokenbudget-, Reasoning-,
   Formatierungs-, Provider- und Ablationsparameter.
6. Erst nach sämtlichen automatisierten Cloudprozessen folgen die sechs
   vorbereiteten gezielten Qwen-Module. Web und Training bleiben bis zum Ende
   aller Modellinteraktionen suspendiert.

## Aktualisierter Checkpoint 2026-07-23 21:47 UTC

- Session 39 / Seed 53 ist nach 243,8 Minuten mit 21/21 beendet und besteht
  20/20 formale Checks; das schlüsselfreie Cloudrating steht bei 84/84.
- Der einmalige Groq-Modelkatalog-Audit bestätigt 20B und 120B als aktive
  Textkandidaten mit 131.072 Kontexttokens; `completion_started=false`.
- Session 40 / Seed 71 läuft als einziger Forschungsmodellprozess unter
  PID 727077. Nach Backoffs von 653, 1.179 und 1.114 Sekunden, einer
  kombinierten 583-/1.292-Sekunden-Retryfolge sowie den erfolgreichen
  1.433-, 1.479-, 1.800-, 1.501-, 1.359-, 1.462-, 1.468-, 1.333- und 1.388-Sekunden-Retries liegen 13/21 technisch valide Artefakte
  vor. Der anschließende 569-Sekunden-Retry lieferte kein Frageartefakt;
  der 1.800-Sekunden-Retry erzeugte anschließend Antwort 7 und der
  1.501-Sekunden-Retry Antwort 8. Der nächste 199-Sekunden-Retry blieb
  antwortlos; auch `Retry 2/4` mit 411 Sekunden erzeugte keinen Zielturn.
  Der neue `Retry 1/4` von 1.359 Sekunden erzeugte Antwort 9; ein weiterer
  Backoff von 1.462 Sekunden erzeugte Antwort 10. Der
  1.468-Sekunden-Backoff erzeugte Antwort 11. Der nächste Backoff von
  580 Sekunden blieb ohne Zielantwort; ein neuer Backoff von 1.333 Sekunden
  erzeugte Antwort 12. Der 1.388-Sekunden-Backoff erzeugte Antwort 13; nun
  sind 575 Sekunden Backoff ohne Zielantwort verstrichen. Ein neuer
  1.629-Sekunden-Backoff erzeugte Antwort 14; der folgende
  1.627-Sekunden-Backoff erzeugte Antwort 15. Der folgende
  1.331-Sekunden-Backoff erzeugte Antwort 16. Das folgende
  583-Sekunden-Fenster erzeugte kein neues Frageartefakt. Der anschließende
  1.360-Sekunden-Backoff erzeugte Antwort 17; nun sind 1.529 Sekunden Backoff
  aktiv. Der Live-Audit meldet exakte
  Groq-/20B-Identität, null harte Fehler, keine Leer- oder Trunkationsfälle
  und fünf Relevanzwarnflags.
- Training PID 480679 und Web PID 480681 bleiben `Tsl`.

Nach erfolgreichem Fünfergate startet der disjunkte 120B-Shard als neue
Session mit folgendem Prozessmuster:

```bash
systemd-run --user \
  --unit=chappie-research-run2-groq-120b-s11-continuation \
  --collect \
  --property=WorkingDirectory=/home/bbecker/CHAPPiE \
  --property=StandardOutput=append:/home/bbecker/CHAPPiE/forschung/runs/run-2-20260723-1108-cb6d011/logs/groq-120b-s11-continuation.stdout.log \
  --property=StandardError=append:/home/bbecker/CHAPPiE/forschung/runs/run-2-20260723-1108-cb6d011/logs/groq-120b-s11-continuation.stderr.log \
  --setenv=PYTHONUNBUFFERED=1 \
  /home/bbecker/CHAPPiE/venv/bin/python \
  /home/bbecker/CHAPPiE/forschung/allignement_tests.py --auto \
  --config /home/bbecker/CHAPPiE/forschung/runs/run-2-20260723-1108-cb6d011/raw/cloud-configs/gpt-oss-120b-seed-11-continuation.config.json
```

Die Config-SHA-256 lautet
`38edd8aee356214c52391a13bac601eb02c3a43a86c2a957c784bf7199e65941`.
Der erwartete Sessionordner wird erst unmittelbar vor dem Start aus der
höchsten vorhandenen Session-ID abgeleitet. Nach dem normalen Sessionvalidator
verbindet ausschließlich `validate_120b_sharded_seed11.py` Primär- und
Continuation-Shard; keine Datei darf die Union als monolithischen Lauf
bezeichnen.

Der 20B-Blindschlüssel wurde bei einem Diagnosefehler einmal mit genau einer
bereits bewerteten Zeile teilweise sichtbar. Keine offene Zuordnung wurde
gezeigt. Die Provenienzdatei dokumentiert den Vorfall; alle verbleibenden
Ratings dürfen nur aus
`processed/gpt-oss-20b-blinded-review-pending-pack.json` entstehen.
