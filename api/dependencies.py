from __future__ import annotations

import threading

from web_infrastructure.backend_wrapper import create_chappie_backend

_backend = None
_backend_lock = threading.Lock()


def get_backend():
    global _backend
    with _backend_lock:
        if _backend is None:
            _backend = create_chappie_backend()
    return _backend
