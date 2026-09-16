"""Regression tests for provenance, resumed failures and layer-aligned capture."""

import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
import numpy as np
import torch
from forschung.steering_v17 import benchmark
from forschung.steering_v17.build_vectors import build
from forschung.steering_v17.collect_activations import capture


def test_untracked_source_fingerprint():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "brain").mkdir()
        path = root / "brain/new.py"
        path.write_text("first")
        with (
            patch.object(benchmark, "ROOT", root),
            patch.object(
                benchmark.subprocess, "check_output", return_value=b"brain/new.py\0"
            ),
        ):
            first = benchmark.source_fingerprint()
            path.write_text("second")
            assert benchmark.source_fingerprint() != first


def test_resume_retries_errors_without_duplicating_success():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        dataset = root / "cases.jsonl"
        dataset.write_text(json.dumps({"id": "a", "prompt": "Test"}) + "\n")
        request = httpx.Request("POST", "http://localhost/v1/chat/completions")
        failed = httpx.Response(503, request=request)
        success = httpx.Response(
            200, request=request, json={"choices": [{"message": {"content": "ok"}}]}
        )

        class Client:
            calls = 0

            def __init__(self, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def post(self, *args, **kwargs):
                Client.calls += 1
                return failed if Client.calls == 1 else success

        manifest = {
            key: "fixed"
            for key in (
                "dataset_hash",
                "model",
                "modes",
                "seeds",
                "temperature",
                "max_tokens",
                "source_tree_sha256",
            )
        }
        with (
            patch.object(benchmark, "create_manifest", return_value=manifest),
            patch.object(benchmark, "freeze_source"),
            patch.object(benchmark.httpx, "Client", Client),
        ):
            kwargs = dict(
                endpoint="http://localhost", model="test", modes=["off"], seeds=[42]
            )
            first = benchmark.run(dataset, root / "run", **kwargs)
            assert first["errors"] == 1
            second = benchmark.run(dataset, root / "run", **kwargs)
            assert (
                second["errors"] == 0
                and second["recorded"] == 1
                and second["historical_errors"] == 1
            )
            benchmark.run(dataset, root / "run", **kwargs)
            assert Client.calls == 2


def test_sweep_resume_preserves_json_configuration():
    from forschung.steering_v17 import layer_sweep
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        dataset = root / "cases.jsonl"
        dataset.write_text(json.dumps({"id": "a", "prompt": "Test"}) + "\n")
        pack = SimpleNamespace(layers=1, metadata={"poolings": ["last_four_tokens"], "model_revision": "r1",
                               "emotions": {"frustration": {"valid_directions": [[True]]}}},
                               vector_spec=lambda *a: {"pack_hash": "fixed"}, payload=lambda *a: {})
        response = httpx.Response(200, request=httpx.Request("POST", "http://localhost"),
                                 json={"choices": [{"message": {"content": "ok"}}],
                                       "runtime_provenance": {"model": "test", "model_revision": "r1"}})
        class Client:
            calls = 0
            def __init__(self, **kwargs): pass
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def post(self, *args, **kwargs):
                self.__class__.calls += 1
                return response
        args = SimpleNamespace(pack=root/"pack.json", model="test", dataset=dataset, output=root/"run",
                               stage="screen", emotion="frustration", pooling="last_four_tokens", previous=None,
                               max_tokens=8, endpoint="http://localhost", seeds=[42, 43])
        with patch.object(layer_sweep, "LayerVectorPack", return_value=pack), patch.object(layer_sweep.httpx, "Client", Client):
            layer_sweep.run(args)
            layer_sweep.run(args)
        assert Client.calls == 2
        rows = list(map(json.loads, (root / "run/generations.jsonl").read_text().splitlines()))
        assert {row["seed"] for row in rows} == {42, 43}


def test_null_layer_does_not_discard_good_vectors():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        captures = root / "capture"
        captures.mkdir()
        (captures / "manifest.json").write_text(
            json.dumps(
                {
                    "model": "test",
                    "model_revision": "r1",
                    "site": "decoder_layer_input",
                    "dataset_hashes": {},
                }
            )
        )
        for index in range(64):
            neutral = np.zeros((3, 2, 2), dtype=np.float32)
            positive = neutral.copy()
            positive[:, 1, 0] = 2
            np.savez(
                captures / f"p{index}.npz",
                emotion="calm",
                split="train" if index < 48 else "validation",
                neutral=neutral,
                positive=positive,
            )
        pack = build(captures, root / "vectors")
        assert pack["emotions"]["calm"]["valid_directions"] == [[False, True]] * 3
        with np.load(root / "vectors/calm.npz") as data:
            assert np.isfinite(data["vectors"]).all()
            assert np.all(data["vectors"][:, 1, 0] == 1)


def test_builder_rejects_incomplete_capture():
    import hashlib
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        dataset = root / "pairs.jsonl"
        dataset.write_text(json.dumps({"id": "missing-pair"}) + "\n")
        captures = root / "capture"
        captures.mkdir()
        (captures / "manifest.json").write_text(json.dumps({"dataset_hashes": {str(dataset): hashlib.sha256(dataset.read_bytes()).hexdigest()}}))
        try:
            build(captures, root / "pack")
        except ValueError as exc:
            assert "incomplete" in str(exc)
        else:
            raise AssertionError("An incomplete capture was built into a vector pack")


def test_capture_ignores_template_end_markers():
    prompt = "USER: hi ASSISTANT: abc!<END>"

    class Tokenizer:
        def apply_chat_template(self, *args, **kwargs):
            return prompt

        def __call__(self, text, **kwargs):
            return {
                "input_ids": torch.arange(len(text)).unsqueeze(0),
                "offset_mapping": torch.tensor(
                    [[[i, i + 1] for i in range(len(text))]]
                ),
            }

    layers = [torch.nn.Identity(), torch.nn.Identity()]

    def model(input_ids, **kwargs):
        hidden = input_ids.float().unsqueeze(-1).repeat(1, 1, 2)
        for layer in layers:
            hidden = layer(hidden)
        return hidden

    engine = SimpleNamespace(
        tokenizer=Tokenizer(), layers=layers, device=torch.device("cpu"), model=model
    )
    result = capture(engine, "abc!", "hi", 2)
    last = prompt.index("abc!") + 3
    assert np.all(result[0] == last)
    assert np.all(result[1] == last - 1.5)
    assert np.all(result[2] == last - 0.5)
    assert all(not layer._forward_pre_hooks for layer in layers)



def test_snapshot_tampering_and_pinned_provenance():
    import hashlib
    import zipfile
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        files = [("brain/example.py", b"original")]
        fingerprint = hashlib.sha256(b"brain/example.py\0original\0").hexdigest()
        manifest = {"source_tree_sha256": fingerprint, "model_revision": "r1"}
        with patch.object(benchmark, "source_files", return_value=iter(files)):
            benchmark.freeze_source(root, manifest)
        benchmark.freeze_source(root, manifest)
        with zipfile.ZipFile(root / "source.zip", "w") as archive:
            archive.writestr("brain/example.py", b"changed")
        try:
            benchmark.freeze_source(root, manifest)
        except benchmark.ProvenanceMismatch:
            pass
        else:
            raise AssertionError("Tampered source archive accepted")
        (root / "manifest.json").write_text(json.dumps(manifest))
        try:
            benchmark.record_server_provenance(root, {})
        except benchmark.ProvenanceMismatch:
            pass
        else:
            raise AssertionError("Pinned experiment accepted missing provenance")


def test_pooling_comparison_holds_sites_and_doses_constant():
    from forschung.steering_v17.layer_sweep import configurations
    with tempfile.TemporaryDirectory() as directory:
        previous = Path(directory) / "metrics.json"
        rows = [{"layers": [1, 2], "strength": .15},
                {"layers": [1], "strength": .2},
                {"layers": [2], "strength": .1}]
        previous.write_text(json.dumps({"ranking": rows}))
        pack = SimpleNamespace(metadata={"poolings": ["a", "b", "c"],
            "emotions": {"frustration": {"valid_directions": [[True] * 3] * 3}}})
        results = [configurations("pooling", pack, "frustration", pooling, previous)
                   for pooling in ("a", "b", "c")]
        assert results[0] == results[1] == results[2]
        assert results[0] == [([1, 2], .15), ([1], .2), ([2], .1)]
        refined = configurations("refine", pack, "frustration", "a", previous, top_configurations=1)
        assert refined == [([1, 2], .4), ([1, 2], .55), ([1, 2], .7)]
        try:
            configurations("refine", pack, "frustration", "a", previous, strengths=[float("nan")])
        except ValueError:
            pass
        else:
            raise AssertionError("Nonfinite experimental strength accepted")
        pack.metadata["emotions"]["frustration"]["valid_directions"] = [[True] * 3, [True, False, True], [True] * 3]
        try:
            configurations("pooling", pack, "frustration", "b", previous)
        except ValueError as exc:
            assert "Fixed pooling candidates" in str(exc)
        else:
            raise AssertionError("Invalid pooling silently selected different sites")

if __name__ == "__main__":
    test_pooling_comparison_holds_sites_and_doses_constant()
    test_snapshot_tampering_and_pinned_provenance()
    test_sweep_resume_preserves_json_configuration()
    test_untracked_source_fingerprint()
    test_resume_retries_errors_without_duplicating_success()
    test_null_layer_does_not_discard_good_vectors()
    test_capture_ignores_template_end_markers()
    test_builder_rejects_incomplete_capture()
    print("Research integrity regressions passed")
