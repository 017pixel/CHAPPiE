# CHAPiE Upgrade Guide - Voice Engine V2

## 🚀 Schnellstart

### 1. Dependencies installieren

```powershell
# Aktiviere Virtual Environment
.\venv\Scripts\activate

# Installiere neue Packages
pip install faster-whisper edge-tts

# Optional: Alle Requirements neu installieren
pip install -r requirements.txt
```

### 2. Konfiguration anpassen (Optional)

Öffne `config/secrets.py` und passe die Voice-Einstellungen an:

```python
# === Voice Einstellungen (Empfohlen) ===
TTS_ENGINE = 'edge'         # Edge-TTS: Kostenlos, beste Qualität
STT_ENGINE = 'google'       # Google: Schnell, Online
```

**Für Offline-Nutzung**:
```python
TTS_ENGINE = 'pyttsx3'           # Funktioniert offline
STT_ENGINE = 'faster-whisper'    # Lokal, gute Qualität
WHISPER_MODEL_SIZE = 'base'      # Modellgröße
```

### 3. Starten

```powershell
python main.py
```

---

## 🔧 Detaillierte Installation

### Windows (PowerShell)

```powershell
# 1. Virtual Environment aktivieren
cd C:\Users\Benja\OneDrive\Desktop\CHAPiE
.\venv\Scripts\activate

# 2. Upgrade pip
python -m pip install --upgrade pip

# 3. Neue Dependencies
pip install faster-whisper edge-tts

# 4. Optional: CUDA Support (falls GPU vorhanden)
# pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 5. Teste Installation
python -c "import edge_tts; print('Edge-TTS OK')"
python -c "from faster_whisper import WhisperModel; print('Faster-Whisper OK')"
```

### Linux/Mac

```bash
# 1. Virtual Environment aktivieren
cd /pfad/zu/CHAPiE
source venv/bin/activate

# 2. Upgrade pip
python -m pip install --upgrade pip

# 3. Neue Dependencies
pip install faster-whisper edge-tts

# 4. Teste Installation
python -c "import edge_tts; print('Edge-TTS OK')"
python -c "from faster_whisper import WhisperModel; print('Faster-Whisper OK')"
```

### 4. Trainingsmodus nutzen

Der neue automatisierte Trainingsmodus ermöglicht es, CHAPiE ohne manuelles Zutun über lange Zeit zu trainieren.

```powershell
# Starte den Trainingspartner
python -m Chappies_Trainingspartner.trainingspartner_main
```

**Features**:
- Wählbare Trainer-Persona und Fokus-Area
- Automatischer Fallback auf lokale Modelle bei API-Limits
- Regelmäßige Memory-Consolidation (alle 24 Nachrichten)

---

## ⚙️ Konfigurationsoptionen

### TTS Engines

| Engine | Qualität | Geschwindigkeit | Online | Kosten | Empfohlen |
|--------|----------|----------------|--------|--------|-----------|
| `edge` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ | Kostenlos | ✅ |
| `pyttsx3` | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ | Kostenlos | - |
| `gtts` | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ | Kostenlos | - |
| `bark` | ⭐⭐⭐⭐⭐ | ⭐⭐ | ❌ | Kostenlos | - |

**Einstellung in `config/secrets.py`**:
```python
TTS_ENGINE = 'edge'  # edge, pyttsx3, gtts, bark
```

### STT Engines

| Engine | Qualität | Geschwindigkeit | Online | Kosten | Empfohlen |
|--------|----------|----------------|--------|--------|-----------|
| `google` | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ | Kostenlos* | ✅ |
| `faster-whisper` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ❌ | Kostenlos | ✅ |
| `whisper` | ⭐⭐⭐⭐⭐ | ⭐⭐ | ❌ | Kostenlos | - |
| `vosk` | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ | Kostenlos | - |

*Google: Fair Use Policy, keine API Key nötig

