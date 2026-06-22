---
name: chappie-testing
description: CHAPPiE testing strategy. Use when writing or running tests, CI/CD, or validating changes before push.
---

# CHAPPiE Testing Strategy

## Test Types (from safest to most expensive)

| Type | Location | Cost | Examples |
|---|---|---|---|
| py_compile | inline | zero | `python3 -m py_compile <file>` |
| Quick tests | `tests/test_quick.py` | zero (no API) | imports, agents, forgetting curve |
| Unit tests | `tests/test_*.py` | zero | logic, parsing, formatting |
| API contract | `tests/test_api_contract.py` | zero (mocked) | endpoint validation |
| Frontend build | `cd frontend && npm run build` | npm only | TypeScript + Vite |
| Live tests | `tests/test_brain_agents.py` | needs model | use sparingly |

## Running Safe Tests (no model loading)
```bash
# Syntax check
python3 -m py_compile api/main.py api/routers/*.py web_infrastructure/backend_wrapper.py brain/vllm_brain.py config/config.py config/prompts.py

# Quick test suite
python3 tests/test_quick.py

# Specific tests
python3 tests/test_repetition_penalty.py  # 8 tests: penalty, loop detector, steering merge
python3 tests/test_reasoning_layering.py  # response parser
python3 tests/test_forgetting_curve.py    # Ebbinghaus math
python3 tests/test_chat_ui_formatting.py  # text formatting
python3 tests/test_training_config_ui.py  # training config
```

## Mocking Dependencies for Tests
```python
import sys
from unittest.mock import MagicMock, patch

# Required mocks for brain imports
for mod in ("ollama", "chromadb", "chromadb.config", "requests", "openai"):
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

# Then import from brain modules
from brain.base_brain import GenerationConfig
from brain.vllm_brain import VLLMBrain
```

## Pre-Commit Checklist
1. `py_compile` all modified Python files
2. Run at least the quick test suite
3. Frontend build for any TSX changes
4. Check no secrets in diff (`CHAPPIE_CONFIG.json`, `config/secrets.py`)
5. Review git log for commit style

## Known Test Issues
- Many tests need `ollama`, `chromadb`, `openai` installiert
- `brain/__init__.py` imports ALL brain impls → mock before import
- `memory/__init__.py` imports MemoryEngine → needs chromadb
- Frontend has broken import: `../lib/format` (fixed — created `format.ts`)
