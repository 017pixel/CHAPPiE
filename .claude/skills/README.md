# CHAPPiE Developer Skills (OpenCode)

Diese Skills sind für **Entwickler, die mit AI Agents (OpenCode, Claude Code, etc.) an CHAPPiE arbeiten**.

Sie enthalten projektspezifisches Wissen über Architektur, Konventionen, Patterns und Workflows — nicht für CHAPPiEs Runtime, sondern für den Entwicklungsprozess.

## Skills

| Skill | Beschreibung |
|---|---|
| `chappie-architecture` | Brain, Memory, Life — Architektur und Komponenten |
| `chappie-backend` | FastAPI, vLLM, Cerebras, Training-Daemon |
| `chappie-frontend` | React, TypeScript, Tailwind, Chat-Streaming |
| `chappie-prompts` | System-Prompt, Emotion-Templates, Cerebras-Formatierung |
| `chappie-testing` | Teststrategie, Mocking, py_compile |
| `chappie-config` | Settings, Provider, Hot-Reload |
| `chappie-update` | Update-Workflow: git pull, Dienste neustarten, Tests, Health-Check |

## Format

Jeder Skill folgt dem [OpenCode Skills Standard](https://opencode.ai/docs/skills/):
- `SKILL.md` mit YAML-Frontmatter (`name`, `description`)
- Markdown-Body mit Instruktionen für den AI Agent

## Nutzung

OpenCode durchsucht `.opencode/skills/`, `.claude/skills/` und `.agents/skills/` nach Skills. Der Agent lädt automatisch den relevanten Skill basierend auf der `description` im Frontmatter.
