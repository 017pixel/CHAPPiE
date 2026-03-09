# vLLM-Setup fuer CHAPPiE mit Qwen 3.5 und Layer Editing

## Zielbild

Dieses Repository soll bevorzugt mit **lokalem vLLM + Qwen 3.5** laufen.

- **lokal**: Emotionen **nicht** im Systemprompt anhängen
- **lokal + vLLM + Qwen 3.5**: Emotionen über **Layer Editing / Activation Steering** ausdrücken
- **API-Modelle**: Emotionsregeln dürfen zusätzlich im Prompt bleiben

## 1. Voraussetzungen

Du brauchst:

1. eine funktionierende Python-Umgebung fuer CHAPPiE
2. ein lokales Qwen-3.5-Modell oder einen Pfad/Checkpoint dafuer
3. einen laufenden **OpenAI-kompatiblen vLLM-Endpunkt**
4. genug GPU-/RAM-Ressourcen fuer das gewaehlte Modell

## 2. vLLM starten

Starte vLLM mit deinem Qwen-3.5-Modell und einem OpenAI-kompatiblen Endpoint, typischerweise auf `http://localhost:8000/v1`.

Wichtig fuer CHAPPiE:

- nutze ein **Qwen-3.5-Modell** als Hauptmodell
- wenn moeglich `chat_template_kwargs.enable_thinking=false`
- der Endpunkt muss Chat-Completions kompatibel sein

## 3. CHAPPiE konfigurieren

Setze in deiner Konfiguration bzw. UI mindestens:

- `LLM_PROVIDER = "vllm"`
- `VLLM_URL = "http://localhost:8000/v1"`
- `VLLM_MODEL = "Qwen/..."`

Optional sinnvoll:

- `INTENT_PROCESSOR_MODEL_VLLM` fuer Step-1 / Intent
- `QUERY_EXTRACTION_VLLM_MODEL` fuer kleinere Memory-Aufgaben

Relevante Dateien:

- `config/config.py`
- `config/secrets_example.py`
- `web_infrastructure/settings_ui.py`

## 4. Streamlit-UI richtig setzen

Im Settings-Overlay:

1. Provider auf **vLLM** stellen
2. URL und Modell fuer vLLM setzen
3. im Tab **Emotionen** die 7 Emotionswerte pruefen
4. darunter im Bereich **Layer Editing pro Emotion** pro Emotion anpassen:
   - `Steering-Staerke`
   - `Start-Layer`
   - `End-Layer`

Damit steuerst du direkt, wie stark und in welchem Layerbereich lokale Emotionen wirken.

## 5. Was jetzt bewusst NICHT passieren soll

Bei lokalem Betrieb sollen **keine Emotions-Vitalwerte** im Systemprompt landen.

Das gilt jetzt fuer lokale Laufzeitpfade wie:

- Web-UI
- CLI
- Training-Loop

Nur bei **API-Modellen** bleiben Emotionsregeln im Prompt aktiv.

## 6. Wie die Emotionen transportiert werden

Fuer lokales vLLM + Qwen 3.5 gilt:

1. CHAPPiE berechnet aktuelle 7 Emotionen
2. daraus werden Basisvektoren und Composite-Modi abgeleitet
3. daraus wird ein Steering-Payload fuer vLLM gebaut
4. Qwen bekommt die Wirkung ueber Layer-/Activation-Steering statt ueber eine Prompt-Liste der Vitalwerte

## 7. Sichtbarkeit und Debugging

Du kannst das Verhalten an zwei Stellen sehen:

### Emotionen-Tab

- aktueller Modus (`api_prompt_emotions`, `local_layer_only`, ...)
- aktive Vektoren / Composite-Modi
- editierbare Basis-Konfiguration pro Emotion

### Debug Mode / Brain Monitor

- rohe Emotions-Deltas
- angewandte geglaettete Deltas
- Gruende aus Intent/Homeostasis
- aktive Layer-Vektoren und Basis-Konfiguration

## 8. Warum die Emotionsspruenge jetzt sanfter sind

Starke Einzelturn-Spruenge werden geglaettet und pro Emotion gedeckelt.

Ziel:

- keine unplausiblen Abstuerze wie z. B. `100 -> 15` in einem Schritt
- trotzdem sichtbare Reaktion auf neue Ereignisse
- besser lesbare Entwicklung im Debug-Monitor

## 9. Schnelle Verifikation

Ohne `pytest` kannst du direkt ausfuehren:

- `python tests/test_local_first_runtime.py`
- `python tests/test_emotion_transition_rules.py`
- `python tests/test_debug_monitor_data.py`
- `python tests/test_vllm_response_handling.py`

## 10. Wenn es lokal nicht wie erwartet wirkt

Pruefe in dieser Reihenfolge:

1. laeuft wirklich `vLLM` und nicht Ollama/API?
2. zeigt die UI `local_layer_only`?
3. ist ein **Qwen-3.5-Modell** aktiv?
4. ist die Steering-Staerke pro Emotion groesser als `0.0`?
5. liegen `Start-Layer` und `End-Layer` in einem sinnvollen mittleren/spaeteren Layerbereich?

Wenn diese Punkte stimmen, ist das gewuenschte Zielbild erreicht: **lokale Emotionen ueber Layer Editing, Prompt-Emotionen nur fuer API-Modelle**.