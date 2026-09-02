# vLLM- und Steering-Setup

## Architektur

Der Prozess `python3 -m brain.steering_api_server` stellt auf Port 8000 eine OpenAI-kompatible API bereit. `brain/vllm_brain.py` verbindet sich mit diesem Endpoint und übergibt Generationseinstellungen sowie Steering-Metadaten. Der Web-Chat selbst läuft über die App-API auf Port 8010.

```text
CHAPPiERuntime -> VLLMBrain -> :8000/v1 -> SteeringBackend -> Modell
```

## Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements/runtime.txt
pip install -r requirements/providers-local.txt
```

Die konkrete Torch-, CUDA-, Transformers- und vLLM-Kombination muss zur Ziel-GPU passen. Die CI installiert diesen GPU-Stack nicht.

## Konfiguration

`config/config.py` ist die zentrale Quelle, `config/example_config.py` die Vorlage. Lokale Werte werden in der ignorierten `CHAPPIE_CONFIG.json` gespeichert.

Mindestens prüfen:

- `local_models.llm_provider = "vllm"`
- `local_models.vllm_url = "http://127.0.0.1:8000/v1"`
- `local_models.vllm_model = "Qwen/Qwen3.5-4B"`
- `local_models.vllm_force_single_model = true`
- `local_models.enable_steering = true`
- `small_tasks.intent_provider = "vllm"`
- `small_tasks.query_extraction_provider = "vllm"`

## Start

```bash
python3 -m brain.steering_api_server
python3 app.py
```

Die systemd-Reihenfolge ist:

1. `chappie-vllm.service`
2. `chappie-web.service`
3. `chappie-frontend.service`

`chappie-training.service` läuft separat.

## Health-Checks

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8010/health
```

Die genaue Health-Route des Steering-Service wird zusätzlich durch dessen API-Tests abgesichert. Für reine Logiktests sind keine laufenden Dienste erforderlich.

## Modelle und Steering

Das Standardprofil für Qwen 3.5 4B nutzt Emotion-Layer 10 bis 26. Andere Modelle dürfen nur mit einem geprüften Layerprofil und ausreichendem Speicher gestartet werden. Quantisierung und Kontextlimit beeinflussen VRAM stark und sind operative Modellentscheidungen.

Weitere Details: [Lokale Modelle](local-models.md), [Deployment](deployment.md), [Architektur](architecture.md).
