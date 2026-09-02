"""Compatibility import for the active steering manager.

The implementation moved to :mod:`brain.steering_manager` so importing active
steering no longer initializes the historical multi-agent namespace.
"""

from brain.steering_manager import *  # noqa: F401,F403
