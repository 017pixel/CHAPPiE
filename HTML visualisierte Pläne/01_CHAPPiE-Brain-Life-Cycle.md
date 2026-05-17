# CHAPPiE Brain & Life Cycle — Kurzfassung

## Zyklus bei einer Eingabe (13 Phasen)

| # | Phase | Komponente | Funktion |
|---|-------|-----------|----------|
| 1 | **prepare_turn** | Life Service | Clock, Decay, Activity, Homeostasis, Snapshot |
| 2 | **Sensory Cortex** | brain/agents/sensory_cortex.py | Input-Typ, Urgency, Memory-Bedarf |
| 3 | **Amygdala** | brain/agents/amygdala.py | 7 Emotionen, Intensity, memory_boost |
| 4 | **Hippocampus** | brain/agents/hippocampus.py | Query, Context-Relevanz, Short-Term-Entries |
| 5 | **Memory Engine** | memory/memory_engine.py | Episodische Suche (top_k + min_relevance) |
| 6 | **Global Workspace** | brain/global_workspace.py | 7 Signale mit Salience → Broadcast |
| 7 | **Prefrontal Cortex** | brain/agents/prefrontal_cortex.py | Strategie, Tone, Guidance, Action-Plan |
| 8 | **Steering Manager** | brain/agents/steering_manager.py | VAD → Alpha → Composite Modes → Layer Editing |
| 9 | **LLM-Call** | brain/vllm_brain.py (oder Cloud) | Prompt + Steering-Payload → Response |
| 10 | **Antwort + Debug** | — | Token-Level Streaming, Causal Trace |
| 11 | **finalize_turn** | Life Service | Goals, Relationship, Habits, Attachment, Self-Model |
| 12 | **Background** | Basal Ganglia, Neocortex, Memory Agent | Reward, Konsolidierung, Context-Dateien |
| 13 | **Sleep-Check** | memory/sleep_phase.py | Sleep-Trigger prüfen, ggf. Konsolidierung |

## Life Simulation Komponenten

- **Needs** (Homeostasis): energy, social, curiosity, stability, achievement, rest
- **Goal Engine**: Goal Competition (Kognitive Entwicklung, Beziehungsaufbau, Selbstkonsistenz)
- **World Model**: Predicted User Need, Next Best Action, Risk Factors
- **Habit Engine**: Reinforcement + Dynamics pro Aktivität
- **Development Engine**: Stage Progression (awakening, ...)
- **Attachment Model**: Bond Type (cautious_alignment, ...)
- **Planning Engine**: Milestones, Bottlenecks, Confidence
- **Self-Forecast**: Risk Level, Turn Outlook, Stage Trajectory
- **Social Arc**: Arc Name, Score, Guidance
- **History Engine**: Timeline + Checkpoints

## Salience-Formeln (Global Workspace)

| Signal | Formel |
|--------|--------|
| Homeostasis | `min(1.0, pressure/100)` |
| Emotion | `min(1.0, emotional_intensity)` |
| Sensory | `map(low:0.25, medium:0.55, high:0.82, critical:0.95)` |
| Memory | `min(0.92, 0.38 + count * 0.08)` |
| Goal | `min(0.96, priority * (1.15 - progress))` |
| World Model | `min(0.9, confidence + risks * 0.05)` |
| Planning | `min(0.88, plan_confidence + bottlenecks * 0.04)` |
| Forecast | `0.66 (low) / 0.79 (mid/high)` |

## Emotion-Steering Pipeline

```
7 Emotionen (0-100) → VAD-Mapping → Alpha (44-56 tot, 56-74 sigmoid, 74+ max)
→ Composite Modes (crashout, warm, guarded, melancholic, charged)
→ Layer-Profile (z.B. Qwen3.5-4B: L10-26)
→ Forward Pre-Hook: hidden_state += alpha * steering_vector
```

## Betroffene Hauptdateien

- `brain/brain_pipeline.py` — Orchestrierung
- `life/service.py` — prepare_turn + finalize_turn
- `brain/global_workspace.py` — Salience-Workspace
- `brain/agents/steering_manager.py` — Emotion Steering
- `web_infrastructure/backend_wrapper.py` — process() Kapselung

---

*Plan: 01_CHAPPiE-Brain-Life-Cycle.html • 14.05.2026*
