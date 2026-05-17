---
name: chappie-update
description: Führt ein vollständiges CHAPPiE-Update durch: git pull, Dienste neustarten, Tests, Health-Check, Reparatur bei Bedarf.
---

# CHAPPiE Update Workflow

Universeller Update-Workflow für CHAPPiE. Dieser Skill beschreibt **exakt** was wann zu tun ist — und was **nicht** zu tun ist.

## Voraussetzungen
- Systemd-Services: `chappie-vllm` (Steering-Server), `chappie-web` (Backend), `chappie-frontend` (Frontend), `chappie-training` (Training-Daemon)
- Tests: `python3 tests/<test-datei>.py` (Einzeltests, kein pytest)
- Remote-IP: `100.105.94.71`
- Sudo-Passwort: erfragen, nicht hartcodieren

## WICHTIG: Was NICHT zu tun ist

- **Training-Daemon NICHT neustarten**, es sei denn der User fragt explizit danach. `chappie-training` ist standardmäßig **deaktiviert** und bleibt deaktiviert nach Updates.
- **Keine** Config-Werte in `CHAPPIE_CONFIG.json` ändern, es sei denn der User verlangt es.
- **Keine** manuellen pip-installs außerhalb von `requirements.txt`.
- Vorbestehende Fehler nicht beheben (separates Issue).
- Sudo-Passwort niemals hartcoden.

## Bevor der Agent startet: IMMER zuerst fragen

Der Agent MUSS **vor jedem Update-Schritt** zwei Fragen mit dem JSON-Question-Tool stellen:

### Frage 1: Test-Modus
```
Wähle den Test-Modus:
- "quick": Nur lokale Fast-Tests (keine API-Calls nötig, ~15 Tests, dauert ~30s)
- "full": Alle Tests inklusive Integration/Live-API-Tests (dauert mehrere Minuten)
```

### Frage 2: Requirements
```
Sollen die Python-Requirements aus requirements.txt installiert werden?
- "yes": pip install -r requirements.txt ausführen
- "no": Überspringen
```

## Update-Flow (exakt in dieser Reihenfolge)

### 1. Git Pull
`git pull` im CHAPPiE-Projektordner ausführen.

### 2. Dependencies aktualisieren
- **Python**: Wenn der User in Frage 2 "yes" gewählt hat: venv aktivieren (falls vorhanden), dann `pip install -r requirements.txt`
- **Frontend**: `cd frontend && npm install`

### 3. Service-Dateien prüfen und aktualisieren
Wenn `.service`-Dateien geändert wurden (z.B. `chappie-vllm.service`, `chappie-web.service`):
```bash
# Geänderte Service-Dateien nach /etc/systemd/system/ kopieren
sudo cp deploy/chappie-vllm.service /etc/systemd/system/
sudo cp deploy/chappie-web.service /etc/systemd/system/
sudo cp deploy/chappie-frontend.service /etc/systemd/system/
# Training-Service NUR kopieren, NICHT aktivieren
sudo cp deploy/chappie-training.service /etc/systemd/system/
# Danach daemon-reload, damit systemd die Änderungen erkennt
sudo systemctl daemon-reload
```
**Wichtig**: `systemctl daemon-reload` ist PFLICHT nach jeder .service-Änderung, sonst werden die neuen Environment-Variablen oder ExecStart-Parameter nicht übernommen.

### 4. Frontend bauen
```bash
cd frontend && npm run build
```
**Wichtig**: Der `dist/`-Ordner wird nicht via Git versioniert. Nach jedem Pull MUSS das Frontend neu gebaut werden, sonst sind UI-Änderungen nicht sichtbar.

### 5. Dienste neustarten (Reihenfolge ist wichtig!)
Steering-Server (vLLM) MUSS zuerst starten, da chappie-web davon abhängt:
```bash
# 1. Steering-Server (lädt GPU-Modell, dauert ~30-60s mit Quantisierung)
sudo systemctl restart chappie-vllm
# Kurz warten, bis Modell geladen ist
sleep 10
# Health-Check: Steering-Server bereit?
curl -sf http://localhost:8000/health && echo " vLLM OK" || echo " vLLM noch nicht bereit"

# 2. Backend (abhängt von vLLM)
sudo systemctl restart chappie-web

# 3. Frontend
sudo systemctl restart chappie-frontend

# 4. Training: NICHT neustarten! Standardmäßig deaktiviert.
# Nur neustarten wenn der User explizit danach fragt:
# sudo systemctl restart chappie-training
```
Falls der vLLM-Health-Check fehlschlägt: weitere 20s warten und erneut prüfen. Das Modell laden kann auf der T4 mit NF4-Quantisierung 30-60s dauern.

