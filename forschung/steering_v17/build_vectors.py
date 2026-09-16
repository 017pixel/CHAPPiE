"""Training-only DiffMean vectors with held-out projection and cosine diagnostics."""

from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from forschung.steering_v17.collect_activations import POOLINGS


def build(captures: Path, output: Path) -> dict:
    source = json.loads((captures / "manifest.json").read_text())
    expected_pairs = {}
    for name, checksum in source["dataset_hashes"].items():
        dataset = Path(name)
        if hashlib.sha256(dataset.read_bytes()).hexdigest() != checksum:
            raise ValueError("Capture dataset checksum changed")
        for pair in map(json.loads, dataset.read_text().splitlines()):
            if pair["id"] in expected_pairs:
                raise ValueError("Duplicate capture pair id")
            expected_pairs[pair["id"]] = hashlib.sha256(json.dumps(pair, sort_keys=True).encode()).hexdigest()
    if expected_pairs and {p.stem for p in captures.glob("*.npz")} != set(expected_pairs):
        raise ValueError("Capture is incomplete or contains unexpected pairs")
    groups = {}
    for path in sorted(captures.glob("*.npz")):
        with np.load(path, allow_pickle=False) as data:
            if expected_pairs and data["pair_hash"].item() != expected_pairs[path.stem]:
                raise ValueError("Captured pair differs from frozen dataset")
            emotion, split = str(data["emotion"].item()), str(data["split"].item())
            groups.setdefault(emotion, {"train": [], "validation": []})[split].append(
                path
            )
    if not groups:
        raise ValueError("No captures")
    output.mkdir(parents=True, exist_ok=True)
    pack = {
        "schema_version": 1,
        "model": source["model"],
        "model_revision": source["model_revision"],
        "site": source["site"],
        "method": "diffmean",
        "status": "uncalibrated",
        "capture_pair_count": len(expected_pairs) if expected_pairs else None,
        "runtime_provenance": source.get("runtime_provenance"),
        "capture_manifest_hash": hashlib.sha256(
            (captures / "manifest.json").read_bytes()
        ).hexdigest(),
        "dataset_hashes": source["dataset_hashes"],
        "poolings": list(POOLINGS),
        "emotions": {},
    }
    all_vectors = []
    for emotion, splits in sorted(groups.items()):
        if len(splits["train"]) != 48 or len(splits["validation"]) != 16:
            raise ValueError(f"{emotion} requires 48 training and 16 held-out pairs")
        total = None
        for path in splits["train"]:
            with np.load(path, allow_pickle=False) as data:
                delta = data["positive"].astype(np.float64) - data["neutral"]
                total = delta if total is None else total + delta
        mean = total / len(splits["train"])
        norms = np.linalg.norm(mean, axis=-1, keepdims=True)
        valid = norms.squeeze(-1) >= 1e-10
        vectors = (mean / np.maximum(norms, 1e-10)).astype(np.float32)
        projections = []
        for path in splits["validation"]:
            with np.load(path, allow_pickle=False) as data:
                projections.append(
                    np.sum((data["positive"] - data["neutral"]) * vectors, axis=-1)
                )
        projection = np.stack(projections)
        filename = emotion + ".npz"
        np.savez_compressed(
            output / filename, vectors=vectors, raw_norms=norms.squeeze(-1)
        )
        pack["emotions"][emotion] = {
            "vector_file": filename,
            "sha256": hashlib.sha256((output / filename).read_bytes()).hexdigest(),
            "train_count": 48,
            "validation_count": 16,
            "valid_directions": valid.tolist(),
            "heldout_positive_fraction": (projection > 0).mean(axis=0).tolist(),
            "heldout_projection_mean": projection.mean(axis=0).tolist(),
            "heldout_projection_std": projection.std(axis=0).tolist(),
        }
        all_vectors.append(vectors)
    stacked = np.stack(all_vectors)
    cosine = np.einsum("eplh,fplh->plef", stacked, stacked)
    np.savez_compressed(
        output / "cosine_matrix.npz", cosine=cosine, emotions=np.array(sorted(groups))
    )
    pack["hidden_size"] = int(stacked.shape[-1])
    pack["num_layers"] = int(stacked.shape[-2])
    text_config = source.get("model_config", {}).get(
        "text_config", source.get("model_config", {})
    )
    pack["layer_types"] = text_config.get("layer_types", [])
    (output / "vector_pack.json").write_text(json.dumps(pack, indent=2) + "\n")
    return pack


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--captures", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    pack = build(args.captures, args.output)
    print(
        f"Built {len(pack['emotions'])} concepts, {pack['num_layers']} layers; not production-calibrated"
    )
