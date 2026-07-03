# Gemma 4 Installation

## Übersicht

Zwei Varianten:

| Modell | VRAM | Geschwindigkeit | Kontext |
|---|---|---|---|
| `google/gemma-4-E4B-it` | ~9 GB (FP16) | ~7-10 tk/s | 32K+ |
| `google/gemma-4-26B-A4B-it` | ~15 GB (NF4) | ~3-5 tk/s | max 8K |

---

## 1. Voraussetzungen

```bash
pip install --upgrade transformers>=5.0.0 huggingface-hub
```

HuggingFace-Lizenz akzeptieren:

1. https://huggingface.co/google/gemma-4-E4B-it besuchen
2. "Agree and access repository" klicken (einmalig pro Account)
3. Bei 26B: https://huggingface.co/google/gemma-4-26B-A4B-it

Dann lokal einloggen:

```bash
huggingface-cli login
# Token eingeben (Settings → Access Tokens)
```

---

## 2. Modell herunterladen (einmalig)

```bash
# Gemma 4 E4B (4B, FP16, ~9 GB)
huggingface-cli download google/gemma-4-E4B-it

# Gemma 4 26B-A4B (MoE, NF4-faehig, ~13 GB)
huggingface-cli download google/gemma-4-26B-A4B-it
```

Die Modelle landen im HF-Cache (`~/.cache/huggingface/hub/`).

---

## 3. Steering-Server starten

### 3a. Gemma 4 E4B (4B dense, FP16, T4-tauglich)

```bash
python -m brain.steering_api_server \
  --model google/gemma-4-E4B-it \
  --context-length 8192
```

### 3b. Gemma 4 26B-A4B (MoE, NF4, 16 GB VRAM)

```bash
python -m brain.steering_api_server \
  --model google/gemma-4-26B-A4B-it \
  --context-length 4096 \
  --quantize
```

- `--quantize` aktiviert NF4 (4-Bit). Automatisch erzwungen bei 26B auf GPUs unter 48 GB.
- `--context-length 4096` schuetzt vor OOM auf T4 (16 GB). Auf GPUs mit mehr VRAM kann `8192` oder hoeher gesetzt werden.

### 3c. Server-Status pruefen

```bash
curl http://localhost:8000/health
# {"status":"ok","model":"google/gemma-4-26B-A4B-it","restart_status":"ready"}
```

---

## 4. CHAPPiE konfigurieren

In `CHAPPIE_CONFIG.json`:

### Gemma 4 E4B (empfohlen fuer T4)

```json
{
  "local_models": {
    "llm_provider": "vllm",
    "vllm_model": "google/gemma-4-E4B-it",
    "vllm_url": "http://localhost:8000/v1",
    "vllm_force_single_model": true
  },
  "steering": {
    "enable_steering": true,
    "steering_provider": "vllm",
    "steering_model": "google/gemma-4-E4B-it",
    "steering_quantize": false,
    "steering_context_length": 8192
  },
  "generation": {
    "temperature": 1.0,
    "top_p": 0.95,
    "top_k": 64,
    "use_model_defaults": true
  }
}
```

### Gemma 4 26B-A4B (NF4, nur mit Quantisierung)

```json
{
  "local_models": {
    "llm_provider": "vllm",
    "vllm_model": "google/gemma-4-26B-A4B-it",
    "vllm_url": "http://localhost:8000/v1",
    "vllm_force_single_model": true
  },
  "steering": {
    "enable_steering": true,
    "steering_provider": "vllm",
    "steering_model": "google/gemma-4-26B-A4B-it",
    "steering_quantize": true,
    "steering_context_length": 4096
  },
  "generation": {
    "temperature": 1.0,
    "top_p": 0.95,
    "top_k": 64,
    "use_model_defaults": true
  }
}
```

**Wichtig:** `steering_quantize: true` bei 26B-A4B, sonst OOM.

---

## 5. Alternative: Modellwechsel ueber CLI

Ohne Config-Edit, nur lokaler Modus:

```bash
python chappie_brain_cli.py --model gemma4-e4b

# Oder waehrend der Session:
# /model gemma4-e4b
# /model gemma4-26b
# /model qwen
```

---

## 6. Schnelltest

```bash
# Steering-Server antwortet?
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "google/gemma-4-E4B-it",
    "messages": [{"role":"user","content":"Hallo"}],
    "max_tokens": 50
  }'

# CHAPPiE-eigener Gemma-Test (kein Modell noetig)
python tests/test_gemma4_integration.py
```

---

## 7. Systemd-Service (Produktiv)

`/etc/systemd/system/chappie-vllm.service` anpassen:

### Gemma 4 E4B

```ini
Environment="CHAPPIE_STEERING_MODEL=google/gemma-4-E4B-it"
ExecStart=/usr/bin/python3 -m brain.steering_api_server \
  --model google/gemma-4-E4B-it \
  --context-length 8192
```

### Gemma 4 26B-A4B

```ini
Environment="CHAPPIE_STEERING_MODEL=google/gemma-4-26B-A4B-it"
ExecStart=/usr/bin/python3 -m brain.steering_api_server \
  --model google/gemma-4-26B-A4B-it \
  --context-length 4096 \
  --quantize
```

Danach:

```bash
sudo systemctl daemon-reload
sudo systemctl restart chappie-vllm.service
```

---

## 8. Zurueck zu Qwen

```bash
# Steering-Server
python -m brain.steering_api_server --model Qwen/Qwen3.5-4B

# Config: vllm_model zurueck auf "Qwen/Qwen3.5-4B" setzen
# Oder CLI: /model qwen
```
