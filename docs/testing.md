# Testing

## Testphilosophie

CHAPPiE enthält sowohl **sichere lokale Prüfungen** als auch **live-/manuelle Tests**. Diese sollten bewusst getrennt betrachtet werden.

## Testtypen

| Typ | Ziel | Beispiele |
|---|---|---|
| Schnelle lokale Checks | Kernlogik ohne riskante Seiteneffekte prüfen | `tests/test_forgetting_curve.py`, `tests/test_life_simulation.py` |
| Struktur-/Kompatibilitätschecks | Module, Services und Dateien validieren | `tests/manual/test_compatibility.py` |
| Live-/Provider-Tests | Verhalten mit echten Modellen/APIs prüfen | `tests/test_brain_agents.py`, `tests/test_nvidia_api.py`, `tests/test_integration.py` |
| Interaktive Smoke-Tests | UI oder Chat manuell antesten | `tests/manual/test_chat_live.py`, `tests/manual/test_chappie.py` |

## GitHub Actions / CI

Bei Pushes und Pull Requests auf `main`/`master` läuft der Workflow `.github/workflows/ci.yml`.

Er führt die sicheren lokalen Prüfungen automatisiert aus:

- schnelle Python-Tests aus `tests/`
- den Kompatibilitätscheck
- `py_compile` für die zentralen App-/UI-Dateien
- einen headless Streamlit-Smoke-Test mit HTTP-Check

## Wichtige Regel

Nicht jeder Test ist für jeden Commit geeignet. Vor allem Live- und API-Tests können:

- externe Kosten verursachen
- auf lokale Services angewiesen sein
- Kontextdateien verändern
- langsamer oder fragiler sein

## Empfohlene Reihenfolge

1. **kleinster lokaler Test**
2. **passender Dateitest**
3. **Kompatibilitätscheck**
4. **erst dann Live-/API-Test**, wenn die Änderung das wirklich benötigt

## Sinnvolle schnelle Checks

- `python tests/test_forgetting_curve.py`
- `python tests/test_life_simulation.py`
- `python tests/test_local_first_runtime.py`
- `python tests/test_steering_backend.py`
- `python tests/test_brain_pipeline_steering_integration.py`
- `python tests/test_debug_monitor_data.py`
- `python tests/test_ollama_response_handling.py`
- `python tests/test_chat_manager_persistence.py`
- `python tests/test_config_package_import.py`
- `python tests/test_vllm_response_handling.py`
- `python tests/test_reasoning_layering.py`
- `python tests/test_web_ui_consistency.py`
- `python -m py_compile app.py web_infrastructure/backend_wrapper.py web_infrastructure/command_handler.py`
- `python tests/manual/test_compatibility.py`
- `python validate_system.py`

Fuer UI-/Debug-Aenderungen rund um Emotions-Steering sind besonders wichtig:

- `python tests/test_debug_monitor_data.py`
- `python tests/test_web_ui_consistency.py`
- `python tests/test_steering_backend.py`
- `python validate_system.py`

## Wenn Doku geändert wurde

Bei reinen Doku-Änderungen reichen meist:

- ein kurzer Struktur-/Import-Check
- ggf. ein schneller Python-Kompatibilitätscheck
- keine teuren Live-Modelltests

## Wenn Modelllogik geändert wurde

Dann zusätzlich prüfen:

- `config/config.py`
- `config/brain_config.py`
- `brain/agents/*.py`
- lokale/API-Unterscheidung im Prompt- und Steering-Pfad
- lokaler Steering-Endpoint (`brain/steering_api_server.py`, `brain/steering_backend.py`)
- Debug-Monitor-Metadaten fuer Emotions-/Layer-Steuerung
- Streamlit-Sichtbarkeit fuer `emotion_state`, `emotion_intensities`, Basisvektoren und Composite-Zusatzmuster
- betroffene Live-/Agent-Tests

## Testkarte

Eine dateinahe Übersicht steht in [`tests/README.md`](../tests/README.md).

## Hinweise für Agents

Vor automatisierten Änderungen immer fragen:

1. Ist der Test lokal sicher?
2. Nutzt er echte APIs oder externe Kosten?
3. Verändert er Dateien in `data/`?
4. Ist ein kleinerer Test ausreichend?

## Weiterführend

- [`tests/README.md`](../tests/README.md)
- [Lokale Modelle & Fallbacks](local-models.md)
- [Deployment](deployment.md)

## Neue Pruefpunkte fuer Debug- und Memory-Upgrade

Fuer die erweiterten Trace- und Memory-Pfade sind diese Dateien besonders wichtig:

- `tests/test_debug_monitor_data.py`
- `tests/test_memory_query_extraction_german.py`
- `tests/test_sleep_phase_context_updates.py`
- `tests/test_forgetting_curve.py`
- `tests/test_brain_pipeline_steering_integration.py`
- `tests/test_reasoning_layering.py`

Wenn nur die Doku angepasst wurde, reicht weiterhin ein schneller Struktur- oder `py_compile`-Check.
