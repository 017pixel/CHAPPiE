# CHAPiE Bug Fixes & Verbesserungen - Changelog

## Datum: 10. Januar 2026

### 🐛 Behobene Bugs

#### 1. ✅ Commands funktionieren jetzt im Schlafmodus
**Problem**: Befehle wie `/exit`, `/help` oder `/sleep` funktionierten nicht, wenn CHAPiE im Schlafmodus war.

**Lösung**:
- Commands werden jetzt VOR dem Schlafmodus-Check verarbeitet
- Whitelist für erlaubte Commands im Schlafmodus: `/exit`, `/quit`, `/sleep`, `/help`
- Andere Commands zeigen eine Info-Message an
- `/sleep` fungiert jetzt als Toggle (ein/aus)

**Verwendung**:
```
[Im Schlafmodus]
/sleep    -> CHAPiE wacht auf
/help     -> Zeigt Befehle
/exit     -> Beendet CHAPiE
/andere   -> "CHAPiE schläft... Nur /sleep, /help, /exit sind verfügbar."
```

#### 2. ✅ Exit aus Sprachmodus möglich
**Problem**: Es gab keine Möglichkeit, den Sprachmodus zu deaktivieren, ohne die Anwendung neu zu starten.

**Lösung**:
- Neue Commands: `/text` und `/stop` zum Deaktivieren des Sprachmodus
- `/sprechen`, `/speak`, `/voice` togglen weiterhin zwischen Modi
- Visuelle Bestätigung in der UI

**Verwendung**:
```
/text     -> Deaktiviert Sprachmodus
/stop     -> Alias für /text
/sprechen -> Toggle (aktivieren/deaktivieren)
```

#### 3. ✅ Intelligente Leertasten-Erkennung
**Problem**: Leertaste hat immer PTT (Push-to-Talk) getriggert, auch während Texteingabe.

**Lösung**:
- Leertaste wird nur als PTT behandelt, wenn `input_buffer` leer ist
- Bei vorhandener Texteingabe wird Leertaste als normales Zeichen hinzugefügt
- Timestamp-Tracking für zukünftige Idle-Time Features

**Verhalten**:
```
[Leerer Buffer] + Leertaste  -> PTT aktiviert (Sprachaufnahme)
"Hallo" + Leertaste          -> "Hallo " (normaler Text)
```

#### 4. ✅ Verbesserte Markdown-Formatierung
**Problem**: Sternchen, Apostrophe, Bindestriche wurden nicht richtig dargestellt.

**Lösung**:
- Erweiterte Unterstützung für typografische Anführungszeichen (`'`, `'`, `"`, `"`)
- Em-Dash Support (`--` wird zu `—`)
- Besseres Matching für verschiedene Quote-Styles
- Robustere Verarbeitung von Markdown-Elementen

**Unterstützte Formate**:
- `**bold**` -> **bold**
- `*italic*` -> *italic*
- `__underline__` -> underline
- `` `code` `` -> `code`
- `~~strike~~` -> ~~strike~~
- `"quotes"` -> dim italic quotes
- `'single'` -> dim italic quotes
- `--` -> — (em dash)

#### 5. ✅ Automatisierter Trainingsmodus & Fehlerbehandlung
**Problem**: Manuelles Training von CHAPiE war mühsam und fehleranfällig bei API-Limits oder langen Kontexten.

**Lösung**:
- Implementierung eines autonomen `TrainingLoop` mit intelligentem Fehlermanagement.
- **Context Recovery**: Erkennt Token-Limits und kürzt den Kontext automatisch um 50%.
- **API Fallback**: Schaltet bei Erreichen von Tageslimits (RPD) automatisch auf lokale Modelle (Ollama) um.
- **Memory Protection**: Verhindert das Speichern von API-Fehlermeldungen im Gedächtnis.
- **Kumulative Zusammenfassungen**: Konsolidiert den Chat-Kontext alle 24 Nachrichten, um die Performance beizubehalten, ohne den Gesprächsfaden zu verlieren.

---

### 🚀 Neue Features

#### 1. 🎓 CHAPiEs Trainingspartner
**Neue Dateien**: `Chappies_Trainingspartner/*.py`

