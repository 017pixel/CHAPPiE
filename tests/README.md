# CHAPPiE Tests

Alle Tests sind direkt ausführbare Python-Skripte:

```bash
python3 tests/test_runtime_architecture.py
```

## Schnelle Pflichtgruppe

- `test_quick.py`
- `test_runtime_architecture.py`
- `test_pages_workflow.py`
- `test_local_first_runtime.py`
- `test_web_ui_consistency.py`
- `test_settings_integrity.py`
- `test_root_config.py`
- `test_chat_ui_formatting.py`
- `test_reasoning_layering.py`
- `test_vector_only_emotion_path.py`
- `test_memory_associations.py`
- `test_emotion_transition_rules.py`
- `test_forschung_harness.py`
- `test_forschung_report.py`
- `test_v18_unified_steering_profile.py`

## Verträge und Subsysteme

- API und SSE: `test_api_contract.py`, `test_session_export.py`
- Runtime und Provider: `test_vllm_response_handling.py`, `test_ollama_response_handling.py`, `test_provider_factory.py`
- Memory: `test_chat_manager_persistence.py`, `test_short_term_memory.py`, `test_forgetting_curve.py`, `test_memory_associations.py`
- Emotion und Steering: `test_emotion_transition_rules.py`, `test_vector_only_emotion_path.py`, `test_steering_backend.py`
- Life: `test_life_simulation.py` und gezielte Life-/Temporal-Tests
- Training: `test_training_config_ui.py`, `test_training_daemon_lifecycle.py`
- CLI: `test_cli_import.py`, `test_cli_display.py`, `test_cli_commands.py`, `test_cli_remote.py`, `test_cli_copy.py`
- Forschung: `test_forschung_harness.py`, `test_forschung_report.py` und Reportvalidatoren
- v17-Auswertung ohne Modellzugriff: `test_steering_judge.py`, `test_steering_acceptance.py`, `test_state_language_transfer.py`, `test_steering_layer_type_comparison.py`, `test_steering_composition.py`. Diese Skripte gehören zur erweiterten CI-Gruppe. Dort laufen auch die neuen Archiv-, Memory-OFF-, Session-, Autocomplete-, History-, Terminal-Layout- und Mixer-Verträge ohne Modellzugriff.
- v17-Capture mit lokal installiertem PyTorch, ohne Modellgewichte: `test_steering_research_integrity.py`, `test_steering_research_capture.py`. Separat von der minimalen CI-Umgebung ausführen.

## Architekturverträge

`test_runtime_architecture.py` schützt:

- alte und neue Runtime-Imports
- Factory-Optionen
- gemeinsamen Sync-/Stream-`TurnContext`
- lazy Providerauflösung
- Steering-Import ohne historische Agents
- lazy `BrainPipeline`-Kompatibilität
- Abwesenheit entfernter Legacy-Methoden im aktiven Runtime-Code

## Live und manuell

Integrationsnahe Tests und `tests/manual/` können einen laufenden vLLM-/Ollama-Service, lokale Modellgewichte oder echte Daten benötigen. Sie sind nicht Teil der Offline-Pflichtgruppe.

## Umgebung

```bash
pip install -r requirements/ci.txt
```

Die vollständige Teststrategie und CI-Kommandos stehen in [docs/testing.md](../docs/testing.md).
