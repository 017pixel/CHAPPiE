# Architektur und Gehirn-Metapher

## Zielbild

CHAPPiE ist kein neurologisch exaktes Gehirnmodell. Es nutzt eine technische Analogie: Wahrnehmung, Emotion, Gedaechtnis, Planung und Entwicklung werden auf klar getrennte Software-Komponenten abgebildet.

## Systemkarte

```mermaid
flowchart TD
    FE["Frontend / CLI / Training"] --> API["App API oder direkter Laufzeitpfad"]
    API --> PIPE["brain/brain_pipeline.py"]
    PIPE --> S["Sensory Cortex\nInput-Klassifikation"]
    PIPE --> L["life/service.py\nprepare_turn"]
    S --> A["Amygdala\nEmotionsanalyse"]
    S --> H["Hippocampus\nMemory-Operationen"]
    A --> M["Memory Engine\nEpisodische Suche"]
    H --> M
    A --> GW["Global Workspace\n7 Signale mit Salience"]
    H --> GW
    M --> GW
    L --> GW
    GW --> P["Prefrontal Cortex\nStrategie und Antwortfuehrung"]
    P --> OUT["Antwort und Aktionsplan"]
    P --> BG["Basal Ganglia\nReward und Lernsignal"]
    P --> N["Neocortex\nLangfristige Konsolidierung"]
    P --> STEER["Steering Manager\nVAD + Alpha + Layer Editing"]
    STEER --> VLLM["steering endpoint :8000\n(vLLM mit Layer Editing)"]
    OUT --> L2["life/service.py\nfinalize_turn"]
```

## Abbildung Gehirnidee zu CHAPPiE-Komponente

| Gehirnidee | CHAPPiE-Komponente | Hauptdateien | Aufgabe |
|---|---|---|---|
| Sensorischer Cortex | Sensory Cortex Agent | `brain/agents/sensory_cortex.py` | Eingabe klassifizieren |
| Amygdala | Amygdala Agent | `brain/agents/amygdala.py` | emotionale Gewichtung |
| Hippocampus | Hippocampus Agent | `brain/agents/hippocampus.py` | Retrieval und Encoding |
| Praefrontaler Cortex | Prefrontal Cortex Agent | `brain/agents/prefrontal_cortex.py` | Strategie und Antwortfuehrung |
| Basalganglien | Basal Ganglia Agent | `brain/agents/basal_ganglia.py` | Reward und Lernsignal |
| Neocortex | Neocortex Agent | `brain/agents/neocortex.py` | langfristige Konsolidierung |
| Tool- und Meta-Ebene | Memory Agent | `brain/agents/memory_agent.py` | Entscheidungen zu Kontextdateien |

## Zentrale Integrationsschichten

| Schicht | Datei | Rolle |
|---|---|---|
| Brain Pipeline | `brain/brain_pipeline.py` | verbindet Agenten, Memory und Life-Simulation |
| Global Workspace | `brain/global_workspace.py` | buendelt priorisierte Signale |
| Action Response Layer | `brain/action_response.py` | leitet konkrete Antwortaktionen ab |
| lokaler Steering-Endpoint | `brain/steering_api_server.py`, `brain/steering_backend.py` | OpenAI-kompatibles Serving und Steering |
| Life Simulation | `life/service.py` | Needs, Goals, Forecast und Beziehung |
| Memory Engine | `memory/memory_engine.py` | episodisches Gedaechtnis und Suche |
| Sleep Phase | `memory/sleep_phase.py` | Konsolidierung, Replay und Verdichtung |
| Web-Bruecke | `web_infrastructure/backend_wrapper.py` | UI-freie Laufzeitkopplung fuer API, CLI und Tests |

## Life-Simulation

Die Life-Simulation erweitert die Gehirn-Metapher um:

- Homeostasis und Needs
- Goal Competition
- World Model
- Habit Dynamics
- Development Stage
- Attachment und Social Arc
- Timeline und autobiografische Entwicklung

## Emotion-Steering

Emotionen werden nicht nur als Prompt-Text transportiert, sondern bei lokalen Modellen direkt in die neuronalen Schichten injiziert:

1. **VAD-Mapping**: Jede Emotion wird auf Valence, Arousal, Dominance abgebildet
2. **Alpha-Berechnung**: Toter Bereich 44-56, sigmoider Anstieg ab 56, Maximum ab 74
3. **Composite Modes**: Kombinationen erzeugen komplexe Modi (crashout, guarded, melancholic, warm, charged)
4. **Layer-Profile**: Modell-spezifische Layer-Bereiche (Qwen3.5-4B: L10-26, Qwen2.5-32B: L20-44)
5. **Forward Pre-Hook**: Wahrend der Generierung wird `hidden_state += alpha * steering_vector` angewendet

Bei Cloud-Providern (Groq, NVIDIA, Cerebras) entfallt Layer Editing – dort wird eine Style-Instruction in den Systemprompt injiziert.

Relevante Dateien:

- `brain/agents/steering_manager.py`
- `brain/steering_backend.py`
- `brain/steering_api_server.py`

## 3D Emotion Lattice

CHAPPiEs emotionale Zustaende werden in einer 3D-Visualisierung sichtbar:

- **Living Orb**: Verformte Geometrie mit Vertex Displacement via FBM Noise
- **Emotion-Mapping**: Alle 7 Emotionen steuern Farbe, Oberflaechenstruktur, Puls und Partikel
- **Inner Core**: Zweiter transparenter Kern mit eigenem Puls
- **Partikel-Feld**: 100 schwebende Partikel, deren Bewegung von Frustration und Energie gesteuert wird
- **Material**: `meshPhysicalMaterial` mit `transmission`, `clearcoat`, `iridescence`

Relevante Dateien:

- `frontend/src/components/visualizer-canvas.tsx`
- `frontend/src/pages/visualizer-page.tsx`
- `api/services/command_service.py` (`build_visualizer_payload`)

## Debug- und Entscheidungsspuren

Der Debug-Pfad macht die Ursache-Wirkung-Kette sichtbar:

- Input und Intent
- Memory-Treffer
- Emotionen und Deltas
- Life-Signale
- finale Ton- und Antwortentscheidung

Wichtige Pfade:

- `web_infrastructure/backend_wrapper.py`
- `api/routers/system.py`
- `memory/memory_engine.py`
- `memory/sleep_phase.py`

## Weiterfuehrend

- [Workflows](workflows.md)
- [Lokale Modelle](local-models.md)
- [Projektkarte](project-map.md)