**Einstellung in `config/secrets.py`**:
```python
STT_ENGINE = 'google'  # google, faster-whisper, whisper, vosk
```

---

## 🧪 Testen

### Voice Engine testen

```powershell
# Starte CHAPiE
python main.py

# In CHAPiE:
/sprechen           # Aktiviere Sprachmodus
[Halte Leertaste]   # Teste Spracheingabe
/text               # Deaktiviere Sprachmodus
```

### Commands testen

```powershell
# Schlafmodus
/sleep              # Einschlafen
/help               # Sollte funktionieren
/sleep              # Aufwachen

# Sprachmodus
/sprechen           # Toggle an
/text               # Sprachmodus aus
/stop               # Alternative zu /text
```

---

## 🚨 Troubleshooting

### Problem: `ModuleNotFoundError: No module named 'edge_tts'`

**Lösung**:
```powershell
pip install edge-tts
```

### Problem: `ModuleNotFoundError: No module named 'faster_whisper'`

**Lösung**:
```powershell
pip install faster-whisper
```

### Problem: Faster-Whisper sehr langsam

**Lösung**: Installiere CUDA-Support für GPU-Beschleunigung:
```powershell
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

Oder verwende kleineres Modell in `config/secrets.py`:
```python
WHISPER_MODEL_SIZE = 'tiny'  # Schneller, etwas schlechtere Qualität
```

### Problem: Edge-TTS funktioniert nicht

**Check**:
- Internet-Verbindung vorhanden?
- Firewall blockiert Python?

**Fallback**: Nutze pyttsx3 (offline):
```python
# config/secrets.py
TTS_ENGINE = 'pyttsx3'
```

### Problem: PTT (Push-to-Talk) funktioniert nicht

**Windows**: `keyboard` Library benötigt Admin-Rechte für globale Hotkeys.

**Lösung**:
1. Starte PowerShell als Administrator
2. Aktiviere venv und starte CHAPiE
3. Oder: Ändere PTT Key in `config/secrets.py`:
   ```python
   PTT_KEY = 'space'  # Versuche andere Tasten: 'ctrl', 'shift'
   ```

### Problem: Voice Engine V2 lädt nicht

**Check ob verfügbar**:
```powershell
python -c "from brain.voice_engine_v2 import VoiceEngineV2; print('V2 verfügbar')"
```

**Falls Fehler**: CHAPiE nutzt automatisch Fallback zur alten `voice_engine.py`. 
Funktioniert weiterhin, aber ohne neue Features.

---

## 📊 Performance-Tipps

### Beste Performance (Online)
```python
TTS_ENGINE = 'edge'          # Schnell, gute Qualität
STT_ENGINE = 'google'        # Sehr schnell
```

### Beste Qualität (Offline)
```python
TTS_ENGINE = 'bark'                # Langsam, beste Qualität
STT_ENGINE = 'faster-whisper'      # Gute Balance
WHISPER_MODEL_SIZE = 'medium'      # Oder 'large' für beste Qualität
```

### Balance (Offline)
```python
TTS_ENGINE = 'pyttsx3'             # Schnell, ok Qualität
STT_ENGINE = 'faster-whisper'      # Schnell genug
WHISPER_MODEL_SIZE = 'base'        # Gute Balance
```

---

## 🔄 Rollback zur alten Voice Engine

Falls Probleme mit V2:

1. **Temporär**: Lösche `brain/voice_engine_v2.py`
   ```powershell
   rm brain/voice_engine_v2.py
   ```

2. **Dauerhaft**: Editiere `main.py` Zeile 31-34:
   ```python
   # Alte Engine erzwingen
   from brain.voice_engine import VoiceEngine
   ```

---

## 📝 Weitere Hilfe

- Siehe `BUGFIX_CHANGELOG.md` für alle Änderungen
- Siehe `README.md` für allgemeine Installation
- Siehe `START_ANLEITUNG.md` für erste Schritte

---

**Viel Erfolg! 🚀**
