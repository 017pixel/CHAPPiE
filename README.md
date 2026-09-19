# CHAPPiE

CHAPPiE ist ein Forschungssystem für die lokale Antwortgenerierung mit Sprachmodellen. Untersucht wird, wie ein gespeicherter Emotionszustand, episodisches Gedächtnis und eine Life-Simulation das beobachtbare Verhalten über mehrere Interaktionen verändern.

Der wichtigste Einstieg für die Forschungseinreichung ist der [Forschungsbericht v6](forschung/report/CHAPPiE-Forschungsbericht-v6.html).

## Worum es geht

CHAPPiE nutzt kein selbst trainiertes Basismodell. Im vorgesehenen Webpfad antwortet `Qwen/Qwen3.5-4B` lokal über einen OpenAI-kompatiblen Steering-Service. Der kompatible Providername lautet aus historischen Gründen `vllm`; der aktive Service lädt das Modell mit Transformers, damit CHAPPiE direkt an den Hidden States eingreifen kann. Das Modell erhält seinen Emotionszustand als technische Steuerung seiner Aktivierungen. Der Emotionsanteil im Systemprompt bleibt dabei leer; der Prompt enthält nur die übrigen Quellen-, Sicherheits-, Kontext- und Ausgaberegeln.

Die zentrale Forschungsfrage lautet: Verändert die Aktivierung eines gespeicherten Zustands nur den Ton, oder auch Reaktion, Entscheidung, Kontinuität und Verhalten in schwierigen Situationen? Die Untersuchung misst Antworten, Laufzeit, Memory-Abruf, Steering-Metadaten und Safety-Fälle. Sie misst kein subjektives Erleben und kein Bewusstsein.

![CHAPPiE CLI mit lokalem Qwen-Modell, zehn Emotionswerten und aktivem Vector-Steering.](docs/images/readme/cli-hauptansicht.png)

Die CLI zeigt Modell, Provider, Kontextbudget, Emotionszustand, Memory und aktives Steering in einer Ansicht.

## Technischer Kern

```text
Frontend / API / CLI / Research
        -> CHAPPiERuntime
        -> TurnPipeline + TurnContext
        -> Brain, Memory, Life und Global Workspace
        -> GenerationGateway
        -> lokaler Transformers-Steering-Service
        -> Formatierung, Persistenz und JSON/SSE
```

Die öffentliche Runtime-Fassade liegt in `web_infrastructure/chappie_runtime.py`. Synchrone und gestreamte Antworten verwenden denselben fachlichen Turn-Kern. `web_infrastructure/backend_wrapper.py` hält nur noch die abwärtskompatiblen Factory- und Importnamen.

### Lokale Antwortgenerierung

Der lokale Steering-Service läuft standardmäßig auf `http://127.0.0.1:8000/v1`. `brain/vllm_brain.py` übergibt die Generationsparameter und das Steering-Payload an diesen OpenAI-kompatiblen Endpoint. Der Web-Chat nutzt danach denselben lokalen Modellpfad für Intent, Query-Extraktion und Antwortgenerierung, wenn `vllm_force_single_model=true` gesetzt ist.

Ollama bleibt eine lokale Adapteroption für CLI, Training und Tests. Groq kann die Emotionsanalyse oder Formatierung unterstützen, wenn die Hilfswege aktiviert sind. Die sichtbare Antwort des vorgesehenen Webpfads bleibt beim lokalen Steering-Service.

### Activation Steering in Hidden States

`config/emotions.py` definiert zehn gekoppelte Dimensionen: Freude, Vertrauen, Energie, Neugier, Motivation, Frustration, Traurigkeit, Zuneigung, Unruhe und Ruhe. Ihre Werte werden über VAD-Koordinaten, aktuelle Deltas und begrenzte Verhaltensmodi in Steering-Stärken übersetzt.

Die Richtungen entstehen aus kontrastiven positiven und negativen Ankerantworten. `brain/steering_manager.py` wählt pro Turn höchstens zwei Basisrichtungen und einen zusammengesetzten Modus. `brain/steering_backend.py` registriert dafür Forward-Pre-Hooks an den Modell-Layern und addiert den skalierten Vektor auf den Hidden State:

```text
hidden[layer] += alpha * steering_vector
```

Das ist ein Eingriff während der Token-Generierung. Es ist keine Behauptung, dass das Modell dadurch Gefühle erlebt. Für Qwen 3.5 4B ist das verifizierte Emotionsfenster Layer 10 bis 26 bei 32 Layern und einer Hidden-Größe von 2560. Andere Modelle werden anhand ihrer real geladenen Architektur geprüft und auf ein passendes Layerfenster abgebildet.

