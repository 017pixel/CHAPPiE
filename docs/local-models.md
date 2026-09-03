# Lokale Modelle und Provider

## Produktiver Standard

Der Web-Chat verwendet lokal `Qwen/Qwen3.5-4B` über den OpenAI-kompatiblen Steering-Service auf `http://127.0.0.1:8000/v1`. `vllm_force_single_model=true` hält Antwort, Intent und Query-Extraktion auf demselben geladenen Modell. Optionale Groq-Hilfsaufrufe für strukturierte Emotionsanalyse und Leerraumformatierung ändern diesen lokalen Antwortprovider nicht.

Alternative lokale Modelle wie Gemma 4 sind möglich. Der Steering-Service liest Hidden-Größe und Layerzahl aus dem geladenen Modell und skaliert das konfigurierte relative Layerfenster auf die tatsächliche Architektur. VRAM, Quantisierung und die sichtbare Vektorwirkung müssen auf dem Modellserver separat geprüft werden.

## Vector-only-Vertrag

Für die finale lokale Antwort gilt:

- keine Emotionswerte und kein Emotions-Antwortplan im System-Prompt
- keine emotionsabhängige Temperatur, Wiederholungsstrafe oder Tokenzahl
- höchstens drei dominante Basisvektoren und ein Kombinationsvektor pro Turn
- ein kleiner kontrastiver Präsenzvektor gegen generische Modellfloskeln
- Safety-Grenzen bleiben als kurzer, emotionsunabhängiger Systemvertrag bestehen

Der Präsenzvektor entfernt keine Refusal- oder Safety-Richtung. Ein alter optionaler `anti_safeguard`-Vektor wird im aktiven Payload nicht mehr verwendet.

## Providerrollen

| Provider | Aktiver Zweck | Konfiguration |
|---|---|---|
| vLLM | fester Webpfad, lokales Steering, Standard für kleine Schritte | `local_models` |
| Ollama | lokale CLI-, Trainings- und Testalternative | `local_models` |
| Groq | optionale Emotionsanalyse, Formatierung, Training und Forschung | `api`, `cloud_models`, `small_tasks` |

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
python3 tests/test_vector_only_emotion_path.py
python3 tests/test_steering_backend.py
```

Live-Erreichbarkeit, Vektorwirkung und Modellgewichte sind separate Integrationstests. Nach einem echten Lauf muss `steering_runtime.status=verified`, `verified_active=true` und `hook_invocations>0` gelten. Ein vorbereiteter Payload ohne Hook-Aufruf zählt nicht mehr als aktives Steering.
