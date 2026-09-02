# Deployment

## Dienste

| Dienst | Entrypoint | Port |
|---|---|---|
| Steering/vLLM | `python3 -m brain.steering_api_server` | 8000 |
| Web-API | `python3 app.py` | 8010 |
| Frontend Preview | `npm run preview` | 4173 |
| Training | `python3 -m Chappies_Trainingspartner.training_daemon` | keiner |

Startreihenfolge: Steering, Web-API, Frontend. Training ist unabhängig.

## systemd

Die Dateien unter `deploy/` sind konkrete Zielserver-Beispiele. Feste Pfade wie `/home/bbecker/CHAPPiE` sind dort absichtlich deploymentspezifisch und keine portable Projektvorgabe. Für andere Installationen müssen `User`, `WorkingDirectory`, Python-Pfad, Node-Pfad und Environment angepasst werden.

Vor Übernahme prüfen:

- Zielbenutzer und Dateirechte
- absoluten Projekt- und Venv-Pfad
- GPU-/CUDA-Umgebung
- `CHAPPIE_CONFIG.json` und Secret-Dateien
- writable `data/` und `data/training_runtime/`
- Ports 8000, 8010 und 4173
- Restart- und Timeout-Regeln

Service-Dateien wurden beim Repository-Cleanup nicht automatisch auf den aktuellen Workspace-Pfad umgeschrieben und keine laufenden Dienste wurden neu gestartet.

## Manuell starten

```bash
source venv/bin/activate
python3 -m brain.steering_api_server
python3 app.py
cd frontend && npm run preview
```

## Training

Die Trainingskonfiguration liegt neu unter `config/training_config.json`. Eine vorhandene `training_config.json` im Root bleibt lesbar. Daemon-State und Logs liegen unter `data/training_runtime/`; die PID-Datei bleibt aus Kompatibilitätsgründen im Projekt-Root.

## Sicherheit

- Keine Keys in systemd-Dateien oder Git schreiben.
- Lokale Services möglichst nur an Loopback binden.
- CORS, Authentifizierung und Reverse-Proxy-Regeln vor öffentlicher Exposition separat härten.
- Memory-, Session- und Forschungsdaten nicht öffentlich ausliefern.
- Debuglogs vor Weitergabe auf Prompts, Keys und personenbezogene Inhalte prüfen.

## Prüfung

```bash
python3 scripts/validate_system.py
python3 tests/test_api_contract.py
python3 tests/test_training_daemon_lifecycle.py
cd frontend && npm run build
```

Live-Checks erfolgen nur in einer dafür freigegebenen Umgebung. Nutzer-Previews und laufende Sessions werden für Repositorytests nicht verändert.
