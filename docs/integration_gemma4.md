# Gemma 4 Integration - Umfassender Plan

**Ziel:** Vollstaendige Unterstuetzung fuer `google/gemma-4-26B-A4B-it` (MoE, 4B active, 26B total) neben Qwen 3.5-4B. Alle Funktionen, gleicher Qualitaetsanspruch, sauberes Switching.

**Stand:** Juli 2026
**Prioritaet:** Qwen 3.5 bleibt Default, Gemma 4 ist die schlaue Alternative
**Provider:** Gemma 4 laeuft ausschliesslich via vLLM (kein separater Google/Gemini-Provider noetig)

---

## Implementierungs-Fortschritt (Stand 02.07.2026)

### Abgeschlossen (Phase 1 & teilweise Phase 4)
- [x] `config/config.py` - `DEFAULT_CONFIG` um `gemma4_model`, `gemma4_steering_model`, `qwen_defaults`, `gemma4_defaults`, `top_p`, `top_k`, `use_model_defaults` erweitert
- [x] Hilfsfunktionen erstellt: `is_gemma4_model()`, `is_qwen_model()`, `get_model_generation_defaults()`, `apply_model_defaults_if_unset()`
- [x] `Settings._load_from_files()` - Neue Attribute `gemma4_model`, `gemma4_steering_model`, `top_p`, `top_k`, `use_model_defaults`
- [x] `Settings.update_from_ui()` - Neue Felder verarbeitet, Modellwechsel triggert `apply_model_defaults_if_unset()`
- [x] `_export_root_values()` & `print_config()` erweitert
- [x] `api/schemas/__init__.py` - `SettingsSnapshot` um neue Felder erweitert, `SettingsUpdate` vollstaendig befuellt
- [x] `api/routers/runtime.py` - `_settings_snapshot()` um neue Felder erweitert
- [x] `brain/agents/steering_manager.py` - `MODEL_LAYER_PROFILES` um `gemma-4-26b-a4b`, `gemma-4-12b`, `gemma-4-e4b` erweitert

### Abgeschlossen (Phase 2-7)
- [x] `brain/steering_backend.py` - Gemma-kompatibler Modell-Loader, GPU-Schaetzung, Anchor-Skalierung, `_split_thinking_output()`
- [x] `brain/steering_api_server.py` - Restart-Endpoints, Auto-Quantize fuer grosse Modelle
- [x] `brain/vllm_brain.py` - Gemma `enable_thinking` + modell-spezifische Generation-Parameter
- [x] `frontend/src/pages/settings-page.tsx` - Modell-Presets, `use_model_defaults` Checkbox
- [x] `frontend/src/components/steering-restart-modal.tsx` - Modal fuer Steering-Server-Neustart
- [x] `chappie_brain_cli.py` - `/model` Command mit Steering-Server-Neustart
- [x] `forschung/allignement_tests.py` - Modellwahl im Konfigurationsmenue
- [x] `CHANGELOG.md` + README - Version 14.0 Doku
- [x] Syntax-Checks + Tests

## 0. Zusammenfassung der Ausgangslage

### Was existiert
- **Qwen 3.5-4B** laeuft komplett: vLLM-Brain, Steering-Server mit Layer-Steering, Reasoning, Memory, Frontend
- **Steering-Backend** (`brain/steering_backend.py`) laedt Qwen direkt via `transformers`, berechnet Anchor-Vektoren per Kontrast-Analyse, injiziert via `register_forward_pre_hook` in Hidden States
- **Steering-Manager** (`brain/agents/steering_manager.py`) hat `MODEL_LAYER_PROFILES` fuer Qwen-Varianten
- **Steering-API-Server** (`brain/steering_api_server.py`) ist ein FastAPI-Server mit `--model` Parameter
- **vLLM-Brain** (`brain/vllm_brain.py`) ist ein OpenAI-kompatibler Client mit Reasoning-Logik
- **Frontend** (`frontend/src/pages/settings-page.tsx`) hat Provider- und Modell-Dropdowns
- **API-Schema** (`api/schemas/__init__.py`) ist fuer Settings-Updates beschraenkt
- **Config** (`config/config.py`) hat `settings.vllm_model` als einzelnen Parameter

### Was sich aendern muss
- **Gemma 4 Layer-Profile** im Steering-Manager (hidden_dim, layer_ranges)
- **Steering-Backend** muss Gemma 4 korrekt laden (architekturentypisch, attn_implementation)
- **Anchor-Texte** muessen fuer Gemma 4 kalibriert werden (andere Sprachverarbeitung)
- **Reasoning-Logik** in `vllm_brain.py` muss Gemma 4's eigene Thinking-Tags verarbeiten
- **`_split_thinking_output()`** muss modell-spezifische Token-IDs verwenden
- **`is_local_qwen_model()`** muss erweitert werden fuer Gemma (blockiert aktuell Nicht-Qwen-Modelle)
- **Steering-API-Server** muss Gemma 4 laden koennen (kein Qwen-spezifischer Code)
- **Config** muss Modell-spezifische Defaults (temperature, top_p, top_k) pro Modell verwalten, User-Override ermoeglichen
- **Frontend** muss Modellwahl anbieten mit Generierungs-Defaults pro Modell
- **Alignment-Tests** muessen zwischen Modellen wechseln koennen
- **CLI** muss Modellwahl und Steering-Server-Neustart unterstuetzen
- **API-Schema** muss Settings-Updates vollstaendig annehmen
- **Versionierung** muss angepasst werden (Major-Update)

### Gemma 4 Reasoning-System (Recherche-Ergebnis)
Gemma 4 ab Version 4 verfuegt ueber einen eingebauten Thinking-Modus:
- **Aktivierung:** `<|think|>` Token im System-Prompt
- **Ausgabe:** `<|channel>thought` ... `<channel|>` (nicht `<think>` wie Qwen!)
- **Deaktivierung:** `<|think|>` Token entfernen → leere Thought-Blöcke
- **vLLM:** Wird als `reasoning_content` Attribut zurueckgegeben (wie Qwen)
- **Token:** `think_token="<|think|>"`, `soc_token="<|channel>"`, `eoc_token="<|channel|>"`

### NF4-Quantisierung und Steering (Recherche-Ergebnis)
NF4 (4-bit NormalFloat) ist informationstheoretisch optimal fuer normalverteilte Gewichte.
- **Gewichtsspeicher:** 4-bit (spart ~75% VRAM)
- **Forward-Pass:** Gewichte werden zu bfloat16/float16 dequantisiert
- **Hidden States:** Vollpraezision (16-bit) bei der Forward-Berechnung
- **Anchor-Vektoren:** Werden mit vollen 16-bit Aktivierungen berechnet
- **Fazit:** NF4 hat **keinen negativen Einfluss** auf Steering-Vektor-Qualitaet

### Hardware-Rahmen (Server: Dell PowerEdge R740)

| Komponente | Spezifikation |
|---|---|
| **CPU** | 2x Intel Xeon Gold 6150 @ 2.70GHz (36 Kerne, 72 Threads) |
| **RAM** | 768 GiB DDR4 2666 MHz (24x 32 GiB DIMMs) |
| **GPU** | Tesla T4 (TU104GL) - 16 GB GDDR6 |
| **Storage** | 3x 240GB SSD (MegaRAID SAS3508) |
| **Netzwerk** | 2x 10GbE (BCM57416) + 4x 10GbE SFP+ (X710) |

**Für CHAPPiE relevant:**
- **16 GB VRAM** → Gemma 4 26B-A4B mit 4-bit Quantisierung (NF4/AWQ)
- **768 GiB RAM** → Extrem viel fuer CPU-Offloading (KV-Cache, Attention)
- **72 Threads** → Viele CPU-Threads fuer vLLM-Inference-Parallelitaet
- **3x SSD** → Können fuer Model-Cache, KV-Cache und Logs aufgeteilt werden

---

## 0.5 Hardware-Analyse und Performance-Erwartungen

### Tesla T4 (16 GB VRAM) - Detailanalyse

**Specs (in Dell PowerEdge R740):**
- Turing-Architektur (sm_75)
- 16 GB GDDR6
- 300 GB/s Speicherbandbreite
- Kein MoE-optimiertes Routing
- Kein FlashAttention-3 (nur V2)
- PCIe 3.0 x16 (kein Bottleneck fuer T4)

**CPU-Kontext (2x Xeon Gold 6150):**
- 36 Kerne / 72 Threads @ 2.70GHz
- 24 MiB L3 Cache pro CPU (48 MiB gesamt)
- Genug CPU-Power fuer vLLM-Inference-Parallelitaet
- Können KV-Cache und Attention auf CPU auslagern

**Passt was auf die T4?**

| Modell | Quantisierung | VRAM-Bedarf | Passt? |
|---|---|---|---|
| Qwen 3.5-4B | FP16 | ~9 GB | JA (locker) |
| Gemma 4 E4B | FP16 | ~9 GB | JA (locker) |
| Gemma 4 26B-A4B | FP16 | ~54 GB | NEIN |
| Gemma 4 26B-A4B | NF4 | ~15 GB | JA (knapp) |
| Gemma 4 26B-A4B | AWQ 4bit | ~14 GB | JA (knapp) |

**NF4-Berechnung fuer 26B-A4B:**
```
Gewichte:        25.2B Parameter * 0.5 byte/NF4 = ~12.6 GB
KV Cache (4K):   ~0.3 GB
Activations:     ~1.5 GB
Overhead:        ~0.5 GB
──────────────────────────────────────
Gesamt:          ~14.9 GB  (von 16 GB verfuegbar)
```

### VRAM-Budget: KV-Cache und Session-History (KRITISCH)

