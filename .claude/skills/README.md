# Projekt-Skills für Claude-kompatible Harnesses

Die kanonische Quelle liegt unter `.agents/skills/`. Dieses Verzeichnis ist ein bewusst synchronisierter Spiegel für Harnesses, die `.claude/skills/` erwarten.

Änderungen werden zuerst in `.agents/skills/<name>/SKILL.md` vorgenommen und anschließend in den gleichnamigen Spiegel übertragen. Der Validator prüft Bytegleichheit:

```bash
python3 scripts/validate_skill_sync.py
```

| Skill | Geltungsbereich |
|---|---|
| `chappie-architecture` | Runtime, Brain, Memory, Life, Steering und Workspace |
| `chappie-backend` | FastAPI, modulare Runtime, Provider und Training |
| `chappie-config` | zentrale Config, Schemas, Provider und lokale Overrides |
| `chappie-frontend` | React, Vite, Tailwind und Chat-Streaming |
| `chappie-prompts` | aktive Prompttemplates und Antwortbudgets |
| `chappie-testing` | Standalone-Tests, CI, Ruff, Mypy und Reports |
| `chappie-update` | vollständiger Betriebsupdate-Ablauf |

Der aktive Chatpfad läuft über `web_infrastructure/chappie_runtime.py`. Die historische BrainPipeline v1 liegt unter `Legacy-Code/`.
