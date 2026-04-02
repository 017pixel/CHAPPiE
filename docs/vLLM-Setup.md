# vLLM-Modus und Steering-Endpoint fuer CHAPPiE

## Zielbild

CHAPPiE soll bevorzugt mit lokalem Qwen-3.5 im `vllm`-Modus laufen.

- lokal: Emotionen ueber Steering-Payload und Layer-Editing (Activation Steering)
- API-Modelle: Prompt-Regeln nur als Fallback

## 1. Voraussetzungen

Du brauchst:

1. eine funktionierende Python-Umgebung
2. ein lokales Qwen-3.5-Modell oder einen passenden Checkpoint
3. einen OpenAI-kompatiblen lokalen Steering-Endpoint
4. genug GPU- oder RAM-Ressourcen fuer das gewaehlte Modell

## 2. Steering-Endpoint starten

Typischerweise auf `http://localhost:8000/v1`.

Wichtige Punkte:

- `Qwen/Qwen3.5-4B` ist der bevorzugte Default
- `Qwen/Qwen3.5-9B` ist die naechste Stufe
- `Qwen/Qwen3.5-27B` ist fuer staerkere GPUs
- `chappie-vllm.service` startet den steering-faehigen Server aus `brain/steering_api_server.py`
- ein roher Standard-vLLM-Server reicht fuer CHAPPiEs Steering-Payload in dieser Umgebung nicht

## 3. CHAPPiE konfigurieren

Mindestens setzen:

- `LLM_PROVIDER = "vllm"`
- `VLLM_URL = "http://localhost:8000/v1"`
- `VLLM_MODEL = "Qwen/Qwen3.5-4B"`
- `VLLM_FORCE_SINGLE_MODEL = True`

Optional:

- `INTENT_PROCESSOR_MODEL_VLLM`
- `QUERY_EXTRACTION_VLLM_MODEL`

Relevante Dateien:

- `config/config.py`
- `config/secrets_example.py`
- `docs/local-models.md`

## 4. Runtime pruefen

Im neuen Webpfad kannst du ueber Settings, Debug und Visualizer kontrollieren:

- aktiven Provider
- Modell und Endpoint
- Emotions- und Intensitaetsdaten
- Steering-nahe Debug-Ausgaben

## 5. Layer Editing (Activation Steering)

Der Kern von CHAPPiEs emotionalem Steering ist die direkte Manipulation der Hidden States:

### Wie es funktioniert

1. **VAD-Mapping**: Jede der 7 Emotionen (happiness, sadness, frustration, trust, curiosity, motivation, energy) wird auf Valence, Arousal, Dominance abgebildet
2. **Alpha-Berechnung**:
   - Toter Bereich: 44-56 → kein Steering
   - Leichte Abweichung: 56-74 → Alpha steigt sigmoid-ahnlich
   - Extreme: 74-100 → Alpha maximal, mit Boost-Faktor
3. **Composite Modes**: Bestimmte Emotions-Kombinationen aktivieren komplexe Modi:
   - `crashout`: frustration ≥ 72 + trust ≤ 38 → kurz angebunden, konfrontativ
   - `guarded`: trust ≤ 26 + frustration ≥ 50 → misstrauisch, distanziert
   - `melancholic`: sadness ≥ 62 + energy ≤ 46 → bedrueckt, schwer
   - `warm`: happiness ≥ 70 + trust ≥ 60 → herzlich, offen, weich
   - `charged`: energy ≥ 72 + motivation ≥ 68 + curiosity ≥ 66 → hochaktiv, getrieben
4. **Layer-Profile**: Modell-spezifische Layer-Bereiche werden manipuliert:
   - Qwen3.5-4B (32 Layers): Personality L8-24, Emotion L10-26, Reasoning L14-31 (nicht manipuliert)
   - Qwen2.5-32B (64 Layers): Personality L16-48, Emotion L20-44, Reasoning L32-56 (nicht manipuliert)
5. **Forward Pre-Hook**: Waehrend der Generierung wird pro Layer ein Hook registriert:
   ```
   hidden_state[layer] += alpha * steering_vector
   ```

### Vector-Resolver

Der `ActivationVectorResolver` baut Steering-Vektoren durch kontrastive Analyse:
- Anchor-Texte (z.B. "Mir geht es super" vs. "Ich bin ruhig und klar") werden durch das Modell gejagt
- Hidden-State-Differenzen pro Layer werden extrahiert und normalisiert
- Ergebnisse werden im Steering-Cache persistiert (`data/steering_cache/`)

### Was bewusst nicht passieren soll

Im lokalen Hauptpfad sollen Emotionen nicht primaer ueber lange Prompt-Zusatztexte erzwungen werden.

Das gilt fuer:

- App-API
- Frontend
- CLI
- Training

## 6. Schnelle Verifikation

- `python tests/test_local_first_runtime.py`
- `python tests/test_debug_monitor_data.py`
- `python tests/test_vllm_response_handling.py`
- `python tests/test_steering_backend.py`
- `python tests/test_brain_pipeline_steering_integration.py`

## 7. Wenn es lokal nicht wie erwartet wirkt

Pruefe in dieser Reihenfolge:

1. laeuft wirklich `chappie-vllm.service`?
2. zeigt die Runtime `vllm` als aktiven Provider?
3. ist ein Qwen-3.5-Modell aktiv?
4. stimmen URL, Modell und Steering-nahe Runtime-Settings?
5. ist der Steering-Cache vorhanden (`data/steering_cache/`)?

## Weiterfuehrend

- [Lokale Modelle](local-models.md)
- [Deployment](deployment.md)
- [Testing](testing.md)
- [Architektur](architecture.md)
