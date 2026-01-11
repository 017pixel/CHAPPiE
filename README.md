# 🤖 CHAPPiE - Chappie Proto

> Ein KI-Agent mit episodischem Gedächtnis - "Lernen wie ein Kind"

## 📋 Überblick

CHAPPiE ist ein experimenteller KI-Agent, der sich an vergangene Interaktionen erinnert und sein Verhalten basierend auf Feedback anpasst. Das Kernkonzept ist ein **episodisches Gedächtnis** mit ChromaDB als Vektordatenbank.

## 🏗️ Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                        MAIN LOOP                            │
│  ┌─────────┐    ┌──────────────┐    ┌─────────────────┐    │
│  │  User   │───▶│    RAG       │───▶│     Brain       │    │
│  │  Input  │    │  Retrieval   │    │  (LLM Backend)  │    │
│  └─────────┘    └──────────────┘    └─────────────────┘    │
│       │              ▲                      │               │
│       │              │                      │               │
│       ▼              │                      ▼               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  MEMORY ENGINE                       │   │
│  │                   (ChromaDB)                         │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Projektstruktur

```
CHAPPiE/
├── config/
│   ├── config.py          # Zentrale Konfiguration
│   └── secrets.py         # API-Keys & Modell-Einstellungen ⚠️
├── memory/
│   └── memory_engine.py   # ChromaDB Wrapper
├── brain/
│   ├── base_brain.py      # Abstrakte LLM-Klasse
│   ├── ollama_brain.py    # Ollama Implementation
│   └── groq_brain.py      # Groq Cloud Implementation
├── data/
│   └── chroma_db/         # Persistente Vektordatenbank
├── main.py                # Haupt-Loop
└── requirements.txt       # Dependencies
```

## 🚀 Installation

### 1. Repository klonen & Virtual Environment

```bash
cd CHAPpIE
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

### 2. Dependencies installieren

```bash
pip install -r requirements.txt
```

### 3. Konfiguration

Öffne `config/secrets.py` und trage deine Einstellungen ein:

```python
# LLM Provider wählen: "ollama" (lokal) oder "groq" (cloud)
LLM_PROVIDER = "ollama"

# Falls Groq: API-Key eintragen
GROQ_API_KEY = "dein_key_hier"
```

### 4. Ollama einrichten (für lokale Modelle)

```bash
# Ollama installieren: https://ollama.ai
# Modell herunterladen:
ollama pull llama3:8b
```

## ⚙️ Konfiguration

Alle Einstellungen befinden sich in `config/secrets.py`:

| Variable | Beschreibung | Standard |
|----------|-------------|----------|
| `LLM_PROVIDER` | Backend: `ollama` oder `groq` | `ollama` |
| `OLLAMA_MODEL` | Lokales Modell | `llama3:8b` |
| `GROQ_API_KEY` | Groq Cloud API Key | (leer) |
| `GROQ_MODEL` | Groq Modell | `llama-3.1-8b-instant` |
| `MEMORY_TOP_K` | Anzahl Erinnerungen | `5` |
| `TEMPERATURE` | Kreativität (0.0-1.0) | `0.7` |

## 🎮 Verwendung

```bash
python main.py
```

## 🧠 Features

- **Episodisches Gedächtnis**: Speichert alle Konversationen als Vektoren
- **RAG (Retrieval Augmented Generation)**: Findet relevante Erinnerungen
- **Modulares Backend**: Wechsel zwischen Ollama (lokal) und Groq (Cloud)
- **Token-Streaming**: Flüssige Textausgabe im Terminal
- **Persistenz**: Erinnerungen bleiben nach Neustart erhalten

## 📊 Hardware-Anforderungen

| Umgebung | GPU | RAM | Modelle |
|----------|-----|-----|---------|
| Entwicklung | RTX 3060 (12GB) | 16GB | Llama-3-8b, Embeddings |
| Produktion | Server-GPU | 32GB+ | GPT-OSS-20b/120b |

## 🔧 Development Roadmap

- [x] Phase 1: Setup & Konfiguration ✅
- [x] Phase 2: Memory Engine (ChromaDB) ✅
- [x] Phase 3: Brain Engine (Ollama/Groq) ✅
- [x] Phase 4: Main Loop & Integration ✅
- [x] Phase 5: Bug Fixes & Voice Engine V2 ✅

**🎉 PROJEKT ABGESCHLOSSEN!**

## 🆕 Letzte Updates (10. Januar 2026)

### Bug Fixes
- ✅ Commands funktionieren jetzt im Schlafmodus
- ✅ Sprachmodus kann mit `/text` oder `/stop` deaktiviert werden
- ✅ Intelligente Leertasten-Erkennung (kein PTT-Trigger während Texteingabe)
- ✅ Verbesserte Markdown-Formatierung (Apostrophe, Bindestriche, Quotes)

### Neue Features
- 🎙️ **Voice Engine V2** mit besseren Modellen:
  - Edge-TTS (kostenlos, exzellente Qualität) 🆕
  - Faster-Whisper (4x schneller als OpenAI Whisper) 🆕
  - Threading für non-blocking Audio
- 📚 Siehe `BUGFIX_CHANGELOG.md` für Details

---

*Erstellt am 08. Januar 2026*  
*Aktualisiert am 11. Januar 2026*
