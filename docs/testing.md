# Testing

## Testphilosophie

CHAPPiE trennt zwischen sicheren lokalen Checks, manuellen Kompatibilitaetstests und teureren Live-Pfaden.

## Testtypen

| Typ | Ziel | Beispiele |
|---|---|---|
| schnelle lokale Checks | Kernlogik und Webpfad ohne externe Kosten pruefen | `tests/test_forgetting_curve.py`, `tests/test_api_contract.py` |
| Struktur- und Kompatibilitaetschecks | Module, Dateien, Startpfade validieren | `tests/manual/test_compatibility.py`, `py_compile` |
| Live- und Provider-Tests | Verhalten mit echten Modellen oder APIs pruefen | `tests/test_brain_agents.py`, `tests/test_integration.py` |
| manuelle Bedienung | Chat oder UI bewusst testen | `tests/manual/test_chat_live.py`, `tests/manual/test_chappie.py` |
| Alignment/Emotion Research | Automatisierte Test-Sessions ueber 14 Themenkategorien (86 Fragen) via Backend-API; Antwort-Formatting laeuft im Harness lokal, damit Groq-Rate-Limits nicht durch Formatierungsrequests belastet werden | `forschung/allignement_tests.py` |

## GitHub Actions / CI

`.github/workflows/ci.yml` fuehrt automatisiert aus:

- schnelle Python-Tests
- API-Contract-Checks
- Text-Formatting-Checks fuer Chat-Ausgabe
- Training-Config-Checks
- `py_compile` fuer zentrale Python-Dateien
- Frontend-Build

## Empfohlene Reihenfolge

1. kleinster lokaler Test
2. passender Dateitest
3. `py_compile`
4. Frontend-Build bei Web-Aenderungen
5. erst danach Live- oder Provider-Test

## Sinnvolle schnelle Checks

- `python tests/test_forgetting_curve.py`
- `python tests/test_life_simulation.py`
- `python tests/test_debug_monitor_data.py`
- `python tests/test_local_first_runtime.py`
- `python tests/test_ollama_response_handling.py`
- `python tests/test_chat_manager_persistence.py`
- `python tests/test_config_package_import.py`
- `python tests/test_vllm_response_handling.py`
- `python tests/test_web_ui_consistency.py`
- `python tests/test_reasoning_layering.py`
- `python tests/test_api_contract.py`
- `python tests/test_chat_ui_formatting.py`
- `python tests/test_training_config_ui.py`
- `python tests/test_provider_factory.py`
- `python tests/test_settings_integrity.py`
- `python tests/test_groq_brain_unit.py`
- `python tests/test_groq_limits.py`
- `python tests/test_quick.py`
- `python tests/test_runtime_switching.py`
- `python tests/test_root_config.py`
- `python tests/test_response_policy.py`
- `python tests/test_steering_manager_policy.py`
- `python tests/test_memory_query_extraction_german.py`
- `python tests/manual/test_compatibility.py`
- `python -m py_compile app.py api/main.py api/routers/chat.py api/routers/system.py web_infrastructure/backend_wrapper.py`
- `cd frontend && npm run build`

## Bei Modelllogik-Aenderungen

Zusammen pruefen:

- `config/config.py`
- `config/brain_config.py`
- `brain/agents/*.py`
- `brain/steering_api_server.py`
- `tests/test_debug_monitor_data.py`
- `tests/test_response_policy.py`
- `tests/test_steering_manager_policy.py`
- `tests/test_web_ui_consistency.py`

Bei Emotionsmodell-Aenderungen zusaetzlich pruefen:

- alte 7-Emotionen-States werden mit den aktuellen Defaults auf 10 Emotionen normalisiert
- neue Emotionen erscheinen in `/emotions/state`, `/emotion`, Settings, Debug und Visualizer
- neue Steering-Vektoren bleiben konservativ gecappt und erzeugen keine Anti-Vektoren bei niedrigen negativen Werten

## Bei Web-Aenderungen

Besonders wichtig:

- `tests/test_api_contract.py`
- `tests/test_chat_ui_formatting.py`
- `tests/test_training_config_ui.py`
- `tests/test_web_ui_consistency.py`
- `cd frontend && npm run build`

## Hinweise fuer Agents

Vor automatisierten Aenderungen immer pruefen:

1. Ist der Test lokal sicher?
2. Nutzt er echte APIs oder verursacht Kosten?
3. Veraendert er Dateien in `data/`?
4. Reicht ein kleinerer Test?

## Weiterfuehrend

- [`tests/README.md`](../tests/README.md)
- [Forschung / Alignment-Tests](../forschung)
- [Lokale Modelle](local-models.md)
- [Deployment](deployment.md)
