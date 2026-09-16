"""Validated model-specific layer vectors. No Qwen/Gemma remapping is allowed."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from config.config import get_steering_runtime_config


class LayerVectorPack:
    def __init__(
        self, manifest_path: Path, model: str, *, require_calibrated: bool = True
    ):
        self.path = Path(manifest_path).resolve()
        self.metadata = json.loads(self.path.read_text())
        if (
            self.metadata.get("schema_version") != 1
            or self.metadata.get("model") != model
        ):
            raise ValueError("Vector pack schema/model mismatch")
        if self.metadata.get("site") != "decoder_layer_input":
            raise ValueError("Vector pack intervention site mismatch")
        if require_calibrated and self.metadata.get("status") != "calibrated":
            raise ValueError("Vector pack is not empirically calibrated")
        self.model = model
        self.layers = int(self.metadata["num_layers"])
        self.hidden_size = int(self.metadata["hidden_size"])
        self.arrays = {}
        for emotion, entry in self.metadata["emotions"].items():
            path = (self.path.parent / entry["vector_file"]).resolve()
            if path.parent != self.path.parent:
                raise ValueError("Vector file escapes pack directory")
            if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
                raise ValueError("Vector checksum mismatch")
            with np.load(path, allow_pickle=False) as data:
                vectors = np.asarray(data["vectors"], dtype=np.float32)
            if (
                vectors.shape
                != (len(self.metadata["poolings"]), self.layers, self.hidden_size)
                or not np.isfinite(vectors).all()
            ):
                raise ValueError("Invalid vector dimensions or nonfinite values")
            self.arrays[emotion] = vectors

    def vector_spec(
        self, emotion: str, layers: list[int], pooling: str
    ) -> dict[str, Any]:
        pool = self.metadata["poolings"].index(pooling)
        valid = self.metadata["emotions"][emotion]["valid_directions"][pool]
        if not layers or len(set(layers)) != len(layers):
            raise ValueError("Layer selection must be nonempty and unique")
        selected = {}
        for layer in layers:
            if not 0 <= layer < self.layers or not valid[layer]:
                raise ValueError("Selected layer has no measured direction")
            vector = self.arrays[emotion][pool, layer]
            if not np.isclose(np.linalg.norm(vector), 1.0, atol=1e-4):
                raise ValueError("Layer vector is not normalized")
            selected[str(layer)] = vector.tolist()
        return {
            "type": "layer_vectors",
            "model": self.model,
            "model_revision": self.metadata["model_revision"],
            "site": self.metadata["site"],
            "num_layers": self.layers,
            "hidden_size": self.hidden_size,
            "pack_hash": hashlib.sha256(self.path.read_bytes()).hexdigest(),
            "pooling": pooling,
            "layers": selected,
        }

    def payload(
        self, emotion: str, layers: list[int], strength: float, pooling: str
    ) -> dict[str, Any]:
        cap = float(get_steering_runtime_config()["research_alpha_cap"])
        if not np.isfinite(strength) or not 0 <= strength <= cap:
            raise ValueError(f"Research strength must be in [0, {cap:g}]")
        spec = self.vector_spec(emotion, layers, pooling)
        return {
            "steering": {
                "enabled": True,
                "mode": "activation",
                "model_layers": self.layers,
                "vectors": [
                    {
                        "name": emotion,
                        "vector": spec,
                        "layer_range": [min(layers), max(layers)],
                        "strength": strength,
                        "direction": "positive",
                        "source": (
                            "measured_base_composition"
                            if self.metadata["emotions"][emotion].get("method")
                            == "unit_normalized_base_composition"
                            else "measured_diffmean"
                        ),
                    }
                ],
                "sequences": [],
            }
        }
