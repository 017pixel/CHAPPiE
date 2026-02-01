<div align="center">

# 🤖 CHAPPiE 2.0 - Cognitive Hybrid Assistant

[![GitHub](https://img.shields.io/badge/GitHub-017pixel%2FCHAPPiE-blue?logo=github)](https://github.com/017pixel/CHAPPiE)
[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

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

CHAPPiE 2.0 ist ein fortgeschrittener KI-Agent mit einem revolutionären **Zwei-Schritte Verarbeitungssystem**:

1. **Step 1:** Ein kleines KI-Modell analysiert User-Input und trifft Entscheidungen über Tool-Calls, Emotions-Updates und Memory-Management
2. **Step 2:** Ein großes Hauptmodell generiert die Antwort basierend auf allen Context-Dateien

### 🎯 Key Features

- **🧠 Zwei-Schritte Architektur:** Intent Analysis → Tool Execution → Response Generation
- **💾 Mehrschichtiges Gedächtnis:**
  - **Langzeit:** ChromaDB Vektor-Datenbank
  - **Kurzzeit:** JSON-basiert mit 24h TTL & Auto-Migration
  - **Context:** soul.md, user.md, CHAPPiEsPreferences.md
- **🎭 Emotions-Engine:** 6 Dimensionen (Happiness, Trust, Energy, Curiosity, Frustration, Motivation)
- **🔧 Smart Tool System:** Automatische Tool-Call Entscheidungen basierend auf Intent
- **🎓 Autonomes Training:** 24/7 Self-Training mit KI-Trainer
- **🐛 Debug Mode:** CLI immer an, Web UI togglebar

---

## 🏗️ Architektur

```
User Input
    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Intent Processor (NEUE MODELLE 2026)               │
│ • Cerebras: qwen-3-235b-a22b-instruct-2507                  │
│ • Groq: openai/gpt-oss-120b                                 │
│ • Ollama: gpt-oss-20b                                       │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ JSON Output:                                                │
│ • Intent Analysis (Type, Confidence, Entities)              │
│ • Tool Calls (update_user, update_soul, update_prefs)       │
│ • Emotions Update (Delta + Reason)                          │
│ • Short-Term Entries (Content, Category, Importance)        │
│ • Context Requirements (Welche .md Dateien nötig)           │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ Ausführung:                                                 │
│ • Tool Calls → Aktualisiert .md Dateien                     │
│ • Emotions Update → Passt Emotionen an                      │
│ • Short-Term → Speichert in JSON (24h TTL)                  │
│ • Migration → Ältere Einträge → ChromaDB                    │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Response Generator (Hauptmodell)                   │
│ • Cerebras: llama-3.3-70b                                   │
│ • Groq: moonshotai/kimi-k2-instruct-0905                    │
│ • Ollama: llama3:8b oder größere Modelle                    │
│ Input: Context (soul + user + prefs + short + long)        │
│ Output: Finale Antwort                                      │
└─────────────────────────────────────────────────────────────┘
    ↓
Response an User
```

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

## 📝 Changelog

### Version 2.0 Update (Februar 2026)
- ✅ **NEUE MODELLE für Step 1:**
  - Cerebras: qwen-3-235b-a22b-instruct-2507
  - Groq: openai/gpt-oss-120b
  - Ollama: gpt-oss-20b (lokal)
- ✅ **Context UI verbessert:** Direkte Anzeige von Soul, User, Prefs
- ✅ **ChromaDB Health Check:** Detaillierte Fehleranzeige statt generischer Warnung
- ✅ **Intent Processor optimiert:** Bessere Tool Call Verarbeitung

### Version 2.0 (2026)
- ✅ **Zwei-Schritte Verarbeitung:** Intent Processor + Response Generator
- ✅ **Neue Context-Dateien:** soul.md, user.md, CHAPPiEsPreferences.md
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

## 📄 Lizenz

Dieses Projekt ist unter der MIT Lizenz lizenziert.

---

<div align="center">

**[⬆ Nach oben](#-chappie-20---cognitive-hybrid-assistant)**

Made with ❤️ by [017pixel](https://github.com/017pixel)

</div>
