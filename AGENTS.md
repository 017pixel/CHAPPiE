# CHAPPiE Agent Entry Point

Die **kanonische Agent-Datei** dieses Repositorys ist [`agent.md`](agent.md).

Wenn du als KI-Agent in diesem Projekt arbeitest, lies **immer zuerst**:

1. [`agent.md`](agent.md)
2. [`README.md`](README.md)
3. je nach Aufgabe die passende Detailseite unter [`docs/`](docs)

## Unverhandelbare Regeln

### 1. Training-Service

- korrekt: `ExecStart=... -m Chappies_Trainingspartner.training_daemon`
- falsch: `ExecStart=... -m Chappies_Trainingspartner.training_loop`

`training_loop.py` ist kein systemd-Entry-Point.

### 2. Service-Zuverlässigkeit

- `Restart=always` beibehalten
- absolute Pfade in `ExecStart` und `WorkingDirectory`

### 3. Doku-Prüfung vor Pushes

Vor jedem GitHub-Push-Update muss geprüft werden, ob mindestens eine dieser Dateien angepasst werden muss:

- `README.md`
- `agent.md`
- `docs/*`
- `tests/README.md`
- betroffene Brückendateien in `Info Dateien/`

### 4. Modellstrategie

- lokale **Qwen-3.5-Modelle zuerst**
- `vLLM` bevorzugt
- APIs nur Fallback, wenn lokal nicht praktikabel

## Dokumentationskarte

- Projektüberblick: [`README.md`](README.md)
- Gehirn-Metapher: [`docs/architecture.md`](docs/architecture.md)
- Workflows: [`docs/workflows.md`](docs/workflows.md)
- Modellstrategie: [`docs/local-models.md`](docs/local-models.md)
- Projektstruktur: [`docs/project-map.md`](docs/project-map.md)
- Tests: [`docs/testing.md`](docs/testing.md), [`tests/README.md`](tests/README.md)
- Deployment: [`docs/deployment.md`](docs/deployment.md)

## Warum diese Datei kurz bleibt

`AGENTS.md` soll als automatischer Einstieg funktionieren. Die ausführliche Spezifikation, Push-Regeln und Dateimatrix stehen in [`agent.md`](agent.md).