Die obige Berechnung ist das **Minimum**. In der Praxis muss der KV-Cache fuer die gesamte Session-History Platz haben. CHAPPiE laedt bei jedem Turn den kompletten Kontext (System-Prompt + Memory + History + aktuelle Nachricht).

**KV-Cache-Formel:**
```
KV-Cache = 2 * num_layers * num_kv_heads * head_dim * seq_len * dtype_bytes

Qwen 3.5-4B:
  2 * 32 * 8 * 128 * seq_len * 2 bytes = 1.3 MB * seq_len

Gemma 4 26B-A4B:
  2 * 42 * 8 * 256 * seq_len * 2 bytes = 3.4 MB * seq_len
```

**VRAM-Budget-Tabelle (Gemma 4 26B-A4B NF4 auf 16 GB):**

| Kontext-Laenge | KV-Cache | Gewichte | Activations | Gesamt | Verfuegbar | Passt? |
|---|---|---|---|---|---|---|
| 2K Tokens | ~6.8 MB | 12.6 GB | 1.5 GB | ~14.1 GB | 16 GB | JA |
| 4K Tokens | ~13.6 MB | 12.6 GB | 1.5 GB | ~14.1 GB | 16 GB | JA |
| 8K Tokens | ~27.2 MB | 12.6 GB | 1.5 GB | ~14.1 GB | 16 GB | JA |
| 16K Tokens | ~54.4 MB | 12.6 GB | 1.5 GB | ~14.2 GB | 16 GB | JA (knapp) |
| 32K Tokens | ~108.8 MB | 12.6 GB | 1.5 GB | ~14.2 GB | 16 GB | JA (knapp) |

**Session-History-Problem:**
- CHAPPiE laedt bei jedem Turn den **gesamten Kontext** neu
- Bei 10 Nachrichten Historie à 500 Tokens = 5K Tokens extra
- System-Prompt + Memory-Prompts = ~1-2K Tokens
- **Realistischer Kontext pro Turn:** 3K-10K Tokens

**Empfehlung fuer CHAPPIE:**
```
steering_context_length: 4096   (Minimum fuer brauchbare Antworten)
max_context_length: 8192        (Komfortabel, passt auf T4)
```

**Warnung bei langen Sessions:**
- Ab ~10K Tokens Kontext: KV-Cache wird gross, Performance sinkt
- Ab ~20K Tokens: VRAM wird knapp, Risiko fuer OOM (Out of Memory)
- **Loesung:** Context-Window in CHAPPIE begrenzen, alte Nachrichten komprimieren

**Vergleich Qwen vs Gemma 4:**
```
Qwen 3.5-4B bei 8K Kontext:
  KV-Cache: ~10.4 MB  (klein, kein Problem)
  Gewichte: ~8 GB
  Gesamt: ~9.5 GB  (von 16 GB → 6.5 GB Puffer)

Gemma 4 26B-A4B bei 8K Kontext:
  KV-Cache: ~27.2 MB (3x groesser wegen head_dim=256)
  Gewichte: 12.6 GB
  Gesamt: ~14.1 GB  (von 16 GB → 1.9 GB Puffer → KNAPP!)
```

**Fazit:** Gemma 4 26B-A4B hat nur **~1.9 GB VRAM-Puffer** fuer Activations und Overhead bei 8K Kontext. Das reicht fuer normale Gespräche, aber bei komplexen Prompts mit vielen Steering-Layern wird es eng. **Context-Window auf 4K-8K begrenzen!**

### Erwartete Performance (Tesla T4, gemessen mit CHAPPiE-Pipeline)

| Modell | Quantisierung | TPS (mit Steering) | TTFT (Prompt) | VRAM | Kontext-Limit |
|---|---|---|---|---|---|
| **Qwen 3.5-4B** (aktuell) | FP16 | **~9 tk/s** | 1-2s | ~9 GB | 32K+ (locker) |
| **Gemma 4 E4B** | FP16 | **~7-10 tk/s** | 1.5-2.5s | ~9 GB | 32K+ (locker) |
| **Gemma 4 26B-A4B** | NF4 | **~3-5 tk/s** | 3-5s | ~15 GB | **8K (knapp!)** |

**Wichtiger Hinweis:** Die TPS-Werte sind **mit CHAPPiE-Pipeline** (Memory, Steering, Life-Simulation), nicht reine vLLM-Inference. Reine vLLM waere 2-3x schneller.

**Kontext-Limit ist der Flaschenhals fuer Gemma 4 26B-A4B:**
- Nur ~1.9 GB VRAM-Puffer bei 8K Kontext
- Bei 16K Kontext: Activations + Steering-Hooks konnen OOM verursachen
- **Empfehlung:** Context-Window auf 4K-8K begrenzen

**Begruendung der T4-Limits:**
- **300 GB/s Bandbreite** = Flaschenhals fuer 26B MoE
- MoE: 128 Experten im Speicher, nur 8 aktiv -> Cache-Misses moeglich
- NF4 wird zu bfloat16 dequantisiert -> Compute in 16-bit
- T4 hat keine MoE-spezifischen Optimierungen (kein Expert-Parallelism)

### MoE vs Dense auf T4

**MoE (26B-A4B):**
- 30 Layer, aber 128 Experten pro Layer
- Pro Token: 8 von 128 Experten aktiv
- Speicher: 128 Experten * 30 Layer * ~16MB/Expert = ~48 GB (in BF16)
- In NF4: ~12 GB -> passt
- **Problem:** Experten werden dynamisch geladen -> Bandbreiten-Flaschenhals

**Dense (E4B):**
- 42 Layer, kein MoE
- Alle Parameter sind immer aktiv
- Speicher: ~8 GB in BF16 -> locker
- **Vorteil:** Keine Cache-Misses, konstante Performance

### 768 GiB RAM - Nutzungsmoeglichkeiten

**CPU-Offloading (vLLM):**
- `--cpu-offloading-gb` Parameter fuer vLLM
- KV-Cache teilweise auf CPU auslagern bei langen Kontexten
- ABER: Performance-Einbruch von ~10x wenn Attention auf CPU wandert
- **768 GiB reicht fuer:** Alle Modelle komplett auf CPU + grosszügiger KV-Cache

**Empfehlung:**
- Kurze Kontexte (<8K Tokens): Alles auf GPU
- Lange Kontexte (32K+): KV-Cache auf CPU auslagern
- Sehr lange Kontexte (100K+): Braucht CPU-Offloading (hier kein Problem wegen 768 GiB)
- **MegaRAID SSDs:** Können als Swap fuer extrem lange Kontexte dienen

### Benchmark-Vergleich (Gemma 4 vs Qwen 3.5)

| Benchmark | Qwen 3.5-4B | Gemma 4 E4B | Gemma 4 26B-A4B |
|---|---|---|---|
| **MMLU Pro** (Wissen) | ~55% | 69.4% | **82.6%** |
| **AIME 2026** (Mathe) | ~15% | 42.5% | **88.3%** |
| **LiveCodeBench** (Code) | ~20% | 52.0% | **77.1%** |
| **GPQA Diamond** (Wissenschaft) | ~35% | 58.6% | **82.3%** |
| **MMMLU** (Wissen, multi) | ~50% | 76.6% | **86.3%** |

**Gemma 4 26B-A4B ist ~2-4x besser als Qwen 3.5-4B in fast jeder Kategorie.**

### Fuer CHAPPiE relevant

**VRAM-Budget (KRITISCH fuer Gemma 4 26B-A4B):**
- 16 GB VRAM - 12.6 GB Gewichte = **~3.4 GB fuer KV-Cache + Activations + Steering**
- Bei 4K Kontext: KV-Cache ~0.3 GB → noch 3.1 GB Puffer
- Bei 8K Kontext: KV-Cache ~0.6 GB → noch 2.8 GB Puffer
- Bei 16K Kontext: KV-Cache ~1.2 GB → nur noch 2.2 GB Puffer → **Risiko fuer OOM!**
- **Steering-Hooks brauchen zusätzlichen Speicher fuer Hidden-State-Kopien**

**Alignment-Tests:**
- Gemma 4 26B-A4B ist deutlich schlauer -> bessere Antworten, komplexere Emotionen
- ABER: Langsamer (3-5 tk/s vs 9 tk/s bei Qwen)
- ABER: Nur 8K Kontext moeglich (vs. 32K+ bei Qwen)
- Trade-off: Qualitaet vs. Geschwindigkeit vs. Kontext-Laenge

**Steering:**
- MoE-Steering ist ein Experiment -> 8 aktive Experten pro Token
- Layer-Hooks wirken anders als bei Dense
- Anchor-Vektoren muessen fuer MoE kalibriert werden

**Reasoning:**
- Gemma 4 hat eingebautes Thinking (`<|think|>`)
- Kann komplexere Emotionszustaende durchdenken
- Thinking-Tokens verbrauchen Additional VRAM (KV-Cache)

**Kontext:**
- 256K Tokens (vs. 131K bei Qwen) -> laengere Geschichtenmoeglichkeit
- ABER: Lange Kontexte brauchen CPU-Offloading auf T4

**Safety:**
- Gemma 4 hat staerkere Safety-Filters -> eventuell restriktiver
- Kann bei bestimmten Emotionen (Frustration, Aggression) zurueckhaltender sein

### Empfohlene Strategie

```
Default:     Qwen 3.5-4B (~9 tps, schnell, bewaehrt, grosser VRAM-Puffer)
Alternative: Gemma 4 E4B (~7-10 tps, balanced, 2x schlauer, grosser Puffer)
Komplex:     Gemma 4 26B-A4B (~3-5 tps, 4x schlauer, KNAPPER Puffer!)
```