### 6. Tests durchführen (je nach gewähltem Modus)

#### Quick Tests (`quick`-Modus)
Schnelle, lokale Tests — keine externen APIs nötig:
```bash
python3 tests/test_forgetting_curve.py
python3 tests/test_life_simulation.py
python3 tests/test_debug_monitor_data.py
python3 tests/test_local_first_runtime.py
python3 tests/test_ollama_response_handling.py
python3 tests/test_chat_manager_persistence.py
python3 tests/test_config_package_import.py
python3 tests/test_vllm_response_handling.py
python3 tests/test_web_ui_consistency.py
python3 tests/test_reasoning_layering.py
python3 tests/test_api_contract.py
python3 tests/test_chat_ui_formatting.py
python3 tests/test_training_config_ui.py
python3 tests/test_short_term_memory_v2.py
```

Plus Syntax-Prüfung:
```bash
python3 -m py_compile web_infrastructure/backend_wrapper.py
```

#### Full Tests (`full`-Modus)
Alle Tests aus Quick + zusätzliche Integration/Live-Tests:
```bash
# Alle Quick-Tests (siehe oben)
# Plus:
python3 tests/test_brain_agents.py
python3 tests/test_brain_pipeline_steering_integration.py
python3 tests/test_context_files_manager.py
python3 tests/test_emotion_transition_rules.py
python3 tests/test_integration.py
python3 tests/test_memory_query_extraction_german.py
python3 tests/test_query_extraction.py
python3 tests/test_repetition_penalty.py
python3 tests/test_steering_backend.py
python3 tests/test_training_daemon_lifecycle.py
python3 tests/test_sleep_phase_context_updates.py
```

### 7. Prüfen, ob etwas kaputt ist
- Analyse der Testergebnisse aus Schritt 6
- Nur wenn ein Test fehlschlägt UND der Fehler durch das Update verursacht wurde (nicht vorher schon bestanden): reparieren
- **Nicht** eigenmächtig Dinge ändern, die vorher schon kaputt waren

### 8. Health-Check
Prüfen, ob alle Dienste erreichbar sind:
- Steering-Server: `curl -sf http://localhost:8000/health` (muss `{"status":"ok",...}` liefern)
- Backend: `curl -sf http://100.105.94.71:8010/` oder `curl -sf http://localhost:8010/`
- Frontend: `curl -sf http://100.105.94.71:4173/` oder `curl -sf http://localhost:4173/`
- Training: **Nicht prüfen** (standardmäßig deaktiviert)

Falls der Steering-Server nicht antwortet: Logs checken mit `journalctl -u chappie-vllm --no-pager -n 50` und prüfen ob das Modell korrekt geladen wurde (sollte "NF4 4-bit Quantisierung aktiviert" oder "Steering-Modell geladen" zeigen).

### 9. Bestätigung
Dem User mitteilen:
- "Update erfolgreich: CHAPPiE ist unter http://100.105.94.71:4173/ erreichbar."
- Falls Tests fehlgeschlagen sind: erwähnen, ob/was repariert wurde
- Falls Health-Check fehlschlug: Alarm schlagen, nicht ignorieren

## Wichtige Regeln
- Nur reparieren, was durch das Update kaputt gegangen ist
- Vorbestehende Fehler nicht beheben (das ist ein separates Issue)
- Bei unklaren Fehlern: den User um Entscheidung bitten
- **Niemals** Sudo-Passwort hartcoden — vor jedem sudo-Befehl erfragen
- Frontend NACH Pull und Dependencies bauen, VOR Service-Neustart
- **Steering-Server (chappie-vllm) IMMER vor chappie-web neustarten** — Web hängt von vLLM ab
- Nach .service-Datei-Änderungen: IMMER `systemctl daemon-reload` ausführen
- Falls `CHAPPIE_STEERING_QUANTIZE` geändert wurde: vLLM-Service MUSS neugestartet werden (Env-Variablen in systemd werden nur beim Start gelesen)
- Falls `CHAPPIE_STEERING_CONTEXT_LENGTH` geändert wurde: ebenfalls vLLM neustarten
- **Training-Daemon (chappie-training) standardmäßig NICHT neustarten** — ist deaktiviert und bleibt deaktiviert nach Updates