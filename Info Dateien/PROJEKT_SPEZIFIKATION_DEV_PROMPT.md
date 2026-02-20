# PROJEKT SPEZIFIKATION - CHAPPiE

## Projektname
**CHAPPiE** - Cognitive Hybrid Assistant with Personality, Persistance and Intelligence

---

## Projektübersicht

Ein KI-Agent mit **Brain-Inspired Multi-Agent Architecture**, der "lebendig" wirkt durch:
- Episodisches Gedächtnis mit Vergessenskurve
- Emotionale Verarbeitung
- Autonomes Lernen
- 7 spezialisierte Agenten

---

## Architektur

### Multi-Agent Brain System

```
┌─────────────────────────────────────────────────────────────────┐
│                    CHAPPiE DIGITAL BRAIN                        │
├─────────────────────────────────────────────────────────────────┤
│  SENSORY CORTEX ──> Input Classification                        │
│         │                                                        │
│         ├──> AMYGDALA (parallel) ──> Emotional Processing        │
│         └──> HIPPOCAMPUS (parallel) ──> Memory Operations        │
│         │                                                        │
│         v                                                        │
│  PREFRONTAL CORTEX ──> Orchestration & Response Strategy        │
│         │                                                        │
│         v (async)                                                │
│  BASAL GANGLIA + NEOCORTEX + MEMORY AGENT                       │
└─────────────────────────────────────────────────────────────────┘
```

### Agenten

| Agent | Modell | Funktion |
|-------|--------|----------|
| Sensory Cortex | llama-3.3-70b-instruct | Input-Klassifikation |
| Amygdala | nemotron-70b | Emotionale Analyse |
| Hippocampus | nemotron-70b | Memory-Operationen |
| Prefrontal Cortex | z-ai/glm5 | Haupt-Orchestrierung |
| Basal Ganglia | llama-3.3-70b-instruct | Reward/Learning |
| Neocortex | llama-3.3-70b-instruct | Langzeit-Memory |
| Memory Agent | nemotron-70b | Tool Calls |

---

## Tech Stack

- **Sprache:** Python 3.11+
- **Interface:** Streamlit Web UI + CLI
- **Datenbank:** ChromaDB (Vektor-Datenbank)
- **LLM Backend:** NVIDIA NIM (primär), Groq, Cerebras, Ollama
- **Embedding:** Sentence Transformers (all-MiniLM-L6-v2)

---

## Memory System

### Vergessenskurve (Ebbinghaus)

```
Retention = e^(-t/S)

- 20min: ~58% Retention
- 1h: ~44% Retention  
- 24h: ~33% Retention
- Spaced Repetition boostt Memory Strength
```

### Sleep Phase

- Alle 24 Stunden oder 100 Interaktionen
- Konsolidiert Memories von Hippocampus zu Neocortex
- Aktualisiert Context-Dateien

---

## Dateistruktur

```
brain/
├── agents/                 # 7 Brain Agents
│   ├── base_agent.py
│   ├── sensory_cortex.py
│   ├── amygdala.py
│   ├── hippocampus.py
│   ├── prefrontal_cortex.py
│   ├── basal_ganglia.py
│   ├── neocortex.py
│   └── memory_agent.py
├── brain_pipeline.py
└── nvidia_brain.py

memory/
├── sleep_phase.py
├── forgetting_curve.py
├── memory_engine.py
└── short_term_memory_v2.py

config/
├── brain_config.py
├── config.py
└── prompts.py
```

---

## API Provider

| Provider | Modelle | Limits |
|----------|---------|--------|
| NVIDIA NIM | z-ai/glm5, nemotron-70b, llama-3.3-70b | Höchste Free Limits |
| Groq | llama-3.3-70b-versatile | Schnell |
| Cerebras | llama-3.3-70b | Sehr schnell |
| Ollama | llama3:8b | Lokal |

---

## Commands

| Command | Funktion |
|---------|----------|
| `/sleep` | Memory Consolidation |
| `/soul` | Zeigt soul.md |
| `/user` | Zeigt user.md |
| `/prefs` | Zeigt Preferences |
| `/debug` | Toggle Debug Mode |

---

*Stand: Februar 2026 - Brain-Inspired Architecture*
