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


def test_invalid_session_id_cannot_read_outside_session_directory(tmp_path):
    outside_path = tmp_path / "outside.json"
    outside_path.write_text('{"id":"outside","messages":[{"content":"secret"}]}', encoding="utf-8")
    manager = ChatManager(str(tmp_path))

    session = manager.load_session("../outside")

    assert session["id"] != "../outside"
    assert all(message.get("content") != "secret" for message in session["messages"])
    assert outside_path.read_text(encoding="utf-8").endswith("}")


def test_invalid_session_id_cannot_delete_outside_session_directory(tmp_path):
    outside_path = tmp_path / "outside.json"
    outside_path.write_text('{"protected":true}', encoding="utf-8")
    manager = ChatManager(str(tmp_path))

    deleted = manager.delete_session("../outside")

    assert deleted is False
    assert outside_path.exists()


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        test_save_session_with_missing_session_id_creates_real_session(path)
        test_active_session_is_restored_across_reloads(path)
        test_update_message_replaces_pending_placeholder(path)
        test_invalid_session_id_cannot_read_outside_session_directory(path)
        test_invalid_session_id_cannot_delete_outside_session_directory(path)
    print("OK: chat manager persistence")
