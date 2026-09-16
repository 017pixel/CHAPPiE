"""Offline research capture and measured intervention contracts."""

import json
import sys
import tempfile
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import torch
from brain.steering_backend import LocalSteeringEngine
from forschung.steering_v17.benchmark import load_cases
from brain.steering.telemetry import cached_model_revision, model_artifact_hash, loaded_quantization
from types import SimpleNamespace


def test_revision_pin():
    with patch("huggingface_hub.try_to_load_from_cache", return_value="/cache/snapshots/abc123/config.json"):
        assert cached_model_revision("Qwen/Qwen3.5-4B") == "abc123"
    with tempfile.TemporaryDirectory() as directory:
        assert cached_model_revision(directory) is None
    engine = LocalSteeringEngine.__new__(LocalSteeringEngine)
    engine.model_name = "Qwen/Qwen3.5-4B"
    engine.model_revision = "abc123"
    assert engine._build_loader_kwargs()["revision"] == "abc123"
    assert engine._build_loader_kwargs(for_model=True)["revision"] == "abc123"


def test_loaded_artifact_provenance():
    assert loaded_quantization(SimpleNamespace(is_loaded_in_4bit=True)) == "4bit"
    assert loaded_quantization(SimpleNamespace(is_loaded_in_8bit=True)) == "8bit"
    assert loaded_quantization(SimpleNamespace()) == "none"
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "adapter_model.safetensors"
        path.write_bytes(b"adapter-A")
        first = model_artifact_hash(directory)
        path.write_bytes(b"adapter-B")
        assert model_artifact_hash(directory) != first


def test_measured_intervention():
    stats = {}
    hook = LocalSteeringEngine._pre_hook_factory(torch.tensor([0.3, 0.4]), stats, 7)
    original = torch.ones(1, 2, 2)
    updated = hook(None, (original,))[0]
    actual = updated - original
    measurement = stats["layer_measurements"]["7"]
    assert abs(measurement["hidden_state_rms"] - 1.0) < 1e-6
    assert (
        abs(measurement["intervention_rms"] - float(actual.square().mean().sqrt()))
        < 1e-6
    )
    assert abs(measurement["intervention_norm"] - float(actual.norm())) < 1e-6
    assert torch.equal(original, torch.ones_like(original))
    hook(None, (torch.ones(1, 1, 2) * 3,))
    assert stats["layer_invocations"]["7"] == 2
    assert stats["layer_measurements"]["7"] == measurement


def test_dataset_validation():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "cases.jsonl"
        path.write_text(json.dumps({"id": "a", "prompt": "Test"}) + "\n")
        assert len(load_cases(path)) == 1
        path.write_text(path.read_text() * 2)
        try:
            load_cases(path)
        except ValueError:
            pass
        else:
            raise AssertionError("Duplicate ids accepted")


if __name__ == "__main__":
    test_revision_pin()
    test_loaded_artifact_provenance()
    test_measured_intervention()
    test_dataset_validation()
    print("Research capture contracts passed")
