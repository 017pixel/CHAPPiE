"""Composition cancellation, provenance and physical-dose contracts, no model."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.steering.vector_pack import LayerVectorPack
from forschung.steering_v17.compose_vectors import compose


def check():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        source = root / "source"
        source.mkdir()
        emotions = {}
        for name, vector in {"frustration": [1., 0.], "sadness": [0., 1.], "trust": [1., 0.], "warm": [0., 1.]}.items():
            path = source / (name + ".npz")
            np.savez_compressed(path, vectors=np.array([[vector, vector]], dtype=np.float32))
            emotions[name] = {"vector_file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "valid_directions": [[True, True]], "heldout_positive_fraction": [[1., 1.]]}
        manifest = source / "vector_pack.json"
        manifest.write_text(json.dumps({"schema_version": 1, "model": "test", "model_revision": "revision", "site": "decoder_layer_input", "status": "calibrated", "profiles": {"warm": {}}, "num_layers": 2, "hidden_size": 2, "poolings": ["last_four_tokens"], "emotions": emotions}))
        recipe = root / "recipe.json"
        def run(weights, name):
            recipe.write_text(json.dumps({"source_pack_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(), "composites": {"warm": weights}}))
            return compose(manifest, recipe, root / name)
        metadata = run({"frustration": 3, "sadness": 4}, "good")
        loaded = LayerVectorPack(root / "good/vector_pack.json", "test", require_calibrated=False)
        np.testing.assert_allclose(loaded.arrays["warm"][0, 0], [.6, .8])
        assert loaded.payload("warm", [0], .2, "last_four_tokens")["steering"]["vectors"][0]["source"] == "measured_base_composition"
        assert loaded.payload("frustration", [0], .2, "last_four_tokens")["steering"]["vectors"][0]["source"] == "measured_diffmean"
        assert metadata["model_revision"] == "revision"
        assert metadata["status"] == "uncalibrated" and "profiles" not in metadata
        assert metadata["emotions"]["warm"]["heldout_positive_fraction"] is None
        assert (root / "good/frustration.npz").read_bytes() == (source / "frustration.npz").read_bytes()
        cancelled = run({"frustration": 1, "trust": -1}, "cancelled")
        assert cancelled["emotions"]["warm"]["valid_directions"] == [[False, False]]
        try:
            LayerVectorPack(root / "cancelled/vector_pack.json", "test", require_calibrated=False).vector_spec("warm", [0], "last_four_tokens")
        except ValueError:
            pass
        else:
            raise AssertionError("Cancelled directions must not be injected")
        for index, weights in enumerate(({"unknown": 1}, {"warm": 1}, {"sadness": float("nan")}, {"sadness": True}, {"sadness": 0}, {})):
            try:
                run(weights, f"bad{index}")
            except ValueError:
                assert not (root / f"bad{index}").exists()
            else:
                raise AssertionError("Invalid composition accepted")
        try:
            run({"sadness": 1}, "good")
        except FileExistsError:
            pass
        else:
            raise AssertionError("Prior evidence overwritten")
        recipe.write_text(json.dumps({"source_pack_sha256": "wrong", "composites": {"warm": {"sadness": 1}}}))
        try:
            compose(manifest, recipe, root / "wrong-source")
        except ValueError:
            pass
        else:
            raise AssertionError("Changed source accepted")
        # A checksum-consistent but scaled base must not distort signed weights.
        scaled = source / "sadness.npz"
        np.savez_compressed(scaled, vectors=np.array([[[0., 2.], [0., 2.]]], dtype=np.float32))
        source_meta = json.loads(manifest.read_text())
        source_meta["emotions"]["sadness"]["sha256"] = hashlib.sha256(scaled.read_bytes()).hexdigest()
        manifest.write_text(json.dumps(source_meta))
        try:
            run({"sadness": 1}, "scaled")
        except ValueError as exc:
            assert "unit-norm" in str(exc)
        else:
            raise AssertionError("Scaled valid base silently changed composition weights")
    print("PASS composition norm, cancellation, provenance, validation and immutable output")


if __name__ == "__main__":
    check()
