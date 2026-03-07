# Lokale Modelle zuerst, API als Fallback

## Zielstrategie des Projekts

CHAPPiE soll **primär lokal mit Qwen-3.5-Modellen** laufen. APIs sind nur die zweite Wahl, wenn lokal nicht genügend Leistung oder kein kompatibles Setup vorhanden ist.

## Prioritätsreihenfolge

1. **vLLM + Qwen 3.5** (bevorzugt)
2. **Ollama** für leichtere lokale Setups
3. **NVIDIA / Groq / Cerebras** als Fallbacks

## Warum lokal bevorzugt wird

- bessere Kontrolle über Daten und Verhalten
- weniger externe Abhängigkeiten
- stabile, nachvollziehbare Entwicklungsumgebung
- gute Passung für emotionale Verarbeitung und iterative Experimente

## Relevante Konfigurationsdateien

| Datei | Zweck |
|---|---|
| `config/config.py` | Laufzeit-Settings und Provider-Auswahl |
| `config/brain_config.py` | Zielverteilung der Brain-Agent-Modelle |
| `config/secrets_example.py` | Beispielkonfiguration für lokale oder API-Setups |
| `brain/__init__.py` | Provider-Fabrik (`get_brain()`) |

## Dokumentierte Zielverteilung

Die zentrale Modellverteilung in [`config/brain_config.py`](../config/brain_config.py) priorisiert Qwen-3.5 auf `vLLM`:

- kleinere Qwen-3.5-Modelle für schnellere Subagent-Aufgaben
- größere Qwen-3.5-Modelle für Gedächtnis- und Orchestrierungsaufgaben

## Wichtiger Implementierungshinweis

Die **Zielkonfiguration** ist lokal-first. Einzelne Agent-Klassen unter [`brain/agents/`](../brain/agents) enthalten jedoch aktuell noch explizite Provider-/Modellangaben. Wer die Modelllogik anfasst, sollte deshalb immer **beides** prüfen:

- zentrale Soll-Konfiguration in `config/brain_config.py`
- konkrete Agent-Implementierungen in `brain/agents/*.py`

So bleiben Dokumentation und tatsächliches Laufzeitverhalten konsistent.

## Empfohlene lokale Grundidee

### vLLM-Setup

- `LLM_PROVIDER = "vllm"`
- `VLLM_URL` auf einen OpenAI-kompatiblen lokalen Endpoint setzen
- `VLLM_MODEL` auf ein Qwen-3.5-Modell setzen

### Ollama-Setup

Geeignet für kleinere lokale Maschinen oder einfachere Entwicklungsumgebungen. Ollama ist praktisch, aber für die vollständige Multi-Agent-Architektur meist nicht die erste Wahl.

## Wann API-Fallback sinnvoll ist

- lokale GPU reicht nicht aus
- Modell ist lokal nicht verfügbar
- bestimmte Vergleiche oder Benchmarks sollen mit Cloud-Modellen erfolgen
- kurzfristige Notfall-Ausführung ohne lokalen Stack

## Doku-Regel

Wenn sich Modellstrategie, Provider-Priorität oder Konfigurationsdateien ändern, müssen mindestens diese Dateien geprüft werden:

- `README.md`
- `agent.md`
- `docs/local-models.md`
- `config/secrets_example.py`
- ggf. `docs/architecture.md` und `docs/workflows.md`

## Weiterführend

- [Architektur](architecture.md)
- [Projektkarte](project-map.md)
- [Agent-Anleitung](../agent.md)

