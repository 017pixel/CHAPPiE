# CHAPPiE Agent Instructions

## Critical Configuration Rules

### 1. Systemd Service Configuration
**Strict Requirement:** When configuring the `chappie-training.service` file for background execution, you **MUST** ensure that `ExecStart` points to `training_daemon.py` and **NOT** `training_loop.py`.

- **Correct:** `ExecStart=... -m Chappies_Trainingspartner.training_daemon`
- **Incorrect:** `ExecStart=... -m Chappies_Trainingspartner.training_loop`

`training_daemon.py` contains the necessary entry point and setup for the headless training process. `training_loop.py` is a library module and cannot be executed directly as a service.

### 2. General Service Reliability
- Ensure `Restart=always` is set to guarantee 24/7 operation.
- Use absolute paths for all executables and working directories in service files.

---

## Brain-Inspired Multi-Agent Architecture

### Overview
CHAPPiE now features a brain-inspired cognitive architecture with 7 specialized agents:

```
┌─────────────────────────────────────────────────────────────────┐
│                    CHAPPiE DIGITAL BRAIN                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │  SENSORY     │    │  AMYGDALA    │    │  HIPPOCAMPUS │      │
│  │  CORTEX      │    │  Agent       │    │  Agent       │      │
│  │  (Input)     │    │  (Emotion)   │    │  (Memory)    │      │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘      │
│         │                   │                   │               │
│         ▼                   ▼                   ▼               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    PREFRONTAL CORTEX                     │   │
│  │                    (Orchestrator Agent)                  │   │
│  └──────────────────────────┬──────────────────────────────┘   │
│                             │                                   │
│         ┌───────────────────┼───────────────────┐              │
│         ▼                   ▼                   ▼               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │  BASAL       │    │  NEOCORTEX   │    │  MEMORY      │      │
│  │  GANGLIA     │    │  Agent       │    │  AGENT       │      │
│  │  (Reward)    │    │  (LTM Store) │    │  (Tools)     │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Agent Responsibilities

| Agent | Brain Region | Function |
|-------|--------------|----------|
| Sensory Cortex | Sensory Areas | Input classification, language detection, urgency assessment |
| Amygdala | Limbic System | Emotional processing, memory enhancement, trust tracking |
| Hippocampus | Medial Temporal | Memory encoding, retrieval, consolidation decisions |
| Prefrontal Cortex | Frontal Lobe | Central orchestration, working memory, response strategy |
| Basal Ganglia | Basal Ganglia | Reward evaluation, learning signals, habit formation |
| Neocortex | Neocortex | Long-term memory storage, semantic knowledge |
| Memory Agent | - | Tool call decisions for soul.md, user.md, preferences.md |

### Processing Pipeline

1. **Input** -> Sensory Cortex (classification)
2. **Parallel**: Amygdala (emotions) + Hippocampus (memory)
3. **Orchestration** -> Prefrontal Cortex (response strategy)
4. **Output** -> Response generation
5. **Background**: Basal Ganglia (learning) + Neocortex (consolidation)

### File Locations

```
brain/
├── agents/
│   ├── __init__.py
│   ├── base_agent.py           # Base class
│   ├── sensory_cortex.py       # Input processing
│   ├── amygdala.py             # Emotional analysis
│   ├── hippocampus.py          # Memory operations
│   ├── prefrontal_cortex.py    # Orchestration
│   ├── basal_ganglia.py        # Reward/learning
│   ├── neocortex.py            # LTM storage
│   ├── memory_agent.py         # Tool calls
│   └── orchestrator.py         # Pipeline coordination
├── brain_pipeline.py           # Main integration
└── brain_config.py             # Model configuration

memory/
├── sleep_phase.py              # Memory consolidation
├── forgetting_curve.py         # Ebbinghaus implementation
└── ... (existing files)
```

### Model Configuration

NVIDIA models are prioritized for higher free limits:

| Agent | Model | Provider |
|-------|-------|----------|
| Sensory Cortex | meta/llama-3.3-70b-instruct | NVIDIA |
| Amygdala | nvidia/llama-3.1-nemotron-70b | NVIDIA |
| Hippocampus | nvidia/llama-3.1-nemotron-70b | NVIDIA |
| Prefrontal Cortex | z-ai/glm5 | NVIDIA |
| Basal Ganglia | meta/llama-3.3-70b-instruct | NVIDIA |
| Neocortex | meta/llama-3.3-70b-instruct | NVIDIA |
| Memory Agent | nvidia/llama-3.1-nemotron-70b | NVIDIA |

### Sleep Phase

Memory consolidation runs:
- Every 24 hours (time-based)
- Every 100 interactions (interaction-based)
- Manual trigger: `/sleep` command

### Forgetting Curve

Implements Ebbinghaus forgetting curve:
- Retention after 20min: ~58%
- Retention after 1h: ~44%
- Retention after 24h: ~33%
- Spaced repetition boosts memory strength
