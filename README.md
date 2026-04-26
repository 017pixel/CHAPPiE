# CHAPPiE

CHAPPiE ist eine experimentelle Cognitive-Agent-Architektur, die untersucht, wie sich Verhalten durch die Kombination von LLMs, episodischem Gedächtnis und einer kontinuierlichen Life-Simulation entwickeln kann.

Im Gegensatz zu klassischen Chatbots besitzt CHAPPiE interne Zustände wie Emotionen, Bedürfnisse und langfristige Ziele. Er entwickelt sein Verhalten über Zeit durch Memory, Simulation und Training weiter.

**Ein Agent, der sich an vergangene Interaktionen erinnert, emotionale Zustände entwickelt und sein Verhalten langfristig anpasst.**

---

## Das Problem

LLMs haben kein echtes Gedächtnis. Jede Sitzung fängt bei Null an. Sie haben keine Entwicklung, keine Bedürfnisse, keine emotionale Kontinuität. Sie reagieren – sie erleben nicht.

## Die Idee

CHAPPiE setzt auf drei Säulen, die zusammen ein konsistentes Innenleben erzeugen:

| Säule | Was sie bringt | Forschungsfeld |
|---|---|---|
| **Episodisches Gedächtnis** | Vergangene Interaktionen werden gespeichert, retrieved, verdichtet und vergessen | Memory-Augmented LLMs |
| **Life-Simulation** | Das Life-System bestimmt kontinuierlich Prioritäten zwischen konkurrierenden Zielen und beeinflusst so Verhalten über mehrere Interaktionen hinweg | Agent Systems, Simulation-based AI |
| **Emotion Steering** | Emotionen werden nicht nur im Prompt beschrieben, sondern direkt in die Hidden States des Modells injiziert | Affective Computing |

## Konkretes Szenario

> Ein Nutzer beleidigt den Agenten wiederholt. CHAPPiE speichert diese Interaktionen episodisch, verstärkt negative emotionale Zustände und verändert langfristig seinen Ton und seine Reaktionen gegenüber diesem Nutzer. Vertrauen sinkt, Frustration steigt – bis hin zu einem „crashout"-Modus: kurze, gereizte Antworten ohne Floskeln. Erst wenn der Nutzer sein Verhalten ändert, kann sich CHAPPiE über mehrere Interaktionen hinweg wieder öffnen.

## Was CHAPPiE besonders macht

- **Brain-Pipeline** mit spezialisierten Modulen (Sensory, Amygdala, Hippocampus, Prefrontal Cortex) und einem Global Workspace, der Signale nach Salience priorisiert
- **Life-System** mit Homeostasis, Goal Competition, Habit Dynamics, Attachment-Modell und autobiografischer Timeline
- **Layer Steering** (Activation Steering): Emotionen werden als Vektoren in die neuronalen Schichten des lokalen Modells injiziert – nicht nur als Text im Prompt
- **Sleep-Phase** mit Replay, Verdichtung und Vergessenskurve – echtes "Gedächtnisdenken"
- **Causal Trace**: Jede Antwort ist nachvollziehbar – Input, Memory, Emotion, Steering, Ton
- **Token-Level Streaming**: Antworten werden Wort für Wort live in die UI gestreamt, nicht als Block
- **Message Queue**: Während CHAPPiE antwortet, koennen neue Nachrichten in eine Warteschlange gelegt und automatisch abgeschickt werden
- **3D Emotion Lattice**: Lebendiger 3D-Orb, der sich in Echtzeit an alle 7 Emotionen anpasst – Farbe, Oberflaeche, Puls und Partikel reagieren auf emotionale Zustaende

## Erste Beobachtungen

Agenten mit aktivem Memory und Life-System zeigen konsistentere Persönlichkeitsverläufe über mehrere Sessions hinweg als reine Prompt-basierte Ansätze. Emotionale Zustände bleiben über Interaktionen hinweg stabil, und das Verhalten passt sich nachvollziehbar an wiederkehrende Muster an.

---

## Architektur

```mermaid
flowchart TD
    User["User Input"] --> LifePrep["Life Simulation\nprepare_turn"]
    LifePrep --> Sensory["Sensory Cortex"]
    Sensory --> Amygdala["Amygdala"]
    Sensory --> Hippocampus["Hippocampus"]
    Amygdala --> MemoryEngine["Memory Engine"]
    Hippocampus --> MemoryEngine
    Amygdala --> GW["Global Workspace"]
    Hippocampus --> GW
    MemoryEngine --> GW
    LifePrep --> GW
    GW --> Prefrontal["Prefrontal Cortex"]
    Prefrontal --> Steering["Steering Manager"]
    Prefrontal --> FinalPrompt["Finaler Prompt"]
    Steering --> FinalPrompt
    FinalPrompt --> LLM["LLM-Call\n(vLLM mit Layer Editing\noder Cloud-API)"]
    LLM --> LifeFinal["Life Simulation\nfinalize_turn"]
    LLM --> Response["Antwort +\nDebug + Causal Trace"]
    LifeFinal --> Response

    classDef input fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
    classDef brain fill:#f3e5f5,stroke:#4a148c,stroke-width:2px,color:#000
    classDef output fill:#fce4ec,stroke:#880e4f,stroke-width:2px,color:#000
    classDef steering fill:#fff9c4,stroke:#f57f17,stroke-width:2px,color:#000

    class User,LifePrep input
    class Sensory,Amygdala,Hippocampus,MemoryEngine,GW,Prefrontal brain
    class FinalPrompt,LLM,LifeFinal,Response output
    class Steering steering
```

