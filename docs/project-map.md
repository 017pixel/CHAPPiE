# Projektkarte

| Pfad | Status | Inhalt |
|---|---|---|
| `api/` | aktiv | FastAPI-App, Router, Schemas und Services |
| `brain/` | aktiv | Provider, Steering, Workspace, Parser und Kompatibilitätsimporte |
| `config/` | aktiv | zentrale Settings, Prompts, Emotionen und lokale Trainingsconfig |
| `web_infrastructure/` | aktiv | Runtime-Fassade, Turn-Pipeline und Randverträge |
| `memory/` | aktiv | STM, LTM, Chroma, Kontextdateien, Sleep und Vergessen |
| `life/` | aktiv | Homeostasis, Goals, Zeit, Beziehung und Entwicklung |
| `frontend/` | aktiv | React, Vite, TypeScript und Tailwind |
| `Chappies_Trainingspartner/` | aktiv | Daemon, TrainingLoop und TrainerAgent |
| `forschung/` | aktiv und eingefroren | Harness, Reports, Runs und Evidence, siehe `forschung/INDEX.md` |
| `Legacy-Code/` | historisch | nicht produktive Quellsnapshots und alte Scripts |
| `tests/` | aktiv | eigenständige Python-Testskripte |
| `scripts/` | aktiv | Setup-, Backup- und Validierungswerkzeuge |
| `deploy/` | aktiv | systemd-Dateien und operative Hilfen |
| `data/` | lokal/sensibel | Memories, Kontext und Laufzeitzustand |
| `plans/` | Planung | aktuelle und historische Umsetzungspläne |

## Aktive Runtime-Dateien

```text
web_infrastructure/
├── chappie_runtime.py
├── contracts.py
├── turn_context.py
├── turn_pipeline.py
├── generation.py
├── formatting.py
├── persistence.py
└── backend_wrapper.py
```

`backend_wrapper.py` ist eine kleine Kompatibilitätsschicht. Neue interne Aufrufer sollen `chappie_runtime.py` verwenden; bestehende externe Imports bleiben unterstützt.

## Zentrale Config

- `config/config.py`: Settings, Provider, Pfade und Defaults
- `config/example_config.py`: lesbare Vorlage
- `config/prompts.py`: aktive LLM-Instruktionen
- `config/emotions.py`: zehn Emotionen und Mapping
- `CHAPPIE_CONFIG.json`: ignorierte lokale Overrides und Secrets
- `config/training_config.json`: ignorierte Trainingskonfiguration

Nicht vorhandene Altpfade wie `config/root_config.py`, `config/brain_config.py` oder `CHAPPIE_CONFIG.example.json` sind keine aktiven Quellen.

## Versionen

- Produktrelease: API, Frontend-Paket und CHANGELOG
- UI-Formatversion: unabhängiger interner Vertrag in `ui_utils.py`
- Steering-Service-Version: unabhängige Serviceversion
- Steering-Payload-Version: unabhängige Kompatibilitätsversion
