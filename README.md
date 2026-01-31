# 🤖 CHAPiE - AI Chat Assistant

> Ein KI-Agent mit episodischem Gedächtnis, Emotions-Engine und autonomem Trainingsmodus.

## 🔗 Repository

[![GitHub](https://img.shields.io/badge/GitHub-017pixel%2FCHAPPiE-blue?logo=github)](https://github.com/017pixel/CHAPPiE)

## 📋 Überblick

CHAPiE ist ein fortgeschrittener KI-Agent, der entwickelt wurde, um natürliche, kontextbewusste Gespräche zu führen. Er nutzt ein **episodisches Gedächtnis** (ChromaDB), um sich an vergangene Interaktionen zu erinnern, und eine **Emotions-Engine**, die sein Verhalten dynamisch anpasst. Zusätzlich verfügt er über einen **autonomen Trainingsmodus**, mit dem er sich selbstständig verbessern kann.

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
│  │             (ChromaDB + Short Term)                  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Key Features (Update 2026)

### 🧠 Intelligentes Gedächtnis
- **Langzeitgedächtnis:** Speicherung in Vektor-Datenbank (ChromaDB) für semantische Suche.
- **Kurzzeitgedächtnis:** Automatische Verwaltung aktueller Kontext-Infos mit Auto-Cleanup nach 24h.
- **Traum-Modus:** Konsolidierung von Erinnerungen während "Schlafphasen" (`/sleep`).

### 🎓 Autonomes Training
- **Trainingspartner:** Ein KI-Trainer simuliert User-Interaktionen basierend auf Personas.
- **Curriculum:** Definierbare Lernziele und Themenbereiche.
- **24/7 Server Mode:** Robuster Daemon für dauerhaftes Training auf Linux-Servern.

### ❤️ Emotions & Persönlichkeit
- **6 Dimensionen:** Happiness, Trust, Energy, Curiosity, Frustration, Motivation.
- **Dynamische Anpassung:** Emotionen beeinflussen den Antwortstil in Echtzeit.

### 🛡️ Sicherheit & Zuverlässigkeit
- **API Security:** Strikte Trennung von Code und Keys (werden nicht ins Backup kopiert).
- **Backup System v2.0:** Sichere Backups inklusive Datenbank-Archivierung (ZIP).
- **Service Deployment:** Ready-to-use Systemd Services für Web-UI und Training.

## 📁 Projektstruktur

```
CHAPiE/
├── app.py                 # Hauptanwendung (Web-UI)
├── main.py                # CLI-Version
├── backup_project.py      # Backup-Tool v2.0
├── deploy_training.sh     # Deployment Manager Script
├── config/
│   ├── secrets.py         # ⚠️ API-Keys (wird nicht committed)
│   ├── prompts.py         # System Prompts
│   └── APIs/              # API-Konfigurationen
├── memory/
│   ├── memory_engine.py   # ChromaDB Core
│   ├── short_term_memory.py # Kontext-Speicher
│   └── emotions_engine.py # Emotions-Logik
├── web_infrastructure/    # Streamlit UI Komponenten
└── Chappies_Trainingspartner/ # Autonomes Training
```

## 🚀 Installation & Start

### 1. Setup
```bash
git clone https://github.com/017pixel/CHAPPiE.git
cd CHAPPiE
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Konfiguration
Kopiere `config/secrets_example.py` nach `config/secrets.py` und trage deine API-Keys (Groq, Cerebras, Ollama) ein.

### 3. Starten (Web-UI)
```bash
streamlit run app.py
```
Öffne http://localhost:8501 im Browser.

## 🛠️ Server Deployment (Ubuntu)

CHAPiE ist "Server-Ready". Nutze den Deployment Manager:

```bash
chmod +x deploy_training.sh

# Services installieren (Web + Training)
./deploy_training.sh install-service

# Starten
./deploy_training.sh service-start

# Status prüfen
./deploy_training.sh service-status
```

Detaillierte Anleitung: Siehe `Info Dateien/SSH_Befehle_CHAPPiE.md`.

## 🤝 Beitrag

Pull Requests sind willkommen! Bitte beachte die `Verbesserungsplan.md` für offene Tasks.

## 📄 Lizenz

Experimentelles Projekt. Nutzung auf eigene Gefahr.

---
*Maintained by 017pixel & CodeX*
