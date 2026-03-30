## CHAPPiE Übergabe / TODO für den nächsten Agenten

### Ziel
Lokales `vLLM`/Steering endgültig auf `Qwen/Qwen3.5-9B` umstellen, live testen und danach final committen/pushen, falls dieser Commit hier nicht schon alles enthält.

### Bereits erledigt
- Defaults und aktive lokale Konfiguration auf `Qwen/Qwen3.5-9B` umgestellt:
  - `config/config.py`
  - `config/secrets_example.py`
  - `brain/steering_api_server.py`
  - `chappie-vllm.service`
- Lokale aktive Overrides ebenfalls umgestellt:
  - `config/secrets.py`
  - `config/addSecrets.py`
- UI-Modellauswahl auf `Qwen 3.5 9B/27B` priorisiert:
  - `frontend/src/pages/settings-page.tsx`
- CLI verbessert:
  - `chappie_brain_cli.py` nutzt jetzt den echten Backend-/Zwei-Schritt-/Systemprompt-Pfad
  - neue Kommandos/Metriken: `/runtime`, `/steering`, `/last`, `/emotion`, `/resetemotions`
- Backend für CLI/Tests geöffnet:
  - `web_infrastructure/backend_wrapper.py` hat jetzt `create_chappie_backend()` zusätzlich zu `init_chappie()`
- Steering-Loader ergänzt:
  - `brain/steering_backend.py` enthält Loader-Kwargs für `Qwen 3.5`
- Tests/Doku aktualisiert:
  - `tests/test_steering_backend.py`
  - `README.md`
  - `docs/local-models.md`
  - `docs/vLLM-Setup.md`

### Getestet und aktuell grün
- `./venv/bin/python3 -m py_compile brain/steering_backend.py chappie_brain_cli.py web_infrastructure/backend_wrapper.py`
- `./venv/bin/python3 tests/test_steering_backend.py`
- `./venv/bin/python3 tests/test_local_first_runtime.py`
- `./venv/bin/python3 tests/test_vllm_response_handling.py`
- früher in der Session auch grün:
  - `tests/test_reasoning_layering.py`
  - `tests/test_web_ui_consistency.py`
  - `tests/test_debug_monitor_data.py`
  - `tests/test_brain_pipeline_steering_integration.py`

### Aktueller Live-Blocker
`chappie-vllm.service` startet jetzt korrekt mit `Qwen/Qwen3.5-9B`, crasht aber beim Modell-Laden.

Logfehler:
- `ValueError: ... model type 'qwen3_5' ... Transformers does not recognize this architecture`

Das heißt:
- CHAPPiE-Code ist schon auf `Qwen 3.5` umgestellt
- der verbleibende Blocker ist die installierte `transformers`-Version im `venv`

### Nächster Schritt (so behandeln, als ob der Nutzer jetzt "Ja" gesagt hätte)
Bitte direkt ausführen:
- `./venv/bin/pip install --upgrade transformers`

Falls das nicht reicht:
- `./venv/bin/pip install git+https://github.com/huggingface/transformers.git`

Danach:
- `sudo systemctl daemon-reload`
- `sudo systemctl restart chappie-vllm.service chappie-web.service`
- `systemctl --no-pager --full status chappie-vllm.service chappie-web.service`
- `journalctl -u chappie-vllm.service -n 80 --no-pager`
- `curl -sS http://127.0.0.1:8000/health`

### Danach live verifizieren
1. Direkt gegen den lokalen Endpoint testen:
   - Chat-Completion gegen `http://127.0.0.1:8000/v1`
   - Modell: `Qwen/Qwen3.5-9B`
2. CHAPPiE-CLI testen:
   - `./venv/bin/python3 chappie_brain_cli.py`
   - `/runtime`
   - `/steering`
   - `/emotion happiness 90`
   - eine freundliche Frage schicken
   - `/emotion frustration 85`
   - dieselbe oder ähnliche Frage schicken
   - `/last`
   - prüfen, ob sich dominante Vektoren, Stil und Antwortcharakter sichtbar unterscheiden
3. Frontend und API grob prüfen:
   - API: `http://localhost:8010/health`
   - Frontend: `http://localhost:4173`
   - sicherstellen, dass Antworten wieder kommen

### Erwartetes Zielbild
- `chappie-vllm.service` läuft stabil mit `Qwen/Qwen3.5-9B`
- Systemprompts bleiben aktiv
- Zwei-Schritt-Logik bleibt aktiv
- Steering greift weiter
- CLI zeigt Steering-/Runtime-Metriken nachvollziehbar an

### Wichtige Hinweise
- In `/etc/systemd/system/` mussten die Repo-Service-Dateien benutzt werden; beim Weiterarbeiten immer prüfen, dass die installierten Units aktuell sind.
- API-Service-Name ist `chappie-web.service`.
- In der letzten Live-Prüfung lief `chappie-web.service`, aber `chappie-vllm.service` restartete wegen des `transformers`-Problems.

### Nicht versehentlich mitcommitten
Diese Änderungen lagen lokal herum und stammen nicht sicher aus dieser Aufgabe:
- `data/short_term_memory.json`
- `data/soul.md`
- `autonomy.sh`

### Wenn am Ende alles grün ist
Dann noch:
- ggf. README/Doku fein nachziehen, falls sich durch das echte Upgrade noch etwas ändert
- committen
- auf `origin/main` pushen
