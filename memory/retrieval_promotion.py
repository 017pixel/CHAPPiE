"""One bounded background worker per runtime, backed by durable event outbox."""

from __future__ import annotations

import logging
import threading
from typing import Callable, Any

from memory.event_store import EventStore
from memory.retrieval_quality import is_memory_contaminated
from config.config import MEMORY_PROMOTION_CONFIG

LOGGER = logging.getLogger(__name__)


class RetrievalPromotion:
    def __init__(
        self,
        store: EventStore,
        memory_getter: Callable[[], Any],
        maintenance: Callable[[], Any] | None = None,
    ):
        self.store = store
        self.memory_getter = memory_getter
        self.maintenance = maintenance
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._idle = threading.Event()
        self._idle.set()
        self._worker = threading.Thread(
            target=self._run, name="chappie-retrieval-promotion", daemon=True
        )
        self._worker.start()
        self.schedule()

    def schedule(self):
        self._idle.clear()
        self._wake.set()

    def flush(self, timeout: float = 30) -> bool:
        return self._idle.wait(timeout) and not self.store.pending(limit=1)

    def close(self, timeout: float = MEMORY_PROMOTION_CONFIG["shutdown_seconds"]):
        self._stop.set()
        self._wake.set()
        self._worker.join(timeout)

    def _run(self):
        retry_pending = False
        while not self._stop.is_set():
            self._wake.wait(timeout=MEMORY_PROMOTION_CONFIG["retry_seconds"] if retry_pending else None)
            self._wake.clear()
            if self._stop.is_set():
                break
            retry_pending = False
            try:
                while batch := self.store.pending():
                    if self._stop.is_set():
                        break
                    rejected = [row for row in batch if is_memory_contaminated(
                        row["content"], role=row["role"], source=row["source"])]
                    if rejected:
                        self.store.quarantine([row["event_id"] for row in rejected], "retrieval_hygiene")
                        rejected_ids = {row["event_id"] for row in rejected}
                        batch = [row for row in batch if row["event_id"] not in rejected_ids]
                    if not batch:
                        continue
                    records = [
                        {
                            "id": "event-" + row["event_id"],
                            "content": row["content"],
                            "role": row["role"],
                            "source": row["source"],
                            "timestamp": row["timestamp"],
                            "event_id": row["event_id"],
                            "session_id": row["session_id"],
                        }
                        for row in batch
                    ]
                    try:
                        ids = self.memory_getter().add_memory_batch(records)
                        expected = {record["id"] for record in records}
                        if set(ids) != expected:
                            raise RuntimeError("Incomplete retrieval batch")
                        self.store.mark_promoted([row["event_id"] for row in batch])
                    except Exception as exc:
                        self.store.mark_failed(
                            [row["event_id"] for row in batch], str(exc)
                        )
                        raise
                if self.maintenance is not None:
                    self.maintenance()
            except Exception:
                retry_pending = True
                LOGGER.exception(
                    "Retrieval promotion deferred; durable events remain pending"
                )
            finally:
                # A concurrently scheduled turn keeps the worker non-idle.
                if not self._wake.is_set():
                    self._idle.set()
