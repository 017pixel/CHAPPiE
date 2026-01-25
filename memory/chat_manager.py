import os
import json
import uuid
import glob
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

class ChatManager:
    """
    Manages chat sessions, persistence, and history limits.
    """
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.sessions_dir = os.path.join(data_dir, "chat_sessions")
        os.makedirs(self.sessions_dir, exist_ok=True)
        self.max_sessions = 25

    def _get_file_path(self, session_id: str) -> str:
        return os.path.join(self.sessions_dir, f"{session_id}.json")

    def create_session(self) -> str:
        """Creates a new session ID."""
        return str(uuid.uuid4())

    def save_session(self, session_id: str, messages: List[Dict[str, Any]], title: Optional[str] = None):
        """Saves a chat session to disk."""
        if not messages:
            return # Don't save empty sessions

        # Auto-generate title from first user message if not provided
        if not title:
            for msg in messages:
                if msg["role"] == "user":
                    title = msg["content"][:30] + "..." if len(msg["content"]) > 30 else msg["content"]
                    break
            if not title:
                title = "New Chat"

        data = {
            "id": session_id,
            "title": title,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "messages": messages
        }

        file_path = self._get_file_path(session_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        self._prune_old_sessions()

    def load_session(self, session_id: str) -> Dict[str, Any]:
        """Loads a chat session from disk."""
        file_path = self._get_file_path(session_id)
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"id": session_id, "messages": [], "title": "New Chat"}

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Lists all available sessions sorted by updated_at (newest first)."""
        sessions = []
        files = glob.glob(os.path.join(self.sessions_dir, "*.json"))
        
        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    sessions.append({
                        "id": data.get("id"),
                        "title": data.get("title", "Untitled"),
                        "updated_at": data.get("updated_at", "")
                    })
            except Exception:
                continue # Skip broken files

        # Sort by date descending
        sessions.sort(key=lambda x: x["updated_at"], reverse=True)
        return sessions

    def delete_session(self, session_id: str):
        """Deletes a session file."""
        file_path = self._get_file_path(session_id)
        if os.path.exists(file_path):
            os.remove(file_path)

    def _prune_old_sessions(self):
        """Keeps only the most recent N sessions."""
        sessions = self.list_sessions()
        if len(sessions) > self.max_sessions:
            # Sessions are already sorted newest first, so we remove from the end
            to_remove = sessions[self.max_sessions:]
            for session in to_remove:
                self.delete_session(session["id"])