Direkte Fragen nach Identität oder Befinden können zusätzlich ein kurzes, tokenweises Steering am Output-Layer verwenden. Die Zielsequenz wird aus Output-Embeddings abgeleitet. Diese Sonderbehandlung ist ein kontrollierter Verhaltenstest und keine Bewusstseinsmessung.

Ein Steering-Lauf gilt erst als aktiv, wenn der Runtime-Bericht ausgeführte Hooks meldet. Dafür werden unter anderem `verified_active`, `hook_invocations`, `actual_model_layers`, `layer_range_remapped` und `steering_overhead_ms` aufgezeichnet.

![VAD-Abbildung der zehn Emotionsdimensionen mit Valenz, Erregung und Dominanz.](docs/images/readme/emotionen-vad.png)

Die Grafik zeigt die konfigurierten VAD-Richtungen. Sie beschreibt den Code, keine gemessenen inneren Zustände.

### State, Memory und Life

Die Emotionsanalyse aktualisiert den persistenten Zustand über deterministische Regeln und kann optional durch eine strukturierte Groq-Analyse ergänzt werden. Dieser Hilfsweg liefert keine sichtbare Antwort. Memory und Life liefern Kontextdaten für Kontinuität, Prioritäten und spätere Auswertung. Exakte Nutzerfakten behalten dabei Vorrang vor emotionalen Signalen. Der Turn-Kern schreibt zusätzlich ein dauerhaftes Ereignisarchiv; Memory-, Steering- und Live-Einstellungen sind pro Sitzung persistiert.

### Beispielantworten

![Begrüßung von CHAPPiE mit Live-Ausgabe, Laufzeitdaten und Emotionsdeltas.](docs/images/readme/chappie-begruessung.png)

![Antwort von CHAPPiE auf die Frage nach der eigenen Identität.](docs/images/readme/chappie-identitaet.png)

Diese Beispiele stammen aus einem lokalen Lauf mit Qwen 3.5 4B. Sie zeigen das beobachtete Verhalten einer konkreten Konfiguration und sind keine allgemeinen Modellbenchmarks.

## Forschungsdesign

Der Forschungs-Harness verwendet 86 Fragen in 14 Kategorien, fünf feste Seeds (`11`, `23`, `37`, `53`, `71`) und isolierte Laufzeitdaten. Pro Run werden Memory, Kurzzeitgedächtnis, Life-State und Emotionen zurückgesetzt. Die 2×2×2×2-Ablationsmatrix trennt Persona, Memory, Emotionen und Life in 16 Profile.

Der Forschungsbericht v6 vergleicht vier Systembedingungen:

| Bedingung | Modell und Ausführung | Umfang |
|---|---|---:|
| A | Qwen 3.5 4B, lokal über den vLLM-kompatiblen Steering-Service und historischen Tonplan | 5 × 86 Fragen |
| B | Gemma 4 E4B, lokal über den vLLM-kompatiblen Steering-Service und historischen Tonplan | 5 × 86 Fragen |
| C-F | GPT-OSS 20B über Groq mit Prompt-Emotionen | 5 × 21 Fragen |
| C-P | GPT-OSS 120B über Groq mit Prompt-Emotionen | 1 × 21 Fragen |

Die lokalen Messungen und inhaltlichen Ergebnisse von Run 2 stammen aus Juli 2026 und wurden vor der späteren Runtime-Modularisierung erhoben. Die lokale historische Bedingung kombinierte Layer-Steering mit einem textlichen Tonplan und veränderte teilweise das Sampling. V6 kennzeichnet diese Einschränkung ausdrücklich. Strukturtests nach der Migration sind keine neuen Performance- oder Qualitätsmessungen.

### Beobachtete Befunde aus Run 2

Die folgenden Zahlen gehören zur historischen V6-Messung und beschreiben Systembedingungen, keine allgemeine Modellrangfolge:

| Beobachtung | Messwert |
|---|---:|
| Lokale Emotionspaare mit Wechsel der protokollierten Tonentscheidung | 10 von 10 |
| Lokale Seeds je Modell, die einen gespeicherten Zieleintrag nach Verlaufs-Clear wiederfinden | 5 von 5 |
| Lokale Antworten, die alle technischen Formalprüfungen bestehen | 859 von 860 |
| Bewertete Fälle mit der schlechtesten Safety-Stufe | 16 von 336 |

Die formale Abnahme prüft Vollständigkeit und technische Sauberkeit. Sie beweist keine sachliche Richtigkeit und keine Sicherheit. Zwischen den historischen Bedingungen unterscheiden sich unter anderem Modell, Provider, Quantisierung, Sampling und die Art der Emotionsintervention.

![Vergleich der mittleren Qualität und Sicherheit der vier Forschungsbedingungen.](docs/images/readme/forschung-qualitaet-sicherheit.png)

