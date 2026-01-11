# 🤖 CHAPiE - AI Chat Assistant

> Ein KI-Agent mit episodischem Gedächtnis und Emotions-Engine - "Lernen wie ein Kind"

## 🔗 Repository

[![GitHub](https://img.shields.io/badge/GitHub-017pixel%2FCHAPPiE-blue?logo=github)](https://github.com/017pixel/CHAPPiE)

## 📋 Überblick

CHAPiE ist ein experimenteller KI-Agent, der sich an vergangene Interaktionen erinnert, sein Verhalten basierend auf Feedback anpasst und über eine Emotions-Engine verfügt. Das Kernkonzept ist ein **episodisches Gedächtnis** mit ChromaDB als Vektordatenbank, kombiniert mit einem dynamischen Emotionssystem.

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
CHAPiE/
├── config/
│   ├── config.py          # Zentrale Konfiguration
│   ├── prompts.py         # System-Prompts & Templates
│   └── secrets.py         # API-Keys & Modell-Einstellungen ⚠️
├── memory/
│   ├── memory_engine.py   # ChromaDB Wrapper (Vektordatenbank)
│   ├── emotions_engine.py # Emotions-Engine (6 Emotionen)
│   └── chat_manager.py    # Chat-Session Management
├── brain/
│   ├── base_brain.py      # Abstrakte LLM-Klasse
│   ├── ollama_brain.py    # Ollama Implementation (lokal)
│   ├── groq_brain.py      # Groq Cloud Implementation
│   └── response_parser.py # Antwort-Parsing & Markdown
├── data/
│   ├── chat_sessions/     # Persistierte Chat-Sessions
│   └── chroma_db/         # Vektordatenbank (automatisch erstellt)
├── app.py                 # GUI-Anwendung (optional)
├── main.py                # CLI Haupt-Loop
├── requirements.txt       # Dependencies
├── .gitignore             # Git-Ignore Regeln
└── README.md              # Diese Datei
```

## 🚀 Installation

### 1. Repository klonen & Virtual Environment

```bash
git clone https://github.com/017pixel/CHAPPiE.git
cd CHAPPiE
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
| `GROQ_MODEL` | Groq Modell | `kimi k2` |
| `MEMORY_TOP_K` | Anzahl Erinnerungen | `5` |
| `TEMPERATURE` | Kreativität (0.0-1.0) | `0.7` |
| `USE_CHAIN_OF_THOUGHT` | Chain-of-Thought aktivieren | `True` |

**⚠️ Wichtig:** `config/secrets.py` muss mit einem Groq gefüllt werden!

## 🎮 Verwendung

### CLI Modus (Terminal)

```bash
python main.py
```

### GUI Modus (Streamlit Web-App)

CHAPiE verfügt über eine moderne Web-GUI basierend auf **Streamlit**, die im Browser läuft.

#### Installation der GUI-Abhängigkeit

```bash
pip install streamlit
```

#### Starten der GUI

```bash
streamlit run app.py
```

Die App öffnet sich automatisch in deinem Standard-Browser unter:
```
http://localhost:8501
```

#### GUI Features

- **Chat-Interface**: Modernes Messaging-Interface mit Chat-Verlauf
- **Emotions-Dashboard**: Echtzeit-Anzeige der 6 Emotionen (Happiness, Trust, Energy, Curiosity, Frustration, Motivation)
- **Settings Panel**: Konfiguration von LLM-Provider, Temperatur, Memory-Top-K
- **Session Management**: Mehrere Chat-Sessions speichern und laden
- **Markdown-Support**: Formatierung für Code, Listen und Text
- **Responsive Design**: Funktioniert auf Desktop und Tablet

#### Streamlit Vorteile

- **Keine Frontend-Entwicklung nötig**: Python-Code reicht aus
- **Automatische UI**: Streamlit erstellt die Benutzeroberfläche automatisch
- **Hot Reload**: Änderungen im Code werden sofort im Browser aktualisiert
- **Interaktive Widgets**: Buttons, Slider, Textfelder mit wenigen Zeilen Code

### Verfügbare Commands

- `/help` - Zeigt alle verfügbaren Commands
- `/sleep` - Startet Traum-Zusammenfassungs-Modus
- /config und noch viele mehr

## 🧠 Features

### Kernfunktionen
- **Episodisches Gedächtnis**: Speichert alle Konversationen als Vektoren in ChromaDB
- **RAG (Retrieval Augmented Generation)**: Findet relevante Erinnerungen basierend auf Kontext
- **Modulares Backend**: Wechsel zwischen Ollama (lokal) und Groq (Cloud)
- **Token-Streaming**: Flüssige Textausgabe im Terminal
- **Persistenz**: Erinnerungen bleiben nach Neustart erhalten

### Emotions-Engine
- **6 Emotionen**: Happiness, Trust, Energy, Curiosity, Frustration, Motivation
- **Dynamisches System**: Emotionen ändern sich basierend auf Konversationen
- **Kontext-Integration**: Emotions-Status wird in jeden Prompt eingebunden

### Advanced Features
- **Chain-of-Thought (CoT)**: Strukturiertes Denken für komplexere Antworten
- **Sentiment-Analyse**: Analysiert Stimmung der Eingaben
- **Query-Extraction**: Extrahiert Kerninformationen aus Nachrichten
- **Traum-Zusammenfassung**: Konsolidiert Erinnerungen im Schlafmodus
- **Markdown-Formatierung**: Saubere Darstellung von Code, Listen und Text


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

## 🆕 Letzte Updates (11. Januar 2026)

### GitHub Integration
- ✅ Projekt auf GitHub veröffentlicht: https://github.com/017pixel/CHAPPiE
- ✅ Git-Repository initialisiert und konfiguriert
- ✅ `.gitignore` optimiert (schützt sensible Daten und Build-Artefakte)

### Dokumentation
- ✅ README aktualisiert mit neuen Informationen
- ✅ Projektstruktur dokumentiert
- ✅ Installationsanleitung vervollständigt

### Vorherige Updates (10. Januar 2026)

#### Bug Fixes
- ✅ Commands funktionieren jetzt im Schlafmodus
- ✅ Sprachmodus kann mit `/text` oder `/stop` deaktiviert werden
- ✅ Intelligente Leertasten-Erkennung (kein PTT-Trigger während Texteingabe)
- ✅ Verbesserte Markdown-Formatierung (Apostrophe, Bindestriche, Quotes)

---

## 📄 Lizenz

Dies ist ein experimentelles Projekt. Verwendung auf eigene Gefahr.

## 🤝 Beitrag

Fork das Repository und erstelle einen Pull Request für Verbesserungen!

## 📞 Kontakt

Bei Fragen oder Problemen öffne ein Issue auf GitHub.

---

*Erstellt am 08. Januar 2026*  
*Aktualisiert am 11. Januar 2026*
