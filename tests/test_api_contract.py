"""Leichte Contract-Tests fuer die neue FastAPI-App."""

import os
import sys
from types import SimpleNamespace

from fastapi.testclient import TestClient

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from api.dependencies import get_backend  # noqa: E402
from api.main import app  # noqa: E402


class _DummyDebugLogger:
    enabled = True

    @staticmethod
    def get_entries_as_dict():
        return [{"category": "TURN", "message": "ok"}]

    @staticmethod
    def get_formatted_log():
        return "ok"


class _DummyLife:
    @staticmethod
    def get_snapshot():
        return {
            "clock": {"phase_label": "Tag 1, 10:00 Uhr (Berlin)"},
            "planning_state": {"planning_horizon": "near_term"},
            "forecast_state": {"risk_level": "low"},
            "social_arc": {"arc_name": "trust_building"},
            "timeline_history": [],
            "timeline_summary": {"entries": 0},
            "development": {"stage": "awakening"},
            "habit_dynamics": {},
        }


class _DummyChatManager:
    def __init__(self):
        self.sessions = {
            "session-1": {
                "id": "session-1",
                "title": "Test",
                "updated_at": "",
                "messages": [],
            }
        }

    @staticmethod
    def create_message_id():
        return "message-1"

    def ensure_session_id(self, session_id):
        return session_id or "session-1"

    def load_session(self, session_id):
        return self.sessions.setdefault(session_id, {"id": session_id, "title": "Test", "updated_at": "", "messages": []})

    def load_active_session(self):
        return self.load_session("session-1")

    def set_active_session(self, session_id):
        return session_id

    def save_session(self, session_id, messages, title=None):
        self.sessions[session_id] = {"id": session_id, "title": title or "Test", "updated_at": "", "messages": messages}
        return session_id

    def update_message(self, session_id, message_id, *, content=None, metadata_updates=None, role=None):
        session = self.sessions[session_id]
        for message in session["messages"]:
            if message.get("id") == message_id:
                if content is not None:
                    message["content"] = content
                if role is not None:
                    message["role"] = role
                if metadata_updates:
                    metadata = dict(message.get("metadata") or {})
                    metadata.update(metadata_updates)
                    message["metadata"] = metadata
        return session

    def list_sessions(self):
        return list(self.sessions.values())

    def delete_session(self, session_id):
        self.sessions.pop(session_id, None)

    @staticmethod
    def create_session():
        return "new-session"


class _DummyMemory:
    @staticmethod
    def get_recent_memories(limit=10, offset=0, mem_type_filter=None, label_filter=None):
        return [
            SimpleNamespace(
                id="mem-1",
                content="Memory entry",
                role="assistant",
                timestamp="2026-03-30T10:00:00+00:00",
                mem_type=mem_type_filter or "interaction",
                relevance_score=0.91,
                label=label_filter or "original",
            )
        ]

    @staticmethod
    def search_memory(query, top_k=10, min_relevance=0.0):
        return [
            SimpleNamespace(
                id="mem-search",
                content=f"Match for {query}",
                role="assistant",
                timestamp="2026-03-30T10:00:00+00:00",
                mem_type="interaction",
                relevance_score=0.77,
                label="original",
            )
        ]

    @staticmethod
    def get_filtered_memory_count(mem_type_filter=None, label_filter=None):
        return 1

    @staticmethod
    def health_check():
        return {"memory_count": 1, "embedding_model_loaded": True, "chromadb_connected": True, "is_persistent": True}

    @staticmethod
    def clear_memory():
        return 1


class _DummyShortTermMemory:
    @staticmethod
    def get_active_entries(category=None, query=None):
        return [
            SimpleNamespace(
                id="stm-1",
                content="Short term entry",
                category=category or "chat",
                importance="high",
                created_at="2026-03-30T10:00:00+00:00",
                expires_at="2026-03-31T10:00:00+00:00",
                migrated=False,
            )
        ]

    @staticmethod
    def migrate_expired_entries():
        return 0

    @staticmethod
    def get_count():
        return 1


class _DummyContextFiles:
    @staticmethod
    def get_all_context():
        return {"soul": "Soul", "user": "User", "preferences": "Preferences"}

    @staticmethod
    def get_soul_context():
        return "Soul"

    @staticmethod
    def get_user_context():
        return "User"

    @staticmethod
    def get_preferences_context():
        return "Preferences"


class _DummySteeringManager:
    @staticmethod
    def build_debug_report(emotions):
        return {"mode": "local_layer_only", "emotion_state": emotions}


