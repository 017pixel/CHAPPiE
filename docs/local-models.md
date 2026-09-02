# Lokale Modelle und Provider

## Produktiver Standard

Der Web-Chat verwendet lokal `Qwen/Qwen3.5-4B` über den OpenAI-kompatiblen Steering-Service auf `http://127.0.0.1:8000/v1`. `vllm_force_single_model=true` hält Antwort, Intent und Query-Extraktion auf demselben geladenen Modell.

Alternative lokale Modelle wie Gemma 4 sind möglich, benötigen aber passende VRAM-, Quantisierungs-, Kontext- und Steering-Profile. Ein Modellwechsel ist keine Cleanup-Aufgabe und soll separat verifiziert werden.

## Providerrollen

| Provider | Aktiver Zweck | Konfiguration |
|---|---|---|
| vLLM | fester Webpfad, lokales Steering, Standard für kleine Schritte | `local_models` |
| Ollama | lokale CLI-, Trainings- und Testalternative | `local_models` |
| Groq | optionaler Cloud-Adapter für Training und Forschung | `api`, `cloud_models`, `small_tasks` |

Es gibt kein aktives Cerebras-Backend. Historische Referenzen können nur in eingefrorenen Reports, Runs oder Legacy-Quellen vorkommen.

## Konfigurationsquellen

- Defaults und Pfadzuordnung: `config/config.py`
- lesbare Vorlage: `config/example_config.py`
- lokale ignorierte Overrides: `CHAPPIE_CONFIG.json`
- Secrets: `CHAPPIE_CONFIG.json`, `config/secrets.py`, ignorierte Dateien in `config/APIs/`

Die Config erzeugen:

```bash
python3 -c "from config.config import write_config; write_config({})"
```

Wichtige Werte:

```json
{
  "local_models": {
    "llm_provider": "vllm",
    "vllm_url": "http://127.0.0.1:8000/v1",
    "vllm_model": "Qwen/Qwen3.5-4B",
    "vllm_force_single_model": true,
    "enable_steering": true
  },
  "small_tasks": {
    "intent_provider": "vllm",
    "query_extraction_provider": "vllm"
  }
}
```

## Installation

```bash
pip install -r requirements/runtime.txt
pip install -r requirements/providers-local.txt
```

GPU- und Modellgewichte sind bewusst nicht Teil der minimalen CI-Installation. Die vollständige lokale Installation bleibt `pip install -r requirements.txt`.

## Prüfung

```bash
python3 tests/test_provider_factory.py
python3 tests/test_vllm_response_handling.py
python3 tests/test_ollama_response_handling.py
python3 tests/test_local_first_runtime.py
```

Live-Erreichbarkeit und Modellgewichte sind separate Integrationstests.
