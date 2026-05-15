---
name: chappie-backend
description: Backend development for CHAPPiE. Use when working on FastAPI APIs, vLLM brain, Cerebras integration, training daemon, or backend_wrapper.py.
---

# CHAPPiE Backend Development

## Stack
- **API**: FastAPI (port 8010), CORS wildcard
- **Brain**: vLLM (local), Cerebras/Groq/NVIDIA (cloud fallback)
- **Database**: ChromaDB for episodic memory
- **Training**: daemon_manager subprocess pattern

## Key Files

| File | Role |
|---|---|
| `api/main.py` | App entry, routers, root JSON endpoint |
| `api/routers/*.py` | chat, system, memory, runtime, training, context |
| `api/schemas.py` | Pydantic models |
| `web_infrastructure/backend_wrapper.py` | Main CHAPPiE backend class |
| `brain/vllm_brain.py` | vLLM OpenAI-compatible client |
| `brain/base_brain.py` | Abstract base + GenerationConfig |
| `Chappies_Trainingspartner/daemon_manager.py` | Subprocess daemon control |

## Generation Pipeline (Two-Step)
1. **Step 1**: Intent analysis via Cerebras (fast model: `llama-3.1-8b`)
2. **Step 2**: Response generation via vLLM (Qwen3.5-4B)
3. Post-processing: Cerebras GPT-OSS-120B formats CoT + Answer

## Post-Processing (`_format_via_cerebras`)
- Method in `backend_wrapper.py` (~line 602)
- Sends raw CHAPPiE output to Cerebras for formatting
- Returns `<cot>` + `<antwort>` tagged blocks
- NEVER changes content — only formatting

## Testing Without vLLM
```python
import sys
from unittest.mock import MagicMock
# Mock all brain dependencies before import
sys.modules["ollama"] = MagicMock()
sys.modules["groq"] = MagicMock()
sys.modules["chromadb"] = MagicMock()
# Then import from brain.vllm_brain directly
```

## Key Rules
- `repetition_penalty` muss via `extra_body`, nicht direkt als Keyword
- `enable_thinking=True` für Qwen3.5 Modelle (in `_prepare_extra_body`)
- Reasoning-Loop-Detektor: `_detect_reasoning_loop()` in vllm_brain.py
- Alle Settings über `config.config.settings` → `update_from_ui()` persistiert
