# CHAPPiE Agent Guide

Diese Datei ist die **kanonische Arbeitsanweisung für KI-Agents**, die in diesem Repository Änderungen vornehmen.

## Pflicht vor jeder Änderung

1. `README.md` lesen
2. prüfen, welche Detailseite unter `docs/` die Aufgabe erklärt
3. betroffene Quellpfade bestätigen
4. nach jeder strukturellen oder funktionalen Änderung die Doku-Relevanz prüfen

## Pflicht vor jedem Push / Merge Request

Vor jedem GitHub-Push-Update muss geprüft werden, ob eine oder mehrere dieser Dateien aktualisiert werden müssen:

- `README.md`
- `agent.md`
- `docs/architecture.md`
- `docs/workflows.md`
- `docs/local-models.md`
- `docs/project-map.md`
- `docs/testing.md`
- `docs/deployment.md`
- `tests/README.md`
- betroffene Legacy-Brücken in `Info Dateien/`

Wenn neue Funktionen, neue Workflows, neue Ordner oder neue Modellpfade hinzugekommen sind, müssen die passenden Erklärdateien mitgezogen werden.

## Dokumentationskarte für Agents

| Frage | Datei |
|---|---|
| Worum geht es im Projekt? | `README.md` |
| Wie ist das Gehirnmodell gemeint? | `docs/architecture.md` |
| Wie laufen Anfrage, Schlafphase, Training und UI ab? | `docs/workflows.md` |
| Welche Modelle sind bevorzugt? | `docs/local-models.md` |
| Wo liegt was im Projekt? | `docs/project-map.md` |
| Welche Tests sind sicher oder teuer? | `docs/testing.md`, `tests/README.md` |
| Wie laufen Services und Deployment? | `docs/deployment.md` |

## Modellstrategie

- **lokale Qwen-3.5-Modelle zuerst**
- **vLLM bevorzugt**, Ollama als leichtere lokale Alternative
- **NVIDIA / Groq / Cerebras nur Fallback**, wenn lokal nicht ausreichend möglich

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

## Unverhandelbare Infrastruktur-Regeln

### systemd / Training

- `chappie-training.service` muss `Chappies_Trainingspartner.training_daemon` starten
- **niemals** `training_loop.py` direkt als systemd-Entry-Point verwenden
- `Restart=always` beibehalten
- absolute Pfade in Service-Dateien verwenden

## Arbeitsstil für Agents

- kleine, präzise Änderungen bevorzugen
- erst Quellpfade prüfen, dann editieren
- Links in Doku immer pfadgenau setzen
- Brain-Metapher als **technische Analogie**, nicht als biologische 1:1-Behauptung formulieren
- bei Architekturänderungen Diagramme mitpflegen

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

## Legacy-Hinweis

Ältere Dateien in `Info Dateien/` sind nur noch Brücken. Die Hauptquelle für aktuelle Erklärungen ist `README.md` + `docs/` + `agent.md`.