### Emotion-Steering (lokal)

```mermaid
flowchart LR
    E["7 Emotionen\n0-100"] --> VAD["VAD-Mapping"]
    VAD --> Alpha["Alpha\n44-56: tot\n56-74: sigmoid\n74+: max"]
    Alpha --> Modes["Composite Modes\ncrashout, warm, ..."]
    Modes --> Layers["Layer-Profile\nL10-26 bei 4B"]
    Layers --> Hook["Forward Pre-Hook\nhidden += alpha * vec"]
    Hook --> Out["Emotion im\nneuronalen Zustand"]

    classDef e fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
    classDef p fill:#f3e5f5,stroke:#4a148c,stroke-width:2px,color:#000
    classDef l fill:#fff9c4,stroke:#f57f17,stroke-width:2px,color:#000
    classDef o fill:#fce4ec,stroke:#880e4f,stroke-width:2px,color:#000

    class E e
    class VAD,Alpha,Modes p
    class Layers,Hook l
    class Out o
```

---

## Schnellstart

### 1. Installation

```bash
git clone https://github.com/017pixel/CHAPPiE.git
cd CHAPPiE
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Frontend:

```bash
cd frontend
npm install
cd ..
```

### 2. Konfiguration

- [`config/secrets_example.py`](config/secrets_example.py)
- [`config/config.py`](config/config.py)

Empfohlen:

- `LLM_PROVIDER = "vllm"`
- lokaler Endpoint auf `http://localhost:8000/v1`
- Qwen-3.5 lokal zuerst, APIs nur Fallback

Details: [docs/local-models.md](docs/local-models.md)

### 3. Starten

```bash
# API
uvicorn api.main:app --reload --port 8010

# Frontend
cd frontend && npm run dev

# Training
python -m Chappies_Trainingspartner.training_daemon --neu
```

Mehr Startoptionen: [docs/deployment.md](docs/deployment.md)

---

## Forschungsfelder

CHAPPiE bewegt sich an der Schnittstelle mehrerer etablierter Forschungsgebiete:

- **Cognitive Architectures** – modulare Architektur nach kognitiver Trennung
- **Agent Systems** – autonome Agenten mit internem Zustandsmodell
- **Memory-Augmented LLMs** – episodisches Gedächtnis mit Retrieval und Vergessen
- **Affective Computing** – Emotion Steering via Activation Steering
- **Simulation-based AI** – Life-Simulation als kontinuierliche Umgebung

---

## Schnellnavigation

- [Agent-Guide](agent.md)
- [Dokumentationsindex](docs/README.md)
- [Architektur & Gehirn-Metapher](docs/architecture.md)
- [Workflows](docs/workflows.md)
- [Lokale Modelle](docs/local-models.md)
- [vLLM-Setup](docs/vLLM-Setup.md)
- [Projektkarte](docs/project-map.md)
- [Testing](docs/testing.md)
- [Deployment](docs/deployment.md)

---

## Wichtige Projektbereiche

- [`brain/`](brain) – Brain-Pipeline, Agenten, Steering, Global Workspace
- [`memory/`](memory) – Gedächtnis, Konsolidierung, Kontextdateien
- [`life/`](life) – inneres Zustandsmodell und Entwicklung
- [`api/`](api) – FastAPI-App für den Webpfad
- [`frontend/`](frontend) – React/Vite/TypeScript-Frontend
- [`web_infrastructure/`](web_infrastructure) – UI-freie Brückenschicht
- [`Chappies_Trainingspartner/`](Chappies_Trainingspartner) – autonomes Training
- [`config/`](config) – Provider-, Prompt- und Modellkonfiguration
- [`data/`](data) – Laufzeitdaten, Memories, Kontextdateien

---

## Datenhinweis

[`data/`](data) ist sensibel: enthält Kontextdateien, Memory-Daten und lokale Zustände. Nicht unbedacht löschen. Siehe [`data/README_GEDAECHTNIS_WARNUNG.txt`](data/README_GEDAECHTNIS_WARNUNG.txt).

## Legacy-Hinweis

[`Info Dateien/`](Info%20Dateien) enthält nur noch kurze Brücken. Die aktuelle Hauptdokumentation ist `README.md`, `agent.md` und `docs/`.
