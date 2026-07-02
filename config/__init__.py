"""CHAPPiE Config Module."""
from .config import (
    PROJECT_ROOT,
    LLMProvider,
    Settings,
    get_active_model,
    get_agent_config,
    get_all_agent_configs,
    get_forgetting_curve_config,
    get_sleep_config,
    settings,
)
from . import prompts

try:
    from . import secrets  # type: ignore
except ImportError:  # secrets.py ist optional und kann in CI/clean checkouts fehlen
    secrets = None
