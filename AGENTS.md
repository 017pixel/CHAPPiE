# CHAPPiE Agent Guide

Framework-basierte Anweisungen für diesen Agenten: `.agents/skills/` (OpenCode) + `.claude/skills/` (Architektur, Testing, Backend, Frontend, Prompts, Config, Update).

## Entrypoints

| Zweck | Befehl |
|---|---|
| API starten | `python app.py` (uvicorn auf :8010) |
| Terminal-CLI (lokal) | `python chappie_brain_cli.py` |
| Terminal-CLI (remote) | `python chappie_brain_cli.py --remote` |
| Training-Daemon | `python -m Chappies_Trainingspartner.training_daemon` |
| Frontend dev | `cd frontend && npm run dev` (:5173) |
| Frontend build | `cd frontend && npm run build` (tsc + vite) |

## Services (systemd)

Startreihenfolge: `chappie-vllm.service` -> `chappie-web.service` -> `chappie-frontend.service`.
Training läuft separat via `chappie-training.service`.
Steering API (vLLM) läuft auf :8000, Web-API auf :8010, Frontend Preview auf :4173.

## Tests

**Kein pytest** – Tests laufen als standalone Scripte: `python tests/test_foo.py`.

- **Schnelle Logiktests** (CI-Pflicht): `test_forgetting_curve`, `test_life_simulation`, `test_debug_monitor_data`, `test_local_first_runtime`, `test_config_package_import`, `test_chat_ui_formatting`, `test_reasoning_layering`, `test_web_ui_consistency`, `test_root_config`, `test_settings_integrity`, `test_cli_*`, `test_forschung_harness` u.a.
- **Erweiterte Tests** (CI can fail): `test_vllm_response_handling`, `test_ollama_response_handling`, `test_chat_manager_persistence`, `test_short_term_memory`, `test_training_config_ui`, `test_api_contract`
- **Live/Integrationsnah** (nur bei Bedarf): `test_brain_agents`, `test_integration`, `test_query_extraction`
- **Manuelle Tests**: `tests/manual/`
- Syntax-Check: `python -m py_compile datei.py` (genutzte Liste in `.github/workflows/ci.yml`)

## Konfiguration & Secrets

- `CHAPPIE_CONFIG.json` und `config/secrets.py` sind **gitignored** – nach `CHAPPIE_CONFIG.example.json` und `config/secrets_example.py` richten
- API-Keys in `config/APIs/` sind ebenfalls gitignored
- Modell-Provider werden in `config/config.py` + `config/brain_config.py` verwaltet
- ALLE  configurations Sachen sollen im /config Ordner liegen!
- ALLE Promts, die benutzt werden sollen n promts.py liegen
- 

## Modell-Strategie

- Lokale Qwen3.5-Modelle zuerst, vLLM bevorzugt
- APIs (Groq) nur Fallback
- Steering (Layer Editing) aktiviert, Vektoren in L10–26

## Projekt-Struktur (kondensiert)

| Verzeichnis | Inhalt |
|---|---|
| **Root** | `app.py` (API), `chappie_brain_cli.py` (CLI), Config |
| `api/` | FastAPI (Routers, Schemas, Services) |
| `brain/` | LLM-Pipeline (Agenten, Global Workspace, Steering) |
| `config/` | Zentrale Config, Prompts, Emotionen |
| `frontend/` | React + Vite + Tailwind + Three.js |
| `memory/` | Gedächtnis (LTM, STM, Intent, Sleep, Context) |
| `life/` | Life-Simulation (Homeostasis, Goals, Social) |
| `Chappies_Trainingspartner/` | Autonomes Training (Daemon + Loop) |
| `deploy/` | Systemd-Services, Deploy-Scripts |
| `tests/` | Test-Suite (alle standalone) |
| `docs/` | Dokumentation |
| `scripts/` | Setup, Backup, Validierung; `scripts/archive/` für Legacy |

## Versionierung

- Kleine Änderungen: zweite Zahl erhöhen (`13.4` -> `13.5`)
- Große Updates: erste Zahl erhöhen (`13.4` -> `14.0`)
- Bei sichtbaren Versionsanzeigen (UI/Doku) mitpflegen
- `CHANGELOG.md` manuell in 5 Stichpunkten pro Version

## Bei Änderungen an der Modelllogik

Gemeinsam prüfen: `config/config.py`, `config/brain_config.py`, `config/prompts.py`, `config/secrets_example.py`, `brain/agents/*.py`, `brain/vllm_brain.py`, `brain/ollama_brain.py`, `README.md`, `docs/local-models.md`.

## Doku-Prüfung vor Push

Betroffene Pfade prüfen: `README.md`, `AGENTS.md`, `docs/*`, `tests/README.md`, ggf. Brückendateien in `Info Dateien/`. Auch wenn neue Ordner/Entrypoints, geänderte Provider-Priorität oder Brain/Memory/Life-Workflows angepasst wurden.

## Notes

- Kein Linter/Formatter konfiguriert – Code-Konsistenz manuell wahren
- `brain/steering_api_server.py` ist der vLLM-Steering-Service-Entrypoint (`-m brain.steering_api_server`)
- `training_daemon.py` ist der korrekte systemd-Entrypoint, **nicht** `training_loop.py`
- VAD-Mapping und 10 Emotionen in `config/emotions.py`; Änderungen erfordern Tests aus `tests/README.md` Abschnitt "Emotionsmodell"
- Alignment-Forschung in `forschung/` (86 Fragen, 14 Kategorien)
