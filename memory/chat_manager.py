import json
import glob
import os
import re
import threading
import uuid
import tempfile
import fcntl
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from config.session_settings import SessionRuntimeSettings


SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")


class ChatManager:
    """
    Manages chat sessions, persistence, and history limits.
    """
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.sessions_dir = os.path.join(data_dir, "chat_sessions")
        self.active_session_path = os.path.join(data_dir, "active_chat_session.json")
        os.makedirs(self.sessions_dir, exist_ok=True)
        self.max_sessions = 25
        self._lock = threading.RLock()
        self._repair_legacy_none_session()

    def _get_file_path(self, session_id: str) -> str:
        if not self._is_valid_session_id(session_id):
            raise ValueError("Ungueltige Chat-Session-ID")
        return os.path.join(self.sessions_dir, f"{session_id}.json")

    @staticmethod
    def create_message_id() -> str:
        """Creates a unique ID for a chat message."""
        return str(uuid.uuid4())

    def _is_valid_session_id(self, session_id: Optional[str]) -> bool:
        text = str(session_id or "").strip()
        return bool(text.lower() != "none" and SESSION_ID_PATTERN.fullmatch(text))

    def ensure_session_id(self, session_id: Optional[str]) -> str:
        """Returns a usable session id, restoring the active one when possible."""
        if self._is_valid_session_id(session_id):
            return str(session_id)

        active_session_id = self.get_active_session_id()
        if self._is_valid_session_id(active_session_id):
            return str(active_session_id)

        new_session_id = self.create_session()
        self.set_active_session(new_session_id)
        return new_session_id

    def ensure_message_ids(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ensures every message has a stable ID for later in-place updates."""
        normalized: List[Dict[str, Any]] = []
        for msg in messages or []:
            current = dict(msg)
            current.setdefault("id", self.create_message_id())
            fallback_timestamp = current.get("timestamp") or datetime.now(timezone.utc).isoformat()
            current.setdefault("created_at", fallback_timestamp)
            normalized.append(current)
        return normalized

    def set_active_session(self, session_id: Optional[str]):
        """Persists the currently active session across UI reconnects."""
        normalized_session_id = self.ensure_session_id(session_id)
        payload = {
            "session_id": normalized_session_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._lock:
            with open(self.active_session_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)

    def get_active_session_id(self) -> Optional[str]:
        """Loads the last active session id if available."""
        if not os.path.exists(self.active_session_path):
            return None

        try:
            with open(self.active_session_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            session_id = payload.get("session_id")
            return str(session_id) if self._is_valid_session_id(session_id) else None
        except Exception:
            return None

    def load_active_session(self) -> Dict[str, Any]:
        """Loads the last active session or creates a fresh one."""
        active_session_id = self.get_active_session_id()
        if active_session_id:
            data = self.load_session(active_session_id)
            if data.get("messages") or data.get("id") == active_session_id:
                return data

        session_id = self.create_session()
        self.set_active_session(session_id)
        return {"id": session_id, "messages": [], "title": "New Chat", "updated_at": ""}

    def _repair_legacy_none_session(self):
        """Migrates broken legacy sessions saved as None.json to a proper UUID."""
        legacy_path = os.path.join(self.sessions_dir, "None.json")
        if not os.path.exists(legacy_path):
            return

        with self._lock:
            try:
                with open(legacy_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                return

            new_session_id = self.create_session()
            data["id"] = new_session_id
            data["messages"] = self.ensure_message_ids(data.get("messages", []))

            with open(self._get_file_path(new_session_id), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            os.remove(legacy_path)
            self.set_active_session(new_session_id)

    def create_session(self) -> str:
        """Creates a new session ID."""
        return str(uuid.uuid4())

    def save_session(self, session_id: str, messages: List[Dict[str, Any]], title: Optional[str] = None):
        """Saves a chat session to disk."""
        if not messages:
            return self.ensure_session_id(session_id)  # Don't save empty sessions

        normalized_session_id = self.ensure_session_id(session_id)
        normalized_messages = self.ensure_message_ids(messages)

        # Auto-generate title from first user message if not provided
        if not title:
            for msg in normalized_messages:
                if msg["role"] == "user":
                    title = msg["content"][:30] + "..." if len(msg["content"]) > 30 else msg["content"]
                    break
            if not title:
                title = "New Chat"

        data = {
            "id": normalized_session_id,
            "title": title,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "messages": normalized_messages
        }

        file_path = self._get_file_path(normalized_session_id)
        with self._session_storage_lock():
            previous = self._read_session_raw(normalized_session_id)
            data["runtime_settings"] = previous.get("runtime_settings") or SessionRuntimeSettings.from_mapping().to_dict()
            self._write_session_atomic(file_path, data)
        
        self.set_active_session(normalized_session_id)
        return normalized_session_id

    @contextmanager
    def _session_storage_lock(self):
        with self._lock:
            with open(os.path.join(self.sessions_dir, ".settings.lock"), "a") as handle:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _read_session_raw(self, session_id: str) -> Dict[str, Any]:
        path = self._get_file_path(session_id)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as handle:
                return json.load(handle)
        return {"id": session_id, "messages": [], "title": "New Chat", "updated_at": ""}

    @staticmethod
    def _write_session_atomic(file_path: str, data: Dict[str, Any]) -> None:
        fd, temporary = tempfile.mkstemp(prefix=".session-", dir=os.path.dirname(file_path))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, file_path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def get_runtime_settings(self, session_id: str) -> SessionRuntimeSettings:
        if not self._is_valid_session_id(session_id):
            raise ValueError("Ungueltige Chat-Session-ID")
        with self._lock:
            return SessionRuntimeSettings.from_mapping(self._read_session_raw(session_id).get("runtime_settings"))

    def update_runtime_settings(self, session_id: str, changes: Dict[str, Any]) -> SessionRuntimeSettings:
        if not self._is_valid_session_id(session_id):
            raise ValueError("Ungueltige Chat-Session-ID")
        SessionRuntimeSettings.validate_patch(changes)
        with self._session_storage_lock():
            data = self._read_session_raw(session_id)
            current = SessionRuntimeSettings.from_mapping(data.get("runtime_settings")).to_dict()
            updated = SessionRuntimeSettings.from_mapping({**current, **changes})
            data["runtime_settings"] = updated.to_dict()
            data["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._write_session_atomic(self._get_file_path(session_id), data)
            return updated

    def load_session(self, session_id: Optional[str]) -> Dict[str, Any]:
        """Loads a chat session from disk."""
        normalized_session_id = self.ensure_session_id(session_id)
        file_path = self._get_file_path(normalized_session_id)
        if os.path.exists(file_path):
            with self._lock:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            normalized_messages = self.ensure_message_ids(data.get("messages", []))
            if normalized_messages != data.get("messages", []):
                data["messages"] = normalized_messages
                self.save_session(normalized_session_id, normalized_messages, title=data.get("title"))
            return data
        return {"id": normalized_session_id, "messages": [], "title": "New Chat", "updated_at": ""}

    def update_message(
        self,
        session_id: Optional[str],
        message_id: str,
        *,
        content: Optional[str] = None,
        metadata_updates: Optional[Dict[str, Any]] = None,
        role: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Updates a single message in an existing session by id."""
        normalized = self.ensure_session_id(session_id)
        with self._session_storage_lock():
            data = self._read_session_raw(normalized)
            messages = self.ensure_message_ids(data.get("messages", []))
            for msg in messages:
                if msg.get("id") != message_id:
                    continue
                if content is not None:
                    msg["content"] = content
                if role is not None:
                    msg["role"] = role
                if metadata_updates is not None:
                    metadata = dict(msg.get("metadata") or {})
                    metadata.update(metadata_updates)
                    msg["metadata"] = metadata
                break

            data["messages"] = messages
            data["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._write_session_atomic(self._get_file_path(normalized), data)
            return data

    def append_messages(self, session_id: str, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Atomic read/append/write across threads and processes."""
        normalized = self.ensure_session_id(session_id)
        additions = self.ensure_message_ids(messages)
        with self._session_storage_lock():
            data = self._read_session_raw(normalized)
            current = self.ensure_message_ids(data.get("messages", []))
            existing = {message["id"]: message for message in current}
            for message in additions:
                if message["id"] in existing:
                    if existing[message["id"]] != message:
                        raise ValueError("Conflicting append for existing message ID")
                    continue
                current.append(message)
                existing[message["id"]] = message
            data["messages"] = current
            data["updated_at"] = datetime.now(timezone.utc).isoformat()
            data.setdefault("runtime_settings", SessionRuntimeSettings.from_mapping().to_dict())
            if data.get("title", "New Chat") == "New Chat":
                first = next((m["content"] for m in current if m.get("role") == "user"), "New Chat")
                data["title"] = first[:30] + ("..." if len(first) > 30 else "")
            self._write_session_atomic(self._get_file_path(normalized), data)
            return data

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Lists all available sessions sorted by updated_at (newest first)."""
        sessions = []
        files = glob.glob(os.path.join(self.sessions_dir, "*.json"))
        
        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    messages = data.get("messages", [])
                    sessions.append({
                        "id": data.get("id"),
                        "title": data.get("title", "Untitled"),
                        "updated_at": data.get("updated_at", ""),
                        "message_count": len(messages) if isinstance(messages, list) else 0,
                    })
            except Exception:
                continue # Skip broken files

        # Sort by date descending
        sessions.sort(key=lambda x: x["updated_at"], reverse=True)
        return sessions

    def delete_session(self, session_id: str) -> bool:
        """Deletes a session file."""
        if not self._is_valid_session_id(session_id):
            return False
        file_path = self._get_file_path(session_id)
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False

    def _prune_old_sessions(self):
        """Compatibility no-op: sessions are no longer automatically deleted."""
        return None