**Funktionen**:
- **Autonomes Training**: Ein Trainer-Agent simuliert einen User basierend auf einer wählbaren Persona und einem Fokus-Thema.
- **Rate-Limit Schutz**: Automatisierte Pausen (60s bei RPM, 30min bei Dauerfehlern).
- **Automatischer Schlafmodus**: Alle 24 Nachrichten wird eine Traum-Phase gestartet, die Erinnerungen konsolidiert und den Kontext für maximale Geschwindigkeit optimiert.
- **Persistenz**: Fortschritt wird in `training_state.json` gespeichert und kann jederzeit fortgesetzt werden.


#### 1. ✨ Voice Engine V2
**Neue Datei**: `brain/voice_engine_v2.py`

**Verbesserungen**:
- **Edge-TTS**: Kostenlose Microsoft Edge Cloud TTS, keine API Key nötig, exzellente Qualität
- **Faster-Whisper**: 4x schneller als OpenAI Whisper durch CTranslate2 Optimierung
- **Threading**: Audio-Verarbeitung läuft in separaten Threads (kein UI-Blocking mehr)
- **Besseres State Management**: Thread-safe State Updates
- **Lazy Loading**: Modelle werden nur bei Bedarf geladen

**Unterstützte Engines**:

**TTS (Text-to-Speech)**:
- `edge` - Edge-TTS (empfohlen, kostenlos, sehr gute Qualität) ⭐
- `pyttsx3` - System-TTS (schnell, offline, einfache Qualität)
- `gtts` - Google TTS (online, gute Qualität)
- `bark` - Bark/Suno (lokal, beste Qualität, langsam)

**STT (Speech-to-Text)**:
- `faster-whisper` - Optimiertes Whisper (empfohlen, 4x schneller) ⭐
- `google` - Google Speech Recognition (online, schnell, gut)
- `whisper` - OpenAI Whisper (lokal, langsam, sehr gut)
- `vosk` - Vosk (lokal, leichtgewichtig, mittelmäßig)

#### 2. 📦 Aktualisierte Dependencies

**Neue Requirements** (`requirements.txt`):
```
faster-whisper>=0.10.0    # Schnelleres Whisper (4x Speedup)
edge-tts>=6.1.9           # Microsoft Edge TTS (kostenlos!)
```

**Optionale Dependencies**:
```
# vosk>=0.3.45            # Leichtgewichtiges offline STT
```

---

### ⚙️ Konfiguration

#### Voice Engine konfigurieren
**Datei**: `config/secrets.py`

```python
# === Voice Einstellungen ===
SPEECH_MODE_DEFAULT = False   # Startet im Textmodus

# TTS Engine wählen
TTS_ENGINE = 'edge'          # Optionen: 'edge', 'pyttsx3', 'gtts', 'bark'

# STT Engine wählen
STT_ENGINE = 'google'        # Optionen: 'faster-whisper', 'google', 'whisper', 'vosk'

# Whisper Modellgröße (für faster-whisper oder whisper)
WHISPER_MODEL_SIZE = 'base'  # Optionen: 'tiny', 'base', 'small', 'medium', 'large'

# Vosk Model Path (nur wenn STT_ENGINE = 'vosk')
VOSK_MODEL_PATH = ''         # z.B. 'models/vosk-model-de-0.21'

# PTT Key
PTT_KEY = 'space'            # Push-to-Talk Taste

# Voice Speed (nur für pyttsx3)
VOICE_SPEED = 150            # Wörter pro Minute
```

---

### 🔄 Migration Guide

#### Von alter Voice Engine zu V2

Die neue Voice Engine V2 ist **100% rückwärtskompatibel**!

**Automatisches Fallback**:
```python
# main.py lädt automatisch die neue Engine, falls verfügbar
try:
    from brain.voice_engine_v2 import VoiceEngineV2 as VoiceEngine
except ImportError:
    from brain.voice_engine import VoiceEngine  # Fallback zur alten
```

**Installation der neuen Dependencies**:
```bash
# Im venv
pip install faster-whisper edge-tts

# Oder alle Requirements neu installieren
pip install -r requirements.txt
```

**Empfohlene Konfiguration** (beste Balance aus Geschwindigkeit & Qualität):
```python
TTS_ENGINE = 'edge'              # Schnell, kostenlos, sehr gut
STT_ENGINE = 'google'            # Schnell, online, gut
# Oder für komplett offline:
STT_ENGINE = 'faster-whisper'   # Gut, offline, etwas langsamer beim ersten Mal
```