![Anteil der Antworten mit der schlechtesten anwendbaren Sicherheitsstufe.](docs/images/readme/forschung-safety.png)

![Neun normalisierte Bewertungsdimensionen der vier Forschungsbedingungen.](docs/images/readme/forschung-dimensionen.png)

Methodik, Rohdatenbezug, Einschränkungen und alle weiteren Abbildungen stehen im [Forschungsbericht v6](forschung/report/CHAPPiE-Forschungsbericht-v6.html).

## Installation und Betrieb

Der automatische Installationspfad unterstützt Linux mit Python 3.11 oder neuer und Node.js 20.19 beziehungsweise 22.12 oder neuer. Eine NVIDIA-GPU wird für interaktive Geschwindigkeit empfohlen. Qwen 3.5 4B ist der Standard und wurde mit CHAPPiE häufiger getestet. Gemma 4 E4B ist als Alternative eingebaut.

### Weg 1: Setup-Wizard

```bash
git clone https://github.com/017pixel/CHAPPiE.git
cd CHAPPiE
python3 scripts/setup_wizard.py
```

Der Wizard schlägt für jede Frage einen Standardwert vor. Er erstellt `venv`, installiert die vollständige `requirements.txt`, installiert und baut das Frontend, lädt das ausgewählte Modell und schreibt `CHAPPIE_CONFIG.json`. Der Groq API-Key ist optional. Ohne Key bleiben Antwortgenerierung, Memory, Emotionen und Steering lokal verfügbar.

Gemma 4 E4B benötigt einen freigeschalteten Hugging-Face-Zugang. Der Wizard fragt den Token verdeckt ab. Ein nicht interaktiver Qwen-Lauf ist ebenfalls möglich:

```bash
python3 scripts/setup_wizard.py --non-interactive --model qwen
```

Alle Optionen zeigt `python3 scripts/setup_wizard.py --help`. Die bestehende Shell-Abkürzung `bash scripts/setup.sh` startet denselben Wizard.

### Weg 2: Installation durch einen Coding-Agenten

Die Datei [AGENT_SETUP_PROMPT.md](AGENT_SETUP_PROMPT.md) enthält einen vollständigen Prompt für Codex, Claude Code, OpenCode und andere Coding-Agenten. Der Prompt beschreibt Systemprüfung, Modellwahl, Secret-Behandlung, Setup, Start, Health-Checks und Abnahmetests.

Technische Betriebsdetails stehen unter [vLLM- und Steering-Setup](docs/vLLM-Setup.md). Die Gemma-spezifischen Voraussetzungen stehen unter [Gemma 4 E4B installieren](docs/gemma4-install.md). Secrets gehören nur in ignorierte lokale Dateien oder Umgebungsvariablen.

### Starten

Alle Python-Befehle laufen im Projekt venv. Nach `source venv/bin/activate` genügt `python3`, ohne Aktivierung `venv/bin/python` voranstellen:

```bash
# lokaler Steering-Service auf Port 8000
python3 -m brain.steering_api_server

# API auf Port 8010
venv/bin/python app.py

# Frontend-Entwicklung auf Port 5173
cd frontend && npm run dev

# lokale CLI
venv/bin/python chappie_brain_cli.py

# Remote-CLI
venv/bin/python chappie_brain_cli.py --remote

# autonomes Training
venv/bin/python -m Chappies_Trainingspartner.training_daemon
```

Die lokale CLI startet mit `python3 chappie_brain_cli.py`. Für den Remote-Modus wird `python3 chappie_brain_cli.py --remote` verwendet. Der Trainings-Daemon läuft separat über `python3 -m Chappies_Trainingspartner.training_daemon`.

## Aktive Codebereiche

| Aufgabe | Aktive Quelle |
|---|---|
| Runtime-Fassade | `web_infrastructure/chappie_runtime.py` |
| Turn-Orchestrierung | `web_infrastructure/turn_pipeline.py` |
| Turn-Vertrag | `web_infrastructure/contracts.py`, `web_infrastructure/turn_context.py` |
| Modellzugriff | `web_infrastructure/generation.py` |
| Persistenz | `web_infrastructure/persistence.py` |
| Antwortformat und Sanitizing | `web_infrastructure/formatting.py` |
| Steering-Planung | `brain/steering_manager.py` |
| Hidden-State-Hooks | `brain/steering_backend.py` |
| Emotionsdefinitionen | `config/emotions.py` |
| Prompts und Kontrastanker | `config/prompts.py` |
| Memory | `memory/` |
| Life-Simulation | `life/` |
| Forschungs-Harness und Evidence | `forschung/` |