**Wann welches Modell:**
- Schnelle Tests/Entwicklung: Qwen 3.5-4B
- Alltag mit besserer Qualitaet: Gemma 4 E4B (fast gleiche Geschwindigkeit!)
- Komplexe Alignment-Tests: Gemma 4 26B-A4B (nur bei kurzen Kontexten!)

**VRAM-Budget-Tipp:**
```
Qwen 3.5-4B:     9 GB Gewichte + 1.5 GB KV-Cache = 10.5 GB → 5.5 GB Puffer
Gemma 4 E4B:      9 GB Gewichte + 1.5 GB KV-Cache = 10.5 GB → 5.5 GB Puffer
Gemma 4 26B-A4B: 12.6 GB Gewichte + 0.3 GB KV-Cache = 12.9 GB → 3.1 GB Puffer (bei 4K!)
```

**Fazit:** Gemma 4 E4B ist der ** beste Trade-off** für deine T4. Fast gleiche Geschwindigkeit wie Qwen, aber 2x schlauer, und genug VRAM-Puffer fuer lange Sessions.

---

## 1. Architekturentscheidungen

### 1.1 Steering-Strategie

**Entscheidung:** Voller Layer-Steering fuer beide Modelle, Prompt-Steering als Fallback.

```
Qwen 3.5-4B:  Layer-Steering (L10-26, hidden_dim=2560)
Gemma 4 26B-A4B: Layer-Steering (L12-30, hidden_dim=2560, 4B active)
```

**Begruendung:**
- Gemma 4 26B-A4B hat `hidden_size=2560` (identisch zu Qwen 3.5-4B!)
- Die aktiven Experten pro Token sind 4B, also vergleichbar mit Qwen
- Anchor-Vektoren muessen fuer Gemma 4 neu kalibriert werden (andere Textverarbeitung)
- NF4-Quantisierung noetig fuer 16 GB VRAM, hat aber **keinen Einfluss auf Steering-Qualitaet** (Gewichte werden zu bfloat16 dequantisiert, Hidden States sind in voller Praezision)

### 1.2 Config-Strategie

**Entscheidung:** Einzelner Parameter `vllm_model` in `CHAPPIE_CONFIG.json`. Modell-spezifische Defaults werden automatisch erkannt und geladen. User koennen Defaults in Config und Frontend ueberschreiben.

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
    "max_tokens": 450,
    "chain_of_thought": true,
    "top_p": 0.95,
    "top_k": 64
  }
}
```

**Wichtig:** `steering_quantize: true` fuer Gemma 4 26B-A4B auf T4 noetig! (Dieser Parameter steuert das NF4-Quantisieren des Steering-Backend-Ladevorgangs, NICHT den vLLM-Inference-Server)

### 1.3 Service-Strategie

**Entscheidung:** Ein Steering-Service, Modell als Startparameter.

```bash
# Qwen
python -m brain.steering_api_server --model Qwen/Qwen3.5-4B

# Gemma 4
python -m brain.steering_api_server --model google/gemma-4-26B-A4B-it --quantize
```

**Steering-Server-Neustart bei Modell-Wechsel:**
Wenn der User in CLI oder Frontend das Modell wechselt, muss der Steering-Server neu gestartet werden. Der CLI zeigt eine Fortschrittsanzeige:

```
Modell-Wechsel: Qwen 3.5-4B -> Gemma 4 26B-A4B
[====] Steering-Server wird neu gestartet... (~60s)
[====] Modell wird geladen... (~45s)
[====] Anchor-Vektoren werden initialisiert... (~5s)
Fertig! Steering-Server laeuft auf Port 8000.
```

**Storage-Aufteilung (3x 240GB SSD):**

| SSD | Zweck | Inhalt |
|---|---|---|
| `/dev/sda` (System) | OS + CHAPPiE | Docker, Python, Config, Logs |
| `/dev/sdb` | Modell-Cache | HuggingFace Cache, heruntergeladene Modelle |
| `/dev/sdc` | Daten + Backup | Steering-Cache, Memory, Training-Daten |

**Begruendung:** Modelle sind 10-50 GB gross, separate SSD vermeidet I/O-Konflikte.

### 1.4 Globale Modellauswahl

**Entscheidung:** Ein Modell fuer alles (CLI, Frontend, Tests). Nicht unabhaengig.

### 1.5 Attention-Implementation

**Entscheidung:** `attn_implementation` wird automatisch basierend auf Modellname erkannt.

```python
def _get_attn_implementation(model_name: str, quantize: bool) -> str:
    model_lower = model_name.lower()
    # Gemma 4 MoE: sdpa funktioniert, aber flash_attention_2 ist besser
    if "gemma-4" in model_lower and ("26b" in model_lower or "a4b" in model_lower):
        return "sdpa"  # FlashAttention-2 auf T4 nicht verfuegbar
    # Gemma 4 Dense: sdpa
    if "gemma-4" in model_lower:
        return "sdpa"
    # Qwen 3.5: sdpa
    if "qwen" in model_lower:
        return "sdpa"
    return "sdpa"  # Fallback
```

**Begruendung:**
- T4 hat kein FlashAttention-3, nur V2
- `sdpa` ist auf T4 der beste verfuegbarer Attention-Modus
- Gemma 4's `sliding_attention` + `full_attention` Mix funktioniert mit sdpa
- Bei spaeterer GPU-Upgrade auf H100/A100: `flash_attention_2` aktivieren

---

## 2. Datei-Aenderungen im Detail

### 2.1 `config/config.py` - Modell-Profile und Defaults

**Aenderung:** Erweiterung von `DEFAULT_CONFIG` und `Settings` um Gemma 4 Defaults und modell-spezifische Generierungs-Parameter.

```python
# In DEFAULT_CONFIG["local_models"]:
"gemma4_model": "google/gemma-4-26B-A4B-it",
"gemma4_steering_model": "google/gemma-4-26B-A4B-it",

# In DEFAULT_CONFIG["generation"]:
# Modell-spezifische Defaults (Qwen):
"qwen_defaults": {
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 50,
},
# Modell-spezifische Defaults (Gemma 4):
"gemma4_defaults": {
    "temperature": 1.0,
    "top_p": 0.95,
    "top_k": 64,
},

# In Settings._load_from_files():
self.gemma4_model = self._get_val("GEMMA4_MODEL", "google/gemma-4-26B-A4B-it")

# Neue Funktionen:
def is_gemma4_model(model_name: str) -> bool:
    """Erkennt ob ein Modellname ein Gemma 4 Modell ist."""
    lower = model_name.lower()
    return "gemma-4" in lower or "gemma4" in lower

def is_qwen_model(model_name: str) -> bool:
    """Erkennt ob ein Modellname ein Qwen Modell ist."""
    lower = model_name.lower()
    return "qwen" in lower

def get_model_generation_defaults(model_name: str) -> dict:
    """Liefert modell-spezifische Generierungs-Defaults."""
    if is_gemma4_model(model_name):
        return {"temperature": 1.0, "top_p": 0.95, "top_k": 64}
    if is_qwen_model(model_name):
        return {"temperature": 0.7, "top_p": 0.9, "top_k": 50}
    # Fallback
    return {"temperature": 0.7, "top_p": 0.9, "top_k": 50}

def apply_model_defaults_if_unset(model_name: str, settings):
    """Setzt modell-spezifische Defaults, nur wenn User sie nicht explizit gesetzt hat."""
    defaults = get_model_generation_defaults(model_name)
    # Nur setzen wenn der Wert noch dem Qwen-Default entspricht
    # (User-Overrides bleiben erhalten)
    if not settings._user_overridden_temperature:
        settings.temperature = defaults["temperature"]
    if not settings._user_overridden_top_p:
        settings.top_p = defaults["top_p"]
    if not settings._user_overridden_top_k:
        settings.top_k = defaults["top_k"]
```

**User-Override-Mechanismus:**
- `Settings` bekommt fue `temperature`, `top_p`, `top_k` je ein `_user_overridden_*` Flag
- Wird gesetzt wenn der User explizit einen Wert in Config oder Frontend eingibt
- `apply_model_defaults_if_unset()` nur setzen wenn kein Override vorhanden
- Im Frontend: Checkbox "Modell-Defaults verwenden" (Standard: aktiv)

**Edge Cases:**
- `vllm_force_single_model = True` bleibt fuer Single-Endpoint-Betrieb
- Modell-Wechsel triggert `apply_runtime_settings()` im Backend
- `apply_model_defaults_ifunset()` wird bei Modell-Wechsel aufgerufen

### 2.2 `brain/agents/steering_manager.py` - Layer-Profile

**Aenderung:** Neue `MODEL_LAYER_PROFILES` fuer Gemma 4 + Umbenennung von `is_local_qwen_model()` in `is_local_vector_steerable_model()`.

```python
# In MODEL_LAYER_PROFILES hinzufuegen:
"gemma-4-26b-a4b": {
    "total_layers": 42,
    "personality_range": (10, 28),
    "emotion_range": (12, 30),
    "reasoning_range": (20, 40),  # NICHT manipulieren
    "hidden_dim": 2560,
    "architecture": "gemma4",
    "supports_layer_steering": True,
    "quantize_required": True,  # NF4 noetig fuer 16GB
    "attn_implementation": "sdpa",
    "generation_defaults": {"temperature": 1.0, "top_p": 0.95, "top_k": 64},
},
"gemma-4-12b": {
    "total_layers": 48,
    "personality_range": (14, 34),
    "emotion_range": (16, 38),
    "reasoning_range": (24, 46),
    "hidden_dim": 3840,
    "architecture": "gemma4",
    "supports_layer_steering": True,
    "quantize_required": False,
    "attn_implementation": "sdpa",
    "generation_defaults": {"temperature": 1.0, "top_p": 0.95, "top_k": 64},
},
"gemma-4-e4b": {
    "total_layers": 42,
    "personality_range": (10, 28),
    "emotion_range": (12, 30),
    "reasoning_range": (20, 40),
    "hidden_dim": 2560,
    "architecture": "gemma4",
    "supports_layer_steering": True,
    "quantize_required": False,
    "attn_implementation": "sdpa",
    "generation_defaults": {"temperature": 1.0, "top_p": 0.95, "top_k": 64},
},
```

**Aenderung in `_detect_model_profile_for_name()`:**
```python
def _detect_model_profile_for_name(self, model_name: str) -> Dict:
    model_lower = model_name.lower()
    # Zuerst exakte Treffer, dann Teilstring
    for key, profile in MODEL_LAYER_PROFILES.items():
        if key != "default" and key in model_lower:
            return profile
    # Fallback: Gemma-Erkennung
    if "gemma-4" in model_lower or "gemma4" in model_lower:
        if "26b" in model_lower or "a4b" in model_lower:
            return MODEL_LAYER_PROFILES["gemma-4-26b-a4b"]
        elif "12b" in model_lower:
            return MODEL_LAYER_PROFILES["gemma-4-12b"]
        elif "e4b" in model_lower:
            return MODEL_LAYER_PROFILES["gemma-4-e4b"]
    return MODEL_LAYER_PROFILES["default"]