class _DummySleep:
    @staticmethod
    def get_status():
        return {"trigger_due": False}


class _DummyBackend:
    def __init__(self):
        self.chat_manager = _DummyChatManager()
        self.debug_logger = _DummyDebugLogger()
        self.life_simulation = _DummyLife()
        self.memory = _DummyMemory()
        self.short_term_memory_v2 = _DummyShortTermMemory()
        self.context_files = _DummyContextFiles()
        self.steering_manager = _DummySteeringManager()
        self.sleep_handler = _DummySleep()

    @staticmethod
    def get_status():
        return {
            "brain_available": True,
            "model": "Qwen/Qwen3.5-4B",
            "emotions": {"happiness": 70},
            "daily_info_count": 2,
            "two_step_enabled": True,
            "life_snapshot": _DummyLife.get_snapshot(),
            "life_state": _DummyLife.get_snapshot(),
        }

    @staticmethod
    def _build_pending_message(message_id):
        return {"id": message_id, "role": "assistant", "content": "_CHAPPiE denkt nach..._", "metadata": {"pending": True}}

    @staticmethod
    def _build_assistant_message(user_input, result, message_id=None):
        return {
            "id": message_id or "message-1",
            "role": "assistant",
            "content": result.get("response_text", ""),
            "metadata": {"pending": False, "status_text": "", "retry_history": result.get("retry_history", [])},
        }

    @staticmethod
    def handle_command(command):
        return f"command:{command}"

    @staticmethod
    def process(message, history, debug_mode=False, status_callback=None):
        if status_callback:
            status_callback({"step": 1, "status_text": "Intent-Analyse"})
        return {
            "response_text": f"echo:{message}",
            "emotions": {"happiness": 72},
            "life_snapshot": _DummyLife.get_snapshot(),
            "sleep_status": {"trigger_due": False},
            "debug_entries": [{"category": "TURN"}],
            "retry_history": [],
        }

    @staticmethod
    def get_emotion_layer_config():
        return [{"emotion": "happiness", "layer_start": 10, "layer_end": 20, "default_alpha": 0.3}]

    @staticmethod
    def update_emotion_layer_config(*args, **kwargs):
        return None

    @staticmethod
    def apply_runtime_settings(force=False):
        return None

    @staticmethod
    def _get_emotions_snapshot():
        return {"happiness": 70, "energy": 60, "frustration": 10}


def test_health_and_status_routes():
    app.dependency_overrides[get_backend] = lambda: _DummyBackend()
    client = TestClient(app)

    health = client.get("/health")
    status = client.get("/status")

    assert health.status_code == 200
    assert health.json()["brain_available"] is True
    assert status.status_code == 200
    assert status.json()["model"] == "Qwen/Qwen3.5-4B"
    app.dependency_overrides.clear()


def test_chat_route_returns_serialized_turn_payload():
    app.dependency_overrides[get_backend] = lambda: _DummyBackend()
    client = TestClient(app)

    response = client.post("/chat", json={"session_id": "session-1", "message": "Hallo", "debug_mode": False, "command_mode": False})

    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"]["content"] == "echo:Hallo"
    assert payload["emotion_snapshot"]["happiness"] == 72
    app.dependency_overrides.clear()


def test_memory_context_and_visualizer_routes_return_expected_shapes():
    app.dependency_overrides[get_backend] = lambda: _DummyBackend()
    client = TestClient(app)

    memories = client.get("/memories")
    short_term = client.get("/memories/short-term")
    context = client.get("/context-files")
    visualizer = client.get("/visualizer")
    debug = client.get("/debug")
    settings = client.get("/settings")
    training = client.get("/training/status")

    assert memories.status_code == 200
    assert memories.json()["items"][0]["id"] == "mem-1"
    assert short_term.status_code == 200
    assert short_term.json()["items"][0]["id"] == "stm-1"
    assert context.status_code == 200
    assert context.json()["preferences"] == "Preferences"
    assert visualizer.status_code == 200
    assert visualizer.json()["model"]
    assert debug.status_code == 200
    assert "entries" in debug.json()
    assert settings.status_code == 200
    assert "llm_provider" in settings.json()
    assert training.status_code == 200
    assert "status_label" in training.json()
    app.dependency_overrides.clear()


if __name__ == "__main__":
    test_health_and_status_routes()
    test_chat_route_returns_serialized_turn_payload()
    test_memory_context_and_visualizer_routes_return_expected_shapes()
    print("OK: api contract")
