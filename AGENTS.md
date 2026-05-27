# CHAPPiE Agent Guide

Kanonische Arbeitsanweisung für KI-Agents, die in diesem Repository Änderungen vornehmen.

## Pflicht vor jeder Änderung

1. `README.md` lesen
2. prüfen, welche Detailseite unter `docs/` die Aufgabe erklärt
3. betroffene Quellpfade bestätigen
4. nach jeder strukturellen oder funktionalen Änderung die Doku-Relevanz prüfen

## Pflicht vor jedem Push / Merge Request

Vor jedem GitHub-Push-Update muss geprüft werden, ob eine oder mehrere dieser Dateien aktualisiert werden müssen:

- `README.md`
- `AGENTS.md`
- `docs/architecture.md`
- `docs/workflows.md`
- `docs/local-models.md`
- `docs/project-map.md`
- `docs/testing.md`
- `docs/deployment.md`
- `tests/README.md`
- betroffene Brückendateien in `Info Dateien/`

## Unverhandelbare Regeln

### 1. Training-Service

- korrekt: `ExecStart=... -m Chappies_Trainingspartner.training_daemon`
- falsch: `ExecStart=... -m Chappies_Trainingspartner.training_loop`
- `training_loop.py` ist kein systemd-Entry-Point

### 2. Service-Zuverlässigkeit

- `Restart=always` beibehalten
- absolute Pfade in `ExecStart` und `WorkingDirectory`

### 3. Doku-Prüfung vor Pushes

Vor jedem GitHub-Push-Update muss geprüft werden, ob mindestens eine dieser Dateien angepasst werden muss:

- `README.md`
- `AGENTS.md`
- `docs/*`
- `tests/README.md`
- betroffene Brückendateien in `Info Dateien/`

### 4. Modellstrategie

- lokale **Qwen-3.5-Modelle zuerst**
- `vLLM` bevorzugt
- APIs nur Fallback, wenn lokal nicht praktikabel

### 5. Lange Downloads / Modellstarts

- lange Modell-Downloads, Cache-Warmups oder aehnliche Jobs nicht unnoetig blockierend im Vordergrund laufen lassen
- stattdessen `nohup`-artig als Hintergrundprozess oder ueber den bestehenden Service starten, Logs beobachten und waehrenddessen an unabhaengigen Schritten weiterarbeiten
- erst fuer den eigentlichen Health-/Live-Test wieder gezielt auf Abschluss und Erreichbarkeit warten

### 6. Projektstruktur

- **Root** enthält nur Einstiegspunkte: `app.py` (API), `chappie_brain_cli.py` (Terminal), Projekt-Config (`requirements.txt`, `CHAPPIE_CONFIG.example.json`)
- **`api/`** — FastAPI Backend (Routers, Schemas, Services)
- **`brain/`** — LLM-Pipeline (vLLM, Groq, Ollama, Steering, Global Workspace)
- **`config/`** — Zentrale Konfiguration (`config.py`, `prompts.py`, `brain_config.py`)
- **`data/`** — Laufzeitdaten (ChromaDB, Steering-Vektoren, Personality-Files)
- **`deploy/`** — Systemd-Services und Deployment-Scripts
- **`frontend/`** — React + Vite + Tailwind Frontend
- **`life/`** — Life-Simulation (Homeostasis, Goals, Planning, Social Arc)
- **`memory/`** — Gedächtnis-Subsystem (LTM, STM, Intent, Sleep, Context)
- **`scripts/`** — Setup, Cleanup, Backup, Validierung; `scripts/archive/` für Legacy-Dateien
- **`tests/`** — Alle Test-Dateien
- **`web_infrastructure/`** — Backend-Wrapper (`CHAPPiEBackend`)
- **`Chappies_Trainingspartner/`** — Autonomes Training (Daemon + Loop)
- **`docs/`** — Alle Dokumentation
- **CLI** ist `chappie_brain_cli.py` (nicht `main.py` — das ist legacy in `scripts/archive/`)

### 7. CLI-Einstiegspunkte

| Zweck | Datei |
|---|---|
| App-API starten | `app.py` |
| Terminal-CLI (lokal) | `python chappie_brain_cli.py` |
| Terminal-CLI (remote) | `python chappie_brain_cli.py --remote` |
| Training-Daemon | `python -m Chappies_Trainingspartner.training_daemon` |

## Dokumentationskarte

| Frage | Datei |
|---|---|
| Worum geht es im Projekt? | `README.md` |
| Wie ist das Gehirnmodell gemeint? | `docs/architecture.md` |
| Wie laufen Anfrage, Schlafphase, Training und UI ab? | `docs/workflows.md` |
| Welche Modelle sind bevorzugt? | `docs/local-models.md`, `docs/vLLM-Setup.md` |
| Wo liegt was im Projekt? | `docs/project-map.md` |
| Welche Tests sind sicher oder teuer? | `docs/testing.md`, `tests/README.md` |
| Wie laufen Services und Deployment? | `docs/deployment.md` |

## Versionsregel

- bei **kleinen Änderungen** wird die **zweite Zahl** erhöht (`13.4` → `13.5`)
- bei **großen Updates** wird die **erste Zahl** erhöht (`13.4` → `14.0`)
- wenn sichtbare Versionsanzeigen in UI oder Doku betroffen sind, müssen diese mitgepflegt werden

Bei Änderungen an der Modelllogik immer diese Pfade gemeinsam prüfen:

- `config/config.py`
- `config/brain_config.py`
- `config/secrets_example.py`
- `brain/agents/*.py`
- `README.md` + `docs/local-models.md`

## Arbeitsstil für Agents

- kleine, präzise Änderungen bevorzugen
- erst Quellpfade prüfen, dann editieren
- Links in Doku immer pfadgenau setzen
- Brain-Metapher als **technische Analogie**, nicht als biologische 1:1-Behauptung formulieren
- bei Architekturänderungen Diagramme mitpflegen
- bei Web-Änderungen `app.py`, `api/` und `frontend/` gemeinsam mitdenken

## Doku-Änderung ist Pflicht, wenn ...

- neue Ordner oder Einstiegspunkte entstehen
- Commands hinzukommen oder verschwinden
- Modellstrategie oder Provider-Priorität geändert wird
- Brain-/Memory-/Life-Workflows angepasst werden
- Services, Deploy-Skripte oder Startanleitungen geändert werden
- Tests verschoben oder neu kategorisiert werden

## Empfohlene Validierung nach Änderungen

1. kleinsten passenden Test wählen
2. keine teuren Live-Tests ohne Bedarf
3. bei Doku-/Konfig-Änderungen mindestens Struktur-/Import-Check durchführen
4. bei Service-/Training-Änderungen Startpfade explizit prüfen