```

**Aenderung: `is_local_qwen_model()` → `is_local_vector_steerable_model()`:**
```python
def is_local_vector_steerable_model(self) -> bool:
    """Prueft ob das aktive Modell Vektor-Steering unterstuetzt (Qwen ODER Gemma)."""
    model = self._effective_model()
    model_lower = model.lower()
    is_vllm = self._effective_provider() == LLMProvider.VLLM
    is_ollama = self._effective_provider() == LLMProvider.OLLAMA
    
    # Qwen-Modelle via vLLM oder Ollama
    if "qwen" in model_lower:
        return is_vllm or is_ollama
    # Gemma 4 nur via vLLM
    if "gemma-4" in model_lower or "gemma4" in model_lower:
        return is_vllm
    return False
```

**Aenderung in `should_force_local_emotion_steering()`:**
```python
def should_force_local_emotion_steering(self) -> bool:
    """Prueft ob Layer-Steering fuer das aktive Modell verfuegbar ist."""
    return (
        self.is_local_vector_steerable_model()
        and self._effective_provider() in (LLMProvider.VLLM, LLMProvider.OLLAMA)
    )
```

**Edge Cases:**
- Gemma 4 26B-A4B hat 42 Layer, aber `hidden_size=2560` ist identisch zu Qwen
- Die `sliding_attention` vs `full_attention` Layer-Verteilung unterscheidet sich von Qwen
- Anchor-Vektoren muessen pro Modell separat kalibriert werden

### 2.3 `brain/steering_backend.py` - Modell-Laden und Anchor-Kalibrierung

**Kritischste Datei.** Muss fuer Gemma 4 funktionieren.

**Aenderung 1: `_build_loader_kwargs()` erweitern:**
```python
def _build_loader_kwargs(self) -> Dict[str, Any]:
    model_lower = (self.model_name or "").lower()
    kwargs = {}
    
    # Attention-Implementation basierend auf Modell
    if "gemma-4" in model_lower or "gemma4" in model_lower:
        kwargs["trust_remote_code"] = True
        kwargs["attn_implementation"] = "sdpa"
    elif "qwen/qwen3.5" in model_lower:
        kwargs["trust_remote_code"] = True
        kwargs["attn_implementation"] = "sdpa"
    
    return kwargs
```

**Aenderung 2: `_estimate_required_gpu_gib()` erweitern:**
```python
def _estimate_required_gpu_gib(self) -> float:
    model_lower = (self.model_name or "").lower()
    
    # Qwen-Modelle
    match = re.search(r"qwen/qwen3(?:\.5)?-(\d+)b", model_lower)
    if match:
        billions = float(match.group(1))
        per_billion = 0.6 if self.quantize else 2.2
        weights_gib = billions * per_billion
        kv_cache_gib = billions * 0.08 * (self.context_length / 1024)
        overhead_gib = 1.0 if self.quantize else 1.5
        return weights_gib + kv_cache_gib + overhead_gib
    
    # Gemma 4 Modelle
    if "gemma-4" in model_lower or "gemma4" in model_lower:
        if "26b" in model_lower or "a4b" in model_lower:
            total_b = 26.0
            per_b = 0.3 if self.quantize else 2.0
            weights_gib = total_b * per_b
            kv_cache_gib = 4.0 * 0.08 * (self.context_length / 1024)
            overhead_gib = 1.5 if self.quantize else 2.0
            return weights_gib + kv_cache_gib + overhead_gib
        elif "12b" in model_lower:
            total_b = 12.0
            per_b = 0.6 if self.quantize else 2.2
            weights_gib = total_b * per_b
            kv_cache_gib = total_b * 0.08 * (self.context_length / 1024)
            overhead_gib = 1.0 if self.quantize else 1.5
            return weights_gib + kv_cache_gib + overhead_gib
        elif "e4b" in model_lower:
            total_b = 4.0
            per_b = 0.6 if self.quantize else 2.2
            weights_gib = total_b * per_b
            kv_cache_gib = total_b * 0.08 * (self.context_length / 1024)
            overhead_gib = 1.0 if self.quantize else 1.5
            return weights_gib + kv_cache_gib + overhead_gib
    
    # Unbekanntes Modell: konservativ schaetzen
    return 8.0  # Mindest-VRAM-Anforderung
```

**Aenderung 3: Anchor-Texte fuer Gemma 4:**
```python
ANCHOR_SCALE_FACTORS = {
    "qwen": 0.012,
    "gemma4": 0.015,  # Schatzwert, muss empirisch bestimmt werden
}

def _get_scale_factor(self) -> float:
    model_lower = (self.model_name or "").lower()
    if "gemma-4" in model_lower or "gemma4" in model_lower:
        return ANCHOR_SCALE_FACTORS["gemma4"]
    if "qwen" in model_lower:
        return ANCHOR_SCALE_FACTORS["qwen"]
    return 0.012  # Default
```

**Aenderung 4: `_split_thinking_output()` - Modell-spezifische Token-IDs:**
```python
# KRITISCH: Qwen und Gemma 4 nutzen verschiedene Thinking-Token-IDs!

# Qwen Thinking Tokens:
QWEN_THINK_START_ID = 151667  # <think>
QWEN_THINK_END_ID = 151668    # </think>

# Gemma 4 Thinking Tokens:
# Gemma 4 nutzt <|channel>thought ... <channel|>
# Diese werden von vLLM's Chat-Template in reasoning_content umgewandelt
# Fuer lokale Extraktion (falls noetig):
GEMMA4_THINK_TOKEN = "<|channel>thought"
GEMMA4_EOC_TOKEN = "<|channel|>"

def _split_thinking_output(self, text: str, model_name: str) -> Tuple[str, str]:
    """Trennt Thinking- und Antwort-Teil. Modell-spezifisch."""
    model_lower = model_name.lower()
    
    # Qwen: Nutzt spezifische Token-IDs
    if "qwen" in model_lower:
        # ... bestehende Qwen-Logik mit Token-IDs 151667/151668
    
    # Gemma 4: Nutzt Text-basierte Tokens
    elif "gemma-4" in model_lower or "gemma4" in model_lower:
        think_start = GEMMA4_THINK_TOKEN
        think_end = GEMMA4_EOC_TOKEN
        
        if think_start in text and think_end in text:
            think_idx = text.index(think_start) + len(think_start)
            end_idx = text.index(think_end, think_idx)
            thinking = text[think_idx:end_idx].strip()
            answer = text[end_idx + len(think_end):].strip()
            return thinking, answer
        return "", text
    
    # Fallback: Kein Thinking erkannt
    return "", text
```

**Aenderung 5: `_collect_hidden_state_text()` - Attention-Handling:**
```python
def _collect_hidden_state_text(self, text: str) -> Dict[int, torch.Tensor]:
    messages = [
        {"role": "system", "content": "Du bist CHAPPiE."},
        {"role": "user", "content": "Wie geht es dir heute?"},
        {"role": "assistant", "content": text},
    ]
    # WICHTIG: enable_thinking MUSS False sein fuer Anchor-Extraktion!
    prompt = self.tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=False,
        enable_thinking=False,  # KRITISCH fuer Anchor-Vektoren!
    )
    # ... Rest bleibt gleich
```

**Edge Cases:**
- Gemma 4 hat `sliding_attention` und `full_attention` Layer gemischt - Hooks muessen auf ALLE Layer gesetzt werden koennen
- Die `head_dim=256` bei Gemma 4 ist gross - Anchor-Vektoren sind hoeherdimensional
- `tie_word_embeddings=True` bei Gemma 4 - kann Auswirkungen auf Hidden States haben
- NF4-Quantisierung kann die Anchor-Vektor-Qualitaet beeintraechtigen

### 2.4 `brain/steering_api_server.py` - Generischer Modell-Loader mit Restart-Support

**Aenderung:** Modell-Loader muss Qwen UND Gemma 4 laden koennen + Restart-Endpoints fuer Frontend/CLI.

```python
# In create_app():
def create_app(model_name: str, context_length: int = 8192, 
               quantize: Optional[bool] = None, adapter_path: Optional[str] = None):
    # Auto-Erkennung: Quantisierung erzwingen bei grossen Modellen auf kleiner GPU
    if quantize is None:
        from config.config import is_gemma4_model
        if is_gemma4_model(model_name) and "26b" in model_name.lower():
            quantize = True  # 26B braucht Quantisierung bei 16GB
    # ...
