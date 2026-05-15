# CHAPPiE Developer Skills

Diese Skills sind für **Entwickler, die mit AI Agents (Claude Code, OpenCode, etc.) an CHAPPiE arbeiten**.

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

## Format

Jeder Skill folgt dem [Claude Code Skills Standard](https://code.claude.com/docs/en/skills):
- `SKILL.md` mit YAML-Frontmatter (`name`, `description`)
- Markdown-Body mit Instruktionen für den AI Agent

## Nutzung

Wenn ein AI Agent das Projekt liest, lädt er automatisch den relevanten Skill basierend auf der `description` im Frontmatter. Skills können auch direkt per `/skill-name` aufgerufen werden.
