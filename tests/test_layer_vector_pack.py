"""Layer vectors never migrate between layers, architectures or model revisions."""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import torch
from brain.steering_backend import ActivationVectorResolver, build_activation_plan


def test_exact_layer_assignment():
    resolver = ActivationVectorResolver.__new__(ActivationVectorResolver)
    resolver.model_name = "Qwen/test"
    resolver.num_layers = 4
    resolver.hidden_size = 2
    resolver.model = SimpleNamespace(config=SimpleNamespace(_commit_hash="r1"))
    vector = {
        "type": "layer_vectors",
        "model": "Qwen/test",
        "model_revision": "r1",
        "site": "decoder_layer_input",
        "num_layers": 4,
        "hidden_size": 2,
        "layers": {"1": [1, 0], "3": [0, 1]},
    }
    item = {
        "name": "frustration",
        "vector": vector,
        "strength": 0.2,
        "layer_range": [1, 3],
    }
    plan = build_activation_plan(
        {"steering": {"model_layers": 4, "vectors": [item]}},
        resolver.resolve,
        actual_layer_count=4,
    )
    assert set(plan) == {1, 3}
    assert torch.allclose(plan[1], torch.tensor([0.2, 0.0]))
    assert torch.allclose(plan[3], torch.tensor([0.0, 0.2]))
    for changes in (
        {"model": "Gemma/test"},
        {"model_revision": "r2"},
        {"site": "decoder_layer_output"},
        {"hidden_size": 3},
        {"layers": {"4": [1, 0]}},
        {"layers": {"1": [float("nan"), 0]}},
    ):
        try:
            resolver.resolve({**item, "vector": {**vector, **changes}}, 1, 3)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Invalid pack accepted: {changes}")


if __name__ == "__main__":
    test_exact_layer_assignment()
    print("Exact layer/model/revision vector contracts passed")
