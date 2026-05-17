---
name: chappie-architecture
description: CHAPPiE's brain, memory, and life simulation architecture. Use when modifying core pipelines, brain agents, steering, or global workspace.
---

# CHAPPiE Architecture

CHAPPiE uses a **brain metaphor** across three interacting layers: Brain, Memory, Life.

## Brain Pipeline (`brain/`)

| Agent | File | Purpose |
|---|---|---|
| Sensory Cortex | `brain/agents/sensory_cortex.py` | Input classification |
| Amygdala | `brain/agents/amygdala.py` | Emotional weighting |
| Hippocampus | `brain/agents/hippocampus.py` | Memory retrieval & encoding |
| Prefrontal Cortex | `brain/agents/prefrontal_cortex.py` | Response strategy & tone |
| Steering Manager | `brain/agents/steering_manager.py` | VAD mapping, alpha, composite modes, layer editing |
| Global Workspace | `brain/global_workspace.py` | 7 signals with salience bundling |
| Brain Pipeline | `brain/brain_pipeline.py` | Orchestrates all agents |

### Key Integration Points
- `web_infrastructure/backend_wrapper.py` → Main CHAPPiE backend class
- `api/main.py` → FastAPI app entry
- `brain/__init__.py` → `get_brain()` factory

## Memory (`memory/`)

| Component | File | Purpose |
|---|---|---|
| Memory Engine | `memory/memory_engine.py` | Episodic search, vector DB (ChromaDB) |
| Sleep Phase | `memory/sleep_phase.py` | Consolidation, replay, compression |
| Forgetting Curve | `memory/forgetting_curve.py` | Ebbinghaus decay model |
| Context Files | `memory/context_files.py` | soul.md, user.md, preferences |
| Short-Term V2 | `memory/short_term_memory_v2.py` | JSON-based STM with timestamps |

## Life Simulation (`life/`)

| Component | Purpose |
|---|---|
| Service | Prepare/finalize turns, homeostasis |
| Goal Engine | Goal competition |
| Planning Engine | Long-term planning |
| Social Arc | Relationship/attachment models |

## Key Rules
- `chappie-training.service` must start `training_daemon`, never `training_loop`
- Absolute paths in systemd ExecStart and WorkingDirectory
- Steering: local Qwen first, vLLM preferred, Cloud APIs as fallback
- `brain/__init__.py` triggert ALL brain imports (ollama, cerebras, vllm) — test imports müssen das mocken
