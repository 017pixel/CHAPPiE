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

### vLLM-Setup (bevorzugt)

Die konkrete Standardrichtung für CHAPPiE ist:

```python
LLM_PROVIDER = "vllm"
VLLM_URL = "http://localhost:8000/v1"
VLLM_MODEL = "Qwen/Qwen3.5-32B-Instruct"

INTENT_PROCESSOR_MODEL_VLLM = "Qwen/Qwen3.5-32B-Instruct"
QUERY_EXTRACTION_VLLM_MODEL = "Qwen/Qwen3.5-9B-Instruct"
```

Wichtig dazu:

1. `VLLM_URL` muss auf einen **OpenAI-kompatiblen lokalen Endpoint** zeigen.
2. `VLLM_MODEL` ist das Hauptmodell für die Antwortgenerierung.
3. `INTENT_PROCESSOR_MODEL_VLLM` kann für Step-1-Klassifikation separat gesetzt werden.
4. `QUERY_EXTRACTION_VLLM_MODEL` kann für Memory-Suche kleiner gewählt werden.
5. Die Streamlit-Einstellungsseite unter [`web_infrastructure/settings_ui.py`](../web_infrastructure/settings_ui.py) kann diese Felder direkt pflegen.

### Empfohlene Qwen-3.5-Profile

| Modell | Einsatzidee |
|---|---|
| `Qwen/Qwen3.5-32B-Instruct` | guter Standard für lokale Hauptnutzung |
| `Qwen/Qwen3.5-72B-Instruct` | höhere Qualität bei stärkerer Hardware |
| `Qwen/Qwen3.5-122B-A10B-Instruct-GPTQ-Int4` | maximale lokale Zielausbaustufe |
| `Qwen/Qwen3.5-9B-Instruct` | sinnvoll für leichtere Query-/Utility-Aufgaben |

### Ollama-Setup (sekundärer lokaler Fallback)

Geeignet für kleinere lokale Maschinen oder einfachere Entwicklungsumgebungen. Ollama ist praktisch, aber für die vollständige Multi-Agent-Architektur meist nicht die erste Wahl.

### Emotion-Analyse aktuell

Die Emotionsanalyse ist weiterhin separat konfigurierbar und nutzt derzeit den dedizierten `EMOTION_ANALYSIS_MODEL`-/`EMOTION_ANALYSIS_HOST`-Pfad. Für die Kernarchitektur bleibt aber **vLLM + Qwen 3.5** die bevorzugte Hauptrichtung.

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

