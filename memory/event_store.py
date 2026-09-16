"""Durable conversation evidence, independent of retrieval eligibility."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from brain.response_parser import looks_like_model_error
from memory.retrieval_quality import is_memory_contaminated
from config.config import MEMORY_PROMOTION_CONFIG


class EventStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, turn_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL,
                    model TEXT NOT NULL, provider TEXT NOT NULL,
                    emotion_before_json TEXT NOT NULL, emotion_after_json TEXT NOT NULL,
                    emotion_delta_json TEXT NOT NULL, steering_mode TEXT NOT NULL,
                    steering_vectors_json TEXT NOT NULL, memory_enabled INTEGER NOT NULL,
                    quality_flags_json TEXT NOT NULL, retrieval_eligible INTEGER NOT NULL,
                    retrieval_confidence REAL NOT NULL, source TEXT NOT NULL,
                    raw_content TEXT, promotion_state TEXT NOT NULL DEFAULT 'skipped',
                    promotion_error TEXT, UNIQUE(session_id, turn_id, role)
                );
                CREATE INDEX IF NOT EXISTS events_session_time ON events(session_id, timestamp);
                CREATE INDEX IF NOT EXISTS events_promotion ON events(promotion_state);
            """)

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def append(
        self,
        *,
        session_id: str,
        turn_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        raw_content: str | None = None,
    ) -> str:
        if role not in ("user", "assistant", "system"):
            raise ValueError("Unknown event role")
        if not isinstance(content, str) or not session_id or not turn_id:
            raise ValueError("Event requires content, session and turn")
        meta = metadata or {}
        flags = list(meta.get("quality_flags", []))
        if looks_like_model_error(content):
            flags.append("model_error")
        if is_memory_contaminated(content, role=role, source=meta.get("source", "conversation")):
            flags.append("retrieval_hygiene")
        if role == "assistant":
            flags.append("assistant_claim")
        if role == "user":
            flags.append("user_statement")
        if meta.get("research_isolated"):
            flags.append("research_isolated")
        eligible = bool(
            role == "user"
            and content.strip()
            and not content.lstrip().startswith("/")
            and not set(flags)
            & {"model_error", "retrieval_hygiene", "research_isolated"}
        )
        event_id = uuid4().hex
        values = (
            event_id,
            session_id,
            turn_id,
            datetime.now(timezone.utc).isoformat(),
            role,
            content,
            str(meta.get("model", "")),
            str(meta.get("provider", "")),
            json.dumps(meta.get("emotions_before", {})),
            json.dumps(meta.get("emotions_after", {})),
            json.dumps(meta.get("emotions_delta", {})),
            str(meta.get("steering_mode", "off")),
            json.dumps(meta.get("steering_vectors", [])),
            int(meta.get("memory_enabled", True)),
            json.dumps(sorted(set(flags))),
            int(eligible),
            0.8 if eligible else 0.0,
            str(meta.get("source", "conversation")),
            raw_content,
            "pending" if eligible else "skipped",
        )
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO events (
                event_id,session_id,turn_id,timestamp,role,content,model,provider,
                emotion_before_json,emotion_after_json,emotion_delta_json,steering_mode,
                steering_vectors_json,memory_enabled,quality_flags_json,retrieval_eligible,
                retrieval_confidence,source,raw_content,promotion_state
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(session_id,turn_id,role) DO NOTHING""",
                values,
            )
            existing = connection.execute(
                "SELECT event_id,content FROM events WHERE session_id=? AND turn_id=? AND role=?",
                (session_id, turn_id, role),
            ).fetchone()
            if existing["content"] != content:
                raise ValueError("Conflicting content for immutable event")
            return existing["event_id"]

    def events(self, session_id: str) -> list[dict]:
        with self.connect() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM events WHERE session_id=? ORDER BY timestamp,event_id",
                    (session_id,),
                )
            ]

    def pending(self, limit: int = MEMORY_PROMOTION_CONFIG["batch_size"]) -> list[dict]:
        with self.connect() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM events WHERE promotion_state='pending' ORDER BY timestamp LIMIT ?",
                    (limit,),
                )
            ]

    def mark_promoted(self, event_ids: list[str]) -> None:
        with self.connect() as connection:
            connection.executemany(
                "UPDATE events SET promotion_state='done',promotion_error=NULL WHERE event_id=? AND retrieval_eligible=1",
                [(event_id,) for event_id in event_ids],
            )

    def quarantine(self, event_ids: list[str], reason: str) -> None:
        with self.connect() as connection:
            connection.executemany(
                "UPDATE events SET retrieval_eligible=0,retrieval_confidence=0,promotion_state='skipped',promotion_error=? WHERE event_id=?",
                [(reason, event_id) for event_id in event_ids],
            )

    def mark_failed(self, event_ids: list[str], error: str) -> None:
        with self.connect() as connection:
            connection.executemany(
                "UPDATE events SET promotion_error=? WHERE event_id=?",
                [(error[:500], event_id) for event_id in event_ids],
            )
