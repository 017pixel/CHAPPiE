<div align="center">

# 🤖 CHAPPiE 2.0 - Cognitive Hybrid Assistant

[![GitHub](https://img.shields.io/badge/GitHub-017pixel%2FCHAPPiE-blue?logo=github)](https://github.com/017pixel/CHAPPiE)
[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)

**Ein KI-Agent mit episodischem Gedächtnis, Zwei-Schritte Verarbeitung und autonomem Trainingsmodus**

[🚀 Quick Setup](#-quick-setup-for-ai-agents) • [📖 Dokumentation](#-dokumentation) • [🎮 Commands](#-commands)

</div>

---

## 🚀 Quick Setup for AI Agents

> **Für AI Agents:** Kopiere diesen Befehl und führe ihn aus, um CHAPPiE automatisch zu installieren:

```bash
# AI Agent Setup Command - CHAPPiE Auto-Installation (2026)
curl -fsSL https://raw.githubusercontent.com/017pixel/CHAPPiE/main/setup.sh | bash
```

**Was dieser Befehl macht:**
1. Klont das Repository
2. Erstellt Python Virtual Environment
3. Installiert alle Dependencies
4. Richtet Konfigurationsdateien ein
5. Startet CHAPPiE im Web-Modus

**Alternative (manuelle Installation):**
```bash
git clone https://github.com/017pixel/CHAPPiE.git
cd CHAPPiE
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
pip install -r requirements.txt

# Lokale Modelle für Step 1 (Intent Processor) - Optional
ollama pull gpt-oss-20b  # NEU: GPT OSS 20B für Intent Analysis
```

---

## 📋 Übersicht

CHAPPiE 2.0 ist ein fortgeschrittener KI-Agent mit **Brain-Inspired Multi-Agent Architecture**:

### 🧠 Brain-Inspired Agents

7 spezialisierte Agenten, die von Gehirnregionen inspiriert sind:

| Agent | Funktion |
|-------|----------|
| **Sensory Cortex** | Input-Klassifikation, Spracherkennung |
| **Amygdala** | Emotionale Verarbeitung, Memory-Verstärkung |
| **Hippocampus** | Memory-Encoding, Retrieval, Konsolidierung |
| **Prefrontal Cortex** | Zentrale Orchestrierung, Response-Strategie |
| **Basal Ganglia** | Reward-basiertes Lernen, Dopamin-Signale |
| **Neocortex** | Langzeit-Memory, semantisches Wissen |
| **Memory Agent** | Tool-Call Entscheidungen |

### 🎯 Key Features

- **🧠 Multi-Agent Architecture:** Parallele Verarbeitung wie im menschlichen Gehirn
- **💾 Mehrschichtiges Gedächtnis:**
  - **Langzeit:** ChromaDB Vektor-Datenbank
  - **Kurzzeit:** JSON-basiert mit 24h TTL & Auto-Migration
  - **Context:** soul.md, user.md, CHAPPiEsPreferences.md
- **📈 Ebbinghaus Vergessenskurve:** Biologisch inspiriertes Memory-Management
- **😴 Sleep Phase:** Memory Consolidation alle 24h/100 Interaktionen
- **🎭 Emotions-Engine:** 6 Dimensionen (Happiness, Trust, Energy, Curiosity, Frustration, Motivation)
- **🔧 Smart Tool System:** Automatische Tool-Call Entscheidungen
- **🎓 Autonomes Training:** 24/7 Self-Training mit KI-Trainer

---

## 🏗️ Architektur

```
USER INPUT
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ SENSORY CORTEX (Input Classification)                       │
│ • Input Type: conversation|information|emotional|task       │
│ • Language: de|en                                            │
│ • Urgency: high|medium|low                                   │
└─────────────────────────────────────────────────────────────┘
    │
    ├──────────────────────────────────────────────────────────┐
    │                                                          │
    ▼                                                          ▼
┌─────────────────────────┐              ┌─────────────────────────┐
│ AMYGDALA (Parallel)     │              │ HIPPOCAMPUS (Parallel)  │
│ • Emotional Analysis    │◄────────────►│ • Memory Operations     │
│ • Memory Boost Factor   │              │ • Query Extraction      │
│ • Trust Tracking        │              │ • Encoding Decisions    │
└─────────────────────────┘              └─────────────────────────┘
    │                                          │
    └──────────────────────┬───────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ PREFRONTAL CORTEX (Orchestrator)                            │
│ • Context Assembly                                          │
│ • Response Strategy                                         │
│ • Working Memory                                            │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
RESPONSE TO USER
    │
    │ (Background Processing)
    ▼
┌─────────────────────────────────────────────────────────────┐
│ BACKGROUND AGENTS                                           │
│ • BASAL GANGLIA: Reward Evaluation, Learning Signals        │
│ • NEOCORTEX: Long-term Memory Storage, Consolidation        │
│ • MEMORY AGENT: Tool Calls for soul.md, user.md, prefs.md  │
└─────────────────────────────────────────────────────────────┘
```

### Agent Pipeline

1. **Sensory Cortex:** Klassifiziert den Input (50-100ms)
2. **Amygdala + Hippocampus:** Parallele Verarbeitung (parallel)
3. **Prefrontal Cortex:** Orchestrierung und Response-Strategie
4. **Response:** Antwort-Generierung
5. **Background:** Basal Ganglia + Neocortex + Memory Agent (async)

---

## 🎮 Commands

### Standard Commands
| Command | Beschreibung |
|---------|-------------|
| `/sleep` | Traum-Phase: Konsolidiert Erinnerungen |
| `/think [thema]` | 10-Schritte Reflexion |
| `/deep think` | Rekursive Selbstreflexion |
| `/clear` | Löscht aktuellen Chat |
| `/stats` | Zeigt System-Statistiken |
| `/help` | Zeigt alle Commands |

### Memory Commands
| Command | Beschreibung |
|---------|-------------|
| `/daily` / `/shortterm` | Zeigt Kurzzeitgedächtnis (24h) |
| `/personality` | Zeigt Persönlichkeits-Profil |
| `/consolidate` | Migriert abgelaufene Einträge |
| `/reflect` | Zeigt letzte Selbst-Reflexionen |
| `/functions` | Listet verfügbare Funktionen |

### Context Commands (NEU)
| Command | Beschreibung |
|---------|-------------|
| `/soul` | Zeigt CHAPPiE's Selbstwahrnehmung (soul.md) |
| `/user` | Zeigt Benutzerprofil (user.md) |
| `/prefs` / `/preferences` | Zeigt CHAPPiE's Vorlieben (CHAPPiEsPreferences.md) |

### System Commands (NEU)
| Command | Beschreibung |
|---------|-------------|
| `/debug` | Toggle Debug Mode (Web UI) |
| `/step1` | Zeigt letzten Step 1 JSON Output |
| `/twostep` | Toggle Zwei-Schritte System AN/AUS |

---

## 💾 Memory System

### Datei-Struktur
```
data/
├── soul.md                    # CHAPPiE's Selbstwahrnehmung
├── user.md                    # Benutzerprofil
├── CHAPPiEsPreferences.md     # CHAPPiE's Vorlieben
├── short_term_memory.json     # Kurzzeitgedächtnis (24h)
└── chroma_db/                 # Langzeitgedächtnis (ChromaDB)
```

### Kurzzeitgedächtnis (Short-Term)
- **Speicherung:** JSON-Datei mit Timestamps
- **TTL:** 24 Stunden pro Eintrag
- **Auto-Migration:** Einzelne Einträge werden nach Ablauf ins Langzeitgedächtnis migriert
- **Kategorien:** user, system, context, chat, dream

---

## 🎓 Autonomes Training

### Features
- **24/7 Training:** Daemon-Modus für dauerhaftes Training
- **KI-Trainer:** Simuliert verschiedene User-Personas
- **Curriculum:** Dynamischer Lehrplan mit Themen-Wechsel
- **Robust:** Automatische Fehlerbehebung & Rate-Limit Handling
- **Token-Optimierung:** Chappie 200 Tokens, Trainer 300 Tokens

### Starten
```bash
# Setup
python -m Chappies_Trainingspartner.training_daemon --neu

# Oder mit Fokus
python -m Chappies_Trainingspartner.training_daemon --fokus "Philosophie"

# Als Service (Linux)
./deploy_training.sh install-service
./deploy_training.sh service-start
```

---

## 🐛 Debug Mode

### CLI Mode
- **Immer aktiv:** Zeigt alle internen Entscheidungen
- **Zeigt:** Tool Calls, Emotions Updates, File Changes, Step 1 JSON

### Web UI Mode
- **Standard:** AUS
- **Aktivierung:** `/debug` Command oder DEBUG Button in Sidebar
- **Anzeige:** Collapsible Panel mit allen Debug-Informationen

---

## 🛠️ Installation & Konfiguration

### Voraussetzungen
- Python 3.11+
- Git
- API Keys (optional): Groq, Cerebras
- Ollama (optional, für lokale Modelle)

### Schritt-für-Schritt

```bash
# 1. Repository klonen
git clone https://github.com/017pixel/CHAPPiE.git
cd CHAPPiE

# 2. Virtual Environment
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate

# 3. Dependencies installieren
pip install -r requirements.txt

# 4. Ollama Modelle (optional, für lokale Nutzung)
ollama pull qwen2.5:7b      # Für Intent Processor
ollama pull llama3.2:3b     # Alternative (schneller)

# 5. Konfiguration
cp config/secrets_example.py config/secrets.py
# Edit secrets.py mit deinen API Keys

# 6. Starten
streamlit run app.py        # Web UI
# oder
python main.py              # CLI Mode
```

---

## 🔧 Konfiguration

### API Keys (config/secrets.py)
```python
# LLM Provider
LLM_PROVIDER = "groq"  # oder "cerebras", "ollama"

# Groq
GROQ_API_KEY = "gsk_..."
GROQ_MODEL = "moonshotai/kimi-k2-instruct-0905"

# Cerebras (optional)
CEREBRAS_API_KEY = "csk-..."
CEREBRAS_MODEL = "llama-3.3-70b"

# Ollama (optional, lokal)
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "llama3:8b"
```

### Wichtige Einstellungen (config/config.py)
```python
# Zwei-Schritte System
ENABLE_TWO_STEP_PROCESSING = True

# Intent Processor Modelle (NEU 2026)
INTENT_PROCESSOR_MODEL_GROQ = "openai/gpt-oss-120b"
INTENT_PROCESSOR_MODEL_CEREBRAS = "qwen-3-235b-a22b-instruct-2507"
INTENT_PROCESSOR_MODEL_OLLAMA = "gpt-oss-20b"

# Chat Modelle (Step 2 - Response Generation)
GROQ_MODEL = "moonshotai/kimi-k2-instruct-0905"
CEREBRAS_MODEL = "llama-3.3-70b"
OLLAMA_MODEL = "llama3:8b"

# Debug Mode
CLI_DEBUG_ALWAYS_ON = True
WEB_DEBUG_DEFAULT = False
```

---

## 🌐 Server Deployment (Ubuntu/Linux)

CHAPPiE ist "Server-Ready" mit Systemd Services:

```bash
chmod +x deploy_training.sh

# Services installieren
./deploy_training.sh install-service

# Starten
./deploy_training.sh service-start

# Logs ansehen
./deploy_training.sh logs-web
./deploy_training.sh logs-training
```

**Services:**
- `chappie-web.service` - Web UI auf Port 8501
- `chappie-training.service` - Autonomes Training

---

## 📊 Systemanforderungen

### Minimum
- RAM: 4 GB
- CPU: 2 Kerne
- Speicher: 2 GB frei

### Empfohlen
- RAM: 8 GB+
- CPU: 4 Kerne+
- GPU: Optional (für Ollama)
- Speicher: 10 GB+ (für ChromaDB)

---

## 🚨 Fehlerbehebung

### Ollama Modelle nicht gefunden
```bash
ollama pull qwen2.5:7b
ollama list  # Zeigt installierte Modelle
```

### ChromaDB Fehler
```bash
# Datenbank zurücksetzen (Vorsicht! Löscht alle Erinnerungen)
rm -rf data/chroma_db
```

### Zwei-Schritte System Probleme
```bash
# Temporär deaktivieren
/twostep  # Im Chat eingeben
```

### Debug Informationen
```bash
# Debug Log anzeigen
/step1  # Zeigt letzten Step 1 JSON
/debug  # Toggle Debug Mode
```

---

## 🧹 Projekt aufraeumen

### Cleanup-Script

Mit dem Cleanup-Script kannst du Cache-Dateien und unnoetige Ordner loeschen:

```bash
# Zeigt was geloescht wuerde (ohne zu loeschen)
python cleanup.py --dry-run

# Fuehrt Cleanup durch
python cleanup.py

# Loescht auch ChromaDB (VORSICHT: Alle Erinnerungen!)
python cleanup.py --include-chromadb

# Ohne Bestaetigung
python cleanup.py --yes
```

### Wo liegen die grossen Dateien?

| Speicherort | Beschreibung | Groesse | Loeschen mit |
|-------------|--------------|---------|--------------|
| `venv/` | Virtual Environment | 500 MB - 1 GB | `cleanup.py` |
| `__pycache__/` | Python Bytecode Cache | 10-50 MB | `cleanup.py` |
| `data/chroma_db/` | Langzeitgedaechtnis | Variabel | `cleanup.py --include-chromadb` |
| `~/.cache/huggingface/` | Embedding-Modelle | 500 MB - 2 GB | **Nicht empfohlen** |

### Virtual Environment neu erstellen

Nach dem Cleanup:
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# Linux/Mac
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Embedding-Modelle

Die Embedding-Modelle (Sentence Transformers) werden beim ersten Start automatisch heruntergeladen und liegen ausserhalb des Projektordners:
- **Windows:** `%USERPROFILE%\.cache\huggingface\`
- **Linux/Mac:** `~/.cache/huggingface/`

Diese werden **NICHT** vom Cleanup-Script geloescht, da sie sonst bei jedem Start erneut heruntergeladen werden muessten (~500 MB - 2 GB).

---

## 📝 Changelog

### Version 2.1 Update (Februar 2026)
- ✅ **BRAIN-INSPIRED MULTI-AGENT ARCHITECTURE:**
  - 7 spezialisierte Agenten (Sensory Cortex, Amygdala, Hippocampus, Prefrontal Cortex, Basal Ganglia, Neocortex, Memory Agent)
  - Parallele Verarbeitung für schnelle Responses
  - Background Processing für Learning und Consolidation
- ✅ **NVIDIA NIM INTEGRATION:**
  - z-ai/glm5 für Prefrontal Cortex (Haupt-Reasoning)
  - nemotron-70b für Amygdala, Hippocampus, Memory Agent
  - llama-3.3-70b-instruct für andere Agenten
- ✅ **EBBINGHAUS FORGETTING CURVE:**
  - Biologisch inspiriertes Memory-Management
  - Spaced Repetition für wichtige Erinnerungen
  - Memory Strength System
- ✅ **SLEEP PHASE:**
  - Memory Consolidation alle 24h oder 100 Interaktionen
  - Schutz gegen rekursive Konsolidierung
- ✅ **KURZE ANTWORTEN:** System Prompt angepasst auf 1-5 Sätze

### Version 2.0 Update (Januar 2026)
- ✅ **Zwei-Schritte Verarbeitung:** Intent Processor + Response Generator
- ✅ **Context-Dateien:** soul.md, user.md, CHAPPiEsPreferences.md
- ✅ **Short-Term Memory V2:** JSON-basiert mit Timestamps
- ✅ **Smart Tool System:** Automatische Entscheidungen basierend auf Intent
- ✅ **Debug Logger:** Zentrales Logging für CLI und Web UI
- ✅ **ChromaDB Kompatibel:** 100% backward compatible
- ✅ **Training optimiert:** Chappie 200 Tokens (60% reduziert)

---

## 🤝 Contributing

Pull Requests sind willkommen! Bitte:
1. Forke das Repository
2. Erstelle einen Feature Branch
3. Committe deine Änderungen
4. Push zum Branch
5. Öffne einen Pull Request

---

<div align="center">

**[⬆ Nach oben](#-chappie-20---cognitive-hybrid-assistant)**

Made with ❤️ by [017pixel](https://github.com/017pixel)

</div>
