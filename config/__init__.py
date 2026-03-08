"""CHAPiE Config Module."""
from .config import settings, Settings, LLMProvider, get_active_model, PROJECT_ROOT
from . import prompts

try:
    from . import secrets  # type: ignore
except ImportError:  # secrets.py ist optional und kann in CI/clean checkouts fehlen
    secrets = None
