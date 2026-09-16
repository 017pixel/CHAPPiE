from __future__ import annotations

import threading

from web_infrastructure.chappie_runtime import CHAPPiERuntime, create_chappie_backend

_backend: CHAPPiERuntime | None = None
_backend_lock = threading.Lock()


def get_backend() -> CHAPPiERuntime:
    global _backend
    with _backend_lock:
        if _backend is None:
            _backend = create_chappie_backend()
    return _backend


def close_backend() -> None:
    global _backend
    with _backend_lock:
        if _backend is not None:
            _backend.close()
            _backend = None
