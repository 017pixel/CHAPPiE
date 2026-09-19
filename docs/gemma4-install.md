# Gemma 4 E4B installieren

CHAPPiE unterstützt `google/gemma-4-E4B-it` als Alternative zu Qwen 3.5 4B. Qwen bleibt der besser getestete Standard. Gemma benötigt vor dem Download einen Hugging-Face-Zugang zum freigeschalteten Modell.

## Installation

1. Öffne [`google/gemma-4-E4B-it`](https://huggingface.co/google/gemma-4-E4B-it), melde dich an und akzeptiere den Modellzugang.
2. Erzeuge bei Bedarf einen Read-Token in den Hugging-Face-Einstellungen.
3. Starte im geklonten Repository den Wizard:

```bash
python3 scripts/setup_wizard.py --model gemma
```

Der Wizard erstellt `venv`, installiert `requirements.txt`, baut das Frontend, lädt das Modell und schreibt eine private `CHAPPIE_CONFIG.json`. Für die breitere Hardwareunterstützung verwendet dieses Profil NF4 mit 4096 Tokens Kontext. Der Hugging-Face-Token wird verdeckt abgefragt und nicht in der CHAPPiE-Konfiguration gespeichert.

Der zweite unterstützte Installationsweg ist der [vollständige Auftrag für einen Coding-Agenten](../AGENT_SETUP_PROMPT.md). Dabei kann der Token über die Umgebung bereitgestellt werden:

```bash
export HF_TOKEN="<read-token>"
python3 scripts/setup_wizard.py --non-interactive --model gemma
```

Die vom Wizard erzeugten Gemma-Werte liegen wie alle Steering-Einstellungen im Abschnitt `local_models`:

```json
{
  "local_models": {
    "llm_provider": "vllm",
    "vllm_url": "http://127.0.0.1:8000/v1",
    "vllm_model": "google/gemma-4-E4B-it",
    "gemma4_model": "google/gemma-4-E4B-it",
    "gemma4_steering_model": "google/gemma-4-E4B-it",
    "vllm_force_single_model": true,
    "enable_steering": true,
    "steering_provider": "vllm",
    "steering_model": "google/gemma-4-E4B-it",
    "steering_quantize": true,
    "steering_context_length": 4096
  },
  "small_tasks": {
    "intent_provider": "vllm",
    "intent_processor_model_vllm": "google/gemma-4-E4B-it",
    "query_extraction_provider": "vllm",
    "query_extraction_vllm_model": "google/gemma-4-E4B-it"
  },
  "generation": {
    "temperature": 1.0,
    "top_p": 0.95,
    "top_k": 64,
    "use_model_defaults": true
  }
}
```

Eine ältere Anleitung verwendete fälschlich einen separaten Abschnitt `steering`. Dieser Abschnitt wird von der aktiven Config nicht gelesen.

## Start und Prüfung

Starte die Prozesse aus dem aktivierten `venv` in getrennten Terminals:

```bash
python3 -m brain.steering_api_server
python3 app.py
cd frontend && npm run dev
```

Prüfe danach beide Health-Endpunkte:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8010/health
```

Der Steering-Endpunkt muss `google/gemma-4-E4B-it` und `restart_status: ready` melden. Ein echter Chatlauf gilt erst als gesteuert, wenn der Debug-Bericht ausgeführte Hooks und `verified_active=true` meldet.

Die modellfreien Regressionstests laufen ohne Gewichte:

```bash
python3 tests/test_gemma4_integration.py
python3 tests/test_steering_backend.py
python3 tests/test_vector_only_emotion_path.py
```

## Grenzen

Gemma 4 E4B wurde im Forschungs-Harness geprüft, Qwen 3.5 4B wurde im laufenden CHAPPiE-System häufiger verwendet. Geschwindigkeit und Speicherbedarf hängen von GPU, Torch-Version, Quantisierung und Kontextlänge ab. Bei Speicherfehlern zuerst die `steering_context_length` senken.

Der größere Checkpoint `google/gemma-4-26B-A4B-it` bleibt im Code als experimentelles Profil erhalten. Der Setup-Wizard installiert bewusst E4B, weil dieser Checkpoint für mehr Rechner geeignet ist.
