# Projektkarte / Ordnerstruktur

## Hauptordner

| Pfad | Inhalt | Wichtige Dateien |
|---|---|---|
| `brain/` | Brain-Pipeline, Agenten, Steering, Global Workspace | `brain_pipeline.py`, `global_workspace.py`, `action_response.py`, `steering_api_server.py`, `steering_backend.py` |
| `brain/agents/` | Spezialisierte Gehirn-Agenten | `sensory_cortex.py`, `amygdala.py`, `hippocampus.py`, `prefrontal_cortex.py`, `steering_manager.py` |
| `memory/` | Gedaechtnis, Konsolidierung, Kontextdateien | `memory_engine.py`, `sleep_phase.py`, `forgetting_curve.py`, `context_files.py` |
| `life/` | Inneres Zustandsmodell und Entwicklung | `service.py`, `goal_engine.py`, `planning_engine.py`, `social_arc.py` |
| `api/` | FastAPI-App fuer den Webpfad | `main.py`, `routers/*`, `schemas.py`, `dependencies.py` |
| `frontend/` | React/Vite/TypeScript-Frontend | `src/router.tsx`, `src/pages/*`, `src/services/api.ts` |
| `web_infrastructure/` | UI-freie Brueckenschicht | `backend_wrapper.py`, `ui_utils.py` |
| `Chappies_Trainingspartner/` | Autonomes Training | `training_daemon.py`, `training_loop.py`, `daemon_manager.py` |
| `config/` | Provider-, Prompt- und Modellkonfiguration | `config.py`, `root_config.py`, `brain_config.py`, `prompts.py` |
| `deploy/` | Systemd-Services und Deployment-Scripts | `chappie-vllm.service`, `chappie-web.service`, `chappie-frontend.service`, `chappie-training.service`, `deploy_training.sh` |
| `scripts/` | Setup, Cleanup, Backup, Validierung | `setup.sh`, `cleanup.py`, `backup_project.py`, `validate_system.py` |
| `scripts/archive/` | Veraltete Dateien (nicht aktiv genutzt) | `main_legacy.py` (altes CLI), `generate_anti_safeguard.py` (Mock-Skript) |
| `tests/` | Lokale, Integrations- und manuelle Tests | `test_*.py`, `manual/*` |
| `forschung/` | Alignment-Test-Harness, automatisierte Emotion/Reasoning/Ethik-Tests | `allignement_tests.py`, `session_runner.py`, `session_logger.py`, `test_fragen.md` |
| `data/` | Laufzeitdaten, Kontextdateien, Vektoren | `soul.md`, `user.md`, `CHAPPiEsPreferences.md`, `life_state.json` |
| `docs/` | Zentrale Erklaertexte | `architecture.md`, `workflows.md`, `local-models.md` |

## Einstiegspunkte

| Zweck | Datei |
|---|---|
| App-API starten | `app.py` → `api/main.py` |
| React-Frontend | `frontend/` |
| Terminal-CLI (v5.0) | `chappie_brain_cli.py` |
| Terminal-CLI (Remote) | `chappie_brain_cli.py --remote` |
| Training-Daemon | `Chappies_Trainingspartner/training_daemon.py` |


| Lokaler Steering-Endpoint | `brain/steering_api_server.py` |
| Forschung / Alignment-Tests (TUI) | `forschung/allignement_tests.py` |
| Forschung / Alignment-Tests (systemd) | `systemctl start chappie-forschung` |

## Systemd-Services (in `deploy/`)

| Service | Zweck |
|---|---|
| `deploy/chappie-vllm.service` | Steering-Server (GPU, Qwen3.5-4B) |
| `deploy/chappie-web.service` | FastAPI Backend |
| `deploy/chappie-frontend.service` | React Frontend (npm preview) |
| `deploy/chappie-training.service` | Autonomes Training (deaktiviert) |
| `forschung/chappie-forschung.service` | Alignment-Test-Harness (Headless-Mode) |

## Besonders wichtige Codepfade

### Brain / Antworterzeugung

- [`brain/brain_pipeline.py`](../brain/brain_pipeline.py)
- [`brain/agents/`](../brain/agents)
- [`brain/action_response.py`](../brain/action_response.py)
- [`brain/global_workspace.py`](../brain/global_workspace.py)
- [`brain/steering_api_server.py`](../brain/steering_api_server.py)
- [`brain/steering_backend.py`](../brain/steering_backend.py) (NF4-Quantisierung, Activation Steering)

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
- [`frontend/src/services/api.ts`](../frontend/src/services/api.ts)
- [`web_infrastructure/backend_wrapper.py`](../web_infrastructure/backend_wrapper.py)

### Training

- [`Chappies_Trainingspartner/daemon_manager.py`](../Chappies_Trainingspartner/daemon_manager.py)
- [`Chappies_Trainingspartner/training_daemon.py`](../Chappies_Trainingspartner/training_daemon.py)

### Skripte & Deployment

- [`scripts/setup.sh`](../scripts/setup.sh)
- [`scripts/cleanup.py`](../scripts/cleanup.py)
- [`scripts/validate_system.py`](../scripts/validate_system.py)
- [`deploy/deploy_training.sh`](../deploy/deploy_training.sh)

## Dokumentationspfade

- [`README.md`](../README.md) fuer Menschen
- [`AGENTS.md`](../AGENTS.md) fuer Agents
- [`docs/`](.) fuer Deep Dives

## Laufzeit- und Kontextdaten

[`data/`](../data) ist sensibel:

- enthaelt Kontextdateien und Memory-Daten
- enthaelt lokale Zustaende (life_state.json, short_term_memory.json)
- sollte nicht unbedacht geloescht werden

## Weiterfuehrend

- [Testing](testing.md)
- [Deployment](deployment.md)
- [Architektur](architecture.md)