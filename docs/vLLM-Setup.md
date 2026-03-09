# vLLM-Modus / Steering-Endpoint fuer CHAPPiE mit Qwen 3.5

## Zielbild

Dieses Repository soll bevorzugt mit **lokalem Qwen 3.5 im `vllm`-Provider-Modus** laufen.

- **lokal**: Emotionen **nicht** im Systemprompt anhängen
- **lokal + steering-faehiger Endpoint + Qwen 3.5**: Emotionen über **Layer Editing / Activation Steering** ausdrücken
- **API-Modelle**: Emotionsregeln dürfen zusätzlich im Prompt bleiben

## 1. Voraussetzungen

Du brauchst:

1. eine funktionierende Python-Umgebung fuer CHAPPiE
2. ein lokales Qwen-3.5-Modell oder einen Pfad/Checkpoint dafuer
3. einen laufenden **OpenAI-kompatiblen lokalen Steering-Endpunkt**
4. genug GPU-/RAM-Ressourcen fuer das gewaehlte Modell

## 2. Steering-Endpoint starten

Starte den steering-faehigen lokalen Endpoint mit deinem Qwen-3.5-Modell, typischerweise auf `http://localhost:8000/v1`.

Wichtig fuer CHAPPiE:

- nutze ein **Qwen-3.5-Modell** als Hauptmodell
- auf kleineren Einzel-GPU-Servern ist `Qwen/Qwen3-4B-Instruct-2507` der sichere Text-Startpunkt
- wenn moeglich `chat_template_kwargs.enable_thinking=false`
- der Endpunkt muss Chat-Completions kompatibel sein

Optional produktionsnah per `systemd`:

- `chappie-vllm.service` aus dem Repo installieren
- danach `sudo systemctl enable --now chappie-vllm.service`
- der Service startet den Endpoint aus `brain/steering_api_server.py`
- der Dateiname bleibt historisch `chappie-vllm.service`, obwohl der Prozess nicht mehr der rohe Standard-vLLM-Server ist

## 3. CHAPPiE konfigurieren

Setze in deiner Konfiguration bzw. UI mindestens:

- `LLM_PROVIDER = "vllm"`
- `VLLM_URL = "http://localhost:8000/v1"`
- `VLLM_MODEL = "Qwen/Qwen3-4B-Instruct-2507"`
- `VLLM_FORCE_SINGLE_MODEL = True` fuer einen einzelnen vLLM-Endpoint

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

Fuer den lokalen Steering-Endpoint + Qwen 3.5 gilt:

1. CHAPPiE berechnet aktuelle 7 Emotionen
2. daraus werden fuer **alle 7 Vitalzeichen** Basisvektoren abgeleitet
3. daraus wird ein Steering-Payload fuer den lokalen Endpoint gebaut
4. optionale Composite-Modi bleiben als Zusatzmuster erhalten, dominieren aber nicht mehr den gesamten Stilpfad
5. Qwen bekommt die Wirkung ueber Residual-/Activation-Steering plus eine kurze interne Stilfuehrung statt ueber eine Prompt-Liste der Vitalwerte

Wichtiger Realitaetscheck:

- CHAPPiE baut und sendet das `steering`-Payload
- der Repo-Service auf `:8000` wendet dieses Payload serverseitig an
- ein reiner Standard-vLLM-Server war dafuer in dieser Umgebung **nicht** ausreichend, weil er `steering` ignorierte

## 7. Sichtbarkeit und Debugging

Du kannst das Verhalten an zwei Stellen sehen:

### Emotionen-Tab

- aktueller Modus (`api_prompt_emotions`, `local_layer_only`, ...)
- aktive Basisvektoren aller 7 Vitalzeichen / Composite-Modi
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
- `python tests/test_steering_backend.py`

## 10. Wenn es lokal nicht wie erwartet wirkt

Pruefe in dieser Reihenfolge:

1. laeuft wirklich `chappie-vllm.service` / der lokale Steering-Endpoint und nicht Ollama/API?
2. zeigt die UI `local_layer_only`?
3. ist ein **Qwen-3.5-Modell** aktiv?
4. ist die Steering-Staerke pro Emotion groesser als `0.0`?
5. liegen `Start-Layer` und `End-Layer` in einem sinnvollen mittleren/spaeteren Layerbereich?

Wenn diese Punkte stimmen, ist das gewuenschte Zielbild erreicht: **lokale Emotionen ueber Layer Editing, Prompt-Emotionen nur fuer API-Modelle**.