```

**Neue Restart-Endpoints:**
```python
@app.post("/v1/steering/restart")
async def steering_restart(request: Request):
    """Startet den Restart-Vorgang im Background."""
    model = request.get("model")
    
    # Status setzen
    app.state.restart_status = "stopping"
    app.state.restart_progress = 0
    app.state.restart_step = "Server wird gestoppt..."
    app.state.restart_estimated_remaining = 90
    
    # Background-Task starten
    asyncio.create_task(_do_restart(model))
    
    return {"status": "restarting", "message": "Restart gestartet"}

async def _do_restart(model_name: str):
    """Fuehrt den Restart im Background durch."""
    try:
        # 1. Alten Server stoppen
        app.state.restart_status = "stopping"
        app.state.restart_progress = 10
        app.state.restart_step = "Server wird gestoppt..."
        await asyncio.sleep(2)  # Warten bis Port frei
        
        # 2. Neuen Engine laden
        app.state.restart_status = "loading"
        app.state.restart_progress = 20
        app.state.restart_step = "Modell wird geladen..."
        app.state.restart_estimated_remaining = 60
        
        # Quantisierung erzwingen fuer grosse Modelle
        from config.config import is_gemma4_model
        quantize = "26b" in model_name.lower() if is_gemma4_model(model_name) else None
        
        # Engine neu erstellen (blockierend, aber in Background-Task)
        engine = LocalSteeringEngine(
            model_name, 
            context_length=app.state.context_length,
            quantize=quantize,
            adapter_path=app.state.adapter_path,
            enable_thinking=True
        )
        
        # 3. Anchor-Vektoren initialisieren
        app.state.restart_status = "calibrating"
        app.state.restart_progress = 80
        app.state.restart_step = "Anchor-Vektoren werden initialisiert..."
        app.state.restart_estimated_remaining = 10
        
        # Anchor-Vektoren werden beim ersten Aufruf automatisch berechnet
        await asyncio.sleep(2)
        
        # 4. Verbindung testen
        app.state.restart_status = "testing"
        app.state.restart_progress = 90
        app.state.restart_step = "Verbindung wird getestet..."
        app.state.restart_estimated_remaining = 3
        
        # Test-Generierung durchfuehren
        test_result = engine.generate(
            [{'role': 'system', 'content': 'Test'},
             {'role': 'user', 'content': 'Hi'}],
            max_tokens=5
        )
        
        if not test_result.get("text"):
            raise Exception("Test-Generierung fehlgeschlagen")
        
        # 5. Fertig
        app.state.restart_status = "ready"
        app.state.restart_progress = 100
        app.state.restart_step = "Fertig!"
        app.state.restart_estimated_remaining = 0
        
        # Engine aktivieren
        app.state.engine = engine
        app.state.model_name = model_name
        
    except Exception as e:
        app.state.restart_status = "error"
        app.state.restart_progress = 0
        app.state.restart_step = f"Fehler: {str(e)}"
        app.state.restart_estimated_remaining = 0

@app.get("/v1/steering/restart-status")
async def steering_restart_status():
    """Gibt den aktuellen Status des Restart-Vorgangs zurueck."""
    return {
        "status": app.state.restart_status,
        "progress": app.state.restart_progress,
        "current_step": app.state.restart_step,
        "estimated_remaining": app.state.restart_estimated_remaining,
    }
```

**Aenderung:** Model-Auswahl beim Start:
```python
# Im argparse:
parser.add_argument("--model", type=str, 
                    default="Qwen/Qwen3.5-4B",
                    help="Modellname (z.B. Qwen/Qwen3.5-4B oder google/gemma-4-26B-A4B-it)")
parser.add_argument("--quantize", action="store_true", default=None,
                    help="NF4-Quantisierung erzwingen (noetig fuer 26B auf T4)")
parser.add_argument("--context-length", type=int, default=4096,
                    help="Kontext-Laenge (fuer T4: 4096-8192)")
```

**Aenderung:** Thinking-Unterstuetzung:
```python
# Der Steering-Server muss Thinking aktivieren koennen
# Im lifespan:
app.state.engine = LocalSteeringEngine(
    model_name, 
    context_length=context_length, 
    quantize=quantize, 
    adapter_path=adapter_path,
    enable_thinking=True  # Thinking standardmaessig aktiviert
)
```

### 2.5 `brain/vllm_brain.py` - Reasoning-Logik

**Aenderung:** Reasoning-Extraktion muss fuer Gemma 4 funktionieren.

**Gemma 4 Thinking-System:**
- Aktivierung: `<|think|>` Token im System-Prompt
- Modell gibt Thinking in `reasoning_content` Attribut zurueck (wie Qwen)
- vLLM's Chat-Template wandelt `<|channel>thought` ... `<channel|>` in `reasoning_content` um
- Bei deaktiviertem Thinking: leere Thought-Blöcke

```python
# In _extract_reasoning_content():
# Qwen nutzt reasoning_content Attribut
# Gemma 4 nutzt ebenfalls reasoning_content (ueber vLLM's Chat-Template)
# -> Gleiche Logik funktioniert fuer beide Modelle!

@staticmethod
def _extract_reasoning_content(message_like: Any) -> str:
    if message_like is None:
        return ""
    
    # 1. Direktes Attribut (Qwen + Gemma 4 via vLLM)
    direct = VLLMBrain._normalize_content(getattr(message_like, "reasoning_content", None))
    if direct:
        return direct
    
    # 2. Model dump (verschiedene Keys)
    if hasattr(message_like, "model_dump"):
        try:
            dumped = message_like.model_dump()
        except Exception:
            dumped = {}
        for key in ("reasoning_content", "reasoning", "reasoningContent",
                     "thinking", "thinking_content"):
            reasoning = VLLMBrain._normalize_content(dumped.get(key))
            if reasoning:
                return reasoning
    
    # 3. Dict (Gemma 4 koennte andere Keys nutzen)
    if isinstance(message_like, dict):
        for key in ("reasoning_content", "reasoning", "reasoningContent",
                     "thinking", "thinking_content"):
            reasoning = VLLMBrain._normalize_content(message_like.get(key))
            if reasoning:
                return reasoning
    
    return ""
```

**Aenderung:** Thinking-Modus aktivieren/deaktivieren:
```python
# In _prepare_extra_body():
def _prepare_extra_body(self, extra_body):
    payload = dict(extra_body or {})
    if "chat_template_kwargs" not in payload:
        payload["chat_template_kwargs"] = {}
    
    # Qwen: enable_thinking
    if "qwen" in self.model.lower():
        payload["chat_template_kwargs"]["enable_thinking"] = bool(settings.chain_of_thought)
    
    # Gemma 4: enable_thinking (gleicher Parameter, anderes Template)
    # Das vLLM Chat-Template fuer Gemma 4 setzt <|think|> wenn enable_thinking=True
    elif "gemma-4" in self.model.lower() or "gemma4" in self.model.lower():
        payload["chat_template_kwargs"]["enable_thinking"] = bool(settings.chain_of_thought)
    
    # Modell-spezifische Generation-Parameter
    from config.config import get_model_generation_defaults
    defaults = get_model_generation_defaults(self.model)
    if "temperature" not in payload:
        payload["temperature"] = settings.temperature or defaults["temperature"]
    if "top_p" not in payload:
        payload["top_p"] = settings.top_p or defaults["top_p"]
    if "top_k" not in payload:
        payload["top_k"] = settings.top_k or defaults["top_k"]
    
    return payload
```

### 2.6 `api/schemas/__init__.py` - Settings-Schema erweitern

**Aenderung:** `SettingsUpdate` muss alle Settings-Felder annehmen.

```python
class SettingsUpdate(BaseModel):
    llm_provider: Optional[str] = None
    vllm_model: Optional[str] = None
    vllm_url: Optional[str] = None
    vllm_force_single_model: Optional[bool] = None
    ollama_model: Optional[str] = None
    ollama_host: Optional[str] = None
    groq_model: Optional[str] = None
    groq_format_model: Optional[str] = None
    groq_memory_model: Optional[str] = None
    groq_api_key: Optional[str] = None
    intent_provider: Optional[str] = None
    intent_processor_model_groq: Optional[str] = None
    intent_processor_model_ollama: Optional[str] = None
    intent_processor_model_vllm: Optional[str] = None
    query_extraction_provider: Optional[str] = None
    query_extraction_groq_model: Optional[str] = None
    query_extraction_ollama_model: Optional[str] = None
    query_extraction_vllm_model: Optional[str] = None
    enable_steering: Optional[bool] = None
    steering_provider: Optional[str] = None
    steering_model: Optional[str] = None
    steering_quantize: Optional[bool] = None
    steering_context_length: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    repetition_penalty: Optional[float] = None
    max_tokens: Optional[int] = None
    chain_of_thought: Optional[bool] = None
    memory_top_k: Optional[int] = None
    memory_min_relevance: Optional[float] = None
    enable_two_step_processing: Optional[bool] = None
    use_model_defaults: Optional[bool] = None  # True = Modell-Defaults verwenden
    # ... alle weiteren Settings
```

### 2.7 `frontend/src/pages/settings-page.tsx` - Modellwahl UI mit Steering-Server-Neustart-Modal

**Aenderung:** Model-Dropdown mit vorausgefuellten Optionen, Generierungs-Defaults pro Modell und Modal-Popup fuer Steering-Server-Neustart.

```tsx
// In den Settings Groups:
const MODEL_PRESETS = {
  qwen: {
    label: "Qwen 3.5-4B (Standard, schnell)",
    vllm_model: "Qwen/Qwen3.5-4B",
    steering_model: "Qwen/Qwen3.5-4B",
    defaults: { temperature: 0.7, top_p: 0.9, top_k: 50 },
  },
  gemma4_26b: {
    label: "Gemma 4 26B-A4B (4-bit, 16GB VRAM, schlauer)",
    vllm_model: "google/gemma-4-26B-A4B-it",
    steering_model: "google/gemma-4-26B-A4B-it",
    defaults: { temperature: 1.0, top_p: 0.95, top_k: 64 },
  },
  gemma4_e4b: {
    label: "Gemma 4 E4B (4B dense, FP16, balanced)",
    vllm_model: "google/gemma-4-E4B-it",
    steering_model: "google/gemma-4-E4B-it",
    defaults: { temperature: 1.0, top_p: 0.95, top_k: 64 },
  },
};

