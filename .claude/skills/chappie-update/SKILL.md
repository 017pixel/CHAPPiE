---
name: chappie-update
description: Führt ein vollständiges CHAPPiE-Update durch: git pull, Dienste neustarten, Tests, Health-Check, Reparatur bei Bedarf.
---

# CHAPPiE Update Workflow

## Voraussetzungen
- Systemd-Services: `chappie-web` (Backend), `chappie-frontend` (Frontend)
- Tests: `python3 tests/<test-datei>.py` (Einzeltests, kein pytest)
- Remote-IP: `100.105.94.71`
- Sudo-Passwort: erfragen, nicht hartcoden

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

### 3. Frontend bauen
```bash
cd frontend && npm run build
```
**Wichtig**: Der `dist/`-Ordner wird nicht via Git versioniert. Nach jedem Pull MUSS das Frontend neu gebaut werden, sonst sind UI-Änderungen nicht sichtbar.

### 4. Backend neustarten
```bash
sudo systemctl restart chappie-web
```

### 5. Frontend neustarten
```bash
sudo systemctl restart chappie-frontend
```

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
python3 tests/test_integration.py
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
Prüfen, ob beide Dienste erreichbar sind:
- Frontend: `curl -sf http://100.105.94.71:4173/` oder `curl -sf http://localhost:4173/`
- Backend: `curl -sf http://100.105.94.71:8010/` oder `curl -sf http://localhost:8010/`

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
