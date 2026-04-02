# Projektkarte / Ordnerstruktur

## Hauptordner

| Pfad | Inhalt | Wichtige Dateien |
|---|---|---|
| `brain/` | Brain-Pipeline, Agenten, Steering, Global Workspace | `brain_pipeline.py`, `global_workspace.py`, `action_response.py`, `steering_api_server.py`, `steering_backend.py` |
| `brain/agents/` | Spezialisierte Gehirn-Agenten | `sensory_cortex.py`, `amygdala.py`, `hippocampus.py`, `prefrontal_cortex.py`, `steering_manager.py` |
| `memory/` | Gedaechtnis, Konsolidierung, Kontextdateien | `memory_engine.py`, `sleep_phase.py`, `forgetting_curve.py`, `context_files.py` |
| `life/` | inneres Zustandsmodell und Entwicklung | `service.py`, `goal_engine.py`, `planning_engine.py`, `social_arc.py` |
| `api/` | FastAPI-App fuer den Webpfad | `main.py`, `routers/*`, `schemas.py`, `dependencies.py` |
| `frontend/` | React/Vite/TypeScript-Frontend | `src/router.tsx`, `src/pages/*`, `src/services/api.ts` |
| `web_infrastructure/` | UI-freie Brueckenschicht | `backend_wrapper.py`, `ui_utils.py` |
| `Chappies_Trainingspartner/` | autonomes Training | `training_daemon.py`, `training_loop.py`, `daemon_manager.py` |
| `config/` | Provider-, Prompt- und Modellkonfiguration | `config.py`, `brain_config.py`, `secrets_example.py` |
| `tests/` | lokale, Integrations- und manuelle Tests | `test_api_contract.py`, `test_chat_manager_persistence.py`, `manual/*` |
| `data/` | Laufzeitdaten, Kontextdateien, Vektoren | `soul.md`, `user.md`, `CHAPPiEsPreferences.md`, `life_state.json` |
| `docs/` | zentrale Erklaertexte | `architecture.md`, `workflows.md`, `local-models.md` |

## Einstiegspunkte

| Zweck | Datei |
|---|---|
| App-API starten | `api/main.py` |
| Kompatibilitaets-Launcher | `app.py` |
| React-Frontend | `frontend/` |
| klassische CLI | `main.py` |
| Brain-CLI | `chappie_brain_cli.py` |
| Training-Daemon | `Chappies_Trainingspartner/training_daemon.py` |
| lokaler Steering-Endpoint | `brain/steering_api_server.py` |
| Linux API-Service | `chappie-web.service` |
| Linux Frontend-Service | `chappie-frontend.service` |
| Linux Modellservice | `chappie-vllm.service` |

## Besonders wichtige Codepfade

### Brain / Antworterzeugung

- [`brain/brain_pipeline.py`](../brain/brain_pipeline.py)
- [`brain/agents/`](../brain/agents)
- [`brain/action_response.py`](../brain/action_response.py)
- [`brain/global_workspace.py`](../brain/global_workspace.py)
- [`brain/steering_api_server.py`](../brain/steering_api_server.py)

### Memory / Konsolidierung

- [`memory/memory_engine.py`](../memory/memory_engine.py)
- [`memory/sleep_phase.py`](../memory/sleep_phase.py)
- [`memory/forgetting_curve.py`](../memory/forgetting_curve.py)
- [`memory/context_files.py`](../memory/context_files.py)

### Webpfad

- [`app.py`](../app.py)
- [`api/main.py`](../api/main.py)
- [`api/routers/`](../api/routers)
- [`api/services/`](../api/services)
- [`frontend/src/router.tsx`](../frontend/src/router.tsx)
- [`frontend/src/pages/chat-page.tsx`](../frontend/src/pages/chat-page.tsx)
- [`frontend/src/pages/training-page.tsx`](../frontend/src/pages/training-page.tsx)
- [`web_infrastructure/backend_wrapper.py`](../web_infrastructure/backend_wrapper.py)
- [`web_infrastructure/ui_utils.py`](../web_infrastructure/ui_utils.py)

### Training

- [`Chappies_Trainingspartner/daemon_manager.py`](../Chappies_Trainingspartner/daemon_manager.py)
- [`Chappies_Trainingspartner/training_daemon.py`](../Chappies_Trainingspartner/training_daemon.py)
- [`Chappies_Trainingspartner/training_loop.py`](../Chappies_Trainingspartner/training_loop.py)

## Dokumentationspfade

- [`README.md`](../README.md) fuer Menschen
- [`agent.md`](../agent.md) fuer Agents
- [`docs/`](.) fuer Deep Dives
- `Info Dateien/` als Legacy-Bruecken

## Laufzeit- und Kontextdaten

[`data/`](../data) ist sensibel:

- enthaelt Kontextdateien und Memory-Daten
- enthaelt lokale Zustandsdateien
- sollte nicht unbedacht geloescht werden

Siehe auch [`data/README_GEDAECHTNIS_WARNUNG.txt`](../data/README_GEDAECHTNIS_WARNUNG.txt).

## Weiterfuehrend

- [Testing](testing.md)
- [Deployment](deployment.md)
- [Architektur](architecture.md)