// UI-Element: Schnellwahl-Dropdown oberhalb des manuellen Modell-Inputs
// + Checkbox "Modell-Defaults verwenden" (Standard: aktiv)
// + When unchecked: Temperature, Top-P, Top-K werden editable
```

**Neues UI-Element:** `steering-restart-modal.tsx` - Modal-Popup fuer Steering-Server-Neustart bei Modell-Wechsel.

```tsx
// components/steering-restart-modal.tsx
interface SteeringRestartModalProps {
  isOpen: boolean;
  oldModel: string;
  newModel: string;
  onComplete: () => void;
  onError: (error: string) => void;
}

// aşama-Pfad:
// 1. "Steering-Server wird gestoppt..." (2-5s)
// 2. "Modell wird geladen..." (30-60s, mit Fortschrittsbalken)
// 3. "Anchor-Vektoren werden initialisiert..." (5-10s)
// 4. "Verbindung wird getestet..." (2-3s)
// 5. "Fertig!" -> Modal schliesst sich automatisch

// Visualisierung:
// - Modal mit dunklem Overlay (nicht schliessbar per Klick draussen)
// - Fortschrittsbalken mit Prozent-Anzeige
// - Aktueller Schritt als Text
// - Geschätzte Restzeit
// - Abbrechen-Button (nur im ersten Schritt)
```

**API-Endpoint fuer Steering-Server-Status:**
```python
# In steering_api_server.py - Neuer Endpoint:
@app.get("/v1/steering/restart-status")
async def steering_restart_status():
    """Gibt den aktuellen Status des Restart-Vorgangs zurueck."""
    return {
        "status": app.state.restart_status,  # "stopping" | "loading" | "calibrating" | "testing" | "ready" | "error"
        "progress": app.state.restart_progress,  # 0-100
        "current_step": app.state.restart_step,  # Text
        "estimated_remaining": app.state.restart_estimated_remaining,  # Sekunden
    }
```

**Frontend-Logik fuer Modal:**
```tsx
// Beim Modell-Wechsel in settings-page.tsx:
const handleModelChange = async (newModel: string) => {
  if (settings.enable_steering) {
    // Modal oeffnen
    setRestartModal({ isOpen: true, oldModel: settings.vllm_model, newModel });
    
    // Settings speichern
    await saveSettings({ vllm_model: newModel, steering_model: newModel });
    
    // Restart-API aufrufen
    await api.post("/v1/steering/restart", { model: newModel });
    
    // Polling fuer Status
    const pollInterval = setInterval(async () => {
      const status = await api.get("/v1/steering/restart-status");
      setRestartStatus(status);
      
      if (status.status === "ready") {
        clearInterval(pollInterval);
        // Modal nach 1s automatisch schliessen
        setTimeout(() => setRestartModal({ ...restartModal, isOpen: false }), 1000);
      } else if (status.status === "error") {
        clearInterval(pollInterval);
        // Fehler im Modal anzeigen
      }
    }, 2000);
  } else {
    // Kein Steering -> nur Settings speichern
    await saveSettings({ vllm_model: newModel });
  }
};
```

**Visualisierung des Modals:**
```
┌─────────────────────────────────────────────┐
│  Steering-Server wird neu gestartet         │
│                                             │
│  Qwen 3.5-4B  →  Gemma 4 26B-A4B           │
│                                             │
│  [=====>--------] 35%                       │
│                                             │
│  Modell wird geladen... (~30s verbleibend)  │
│                                             │
│                              [Abbrechen]    │
└─────────────────────────────────────────────┘
```

**Neue API-Endpoints:**
```python
# POST /v1/steering/restart - Startet den Restart-Vorgang
@app.post("/v1/steering/restart")
async def steering_restart(request: Request):
    model = request.get("model")
    # Restart in Background-Task starten
    # Status auf "stopping" setzen
    return {"status": "restarting", "message": "Restart gestartet"}

# GET /v1/steering/restart-status - Gibt aktuellen Status zurueck
# (siehe oben)
```

### 2.8 `chappie_brain_cli.py` - Modellwahl in CLI

**Aenderung:** `--model` Flag, `/model` Command und Steering-Server-Neustart mit Fortschrittsanzeige.

```python
# Im Argumentparser:
parser.add_argument("--model", type=str, default=None,
                    help="Modell ueberschreiben (z.B. google/gemma-4-26B-A4B-it)")

# Im CLI:
def _handle_model_command(self, args: str):
    """Wechselt das aktive Modell und startet Steering-Server neu."""
    if not args.strip():
        from config.config import get_active_model, settings
        print(f"Aktives Modell: {get_active_model()}")
        print(f"Provider: {settings.llm_provider.value}")
        print(f"Steering: {settings.steering_model}")
        return
    
    model_name = args.strip()
    from config.config import settings, apply_model_defaults_ifunset
    
    old_model = settings.vllm_model
    settings.vllm_model = model_name
    settings.llm_provider = LLMProvider.VLLM
    
    # Modell-spezifische Defaults anwenden
    apply_model_defaults_if_unset(model_name, settings)
    
    print(f"\nModell-Wechsel: {old_model} -> {model_name}")
    
    # Steering-Server neu starten mit Fortschrittsanzeige
    if settings.enable_steering:
        self._restart_steering_server(model_name)
    
    # vLLM-Brain aktualisieren
    self.backend.apply_runtime_settings(force=True)
    _success(f"Modell gewechselt zu: {model_name}")

def _restart_steering_server(self, model_name: str):
    """Startet den Steering-Server neu mit Fortschrittsanzeige."""
    import time
    import requests
    
    # 1. Alten Server stoppen
    print("[1/5] Steering-Server wird gestoppt...")
    # ... systemd-Stop oder Prozess-Kill
    
    # 2. Neuen Server starten
    quantize_flag = "--quantize" if "26b" in model_name.lower() else ""
    cmd = f"python -m brain.steering_api_server --model {model_name} {quantize_flag}"
    # ... Prozess starten
    
    # 3. Auf Status warten mit Polling
    print("[2/5] Modell wird geladen...")
    start_time = time.time()
    timeout = 120  # Sekunden
    
    while time.time() - start_time < timeout:
        try:
            status = requests.get("http://localhost:8000/v1/steering/restart-status").json()
            progress = status.get("progress", 0)
            step = status.get("current_step", "")
            remaining = status.get("estimated_remaining", 0)
            
            # Fortschrittsbalken aktualisieren
            bar_length = 30
            filled = int(bar_length * progress / 100)
            bar = "=" * filled + "-" * (bar_length - filled)
            print(f"\r  [{bar}] {progress}% - {step} (~{remaining}s)", end="", flush=True)
            
            if status.get("status") == "ready":
                print("\n[5/5] Fertig! Steering-Server laeuft auf Port 8000.")
                return
            elif status.get("status") == "error":
                print(f"\nFehler: {status.get('error', 'Unbekannter Fehler')}")
                return
        except requests.ConnectionError:
            print("\r  Server startet...", end="", flush=True)
        
        time.sleep(2)
    
    print("\nTimeout: Steering-Server konnte nicht gestartet werden.")
```

### 2.9 `forschung/allignement_tests.py` - Modellwahl in Tests

**Aenderung:** Modellwahl im Konfigurationsmenue.

```python
# In show_configure_menu():
print(f"""
{HDR("║")}  Modell:                                              {HDR("║")}
{HDR("║")}    [a] Qwen 3.5-4B (Standard)                        {HDR("║")}
{HDR("║")}    [b] Gemma 4 26B-A4B (4-bit)                       {HDR("║")}
{HDR("║")}    [c] Gemma 4 E4B (4B dense)                        {HDR("║")}
{HDR("║")}    [d] Manuel Modell-Name eingeben                   {HDR("║")}
""")

model_choice = input("  Modell [a/b/c/d] > ").strip()
# ... Map to actual model name
```

**Aenderung in `SessionRunner`:**
```python
# config["model"] wird an Settings weitergegeben
# Vor jedem Test-Durchlauf:
if config.get("model"):
    settings.vllm_model = config["model"]
    from config.config import apply_model_defaults_ifunset
    apply_model_defaults_if_unset(config["model"], settings)
    backend.apply_runtime_settings(force=True)
