"""Readiness contract tests for the local steering API."""

import os
import sys
from types import SimpleNamespace

from fastapi.testclient import TestClient

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from brain.steering_api_server import create_app  # noqa: E402


def test_health_is_unavailable_before_engine_is_ready():
    app = create_app("test-model")
    response = TestClient(app).get("/health")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "unavailable"
    assert payload["restart_status"] == "starting"
    assert payload["model"] == "test-model"


def test_models_is_unavailable_during_restart():
    app = create_app("test-model")
    app.state.engine = SimpleNamespace()
    app.state.restart_status = "loading"

    response = TestClient(app).get("/v1/models")

    assert response.status_code == 503
    payload = response.json()
    assert payload["object"] == "list"
    assert payload["data"][0]["id"] == "test-model"


def test_health_and_models_keep_success_contract_when_engine_is_ready():
    app = create_app("test-model")
    app.state.engine = SimpleNamespace(device="cpu", last_steering_report={"status": "verified"})
    app.state.restart_status = "ready"
    client = TestClient(app)

    health = client.get("/health")
    models = client.get("/v1/models")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["device"] == "cpu"
    assert models.status_code == 200
    assert models.json()["object"] == "list"
    assert models.json()["data"][0]["id"] == "test-model"


if __name__ == "__main__":
    test_health_is_unavailable_before_engine_is_ready()
    test_models_is_unavailable_during_restart()
    test_health_and_models_keep_success_contract_when_engine_is_ready()
    print("OK: steering API readiness")
