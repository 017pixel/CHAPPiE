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
├── web_infrastructure/    # 🆕 Modulare Web-UI
│   ├── components.py      # Wiederverwendbare UI-Elemente
│   ├── chat_ui.py         # Chat-Interface
│   └── ...
├── memory/
│   ├── memory_engine.py   # ChromaDB Wrapper (Vektordatenbank)
│   ├── emotions_engine.py # Emotions-Engine (6 Emotionen)
│   └── chat_manager.py    # Chat-Session Management
├── brain/
│   ├── base_brain.py      # Abstrakte LLM-Klasse
│   ├── ollama_brain.py    # Ollama Implementation (lokal)
│   ├── groq_brain.py      # Groq Cloud Implementation
│   ├── deep_think.py      # Deep Think Engine
│   └── response_parser.py # Antwort-Parsing & Markdown
├── data/
│   ├── chat_sessions/     # Persistierte Chat-Sessions
│   └── chroma_db/         # Vektordatenbank (automatisch erstellt)
├── app.py                 # GUI-Anwendung (Startpunkt)
├── main.py                # CLI Haupt-Loop
├── Chappies_Trainingspartner/ # 🆕 Autonomes Training
│   ├── training_daemon.py # 24/7 Hintergrund-Dienst
│   ├── training_loop.py   # Trainings-Logik
│   └── ...
├── deploy_training.sh     # Deployment-Script für Linux/Ubuntu
├── chappie-training.service # Systemd-Service Template
├── .gitignore             # Git-Ignore Regeln (Schützt Secrets!)
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

1. Kopiere `config/secrets_example.py` nach `config/secrets.py`.
2. Öffne `config/secrets.py` und trage deine Einstellungen/Keys ein.

Die `secrets.py` ist automatisch im `.gitignore` und wird nicht auf GitHub geladen!

### 4. Ollama einrichten (für lokale Modelle)

```bash
# Ollama installieren: https://ollama.ai
# Modelle herunterladen:
ollama pull llama3:70b
ollama pull qwen2.5:1.5b
```

## 🆕 Performance Update (Januar 2026)

Das System wurde massiv für lokale Nutzung optimiert:
*   **Dual-Brain Architektur:** Nutzt das leistungsstarke `llama3:70b` für den Chat, aber das pfeilschnelle `qwen2.5:1.5b` für Hintergrundaufgaben (Träume, Analyse).
*   **Smart Query Extraction:** Einfache Fragen ("Wie geht es dir?") umgehen das LLM komplett -> Sofortige Antwort ohne Wartezeit.
*   **Modulare Web-UI:** Die Benutzeroberfläche wurde komplett refactored und ist nun extrem reaktionsschnell dank asynchronem Speichern.

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

- **Automatische UI**: Streamlit erstellt die Benutzeroberfläche automatisch
- **Hot Reload**: Änderungen im Code werden sofort im Browser aktualisiert
- **Interaktive Widgets**: Buttons, Slider, Textfelder mit wenigen Zeilen Code

### 🎮 Verfügbare Commands

- `/help` - Zeigt alle verfügbaren Commands
- `/sleep` - Startet Traum-Zusammenfassungs-Modus
- `/think` - Startet Deep Think Modus

### 🛡️ Server Deployment (24/7 Training)

Für den autonomen Betrieb auf Ubuntu-Servern:

1. Nutze `deploy_training.sh` zur Steuerung:
   ```bash
   ./deploy_training.sh start    # Startet den Daemon via nohup
   ./deploy_training.sh status   # Zeigt Logs und Status
   ```

2. **Systemd Integration** (Empfohlen):
   ```bash
   ./deploy_training.sh install-service  # Installiert CHAPiE als System-Dienst
   ./deploy_training.sh service-start    # Startet den Dienst permanent
   ```

## 🧠 Features

### Kernfunktionen
- **Episodisches Gedächtnis**: Speichert alle Konversationen als Vektoren in ChromaDB
- **RAG (Retrieval Augmented Generation)**: Findet relevante Erinnerungen basierend auf Kontext
- **Modulares Backend**: Wechsel zwischen Ollama (lokal), Groq (Cloud) und Cerebras (High-Speed)
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
*Aktualisiert am 25. Januar 2026*
