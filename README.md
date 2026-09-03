# CHAPPiE

CHAPPiE ist eine experimentelle Cognitive-Agent-Architektur. Das Projekt untersucht, wie LLM-Antworten durch episodisches Gedächtnis, simulierte innere Zustände, Life-Simulation und Activation Steering über längere Interaktionen konsistent beeinflusst werden können.

CHAPPiE verwendet kein selbst trainiertes Basismodell. Der produktive Web-Chat läuft lokal über Qwen 3.5 und einen OpenAI-kompatiblen vLLM-Steering-Service. Ollama und Groq bleiben unterstützte Adapter; Groq kann zusätzlich Emotions-Appraisal und Ausgabeformatierung übernehmen, ohne die lokale Antwortgenerierung zu ersetzen.

## Aktive Architektur

```text
Frontend / API / CLI / Research
        -> CHAPPiERuntime
        -> TurnPipeline + TurnContext
        -> Brain, Memory, Life und Global Workspace
        -> GenerationGateway -> vLLM + Steering
        -> Formatierung + Persistenz
        -> JSON oder SSE
```

Der gemeinsame fachliche Turn-Kern wird von synchronen und gestreamten Antworten verwendet. `web_infrastructure/backend_wrapper.py` ist nur noch die abwärtskompatible Import- und Factory-Schicht.

| Bereich | Aktive Quelle |
|---|---|
| Runtime-Fassade | `web_infrastructure/chappie_runtime.py` |
| Turn-Orchestrierung | `web_infrastructure/turn_pipeline.py` |
| Turn-Vertrag | `web_infrastructure/contracts.py`, `turn_context.py` |
| Modellzugriff | `web_infrastructure/generation.py` |
| Persistenz | `web_infrastructure/persistence.py` |
| Antwortformat | `web_infrastructure/formatting.py` |
| Steering | `brain/steering_manager.py`, `brain/steering_backend.py` |
| Memory | `memory/` |
| Life-Simulation | `life/` |

Die frühere Multi-Agent-`BrainPipeline` ist nicht der aktive Requestpfad. Ihre unveränderte v1-Quelle und die zugehörigen Agenten liegen unter [`Legacy-Code/`](Legacy-Code/README.md). Der alte Import `brain.brain_pipeline` bleibt lazy kompatibel.

## Funktionen

- Episodisches Gedächtnis mit ChromaDB, Hybrid-RAG, Recall-Stärke, Verknüpfungen und Vergessenskurve
- Life-Simulation mit Needs, Goals, Habit Dynamics, Attachment und Timeline
- zehn gekoppelte Emotionen mit VAD-Mapping und reinem Layer-Steering im lokalen Antwortpfad
- gemeinsamer synchroner und gestreamter Turn-Kern
- Causal Trace für Intent, Memory, Emotion, Life, Steering und Tonentscheidung
- Sleep-Phase mit Replay und Konsolidierung
- autonomer Trainings-Daemon in einer isolierten Laufzeitumgebung
- Forschungs-Harness mit 86 Fragen in 14 Kategorien

## Schnellstart

Voraussetzung ist Python 3.11 oder neuer.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd frontend
npm ci --legacy-peer-deps
cd ..
```

`requirements.txt` bleibt die vollständige Installation. Leichtere Gruppen:

| Zweck | Datei |
|---|---|
| API, Memory, Basisruntime | `requirements/runtime.txt` |
| lokale Provider und GPU-Serving | `requirements/providers-local.txt` |
| Training und Fine-Tuning | `requirements/training.txt` |
| deterministische CI | `requirements/ci.txt` |
| Entwicklung | `requirements/development.txt` |

### Konfiguration

Die zentrale Quelle ist `config/config.py`, die lesbare Vorlage `config/example_config.py`. Lokale Overrides und Secrets liegen in der ignorierten Root-Datei `CHAPPIE_CONFIG.json`:

```bash
python3 -c "from config.config import write_config; write_config({})"
```

Der produktive Web-Chat verwendet bewusst immer den lokalen vLLM-Pfad. `enable_two_step_processing` bleibt aus Kompatibilitätsgründen gespeichert und UI-sichtbar, schaltet die aktive Web-Runtime aber nicht auf eine alte Parallelpipeline zurück.

Die Trainingskonfiguration liegt unter `config/training_config.json`. Eine vorhandene Root-Datei `training_config.json` wird weiterhin gelesen, neue Schreibvorgänge verwenden den zentralen Pfad.

Secrets gehören ausschließlich in `CHAPPIE_CONFIG.json`, `config/secrets.py` oder ignorierte Dateien unter `config/APIs/`. Keine dieser Dateien wird committed.

### Starten

```bash
# API auf Port 8010
python3 app.py

