# Lokale Modelle zuerst, API als Fallback

## Zielstrategie

CHAPPiE soll primaer lokal mit Qwen-3.5-Modellen laufen. APIs sind nur der Fallback, wenn lokal nicht genug Leistung oder kein passendes Setup vorhanden ist.

## Prioritaet

1. `vllm` plus Qwen-3.5
2. Ollama fuer leichtere lokale Setups
3. Groq als Fallback

## Relevante Konfigurationsdateien

| Datei | Zweck |
|---|---|
| `CHAPPIE_CONFIG.json` | lokale Laufzeitkonfiguration mit API-Keys, Modellwahl, Memory und Generation |
| `CHAPPIE_CONFIG.example.json` | Vorlage fuer die lokale Konfiguration |
| `config/config.py` | Loader und Runtime-Objekt fuer die Root-Konfiguration |
| `config/brain_config.py` | Modellverteilung der Brain-Agenten |
| `brain/__init__.py` | Provider-Fabrik |

## Empfohlene lokale Grundidee

```python
local_models.llm_provider = "vllm"
local_models.vllm_url = "http://localhost:8000/v1"
local_models.vllm_model = "Qwen/Qwen3.5-4B"
local_models.vllm_force_single_model = true

small_tasks.intent_provider = "groq"
small_tasks.intent_processor_model_groq = "llama-3.1-8b-instant"
small_tasks.query_extraction_provider = "groq"
small_tasks.query_extraction_groq_model = "llama-3.1-8b-instant"
```

Wichtig:

1. `VLLM_URL` muss auf den steering-faehigen lokalen Endpoint zeigen.
2. `VLLM_MODEL` ist das Hauptmodell fuer Antwortgenerierung.
3. `VLLM_FORCE_SINGLE_MODEL = True` ist fuer einen einzelnen lokalen Endpoint robust.
4. `api.groq_api_key` muss in `CHAPPIE_CONFIG.json` gesetzt sein, damit Intent, Query Extraction, Formatierung und STM-Zusammenfassungen ueber Groq laufen.
5. Runtime-Settings werden ueber `CHAPPIE_CONFIG.json`, API und Frontend gepflegt.

## Praxis-Hinweise

- `Qwen/Qwen3.5-4B` ist der bevorzugte Default fuer ca. 16 GB VRAM
- `Qwen/Qwen3.5-9B` ist die naechste Stufe
- `Qwen/Qwen3.5-27B` braucht deutlich mehr GPU-Reserven
- der lokale Service hinter `chappie-vllm.service` ist ein steering-faehiger OpenAI-kompatibler Server
- wenn noetig wird `trust_remote_code=True` verwendet

## Server-Override fuer Produktivbetrieb

Lokale Defaults bleiben bewusst bei `Qwen/Qwen3.5-4B`, damit Entwicklung und sichere Checks nicht unnoetig schwer werden.

Fuer den Produktivserver kann der Steering-Service separat auf `Qwen/Qwen3.5-9B` gezogen werden:

```ini
Environment="CHAPPIE_STEERING_MODEL=Qwen/Qwen3.5-9B"
ExecStart=... -m brain.steering_api_server ... --model Qwen/Qwen3.5-9B
```

Damit bleiben App-Defaults und Tests lokal schlank, waehrend der Server gezielt das staerkere Modell nutzt.

## Emotionale Steuerung

Fuer den bevorzugten lokalen Pfad gilt:

- Emotionen werden nicht primaer als Prompt-Liste transportiert
- der wichtigste Pfad ist Steering ueber Payload und lokale Modellschicht
- API und Frontend zeigen `emotion_state`, Intensitaeten und Debugdaten strukturiert an
- dieselben Daten werden auch fuer Training und Debug genutzt

## Wann API-Fallback sinnvoll ist

- lokale GPU reicht nicht
- Modell ist lokal nicht verfuegbar
- gezielte Cloud-Vergleiche sind noetig
- kurzfristiger Notbetrieb ohne lokalen Stack

## Doku-Regel

Wenn Provider-Prioritaet oder Modellpfade sich aendern, mindestens pruefen:

- `README.md`
- `AGENTS.md`
- `docs/local-models.md`
- `docs/vLLM-Setup.md`
- `config/secrets_example.py`

## Weiterfuehrend

- [vLLM-Setup](vLLM-Setup.md)
- [Architektur](architecture.md)
- [Projektkarte](project-map.md)
