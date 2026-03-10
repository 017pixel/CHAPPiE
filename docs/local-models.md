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

### `vllm`-Provider-Setup (bevorzugt)

Die konkrete Standardrichtung für CHAPPiE ist:

```python
LLM_PROVIDER = "vllm"
VLLM_URL = "http://localhost:8000/v1"
VLLM_MODEL = "Qwen/Qwen3.5-9B"
VLLM_FORCE_SINGLE_MODEL = True

INTENT_PROCESSOR_MODEL_VLLM = "Qwen/Qwen3.5-9B"
QUERY_EXTRACTION_VLLM_MODEL = "Qwen/Qwen3.5-9B"
```

Wichtig dazu:

1. `VLLM_URL` muss auf einen **OpenAI-kompatiblen lokalen Steering-Endpoint** zeigen.
2. `VLLM_MODEL` ist das Hauptmodell für die Antwortgenerierung.
3. `VLLM_FORCE_SINGLE_MODEL = True` ist fuer einen einzelnen lokalen Endpoint oft die robusteste Wahl.
4. `QUERY_EXTRACTION_VLLM_MODEL` kann für Memory-Suche kleiner gewählt werden.
5. Die Streamlit-Einstellungsseite unter [`web_infrastructure/settings_ui.py`](../web_infrastructure/settings_ui.py) kann diese Felder direkt pflegen.
6. Für Qwen-3.5 auf vLLM sollte `chat_template_kwargs.enable_thinking=false` gesetzt sein, wenn du direkt verwertbaren Antworttext priorisierst.
7. Die konkrete Schritt-fuer-Schritt-Anleitung liegt in [`docs/vLLM-Setup.md`](vLLM-Setup.md).

Praxis-Hinweis fuer kleine Server:

- `Qwen/Qwen3.5-9B` ist jetzt der bevorzugte lokale Standardpfad fuer CHAPPiE auf `vllm`
- `Qwen/Qwen3.5-27B` ist die naechste sinnvolle Stufe, wenn mehr VRAM und etwas mehr Latenz akzeptabel sind
- 35B/122B bleiben Zielprofile fuer staerkere Maschinen, nicht die sichere Default-Wahl
- stock vLLM hat das CHAPPiE-`steering`-Payload in dieser Umgebung ignoriert; `chappie-vllm.service` startet deshalb einen steering-faehigen lokalen OpenAI-Server
- echte Wirkung kommt dort ueber eine Hybridspur aus Residual-Activation-Steering plus kompakter interner Stilfuehrung
- fuer `Qwen 3.5` nutzt der lokale Steering-Loader bei Bedarf `trust_remote_code=True`, damit das Modell auch mit aelteren `transformers`-Pins geladen werden kann
- wenn eine lokale GPU fuer das ausgewaehlte Qwen-Modell nicht genug VRAM hat, faellt der Steering-Loader automatisch auf CPU zurueck statt in einem OOM-/Startfehler zu enden; der erste Start kann dann deutlich laenger dauern

### Emotionale Steuerung bei lokalem Qwen 3.5

Fuer das bevorzugte Setup **`vllm`-Provider + lokaler Steering-Endpoint + Qwen 3.5** gilt im Chat jetzt bewusst:

- keine expliziten Emotions-Verhaltensregeln im Systemprompt
- Emotionen sollen sich stattdessen ueber **Layer-/Activation-Steering** bemerkbar machen
- die 7 Basis-Vitalzeichen (`happiness`, `sadness`, `frustration`, `trust`, `curiosity`, `motivation`, `energy`) sind dabei die primaeren Steering-Signale
- der lokale Endpoint stabilisiert das Verhalten zusaetzlich ueber eine kurze interne Stilvorgabe, damit instruction-tuned Qwen die Richtung auch sichtbar ausspielt
- lokales Qwen-Steering wird im Antwortpfad forciert, damit die Wirkung nicht an `ENABLE_STEERING=False` haengen bleibt
- der Debug-Mode zeigt aktive Basisvektoren aller 7 Vitalzeichen und zusaetzliche Composite-Modi wie `warm`, `melancholic`, `guarded` oder `crashout`
- die Streamlit-UI zeigt im Tab **Emotionen** jetzt pro Emotion die editierbare Layer-Range und Steering-Staerke sowie eine Tabelle mit `emotion_state`, `emotion_intensities`, Basisvektoren und Composite-Zusatzmustern
- der **Brain Monitor** trennt sichtbar zwischen Gehirnstruktur (Kontext, Tool-Pfad, Global Workspace) und dem Endausgabe-Steering in Schritt 2
- starke Emotionsspruenge werden pro Turn geglaettet, damit Zustandswechsel sichtbarer und plausibler bleiben

Dadurch soll der Zustand im Stil merkbar werden: waermer, gereizter, rueckzugsorientierter, druckvoller oder eskalierender.

### Empfohlene Qwen-3.5-Profile

| Modell | Einsatzidee |
|---|---|
| `Qwen/Qwen3.5-27B` | staerkeres lokales Hauptmodell, wenn 9B qualitativ nicht reicht |
| `Qwen/Qwen3.5-9B` | kompakt für Step-1/Intent und Utility-Aufgaben |
| `Qwen/Qwen3.5-35B-A3B` | guter Qualitäts-/Latenz-Kompromiss lokal |
| `Qwen/Qwen3.5-35B-A3B-GPTQ-Int4` | empfohlen für lokale GPUs mit VRAM-Limit |
| `Qwen/Qwen3.5-122B-A10B-GPTQ-Int4` | maximale lokale Zielausbaustufe |

### Ollama-Setup (sekundärer lokaler Fallback)

Geeignet für kleinere lokale Maschinen oder einfachere Entwicklungsumgebungen. Ollama ist praktisch, aber für die vollständige Multi-Agent-Architektur meist nicht die erste Wahl.

### Emotion-Analyse aktuell

Die Emotionsanalyse ist weiterhin separat konfigurierbar und nutzt derzeit den dedizierten `EMOTION_ANALYSIS_MODEL`-/`EMOTION_ANALYSIS_HOST`-Pfad. Für die Kernarchitektur bleibt aber **vLLM + Qwen 3.5** die bevorzugte Hauptrichtung.

Hinweis: Bei **Ollama** gibt es in diesem Repository derzeit keinen gleichwertigen Pfad fuer echtes Activation-Steering. Lokale Ollama-Modelle bekommen jetzt ebenfalls keine Emotionsregeln mehr im Systemprompt; fuer spuerbare layergetriebene Emotionsausdruecke bleibt deshalb der steering-faehige lokale `vllm`-Pfad die bevorzugte Zielplattform.

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
