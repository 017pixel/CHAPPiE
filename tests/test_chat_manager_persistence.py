"""Tests fuer stabile Chat-Session-Persistenz."""

import os
import sys
import tempfile
from pathlib import Path

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from memory.chat_manager import ChatManager  # noqa: E402


def test_save_session_with_missing_session_id_creates_real_session(tmp_path):
    manager = ChatManager(str(tmp_path))
    session_id = manager.save_session(None, [{"role": "user", "content": "Hallo"}])

    assert session_id
    assert session_id != "None"
    assert os.path.exists(tmp_path / "chat_sessions" / f"{session_id}.json")
    assert not os.path.exists(tmp_path / "chat_sessions" / "None.json")


def test_active_session_is_restored_across_reloads(tmp_path):
    manager = ChatManager(str(tmp_path))
    session_id = manager.save_session(None, [{"role": "user", "content": "Erste Nachricht"}])

    reloaded = ChatManager(str(tmp_path))
    active = reloaded.load_active_session()

    assert active["id"] == session_id
    assert active["messages"][0]["content"] == "Erste Nachricht"


def test_update_message_replaces_pending_placeholder(tmp_path):
    manager = ChatManager(str(tmp_path))
    session_id = manager.save_session(
        None,
        [
            {"role": "user", "content": "Hi"},
            {
                "id": "assistant-1",
                "role": "assistant",
                "content": "_CHAPPiE denkt nach..._",
                "metadata": {"pending": True, "status_text": "Retry 2/3"},
            },
        ],
    )

    updated = manager.update_message(
        session_id,
        "assistant-1",
        content="Fertige Antwort",
        metadata_updates={"pending": False, "status_text": ""},
    )

    assistant = updated["messages"][1]
    assert assistant["content"] == "Fertige Antwort"
    assert assistant["metadata"]["pending"] is False


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        test_save_session_with_missing_session_id_creates_real_session(path)
        test_active_session_is_restored_across_reloads(path)
        test_update_message_replaces_pending_placeholder(path)
    print("OK: chat manager persistence")