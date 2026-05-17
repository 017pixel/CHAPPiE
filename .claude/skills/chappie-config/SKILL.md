---
name: chappie-config
description: CHAPPiE's configuration system. Use when adding new settings, modifying config.py, updating schemas, or working with CHAPPIE_CONFIG.json.
---

# CHAPPiE Configuration System

## Configuration Flow
```
CHAPPIE_CONFIG.json  →  config/root_config.py  →  config/config.py (Settings class)
                          ↓                            ↓
                    config/secrets.py          API: /settings endpoint
                    config/addSecrets.py       Frontend: settings-page.tsx
```

## Key Files

| File | Role |
|---|---|
| `config/config.py` | Settings class, LLMProvider enum, ALL config defaults |
| `config/root_config.py` | JSON file I/O for `CHAPPIE_CONFIG.json` |
| `CHAPPIE_CONFIG.example.json` | Template (not in git) |
| `config/secrets.py` | API keys (not in git) |
| `api/schemas.py` | SettingsSnapshot, SettingsUpdate Pydantic models |
| `api/routers/runtime.py` | `GET/POST /settings`, `_settings_snapshot()` |

## Adding a New Setting
1. Add attribute to Settings class in `config/config.py`
2. Add `_get_val()` call with default value
3. Add to `update_from_ui()` for persistence
4. Add to `_export_root_values()` for JSON export
5. Add field to `SettingsSnapshot` and `SettingsUpdate` in `api/schemas.py`
6. Add to `_settings_snapshot()` in `api/routers/runtime.py`
7. Add to `frontend/src/pages/settings-page.tsx` `SETTINGS_DEFS` array

## Current Settings Groups
| Group | Settings |
|---|---|
| Provider | llm_provider, vllm_model, ollama_model, cerebras_model |
| Generation | temperature, repetition_penalty, max_tokens, thinking/answer limits |
| Memory | memory_top_k, memory_min_relevance, stm_summary_threshold |
| Steering | enable_steering, steering_model |
| Intent | intent_provider, query_extraction_provider |
| Training | training_chappie_model |

## Provider Values
```python
class LLMProvider(str, Enum):
    OLLAMA = "ollama"
    CEREBRAS = "cerebras"
    VLLM = "vllm"
```

## Hot Reload
- `settings.update_from_ui()` → updates in-memory values
- `backend.apply_runtime_settings(force=True)` → rebuilds brain/intent processor
- Settings persist via `_persist_to_root_config()` → writes to `CHAPPIE_CONFIG.json`

## Key Rules
- API keys NEVER in `config.py` — always in `secrets.py` or `CHAPPIE_CONFIG.json`
- `CHAPPIE_CONFIG.json` is gitignored — never commit real config
- Float settings use `float()` conversion, bool use `bool()`, int use `int()`
- `_parse_provider()` handles `"auto"`, `None`, and `""` → returns `None`
