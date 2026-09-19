from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from web_infrastructure.chappie_runtime import CHAPPiERuntime

_backend: CHAPPiERuntime | None = None
_backend_lock = threading.Lock()


def get_backend() -> CHAPPiERuntime:
    global _backend
    with _backend_lock:
        if _backend is None:
            from web_infrastructure.chappie_runtime import create_chappie_backend

            _backend = create_chappie_backend()
    return _backend


def close_backend() -> None:
    global _backend
    with _backend_lock:
        if _backend is not None:
            _backend.close()
            _backend = None
