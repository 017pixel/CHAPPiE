"""Explicit bounded multiprocess stress of real SQLite and chat-file persistence.

Uses isolated synthetic data and no model/embedding calls. This checks retention
and locking, not retrieval quality or model throughput.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing
from pathlib import Path
import time

from forschung.steering_v17.benchmark import create_manifest, freeze_source
from memory.chat_manager import ChatManager
from memory.event_store import EventStore


def write_batch(arguments):
    directory, session, indices = arguments
    root = Path(directory)
    archive = EventStore(root / "events.sqlite3")
    chats = ChatManager(str(root))
    elapsed = []
    for index in indices:
        started = time.perf_counter()
        turn = str(index)
        content = f"Meine Testnummer lautet {index}."
        event = archive.append(session_id=session, turn_id=turn, role="user", content=content,
                               metadata={"memory_enabled": False})
        if index % 16 == 0:
            assert archive.append(session_id=session, turn_id=turn, role="user", content=content) == event
        chats.append_messages(session, [{"id": f"u{index}", "role": "user", "content": content},
                                       {"id": f"a{index}", "role": "assistant", "content": "pending",
                                        "metadata": {"pending": True}}])
        answer = f"Testnummer {index} erhalten."
        archive.append(session_id=session, turn_id=turn, role="assistant", content=answer,
                       raw_content=f"raw-{index}", metadata={"memory_enabled": False})
        chats.update_message(session, f"a{index}", content=answer, metadata_updates={"pending": False})
        elapsed.append((time.perf_counter() - started) * 1000)
    return elapsed


def run(output, turns=1024, workers=8):
    if not 1 <= workers <= 16 or not workers <= turns <= 8192:
        raise ValueError("Require1..16workers and workers<=turns<=8192")
    output.mkdir(parents=True, exist_ok=False)
    dataset = output / "experiment.json"
    dataset.write_text(json.dumps({"turns": turns, "processes": workers, "expected_events": 2 * turns,
                                  "expected_messages": 2 * turns, "data": "isolated_synthetic"}, indent=2) + "\n")
    manifest = create_manifest(dataset, model="none", modes=["multiprocess_storage_stress"],
                               seeds=[], temperature=0, max_tokens=0)
    manifest["scope"] = "real SQLite and chat JSON, no inference or embedding; not throughput-isolated from other host work"
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    freeze_source(output, manifest)
    runtime = output / "runtime"
    manager = ChatManager(str(runtime))
    session = manager.create_session()
    EventStore(runtime / "events.sqlite3")
    started = time.perf_counter()
    arguments = [(str(runtime), session, list(range(worker, turns, workers))) for worker in range(workers)]
    with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn")) as pool:
        durations = [duration for batch in pool.map(write_batch, arguments) for duration in batch]
    elapsed = time.perf_counter() - started
    # Reopen independent objects after all writer processes have exited.
    messages = ChatManager(str(runtime)).load_session(session)["messages"]
    archive = EventStore(runtime / "events.sqlite3")
    events = archive.events(session)
    assert len(events) == len(messages) == 2 * turns
    assert len({event["event_id"] for event in events}) == 2 * turns
    assert {message["id"] for message in messages} == {f"{role}{i}" for i in range(turns) for role in "ua"}
    for message in messages:
        if message["role"] == "assistant":
            assert message["content"] == f"Testnummer {message['id'][1:]} erhalten."
            assert message["metadata"]["pending"] is False
    assert sum(event["retrieval_eligible"] for event in events) == turns
    assert all(event["memory_enabled"] == 0 for event in events)
    assert all(event["retrieval_eligible"] == 0 and event["raw_content"] == f"raw-{event['turn_id']}"
               for event in events if event["role"] == "assistant")
    try:
        archive.append(session_id=session, turn_id="0", role="user", content="conflicting replacement")
    except ValueError:
        pass
    else:
        raise AssertionError("Immutable event was overwritten")
    with archive.connect() as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        pending = connection.execute("SELECT COUNT(*) FROM events WHERE promotion_state='pending'").fetchone()[0]
    assert integrity == "ok" and pending == turns
    result = {"passed": True, "processes": workers, "turns": turns, "events": len(events),
              "messages": len(messages), "pending_user_promotions": pending,
              "assistant_retrieval_eligible": 0, "sqlite_integrity": integrity,
              "elapsed_seconds": elapsed, "exchange_duration_ms": {"min": min(durations), "max": max(durations)},
              "scope": manifest["scope"], "embedding_promotion_executed": False}
    (output / "completion.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--turns", type=int, default=1024)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    print(json.dumps(run(args.output, args.turns, args.workers), indent=2))
