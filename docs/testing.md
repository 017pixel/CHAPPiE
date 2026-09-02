# Testing

CHAPPiE verwendet eigenständige Python-Skripte. Es gibt keine pytest-Pflicht und keine versteckten Live-Modellaufrufe in der deterministischen CI.

## Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements/ci.txt
cd frontend && npm ci --legacy-peer-deps
```

## Pflichtprüfungen

```bash
python3 -m compileall -q api brain config life memory web_infrastructure Chappies_Trainingspartner chappie_brain_cli.py app.py scripts forschung tests
python3 tests/test_quick.py
python3 tests/test_runtime_architecture.py
python3 tests/test_local_first_runtime.py
python3 tests/test_web_ui_consistency.py
python3 tests/test_settings_integrity.py
python3 tests/test_root_config.py
python3 tests/test_chat_ui_formatting.py
python3 tests/test_reasoning_layering.py
python3 tests/test_api_contract.py
python3 tests/test_forschung_harness.py
python3 tests/test_forschung_report.py
python3 forschung/report/validate_report_v5_freeze.py
python3 forschung/report/validate_report_v6.py
python3 scripts/validate_skill_sync.py
```

## Erweiterte deterministische Tests

- `tests/test_vllm_response_handling.py`
- `tests/test_ollama_response_handling.py`
- `tests/test_chat_manager_persistence.py`
- `tests/test_short_term_memory.py`
- `tests/test_training_config_ui.py`
- `tests/test_training_daemon_lifecycle.py`
- `tests/test_provider_factory.py`
- relevante Memory-, Life-, CLI- und Research-Validatoren

Diese Tests sollen in CI fehlschlagen dürfen, wenn eine Regression vorliegt. `continue-on-error` oder pauschales `|| true` ist für deterministische Tests nicht erlaubt.

## Live-Tests

`tests/test_brain_agents.py`, `tests/test_integration.py`, `tests/test_query_extraction.py` und Dateien unter `tests/manual/` können lokale Modelle, Chroma-Daten oder externe Dienste benötigen. Sie laufen nur bewusst in einer geeigneten Umgebung.

## Ruff und Mypy

```bash
ruff check --config config/ruff.toml --no-cache web_infrastructure api/routers/chat.py brain/steering_manager.py brain/brain_pipeline.py
mypy --config-file config/mypy.ini web_infrastructure/contracts.py web_infrastructure/turn_context.py web_infrastructure/backend_wrapper.py api/schemas
```

Der aktive Typ-Scope beginnt an öffentlichen Runtime- und API-Verträgen. Legacy-Code und eingefrorene Forschungsdaten sind ausgeschlossen. Der vollständige historische Mypy-Bestand bleibt als technische Schuld dokumentiert und wird nicht durch globale Ignorierungen als grün dargestellt.

## Frontend

```bash
cd frontend
npm run build
```

Bei sichtbaren UI-Änderungen ist zusätzlich die im Projekt vorgeschriebene Playwright-MCP-Prüfung nötig. Ohne UI-Änderung genügt der reproduzierbare TypeScript-/Vite-Build.

## Testdaten

- Providerzugriffe in Unit- und Vertragstests faken.
- Zustandsbehaftete Tests verwenden temporäre Verzeichnisse.
- Keine lokalen Secrets oder Nutzerdaten als Fixture committen.
- Zufällige Modelltexte nicht als einzigen Regressionstest verwenden.
- Forschungsdaten und Post-Migrations-Strukturtests klar trennen.