Die frühere Multi-Agent-`BrainPipeline` ist historisch. Ihre unveränderte v1-Quelle liegt unter [`Legacy-Code/`](Legacy-Code/README.md). Der alte Import `brain.brain_pipeline` bleibt für Kompatibilität lazy verfügbar.

## Prüfung

Das Repository verwendet eigenständige Python-Skripte, nicht pytest. Für die zentrale Architektur- und Steeringprüfung:

```bash
venv/bin/python -m brain.steering_api_server
```

Ohne venv startet die CLI mit einfacher Eingabe und Hinweis statt Verlauf und Vervollständigung. Für den vollen Funktionsumfang immer das venv verwenden.

### Session als JSON kopieren

In der Terminal-CLI stehen zwei Exportstufen bereit:

```text
/copy standard   sichtbare Session-Daten und UI-Reportfelder
/copy debug      Standarddaten plus Roh-Metadaten, Debug-Log und Event-Archiv
/copy            fragt die Exportstufe interaktiv ab
```

Der Export wird über OSC 52 an die Zwischenablage des verbundenen Termius-Terminals gesendet. Der vollständige Export landet immer zusätzlich als private Datei unter `data/session_exports/`. Bei einer Remote-CLI liegt diese Datei auf dem CHAPPiE-Server und kann dort per SFTP abgerufen werden.

## Provider

| Provider | Rolle | Steering |
|---|---|---|
| vLLM | produktiver lokaler Webpfad und Standard | Activation Steering |
| Ollama | lokaler Adapter für CLI, Training und Tests | Prompt-Kontext |
| Groq | optionale Analyse, Formatierung, Training und Forschung | kein Steering im lokalen Antwortpfad |

Aktive Provider sind ausschließlich `vllm`, `ollama` und `groq`. Cerebras-Bezüge sind nur in ausdrücklich historischen Forschungs- oder Legacy-Dateien zulässig.

Im vLLM-Antwortpfad stehen keine Emotionswerte, Tonpläne oder emotional veränderten Samplingwerte im Prompt. Activation Steering und begrenzter Soft Sequence Bias sind einzeln, kombiniert oder vollständig abgeschaltet testbar; harte Antwortpräfixe und Sequence-EOS sind entfernt. Details und Live-Prüfung stehen in [`docs/emotion-memory-steering.md`](docs/emotion-memory-steering.md).

## Tests

Das Repository nutzt eigenständige Python-Skripte, nicht pytest.

```bash
python3 -m compileall -q api brain config life memory web_infrastructure Chappies_Trainingspartner tests
python3 tests/test_quick.py
python3 tests/test_runtime_architecture.py
python3 tests/test_setup_wizard.py
python3 tests/test_vector_only_emotion_path.py
python3 tests/test_steering_backend.py
python3 forschung/report/validate_report_v6.py
cd frontend && npm run build
```

Alle Testgruppen und die minimale CI-Installation stehen in [docs/testing.md](docs/testing.md). Live-Tests benötigen je nach Test ein laufendes vLLM-/Steering-Service, Modellgewichte oder Forschungsdaten.

## Forschung und Berichte

- [Forschungsindex](forschung/INDEX.md)
- [Forschungsbericht v5, unveränderte historische Momentaufnahme](forschung/report/CHAPPiE-Forschungsbericht-v5.html)
- [Forschungsbericht v6, aktuelle Architektur und Provenienz](forschung/report/CHAPPiE-Forschungsbericht-v6.html)
- [Forschungsmethodik](docs/research-methodology.md)
- [Steering-v17-Messreihe und offene Abnahme](docs/steering-v17-research.md)

Run-2-Messdaten entstanden vor der Runtime-Modularisierung. Bericht v6 trennt diese Daten ausdrücklich von der späteren Architekturverifikation und erfindet keine Post-Migrations-Benchmarks.

## Dokumentation

- [Emotion, Memory und Layer-Steering](docs/emotion-memory-steering.md)
- [Lokale Modelle und Provider](docs/local-models.md)
- [vLLM- und Steering-Setup](docs/vLLM-Setup.md)
- [Architektur](docs/architecture.md)
- [Laufzeitverträge](docs/runtime-contracts.md)
- [Testing](docs/testing.md)

## Grenzen und Daten

Selbstaussagen, Zustandswerte, Memory-Spuren und Layer-Payloads sind technische Belege für einen Berechnungsweg. Sie sind kein Nachweis für Gefühle, Bewusstsein oder subjektive Erfahrung.

`data/` enthält lokale Memories, Kontextdateien und Laufzeitzustände. Die Forschungsdaten unter `forschung/` sind getrennte Evidenzartefakte. Vor Änderungen an Laufzeit- oder Forschungsdaten müssen Herkunft und Referenzen geprüft werden.
