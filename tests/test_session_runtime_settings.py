"""Session settings survive messages/reloads and remain isolated under updates."""

import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from types import ModuleType, SimpleNamespace
from unittest.mock import patch
from memory.chat_manager import ChatManager
# Exercise the real router and storage, but not the unrelated model/Chroma
# implementation imported by its dependency factory. Real runtime integration
# is covered by the separate live experiment.
def unexpected_runtime(*args, **kwargs):
    raise AssertionError("Offline session tests must override the runtime dependency")

runtime_stub = ModuleType("web_infrastructure.chappie_runtime")
runtime_stub.CHAPPiERuntime = object
runtime_stub.create_chappie_backend = unexpected_runtime
with patch.dict(sys.modules, {"web_infrastructure.chappie_runtime": runtime_stub}):
    from api.routers.chat import router
    from api.dependencies import get_backend


def test_settings(root):
    manager = ChatManager(str(root))
    a, b = manager.create_session(), manager.create_session()
    manager.update_runtime_settings(
        a, {"memory_enabled": False, "steering_mode": "activation"}
    )
    manager.update_runtime_settings(
        b, {"memory_enabled": True, "steering_mode": "combined"}
    )
    manager.save_session(a, [{"role": "user", "content": "Hallo"}])
    restored = ChatManager(str(root))
    assert not restored.get_runtime_settings(a).memory_enabled
    assert restored.get_runtime_settings(b).memory_enabled
    assert restored.get_runtime_settings(a).steering_mode == "activation"
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(
            pool.map(
                lambda i: ChatManager(str(root)).update_runtime_settings(
                    a, {"live_enabled": bool(i % 2)}
                ),
                range(32),
            )
        )
    assert not manager.get_runtime_settings(a).memory_enabled
    assert manager.get_runtime_settings(b).steering_mode == "combined"
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_backend] = lambda: SimpleNamespace(
        chat_manager=manager
    )
    with TestClient(app) as client:
        assert client.get(f"/sessions/{a}/settings").json()["memory_enabled"] is False
        assert (
            client.patch(
                f"/sessions/{a}/settings", json={"steering_enabled": False}
            ).status_code
            == 200
        )
        assert (
            client.patch(
                f"/sessions/{a}/settings", json={"memory_enabled": "false"}
            ).status_code
            == 422
        )
        assert (
            client.patch(
                f"/sessions/{a}/settings", json={"steering_mode": "invalid"}
            ).status_code
            == 422
        )
        assert (
            client.patch(f"/sessions/{a}/settings", json={"unknown": True}).status_code
            == 422
        )
        assert (
            client.patch(
                f"/sessions/{a}/settings", json={"memory_enabled": None}
            ).status_code
            == 400
        )
        assert manager.get_runtime_settings(a).effective_mode == "off"
        assert manager.get_runtime_settings(b).effective_mode == "combined"


def test_commands(root):
    from unittest.mock import MagicMock
    from api.services.command_service import execute_slash_command
    backend = MagicMock()
    backend.chat_manager = ChatManager(str(root))
    backend.get_emotions_snapshot.return_value = {"frustration": 20}
    a, b = backend.chat_manager.create_session(), backend.chat_manager.create_session()
    result = execute_slash_command("/memory off", backend, session_id=a)
    assert result["runtime_settings"]["memory_enabled"] is False
    assert backend.chat_manager.get_runtime_settings(b).memory_enabled
    execute_slash_command("/memory search Geheimnis", backend, session_id=a)
    backend.memory.search_memory.assert_not_called()
    execute_slash_command("/steering mode activation", backend, session_id=a)
    execute_slash_command("/steering mode off", backend, session_id=a)
    assert backend.chat_manager.get_runtime_settings(a).effective_mode == "off"
    execute_slash_command("/steering on", backend, session_id=a)
    assert backend.chat_manager.get_runtime_settings(a).effective_mode == "activation"
    execute_slash_command("/live off", backend, session_id=a)
    assert not backend.chat_manager.get_runtime_settings(a).live_enabled
    assert backend.chat_manager.get_runtime_settings(b).live_enabled
    result = execute_slash_command("/steering mode invalid", backend, session_id=a)
    assert result["command_trace"]["status"] == "rejected"
    result = execute_slash_command("/emotion frustration + 50", backend, session_id=a)
    backend.emotions.set_emotion.assert_called_once_with("frustration", 70)
    assert result["emotion_update"]["is_delta"] is True
    backend.emotions.reset_mock()
    execute_slash_command("/emotion frustration + 50 garbage", backend, session_id=a)
    backend.emotions.set_emotion.assert_not_called()



def test_emotion_commands_wait_for_active_turn():
    import threading
    from unittest.mock import patch
    from api.services import command_service
    entered, executed = threading.Event(), threading.Event()
    backend = SimpleNamespace(_turn_lock=threading.Lock())
    def execute():
        entered.set()
        return command_service.execute_slash_command("/emotion frustration + 50", backend)
    with patch.object(command_service, "_execute_archived_slash_command", side_effect=lambda *args: executed.set()):
        backend._turn_lock.acquire()
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(execute)
            try:
                assert entered.wait(1)
                assert not executed.wait(.05)
            finally:
                backend._turn_lock.release()
            future.result(timeout=1)
        assert executed.is_set()

if __name__ == "__main__":
    test_emotion_commands_wait_for_active_turn()
    with tempfile.TemporaryDirectory() as directory:
        test_settings(Path(directory))
        test_commands(Path(directory) / "commands")
    print("Session persistence, API validation and concurrent isolation passed")
