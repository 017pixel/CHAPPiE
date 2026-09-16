"""Durability, quarantine, idempotency and concurrent-write stress contracts."""

import json
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from memory.event_store import EventStore
from memory.retrieval_promotion import RetrievalPromotion


def test_retention_and_isolation(root):
    store = EventStore(root / "events.sqlite")
    event = store.append(
        session_id="a",
        turn_id="1",
        role="user",
        content="Ich heiße Ada.",
        metadata={"memory_enabled": False},
    )
    assert (
        store.append(session_id="a", turn_id="1", role="user", content="Ich heiße Ada.")
        == event
    )
    store.append(
        session_id="a",
        turn_id="1",
        role="assistant",
        content="Ich war heute drei Stunden draußen.",
        raw_content="raw output",
    )
    store.append(
        session_id="b",
        turn_id="1",
        role="assistant",
        content="Steering-Server Fehler: unavailable",
    )
    restored = EventStore(root / "events.sqlite")
    rows = restored.events("a")
    assert len(rows) == 2 and rows[0]["memory_enabled"] == 0
    assert rows[1]["retrieval_eligible"] == 0 and rows[1]["raw_content"] == "raw output"
    assert "assistant_claim" in json.loads(rows[1]["quality_flags_json"])
    assert len(restored.events("b")) == 1
    try:
        store.append(
            session_id="a", turn_id="1", role="user", content="Changed evidence"
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Immutable evidence was overwritten")
    assert restored.events("a")[0]["content"] == "Ich heiße Ada."


def test_concurrent_stress(root):
    store = EventStore(root / "stress.sqlite")

    def write(index):
        return store.append(
            session_id=f"s{index % 8}",
            turn_id=str(index),
            role="user",
            content=f"Meine Nummer ist {index}.",
        )

    with ThreadPoolExecutor(max_workers=8) as workers:
        ids = list(workers.map(write, range(256)))
    assert len(set(ids)) == 256
    assert sum(len(store.events(f"s{i}")) for i in range(8)) == 256

    class Memory:
        def __init__(self):
            self.ids = set()
            self.batches = []

        def add_memory_batch(self, records):
            self.batches.append(len(records))
            self.ids.update(record["id"] for record in records)
            return [record["id"] for record in records]

    memory = Memory()
    worker = RetrievalPromotion(store, lambda: memory)
    try:
        assert worker.flush(timeout=10)
        assert len(memory.ids) == 256 and max(memory.batches) <= 32
        worker.schedule()
        assert worker.flush(timeout=10)
        assert len(memory.ids) == 256
    finally:
        worker.close()
    assert not store.pending()


def test_poison_record_does_not_block_outbox(root):
    store = EventStore(root / "poison.sqlite")
    bad = store.append(session_id="p", turn_id="bad", role="user", content="Mein internal_log ist leer.")
    store.append(session_id="p", turn_id="good", role="user", content="Mein Name ist Ada.")
    assert len(store.pending()) == 1
    # Simulate an old pending row written before stricter shared eligibility.
    with store.connect() as conn:
        conn.execute("UPDATE events SET retrieval_eligible=1,promotion_state='pending' WHERE event_id=?", (bad,))
    class Memory:
        def add_memory_batch(self, records):
            assert len(records) == 1 and records[0]["content"] == "Mein Name ist Ada."
            return [record["id"] for record in records]
    worker = RetrievalPromotion(store, lambda: Memory())
    try:
        assert worker.flush(5)
        rows = store.events("p")
        assert rows[0]["promotion_state"] == "skipped"
        assert rows[1]["promotion_state"] == "done"
        assert len(rows) == 2
    finally:
        worker.close()


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as directory:
        test_retention_and_isolation(Path(directory))
        test_concurrent_stress(Path(directory))
        test_poison_record_does_not_block_outbox(Path(directory))
    print("Event store: retention, isolation and 256 concurrent writes passed")
