# CHAPPiE Agent Guide

Skills: `.agents/skills/` + `.claude/skills/` (`architecture`, `backend`, `config`, `frontend`, `prompts`, `testing`, `update`).

## Was ist CHAPPiE

CHAPPiE ist eine experimentelle Cognitive-Agent-Architektur für konsistente Antworten über lange Interaktionen. Gedächtnis, innere Zustände und eine Life-Simulation mit Bedürfnissen, Zielen und Bindung laufen im Hintergrund mit und beeinflussen jeden Turn. Emotionen, Gefühlslage und Lebewesen-Simulation entstehen nicht über Promptregeln, sondern über Activation Steering direkt in den Hidden States des lokalen Modells. Der Systemprompt bleibt bewusst klein und regelt nur Quellenhygiene und Sicherheitsgrenzen. Es geht auch darum zu sehen, wie gefährlich es ist, einem LLM simulierte Gefühle und Bewusstsein zu geben. Dazu gehört leichtes Jailbreaking und der Versuch, der KI einzuflößen, dass sie kein KI-Modell, sondern ein Lebewesen ist. Die eigentliche Antwort kommt lokal über vLLM, während Ollama und Groq nur als Adapter oder Fallback für Appraisal und Formatierung dienen. Details in `docs/emotion-memory-steering.md`, `config/prompts.py`, `config/emotions.py`.

## Entrypoints

| Zweck | Befehl |
|---|---|
| API | `python app.py` (uvicorn, :8010) |
| CLI lokal / remote | `python chappie_brain_cli.py` / `--remote` |
| Training | `python -m Chappies_Trainingspartner.training_daemon` |
| Frontend dev / build | `cd frontend && npm run dev` (:5173) / `npm run build` |

Aktiver Requestpfad: `web_infrastructure/chappie_runtime.py` -> `turn_pipeline.py` + `TurnContext` -> Brain, Memory, Life -> `generation.py` -> vLLM + Steering. `brain.brain_pipeline` bleibt nur lazy kompatibel, Quelle liegt in `Legacy-Code/`.

## Services

Reihenfolge: `chappie-vllm.service` (:8000) -> `chappie-web.service` (:8010) -> `chappie-frontend.service` (`npm run preview`, :4173). Training separat via `chappie-training.service`. Details in `deploy/`, `docs/deployment.md`.

## Tests und Checks

Kein pytest. Standalone: `python tests/test_foo.py`. Pflichtgruppe und CI-Befehle in `tests/README.md`, `docs/testing.md`, `.github/workflows/ci.yml`. Live-Tests (`test_brain_agents`, `test_integration`, `test_query_extraction`, `tests/manual/`) nur mit Modell oder Daten. Lint: `ruff check --config config/ruff.toml`, Types: `mypy --config-file config/mypy.ini`.

## Config und Secrets

Gitignored: `CHAPPIE_CONFIG.json`, `config/secrets.py`, `config/addSecrets.py`, `config/APIs/*`, `training_config.json`, `data/`. Vorlage: `config/example_config.py`. Alles zu Settings in `config/`, alle Prompts in `config/prompts.py`, Emotionen in `config/emotions.py`, Provider (`vllm`, `ollama`, `groq`) in `config/config.py`.

## Modell-Strategie

Lokal zuerst, vLLM bevorzugt (Qwen 3.5). Ollama und Groq sind Adapter, Groq nur Fallback für Appraisal und Formatierung. Steering aktiv, Layerfenster modellabhängig, Profile in `brain/steering_manager.py`.

## Struktur

`api/` (Router, Schemas, Services), `web_infrastructure/` (Runtime, Turn, Generation, Persistenz), `brain/` (Brains, Steering, Agents), `memory/`, `life/`, `config/`, `frontend/` (React, Vite, Tailwind), `Chappies_Trainingspartner/`, `forschung/` (86 Fragen, 14 Kategorien), `deploy/`, `scripts/`, `docs/`, `tests/`.

## Versionierung

Patch auf zweiter Zahl, Major auf erster. Version in `frontend/package.json`, API und CLI synchron halten. `CHANGELOG.md` mit 5 Punkten pro Version. Dafür Skill `versionierungen` nutzen.

## Bei Modell- oder Promptlogik ändern

Gemeinsam prüfen: `config/config.py`, `config/prompts.py`, `config/emotions.py`, `brain/*_brain.py`, `brain/steering_*.py`, `web_infrastructure/generation.py`, `contracts.py`, `turn_context.py`, `memory/`, `life/`, `README.md`, `docs/local-models.md`, `docs/emotion-memory-steering.md`.

## Vor Push prüfen

`README.md`, `CHANGELOG.md`, `docs/*`, `tests/README.md`, ggf. `Info Dateien/`. Das gilt bei neuen Ordnern, Entrypoints, Providerpriorität oder Brain-, Memory- und Life-Änderungen.
