# Lokale Modelle und Provider

## Produktiver Standard

Der Web-Chat verwendet lokal `Qwen/Qwen3.5-4B` über den OpenAI-kompatiblen Steering-Service auf `http://127.0.0.1:8000/v1`. `vllm_force_single_model=true` hält Antwort, Intent, Query-Extraktion und optionale Format-/Konsolidierungshilfen auf dem lokalen Ein-Modell-Pfad. Groq-Hilfsaufrufe werden erst verwendet, wenn dieser Schutz ausdrücklich deaktiviert und `groq_auxiliary_enabled=true` gesetzt ist.

Alternative lokale Modelle benötigen eine eigene Prüfung von VRAM, Quantisierung und Vektorwirkung. Der kompatible Ankerpfad kann relative Layerfenster anpassen; gemessene v17-Packs verlangen hingegen eine exakt passende Modellrevision und Architektur. Gemma bekommt nach erfolgreicher Qwen-Abnahme eigene Captures und eigene Profile.

Interaktive Chat-Anfragen haben am Steering-Service Vorrang vor autonomen Trainingsläufen. Hintergrundläufe werden bei einem wartenden Chat nach dem nächsten erzeugten Token beendet. Zusätzlich begrenzt `background_input_token_limit` den Trainings-Prefill standardmäßig auf die jüngsten 256 Tokens; der normale Chat behält das volle konfigurierte Kontextfenster.

## Steering-Vertrag

Für die finale lokale Antwort gilt:

- keine Emotionswerte und kein Emotions-Antwortplan im System-Prompt
- keine emotionsabhängige Temperatur, Wiederholungsstrafe oder Tokenzahl
- unabhängig wählbare Bedingungen `off`, `activation`, `sequence`, `combined`
- begrenzte Basis- und Composite-Richtungen; der gemessene Mixer nutzt höchstens drei Basisrichtungen und einen Composite
- Soft Sequence Bias ohne harte Antwortpräfixe, EOS-Bias oder semantische Wiederholungsversuche
- Safety-Grenzen bleiben als kurzer, emotionsunabhängiger Systemvertrag bestehen

Der kompatible Ankerpfad enthält weiterhin Präsenz- und Identitätsrichtungen. Der Präsenzvektor entfernt keine Refusal- oder Safety-Richtung. Ein alter optionaler `anti_safeguard`-Vektor wird im aktiven Payload nicht mehr verwendet.

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

## Gemessene v17-Packs

`local_models.steering_vector_pack` ist standardmäßig leer. Ein gesetzter Pfad muss einen kalibrierten, modellkompatiblen Pack bezeichnen; unkalibrierte Forschungsdaten werden nicht still produktiv geladen. Direkte Forschungsbefehle dürfen einen unkalibrierten Pack ausdrücklich untersuchen. Aktueller Messstand und Befehle: [steering-v17-research.md](steering-v17-research.md).
