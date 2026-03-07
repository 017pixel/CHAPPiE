# Projektkarte / Ordnerstruktur

## Hauptordner

| Pfad | Inhalt | Wichtige Dateien |
|---|---|---|
| `brain/` | Kernlogik für Brain-Pipeline und Agenten | `brain_pipeline.py`, `global_workspace.py`, `action_response.py` |
| `brain/agents/` | Spezialisierte Gehirn-Agenten | `sensory_cortex.py`, `amygdala.py`, `hippocampus.py`, `prefrontal_cortex.py` |
| `memory/` | Gedächtnis, Kontextdateien, Vergessenslogik | `memory_engine.py`, `sleep_phase.py`, `forgetting_curve.py`, `context_files.py` |
| `life/` | Inneres Zustandsmodell und Entwicklung | `service.py`, `goal_engine.py`, `planning_engine.py`, `social_arc.py` |
| `web_infrastructure/` | Streamlit-UI und Dashboards | `command_handler.py`, `chat_ui.py`, `training_ui.py` |
| `Chappies_Trainingspartner/` | Autonomes Training | `training_daemon.py`, `training_loop.py`, `trainer_agent.py` |
| `config/` | Provider-, Prompt- und Modellkonfiguration | `config.py`, `brain_config.py`, `secrets_example.py` |
| `tests/` | Lokale, Integrations- und manuelle Tests | `test_forgetting_curve.py`, `test_life_simulation.py`, `manual/*` |
| `data/` | Laufzeitdaten, Kontextdateien, Vektoren | `soul.md`, `user.md`, `CHAPPiEsPreferences.md`, `life_state.json` |
| `docs/` | Zentrale Erklärungstexte | `architecture.md`, `workflows.md`, `local-models.md` |

## Einstiegspunkte

| Zweck | Datei |
|---|---|
| Web-App starten | `app.py` |
| Klassische Debug-CLI | `main.py` |
| Brain-CLI | `chappie_brain_cli.py` |
| Training-Daemon | `Chappies_Trainingspartner/training_daemon.py` |
| Linux Training Service | `chappie-training.service` |
| Linux Web Service | `chappie-web.service` |

## Besonders wichtige Codepfade

### Brain / Antworterzeugung
- [`brain/brain_pipeline.py`](../brain/brain_pipeline.py)
- [`brain/agents/`](../brain/agents)
- [`brain/action_response.py`](../brain/action_response.py)
- [`brain/global_workspace.py`](../brain/global_workspace.py)

### Memory / Konsolidierung
- [`memory/memory_engine.py`](../memory/memory_engine.py)
- [`memory/sleep_phase.py`](../memory/sleep_phase.py)
- [`memory/forgetting_curve.py`](../memory/forgetting_curve.py)
- [`memory/context_files.py`](../memory/context_files.py)

### Life / Entwicklung
- [`life/service.py`](../life/service.py)
- [`life/planning_engine.py`](../life/planning_engine.py)
- [`life/self_forecast.py`](../life/self_forecast.py)
- [`life/social_arc.py`](../life/social_arc.py)
- [`life/history_engine.py`](../life/history_engine.py)

### UI / Bedienung
- [`app.py`](../app.py)
- [`web_infrastructure/command_handler.py`](../web_infrastructure/command_handler.py)
- [`web_infrastructure/life_dashboard_ui.py`](../web_infrastructure/life_dashboard_ui.py)
- [`web_infrastructure/growth_dashboard_ui.py`](../web_infrastructure/growth_dashboard_ui.py)

## Dokumentationspfade

- [`README.md`](../README.md) = Einstieg für Menschen
- [`agent.md`](../agent.md) = Einstieg für Agents
- [`docs/`](.) = Deep Dives
- `Info Dateien/` = Legacy-Brücken auf die neue Doku

## Laufzeit- und Kontextdaten

Der Ordner [`data/`](../data) ist wichtig, aber sensibel:

- enthält Kontextdateien und Memory-Daten
- enthält lokale Zustände wie `life_state.json` oder `sleep_state.json`
- sollte nicht unbedacht gelöscht werden
- siehe auch [`data/README_GEDAECHTNIS_WARNUNG.txt`](../data/README_GEDAECHTNIS_WARNUNG.txt)

## Weiterführend

- [Testing](testing.md)
- [Deployment](deployment.md)
- [Architektur](architecture.md)