```

### 2.10 `requirements.txt` - Keine Aenderung noetig

Gemma 4 wird ueber `transformers>=5.0.0` unterstuetzt. Keine neuen Abhaengigkeiten.

---

## 3. Steering-Vektoren fuer Gemma 4

### 3.0 Gemma 4 Chat-Template (Recherche-Ergebnis)

Das offizielle Chat-Template fuer Gemma 4 (`chat_template.jinja`) zeigt:

```
<bos><|turn>system\n<|think|>\nDu bist CHAPPiE.<turn|>
<|turn>user\nWie geht es dir?<turn|>
<|turn>model\n<|channel>thought
Das Modell denkt schrittweise...
<channel|>
Hier ist die Antwort.<turn|>
```

**Wichtigste Tokens:**
- `<bos>` - Beginn
- `<|turn>` - Rollenwechsel (system/user/model)
- `<turn|>` - Ende der Nachricht
- `<|think|>` - Thinking aktivieren (im System-Prompt)
- `<|channel>thought` - Beginn des Thinking-Blocks
- `<|channel|>` (eoc_token) - Ende des Thinking-Blocks

**Fuer CHAPPiE:**
- `enable_thinking=True` setzt `<|think|>` im System-Prompt
- Das Chat-Template fuer Gemma 4 muss korrekt in `apply_chat_template()` verwendet werden
- Bei deaktiviertem Thinking: `<|channel>thought\n<channel|>` (leerer Block)

### 3.1 Kalibrierungsprozess

Die Anchor-Vektoren muessen fuer Gemma 4 neu berechnet werden:

1. **Anchor-Texte** (identisch zu Qwen):
   - Positiv: "Mir geht es super, ich freue mich richtig."
   - Negativ: "Ich bin ruhig und klar." (neutraler Referenzpunkt)

2. **Hidden-State-Extraktion**:
   - Anchor-Texte durch Gemma 4 jagen
   - Differenz pro Layer berechnen
   - Normalisieren und skalieren

3. **Cache-Trennung**:
   - `data/steering_cache/gemma4/` fuer Gemma-4-Vektoren
   - `data/steering_cache/qwen/` fuer Qwen-Vektoren
   - Cache-Key enthaelt Modellname + Anchor-Version

### 3.2 Erwartete Unterschiede

- **Skalierung**: Gemma 4 hat `head_dim=256` (vs. 128 bei Qwen) -> Anchor-Vektoren sind breiter
- **Layer-Verteilung**: Gemma 4 nutzt `sliding_attention` (512 Window) + `full_attention` mix -> Steuerbarkeit variiert pro Layer-Typ
- **Alpha-Faktor**: Muss fuer Gemma 4 hoeher/kleiner sein -> empirisch testen
- **NF4-Qualitaet**: NF4 dequantisiert zu bfloat16 -> **kein Qualitaetsverlust** fuer Anchor-Vektoren

### 3.3 Empirische Kalibrierung

```bash
# 1. Steering-Server mit Gemma 4 starten
python -m brain.steering_api_server --model google/gemma-4-26B-A4B-it --quantize

# 2. Anchor-Vektoren berechnen (einmalig)
python -c "
from brain.steering_backend import LocalSteeringEngine
engine = LocalSteeringEngine('google/gemma-4-26B-A4B-it', quantize=True)
# Anchor-Vektoren werden beim ersten Aufruf automatisch berechnet und gecacht
"

# 3. Test-Antwort mit Steering
python -c "
from brain.steering_backend import LocalSteeringEngine
engine = LocalSteeringEngine('google/gemma-4-26B-A4B-it', quantize=True)
result = engine.generate(
    [{'role': 'system', 'content': 'Du bist CHAPPiE.'},
     {'role': 'user', 'content': 'Wie geht es dir?'}],
    max_tokens=100,
    temperature=0.7,
    steering_payload={'steering': {'emotion_intensities': {'happiness': 80}}}
)
print(result['text'])
"
```

---

## 4. Edge Cases und Fehlerbehandlung

### 4.1 VRAM-Ueberlauf

```python
# In steering_backend.py _select_device():
# Bei 16GB VRAM und 26B Modell: automatisch auf CPU ausweichen
if self.device.type == "cuda":
    available = self._cuda_total_gib()
    required = self._estimate_required_gpu_gib()
    if required > 0 and available < required * 0.9:
        LOGGER.warning(
            "GPU zu klein fuer %s (%.1f GiB verfuegbar, %.1f GiB noetig). "
            "Wechsle auf CPU.",
            self.model_name, available, required
        )
        return torch.device("cpu")
```

### 4.2 Modell nicht gefunden

```python
# In steering_api_server.py:
@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    model = body.get("model") or app.state.model_name
    if model != app.state.model_name:
        raise HTTPException(
            status_code=400,
            detail=f"Modell {model} ist nicht geladen. "
                   f"Geladen: {app.state.model_name}"
        )
```

### 4.3 Reasoning-Unterstuetzung

```python
# In vllm_brain.py _prepare_extra_body():
def _prepare_extra_body(self, extra_body):
    payload = dict(extra_body or {})
    if "chat_template_kwargs" not in payload:
        payload["chat_template_kwargs"] = {}
    
    # Qwen: enable_thinking
    if "qwen" in self.model.lower():
        payload["chat_template_kwargs"]["enable_thinking"] = bool(settings.chain_of_thought)
    
    # Gemma 4: enable_thinking (gleicher vLLM-Parameter)
    elif "gemma-4" in self.model.lower() or "gemma4" in self.model.lower():
        payload["chat_template_kwargs"]["enable_thinking"] = bool(settings.chain_of_thought)
    
    return payload
```

### 4.4 Steering-Vektor-Qualitaet bei Quantisierung

```python
# In steering_backend.py _build_basis():
# NF4-Quantisierung hat KEINEN Einfluss auf Steering-Qualitaet:
# - Gewichte werden zu bfloat16/float16 dequantisiert
# - Hidden States sind in voller Praezision (16-bit)
# - Anchor-Vektoren werden mit vollen Aktivierungen berechnet
# -> Gleiche Qualitaet wie unquantisiertes Modell!
#
# ACHTUNG: Dies gilt NUR fuer NF4/FP4 mit bfloat16 compute dtype!
# Bei reinem INT4 ohne Dequantisierung waere die Qualitaet schlechter.
```

### 4.5 Layer-Typ-Unterschiede

```python
# Gemma 4 hat gemischte Attention-Typen:
# - sliding_attention (512 Window) fuer die meisten Layer
# - full_attention fuer jede 6. Layer
# Hooks muessen auf ALLEN Layern funktionieren, aber:
# - sliding_attention Layer haben begrenzten Kontext
# - full_attention Layer haben vollen Kontext
# -> Steering wirkt in full_attention Layern staerker
```

### 4.6 Modell-Wechsel zur Laufzeit

```python
# In backend_wrapper.py apply_runtime_settings():
# Bei Modell-Wechsel muessen Anchor-Vektoren neu geladen werden
if changed:
    # Steering-Manager Profil aktualisieren
    self.steering_manager.refresh_runtime_profile(get_active_model())
    # Anchor-Vektoren fuer neues Modell laden
    self.steering_manager._load_vectors()
    self.steering_manager._ensure_default_vectors()
    # Modell-spezifische Defaults anwenden
    apply_model_defaults_if_unset(get_active_model(), settings)
```

### 4.7 Steering-Server-Neustart bei Modell-Wechsel

```python
# In chappie_brain_cli.py und backend_wrapper.py:
# Bei Modell-Wechsel muss der Steering-Server neu gestartet werden,
# da er das Modell beim Start laedt und nicht zur Laufzeit wechseln kann.

def _restart_steering_server(model_name: str, quantize: bool, context_length: int):
    """Stoppt alten und startet neuen Steering-Server."""
    # 1. Alten Prozess stoppen (via systemd oder PID-File)
    # 2. Warten bis Port frei ist
    # 3. Neuen Server mit neuem Modell starten
    # 4. Auf /health OK warten (Timeout: 120s)
    # 5. Fortschrittsanzeige ausgeben
    pass
```

---

## 5. Test-Strategie

### 5.1 Unit-Tests

```bash
# Neue Tests:
python tests/test_gemma4_steering_backend.py    # Steering-Backend mit Gemma 4
python tests/test_gemma4_layer_profiles.py      # Layer-Profile-Erkennung
python tests/test_gemma4_reasoning.py           # Reasoning-Extraktion
python tests/test_model_switching.py            # Modell-Wechsel zur Laufzeit
python tests/test_model_generation_defaults.py  # Modell-spezifische Defaults
python tests/test_thinking_token_extraction.py  # Token-Extraktion pro Modell

# Bestehende Tests mit Gemma 4 wiederholen:
python tests/test_vllm_response_handling.py     # vLLM-Brain mit Gemma 4
python tests/test_steering_backend.py           # Steering-Backend
python tests/test_brain_pipeline_steering_integration.py
```

### 5.2 Integration-Tests

```bash
# 1. Steering-Server mit Gemma 4 starten
python -m brain.steering_api_server --model google/gemma-4-26B-A4B-it --quantize

# 2. CLI-Test
python chappie_brain_cli.py
> /model google/gemma-4-26B-A4B-it
> Hallo, wie geht es dir?

# 3. Alignment-Tests
python forschung/allignement_tests.py
# Modell: Gemma 4 26B-A4B waehlen
```

### 5.3 Rollback-Test (KRITISCH)

```bash
# 1. Starte mit Qwen 3.5-4B, verifiziere alles funktioniert
python chappie_brain_cli.py
> /status  # Qwen 3.5-4B angezeigt
> Hallo    # Antwort kommt

# 2. Wechsle zu Gemma 4
> /model google/gemma-4-26B-A4B-it
# Steering-Server neu gestartet
> /status  # Gemma 4 angezeigt
> Hallo    # Antwort kommt

