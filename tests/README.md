# Testübersicht

## Ziel dieser Datei

Diese Übersicht erklärt, welche Tests schnell und sicher sind und welche Tests eher live, manuell oder providerabhängig laufen.

## Aktuelle Kategorien

### 1. Schnelle lokale Logiktests

- `tests/test_forgetting_curve.py`
- `tests/test_life_simulation.py`
- `tests/test_local_first_runtime.py`
- `tests/test_debug_monitor_data.py`
- `tests/test_ollama_response_handling.py`
- `tests/test_chat_manager_persistence.py`
- `tests/test_config_package_import.py`
- `tests/test_vllm_response_handling.py`
- `tests/test_reasoning_layering.py`
- `tests/test_web_ui_consistency.py`
- `tests/test_quick.py`

### 2. Live-/Integrationsnahe Tests

Diese Tests können echte Modelle, Provider oder Kontextdateien berühren:

- `tests/test_brain_agents.py`
- `tests/test_integration.py`
- `tests/test_nvidia_api.py`
- `tests/test_query_extraction.py`

### 3. Manuelle / operatorgeführte Tests

- `tests/manual/test_chat_live.py`
- `tests/manual/test_chappie.py`
- `tests/manual/test_compatibility.py`

## Empfehlung für den Alltag

1. zuerst lokale Logiktests
2. bei Modell-/Emotionsänderungen besonders `tests/test_local_first_runtime.py` und `tests/test_debug_monitor_data.py`
3. dann Kompatibilitätscheck
4. auf GitHub die automatische `CI`-Pipeline prüfen
5. interaktive Tests nur bewusst und mit Kontextwissen
6. Live-/API-Tests nur bei Bedarf

## Warum diese Trennung wichtig ist

CHAPPiE arbeitet mit:

- Modell-Providern
- lokalen Services
- Gedächtnisdateien in `data/`
- life-state- und training-state-Dateien

Deshalb sind nicht alle Tests gleich „billig“ oder gleich sicher.

## Für zukünftige Aufräumarbeiten

Wenn Testdateien verschoben oder neu gruppiert werden, müssen mindestens diese Dateien geprüft werden:

- `README.md`
- `docs/testing.md`
- `tests/README.md`
- ggf. CI-/Skript- oder Service-Dateien
