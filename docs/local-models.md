# Lokale Modelle zuerst, API als Fallback

## Zielstrategie

CHAPPiE soll primaer lokal mit Qwen-3.5-Modellen laufen. APIs sind nur der Fallback, wenn lokal nicht genug Leistung oder kein passendes Setup vorhanden ist.

## Prioritaet

1. `vllm` plus Qwen-3.5
2. Ollama fuer leichtere lokale Setups
3. NVIDIA, Groq oder Cerebras als Fallback

## Relevante Konfigurationsdateien

| Datei | Zweck |
|---|---|
| `config/config.py` | Laufzeit-Settings und Provider-Auswahl |
| `config/brain_config.py` | Modellverteilung der Brain-Agenten |
| `config/secrets_example.py` | Beispielwerte fuer lokale oder API-Setups |
| `brain/__init__.py` | Provider-Fabrik |

## Empfohlene lokale Grundidee

```python
LLM_PROVIDER = "vllm"
VLLM_URL = "http://localhost:8000/v1"
VLLM_MODEL = "Qwen/Qwen3.5-4B"
VLLM_FORCE_SINGLE_MODEL = True

INTENT_PROCESSOR_MODEL_VLLM = "Qwen/Qwen3.5-4B"
QUERY_EXTRACTION_VLLM_MODEL = "Qwen/Qwen3.5-4B"
```

Wichtig:

1. `VLLM_URL` muss auf den steering-faehigen lokalen Endpoint zeigen.
2. `VLLM_MODEL` ist das Hauptmodell fuer Antwortgenerierung.
3. `VLLM_FORCE_SINGLE_MODEL = True` ist fuer einen einzelnen lokalen Endpoint robust.
4. Runtime-Settings werden jetzt ueber API und Frontend gepflegt.

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
- `agent.md`
- `docs/local-models.md`
- `docs/vLLM-Setup.md`
- `config/secrets_example.py`

## Weiterfuehrend

- [vLLM-Setup](vLLM-Setup.md)
- [Architektur](architecture.md)
- [Projektkarte](project-map.md)