# Frontend-Entwicklung auf Port 5173
cd frontend && npm run dev

# lokale CLI
python3 chappie_brain_cli.py

# Remote-CLI
python3 chappie_brain_cli.py --remote

# autonomes Training
python3 -m Chappies_Trainingspartner.training_daemon
```

Der Steering-Service läuft separat auf Port 8000:

```bash
python3 -m brain.steering_api_server
```

## Provider

| Provider | Rolle | Steering |
|---|---|---|
| vLLM | produktiver lokaler Webpfad und Standard | Activation Steering |
| Ollama | lokaler Adapter für CLI, Training und Tests | Prompt-Kontext |
| Groq | optionale Analyse, Formatierung, Training und Forschung | kein Steering im lokalen Antwortpfad |

Aktive Provider sind ausschließlich `vllm`, `ollama` und `groq`. Cerebras-Bezüge sind nur in ausdrücklich historischen Forschungs- oder Legacy-Dateien zulässig.

Im vLLM-Antwortpfad stehen keine Emotionswerte, Tonpläne oder emotional veränderten Samplingwerte im Prompt. Der sichtbare Einfluss entsteht ausschließlich durch kontrastiv berechnete Aktivierungsvektoren. Details und Live-Prüfung stehen in [`docs/emotion-memory-steering.md`](docs/emotion-memory-steering.md).

## Tests

Das Repository nutzt eigenständige Python-Skripte, nicht pytest.

```bash
python3 -m compileall -q api brain config life memory web_infrastructure Chappies_Trainingspartner tests
python3 tests/test_quick.py
python3 tests/test_runtime_architecture.py
python3 tests/test_api_contract.py
python3 forschung/report/validate_report_v5_freeze.py
python3 forschung/report/validate_report_v6.py
cd frontend && npm run build
```

Alle Testgruppen und die minimale CI-Installation stehen in [docs/testing.md](docs/testing.md).

## Forschung und Berichte

- [Forschungsindex](forschung/INDEX.md)
- [Forschungsbericht v5, unveränderte historische Momentaufnahme](forschung/report/CHAPPiE-Forschungsbericht-v5.html)
- [Forschungsbericht v6, aktuelle Architektur und Provenienz](forschung/report/CHAPPiE-Forschungsbericht-v6.html)
- [Forschungsmethodik](docs/research-methodology.md)

Run-2-Messdaten entstanden vor der Runtime-Modularisierung. Bericht v6 trennt diese Daten ausdrücklich von der späteren Architekturverifikation und erfindet keine Post-Migrations-Benchmarks.

## Dokumentation

- [Architektur](docs/architecture.md)
- [Laufzeitverträge](docs/runtime-contracts.md)
- [Workflows](docs/workflows.md)
- [Projektkarte](docs/project-map.md)
- [Lokale Modelle](docs/local-models.md)
- [vLLM-Setup](docs/vLLM-Setup.md)
- [Deployment](docs/deployment.md)
- [Testing](docs/testing.md)
- [Cleanup-Entscheidungen](docs/repository-cleanup.md)
- [Legacy-Code](Legacy-Code/README.md)

## Datenhinweis

`data/` enthält lokale Memories, Kontextdateien und Zustände. Forschungsdaten unter `forschung/` sind Evidenz und wurden beim Cleanup klassifiziert, nicht pauschal gelöscht. Vor Änderungen an Laufzeit- oder Forschungsdaten immer Herkunft und Referenzen prüfen.