---

### 🧪 Testing

**Test-Szenarien**:

1. **Schlafmodus Commands**:
   - CHAPiE mit `/sleep` einschlafen lassen
   - Versuche `/help` -> sollte funktionieren
   - Versuche `/memory` -> sollte abgelehnt werden
   - Drücke `/sleep` erneut -> sollte aufwachen

2. **Sprachmodus Exit**:
   - Aktiviere Sprachmodus mit `/sprechen`
   - Deaktiviere mit `/text`
   - Verifiziere visuellen Status in UI

3. **Intelligente Leertaste**:
   - Sprachmodus aktivieren
   - Leertaste bei leerem Buffer drücken -> PTT sollte starten
   - Text eintippen: "Hallo", dann Leertaste -> sollte "Hallo " ergeben

4. **Markdown Rendering**:
   - Frage CHAPiE nach formatiertem Text
   - Verifiziere dass `**bold**`, `*italic*`, `"quotes"` richtig angezeigt werden

5. **Voice Engine V2**:
   - Teste TTS mit verschiedenen Engines: `/config` -> stelle TTS_ENGINE um
   - Teste STT mit Sprachmodus
   - Verifiziere dass kein UI-Lag entsteht

---

### 📊 Performance

**Verbesserungen**:
- ✅ Kein UI-Blocking mehr durch Voice-Verarbeitung
- ✅ Faster-Whisper: ~4x schneller als OpenAI Whisper
- ✅ Edge-TTS: Schneller als gTTS, bessere Qualität
- ✅ Thread-safe State Management ohne Race Conditions

**Benchmarks** (ungefähr, abhängig von Hardware):
| Engine | Geschwindigkeit | Qualität | Online |
|--------|----------------|----------|--------|
| Edge-TTS | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ |
| pyttsx3 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ |
| gTTS | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ |
| Bark | ⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ |

| Engine | Geschwindigkeit | Qualität | Online |
|--------|----------------|----------|--------|
| Google STT | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ |
| Faster-Whisper | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ |
| Whisper | ⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ |
| Vosk | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ |

---

### 🚧 Bekannte Einschränkungen

1. **Voice Engine V2 Dependencies**: 
   - `faster-whisper` benötigt CUDA für beste Performance (CPU funktioniert auch)
   - `edge-tts` benötigt Internet-Verbindung

2. **Markdown Rendering**:
   - Sehr komplexe verschachtelte Markdown-Strukturen könnten noch fehlerhaft sein
   - Tables werden nicht unterstützt (Rich TUI Limitierung)

3. **PTT im Sprachmodus**:
   - `keyboard` Library benötigt Admin-Rechte unter Windows für globale Hotkeys
   - Alternativ: Nur innerhalb der Anwendung funktionsfähig

---

### 💡 Empfohlene Setup-Konfiguration

**Für beste Nutzererfahrung**:

```python
# config/secrets.py

# === Voice Settings ===
SPEECH_MODE_DEFAULT = False
TTS_ENGINE = 'edge'              # Kostenlos, beste Qualität
STT_ENGINE = 'google'            # Schnell, für Echtzeit-Interaktion
WHISPER_MODEL_SIZE = 'base'      # Falls faster-whisper verwendet wird
PTT_KEY = 'space'

# === Für Offline-Nutzung ===
# TTS_ENGINE = 'pyttsx3'         # Funktioniert offline
# STT_ENGINE = 'faster-whisper'  # Lokal, gute Qualität
```

**Installation**:
```bash
# Aktiviere venv
.\\venv\\Scripts\\activate

# Installiere neue Dependencies
pip install faster-whisper edge-tts

# Teste
python main.py
```

---

### 📝 Weitere Hinweise

- Die alte `voice_engine.py` bleibt als Fallback erhalten
- Beide Engines haben die gleiche API (kompatibel)
- Voice Engine V2 ist production-ready und getestet
- Bei Problemen: Fallback auf alte Engine durch Entfernen von `voice_engine_v2.py`

---

**Erstellt**: 10. Januar 2026  
**Version**: CHAPiE v2.1  
**Status**: ✅ Alle kritischen Bugs behoben
