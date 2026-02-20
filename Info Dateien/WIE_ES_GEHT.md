# WIE ES GEHT - CHAPPiE Projekt-Dokumentation

Willkommen unter der Haube von **CHAPPiE**! Hier erfährst du, wie der KI-Agent technisch funktioniert, wie die Komponenten zusammenspielen und welche Mechanismen ihn "lebendig" machen.

---

## Architektur

Das System basiert auf einer modularen Architektur mit **Brain-Inspired Multi-Agent System**:

### 1. Das digitale Gehirn (`brain/agents/`)

CHAPPiE nutzt 7 spezialisierte Agenten, die von Gehirnregionen inspiriert sind:

| Agent | Gehirnregion | Funktion |
|-------|--------------|----------|
| **Sensory Cortex** | Sensorischer Cortex | Input-Klassifikation, Spracherkennung, Dringlichkeit |
| **Amygdala** | Limbisches System | Emotionale Verarbeitung, Memory-Verstärkung |
| **Hippocampus** | Medialer Temporallappen | Memory-Encoding, Retrieval, Konsolidierung |
| **Prefrontal Cortex** | Frontallappen | Zentrale Orchestrierung, Working Memory |
| **Basal Ganglia** | Basalganglien | Reward-basiertes Lernen, Dopamin-Signale |
| **Neocortex** | Neocortex | Langzeit-Memory, semantisches Wissen |
| **Memory Agent** | - | Tool-Call Entscheidungen |

### Processing Pipeline

```
USER INPUT
    |
    v
[SENSORY CORTEX] --> Input-Klassifikation
    |
    +---> [AMYGDALA] (parallel) --> Emotionale Analyse
    |
    +---> [HIPPOCAMPUS] (parallel) --> Memory-Operationen
    |
    v
[PREFRONTAL CORTEX] --> Response-Strategie
    |
    v
RESPONSE TO USER
    |
    v (async)
[BASAL GANGLIA] + [NEOCORTEX] + [MEMORY AGENT]
```

### 2. Das Gedächtnis (`memory/`)

CHAPPiE vergisst nichts - oder fast nichts.

- **Langzeitgedächtnis (ChromaDB):** Jede Interaktion wird vektorisiert (Embeddings) und gespeichert.
- **Kurzzeitgedächtnis (`short_term_memory_v2.py`):** JSON-basiert mit 24h TTL und Auto-Migration.
- **Context-Dateien:** `soul.md`, `user.md`, `CHAPPiEsPreferences.md`
- **Vergessenskurve:** Ebbinghaus-Implementation mit Spaced Repetition

### 3. Die Emotionen (`emotions_engine.py`)

CHAPPiE ist keine statische Maschine.

- **6 Dimensionen:** Happiness, Trust, Energy, Curiosity, Frustration, Motivation
- **Sentiment-Analyse:** Jede User-Nachricht wird analysiert
- **Amygdala-Integration:** Emotionale Erinnerungen werden verstärkt

---

## Sleep Phase (Memory Consolidation)

Wie das menschliche Gehirn während des Schlafes Erinnerungen konsolidiert:

- **Trigger:** Alle 24 Stunden oder alle 100 Interaktionen
- **Tasks:**
  1. Hippocampus -> Neocortex Transfer
  2. Ebbinghaus Vergessenskurve anwenden
  3. Spaced Repetition Scheduling
  4. Context-Dateien aktualisieren

---

## Der Trainingsmodus (`Chappies_Trainingspartner`)

Autonomer Trainings-Loop für 24/7 Betrieb:

- **Trainer-Agent:** Simuliert verschiedene User-Personas
- **Curriculum:** Dynamischer Lehrplan mit Themen-Wechsel
- **Daemon-Modus:** Läuft als System-Service auf Linux

---

## Wichtige Dateien

```
brain/
├── agents/                    # 7 Brain-Inspired Agents
│   ├── sensory_cortex.py
│   ├── amygdala.py
│   ├── hippocampus.py
│   ├── prefrontal_cortex.py
│   ├── basal_ganglia.py
│   ├── neocortex.py
│   └── memory_agent.py
├── brain_pipeline.py          # Main Integration
└── nvidia_brain.py            # NVIDIA NIM Backend

memory/
├── sleep_phase.py             # Memory Consolidation
├── forgetting_curve.py        # Ebbinghaus Implementation
├── memory_engine.py           # ChromaDB Integration
└── short_term_memory_v2.py    # JSON-based STM

config/
├── brain_config.py            # Agent Model Configuration
├── config.py                  # Main Settings
└── prompts.py                 # System Prompts
```

---

## Modell-Konfiguration

NVIDIA NIM wird primär genutzt (höhere Free Limits):

| Agent | Modell |
|-------|--------|
| Sensory Cortex | meta/llama-3.3-70b-instruct |
| Amygdala | nvidia/llama-3.1-nemotron-70b |
| Hippocampus | nvidia/llama-3.1-nemotron-70b |
| Prefrontal Cortex | z-ai/glm5 |
| Basal Ganglia | meta/llama-3.3-70b-instruct |
| Neocortex | meta/llama-3.3-70b-instruct |
| Memory Agent | nvidia/llama-3.1-nemotron-70b |

---

*Stand: Februar 2026 - Brain-Inspired Multi-Agent Architecture*
