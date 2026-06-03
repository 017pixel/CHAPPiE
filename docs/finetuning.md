# WhatsApp Fine-Tuning in CHAPPiE

## Übersicht

CHAPPiE unterstützt jetzt **LoRA-basiertes Fine-Tuning** von Qwen3.5-4B basierend auf WhatsApp-Chat-Exporten. Das Training erzeugt kleine LoRA-Adapter (~30 MB), die auf das Base Model aufgesetzt werden — das Base Model selbst bleibt unverändert.

## Komponenten

| Komponente | Datei | Zweck |
|---|---|---|
| **Trainer** | `brain/whatsapp_finetune_trainer.py` | Qwen3.5 LoRA Training mit Unsloth |
| **Manager** | `brain/models_manager.py` | CLI + API fuer Modellverwaltung |
| **API** | `api/routers/finetune.py` | REST-Endpunkte |
| **UI** | `frontend/src/pages/models-page.tsx` | Frontend zur Modellauswahl |
| **Service** | `deploy/chappie-finetune@.service` | systemd-Template fuer Training |

## Ablauf

### 1. Vorbereitung

1. WhatsApp-Chat exportieren (Ohne Medien) als `.zip`
2. ZIP-Datei nach `data/finetune_chats/` kopieren

### 2. Training vorbereiten

Via API:
```bash
curl -X POST http://localhost:8010/finetune/prepare \
  -H "Content-Type: application/json" \
  -d '{
    "chat_zips": ["data/finetune_chats/WhatsApp Chat - Benjamin.zip"],
    "target_person": "Benjamin",
    "epochs": 1,
    "lora_r": 16,
    "bf16": true
  }'
```

Via CLI Manager:
```bash
python brain/models_manager.py
# → Option 2: WhatsApp Fine-Tuning starten
```

### 3. Training starten

```bash
# API
curl -X POST http://localhost:8010/finetune/models/{name}/train

# CLI Manager
# → Option 2 → Modell auswaehlen → Training starten
```

**Wichtig**: Das Training stoppt automatisch den `chappie-vllm.service`, um alle GPU-Ressourcen freizugeben.

### 4. Modell wechseln

```bash
# Auf Base Model zurueck
python brain/models_manager.py --switch base

# Auf Fine-Tuned Modell
python brain/models_manager.py --switch benjamin_2026-06-03
```

Oder via Frontend auf `/models`.

### 5. Training stoppen

```bash
curl -X POST http://localhost:8010/finetune/models/{name}/stop
```

## Technische Details

### Training
- **Base Model**: `Qwen/Qwen3.5-4B` (via Unsloth)
- **Methode**: LoRA (Low-Rank Adaptation), rank=16, alpha=32
- **Quantisierung**: bf16 (empfohlen) oder QLoRA 4-bit Fallback
- **VRAM**: ~10-12 GB fuer bf16 LoRA auf 4B Modell
- **Anti-Forgetting**: 15% Bactrian-X deutsche Instruktionen gemischt

### Steering-Kompatibilität
- Base Model bleibt **frozen**
- LoRA-Adapter wird via `PeftModel.from_pretrained()` geladen
- Forward Pre-Hooks fuer Activation Steering funktionieren weiterhin
- Steering-Vektoren bleiben gültig (basierend auf frozen Base Model)

### Datenformat
- WhatsApp Regex: `\[DD.MM.YY, HH:MM:SS\] Sender: Text`
- Qwen Chat-Template mit Thinking aktiviert
- Single-Turn und Multi-Turn Paare aus Chats extrahiert

## API Endpunkte

| Methode | Pfad | Beschreibung |
|---|---|---|
| GET | `/finetune/models` | Liste aller Modelle |
| GET | `/finetune/models/{name}/status` | Trainings-Status |
| DELETE | `/finetune/models/{name}` | Modell löschen |
| POST | `/finetune/models/{name}/train` | Training starten |
| POST | `/finetune/models/{name}/stop` | Training stoppen |
| PUT | `/finetune/active` | Aktiven Adapter setzen |
| GET | `/finetune/active` | Aktiven Adapter abfragen |
| POST | `/finetune/chats/scan` | WhatsApp-ZIPs scannen |
| POST | `/finetune/chats/analyze/{zip}` | Chat analysieren |
| POST | `/finetune/prepare` | Training vorbereiten |

## Fehlerbehebung

### Training startet nicht
1. Prüfe ob `unsloth` installiert: `pip list | grep unsloth`
2. Prüfe GPU-Verfügbarkeit: `nvidia-smi`
3. Prüfe ob genug VRAM frei ist (Steering-Server muss gestoppt sein)

### Adapter lädt nicht
1. Prüfe ob `adapter_config.json` existiert
2. Prüfe Pfad in `CHAPPIE_CONFIG.json` → `finetune.active_adapter`
3. Prüfe systemd Drop-In: `/etc/systemd/system/chappie-vllm.service.d/adapter.conf`

### Steering funktioniert nicht nach Wechsel
1. `systemctl status chappie-vllm.service` prüfen
2. Health-Check: `curl http://localhost:8000/health`
3. Bei Fehler: `journalctl -u chappie-vllm.service -f`

## Weiterführend

- [Architecture](architecture.md)
- [Local Models](local-models.md)
- [Testing](testing.md)