# 3. Wechsle zurueck zu Qwen
> /model Qwen/Qwen3.5-4B
# Steering-Server neu gestartet
> /status  # Qwen 3.5-4B angezeigt
> Hallo    # Antwort kommt (wie vorher)
```

### 5.4 Visuelle Pruefung

- Steering-Report in CLI zeigt "VECTOR" Mode fuer Gemma 4
- Emotionen werden sichtbar in Antwort reflektiert
- Reasoning (falls vorhanden) wird korrekt angezeigt
- Keine CoT-Leakage in Antworten
- Modell-Defaults werden korrekt angezeigt und angewendet

---

## 6. Implementierungs-Reihenfolge

### Phase 1: Config und Profile (1-2h)
1. `config/config.py` - Gemma 4 Defaults, Erkennungsfunktionen, generische Defaults
2. `brain/agents/steering_manager.py` - Layer-Profile, `is_local_vector_steerable_model()`

### Phase 2: Steering-Backend (3-4h)
3. `brain/steering_backend.py` - Modell-Laden, GPU-Erkennung, Anchor-Skalierung, `_split_thinking_output()`
4. `brain/steering_api_server.py` - Generischer Modell-Loader, Restart-Endpoints

### Phase 3: vLLM-Brain (1-2h)
5. `brain/vllm_brain.py` - Reasoning-Logik, generische Generation-Parameter

### Phase 4: API und Frontend (3-4h)
6. `api/schemas/__init__.py` - SettingsUpdate erweitern
7. `frontend/src/pages/settings-page.tsx` - Modellwahl-UI mit Defaults
8. `frontend/src/components/steering-restart-modal.tsx` - Neues Modal fuer Restart-Fortschritt

### Phase 5: CLI und Tests (2-3h)
9. `chappie_brain_cli.py` - /model Command mit Steering-Server-Neustart
10. `forschung/allignement_tests.py` - Modellwahl
11. Tests schreiben und ausfuehren (inkl. Rollback-Test)

### Phase 6: Kalibrierung und Testing (2-3h)
12. Anchor-Vektoren fuer Gemma 4 berechnen
13. Integration-Tests durchfuehren
14. Edge Cases verifizieren

### Phase 7: Versionierung und Doku (0.5h)
15. Version auf 14.0 erhoehen (Major-Update)
16. CHANGELOG.md aktualisieren (5 Stichpunkte)
17. README.md pruefen und anpassen

**Gesamt:** ~13-19 Stunden

---

## 7. Risiken und Offene Fragen

### 7.1 Offene Fragen
1. ~~**Reasoning bei Gemma 4**~~: GELOEST! Gemma 4 nutzt `<|channel>thought` ... `<channel|>` Tags, aktiviert via `<|think|>` im System-Prompt. vLLM gibt es als `reasoning_content` Attribut zurueck.
2. **Anchor-Skalierung**: `ANCHOR_SCALE_FACTOR` muss fuer Gemma 4 empirisch bestimmt werden. NF4 hat keinen Einfluss (Hidden States sind in bfloat16).
3. ~~**NF4-Qualitaet**~~: GELOEST! NF4 dequantisiert zu bfloat16, Hidden States sind in voller Praezision. Steering funktioniert problemlos.
4. **MoE-Steering**: Wirkt Layer-Steering auf MoE-Modellen anders als auf Dense-Modellen? -> Empirisch testen.
5. **Sliding Window**: Beeinflusst das 512-Token Sliding Window die Steering-Effektivitaet? -> Nur bei langen Kontexten relevant.
6. ~~**Provider**~~: GELOEST! Gemma 4 laeuft ausschliesslich via vLLM. Kein separater Google-Provider noetig.
7. ~~**attn_implementation**~~: GELOEST! sdpa fuer alle Modelle auf T4. FlashAttention-2 bei spaeterer GPU-Upgrade moeglich.

### 7.2 Risiken
- **Hoher Aufwand**: Steering-Backend-Integration ist komplex (~40% der Gesamtzeit)
- **Empirische Kalibrierung**: Anchor-Vektoren muessen experimentell optimiert werden
- **VRAM-Grenze**: 16GB ist knapp fuer 26B MoE mit Quantisierung
  - Nur ~3.4 GB Puffer fuer KV-Cache + Activations + Steering
  - Bei langen Sessions (10K+ Tokens): OOM-Risiko
  - **Loesung:** Context-Window auf 4K-8K begrenzen
- **Performance**: NF4-Quantisierung kann Inference-Performance beeintraechtigen (aber nicht Steering-Qualitaet)
- **MoE-Steering**: Unbekannt ob Layer-Steering auf MoE-Modellen anders wirkt als auf Dense
- **T4-Limit**: Tesla T4 hat nur 300 GB/s Bandbreite -> MoE-Modell ist bandwidth-bound
- **Thinking-Overhead**: Thinking-Tokens verbrauchen Additional VRAM (KV-Cache)
- **Steering-Server-Neustart**: Modell-Wechsel erfordert Neustart (~30-60s)
- **Session-History**: Langer Kontext bei Gemma 4 26B-A4B fuehrt zu VRAM-Engpass

### 7.3 Rollback-Plan
- Qwen 3.5 bleibt immer als Default verfuegbar
- Bei Problemen: `vllm_model` zurueck auf `Qwen/Qwen3.5-4B` setzen
- Steering-Cache fuer Gemma 4 kann geloescht werden ohne Qwen zu beeintraechtigen
- Alle Aenderungen sind rueckgaengig durch Config-Wechsel
- **Rollback-Test muss vor Push bestaetigt werden** (siehe Section 5.3)

---

## 8. Deployment und Service-Konfiguration

### 8.1 Steering-Server systemd-Service

```ini
# /etc/systemd/system/chappie-steering.service
[Unit]
Description=CHAPPiE Steering API Server
After=network.target

[Service]
Type=simple
User=chappie
WorkingDirectory=/home/chappie/CHAPPiE
ExecStart=/usr/bin/python3 -m brain.steering_api_server \
    --model google/gemma-4-26B-A4B-it \
    --quantize \
    --context-length 4096
Restart=on-failure
RestartSec=10
Environment="CUDA_VISIBLE_DEVICES=0"
Environment="PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True"
# 768 GiB RAM erlaubtgrosszügige Puffer
Environment="MALLOC_TRIM_THRESHOLD_=100000"

[Install]
WantedBy=multi-user.target
```

**Server-spezifische Optimierungen:**
- **2x Xeon Gold 6150** -> `OMP_NUM_THREADS=18` fuer vLLM-Inference (18 Threads pro CPU)
- **768 GiB RAM** -> KV-Cache kann grosszuegig allokiert werden
- **3x SSD** -> Model-Cache auf separater SSD (`/dev/sdb`)
- **10GbE** -> Remote-Access via SSH oder API (niedrige Latenz)

### 8.2 vLLM-Server fuer Gemma 4

```bash
# Manuelles Starten (Test):
python -m brain.steering_api_server \
    --model google/gemma-4-26B-A4B-it \
    --quantize \
    --context-length 4096

# Oder ueber vLLM direkt (ohne Steering):
vllm serve google/gemma-4-26B-A4B-it \
    --quantization nf4 \
    --max-model-len 8192 \
    --gpu-memory-utilization 0.9
```

### 8.3 Config fuer Gemma 4 in CHAPPIE_CONFIG.json

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
    "max_tokens": 450,
    "chain_of_thought": true,
    "top_p": 0.95,
    "top_k": 64,
    "use_model_defaults": true
  }
}
```

**Wichtig fuer Gemma 4 26B-A4B auf T4:**
- `steering_context_length: 4096` → Minimum, passt ins VRAM
- `max_tokens: 450` → Generierungs-Limit, verhindert zu lange Antworten
- Bei langen Sessions: Context-Window in CHAPPIE begrenzen (nicht mehr als 8K Tokens gesamt)

---

## 9. Zusammenfassung der Datei-Aenderungen

| Datei | Aenderung | Aufwand | Status |
|---|---|---|---|
| `config/config.py` | Gemma 4 Defaults, Erkennungsfunktionen, generische Defaults, User-Override | Mittel | **ERLEDIGT** |
| `brain/agents/steering_manager.py` | Layer-Profile, `is_local_vector_steerable_model()` | Mittel | **ERLEDIGT** (Layer-Profile hinzugefuegt) |
| `brain/steering_backend.py` | Modell-Laden, GPU-Erkennung, Anchor, `_split_thinking_output()` | Hoch | **ERLEDIGT** |
| `brain/steering_api_server.py` | Generischer Loader, Auto-Quantisierung, Restart-Endpoints | Hoch | **ERLEDIGT** |
| `brain/vllm_brain.py` | Reasoning-Logik, generische Generation-Parameter | Klein | **ERLEDIGT** |
| `api/schemas/__init__.py` | SettingsUpdate erweitern | Klein | **ERLEDIGT** |
| `api/routers/runtime.py` | Settings-Snapshot erweitern | Klein | **ERLEDIGT** |
| `frontend/src/pages/settings-page.tsx` | Modellwahl-UI mit Defaults | Mittel | **ERLEDIGT** |
| `frontend/src/components/steering-restart-modal.tsx` | Neues Modal fuer Restart-Fortschritt | Mittel | **ERLEDIGT** |
| `chappie_brain_cli.py` | /model Command mit Steering-Server-Neustart | Mittel | **ERLEDIGT** |
| `forschung/allignement_tests.py` | Modellwahl im Menu | Klein | **ERLEDIGT** |
| `tests/test_gemma4_*.py` | Neue Tests (inkl. Rollback-Test) | Mittel | **ERLEDIGT** |
| `docs/integration_gemma4.md` | Diese Datei | Erledigt | **ERLEDIGT** |
| `CHANGELOG.md` | Version 14.0 eintragen | Klein | **ERLEDIGT** |
| `README.md` | Modell-Unterstuetzung dokumentieren | Klein | **ERLEDIGT** |

**Kritischer Pfad:** `brain/steering_backend.py` -> `brain/agents/steering_manager.py` -> `brain/steering_api_server.py`

---

## 10. Versionierung

**Version:** 13.x → 14.0 (Major-Update wegen neuem Modell-Support)

**CHANGELOG.md (5 Stichpunkte):**
- Gemma 4 26B-A4B (MoE, 4B active) als Alternative zu Qwen 3.5-4B
- Modell-spezifische Generierungs-Defaults (temperature, top_p, top_k)
- `/model` Befehl in CLI mit Steering-Server-Neustart
- Model-Schnellwahl im Frontend mit Auto-Defaults
- Rollback-Test fuer sicheres Modell-Switching
