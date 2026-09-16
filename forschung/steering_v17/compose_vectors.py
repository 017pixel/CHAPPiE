"""Build uncalibrated, unit-norm composite directions from explicit base weights.

The recipe is a frozen research hypothesis. No generated-response measurement or
held-out projection from a directly trained composite is inherited.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np

from brain.steering.vector_pack import LayerVectorPack
from config.emotions import EMOTION_ORDER


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compose(source: Path, recipe_path: Path, output: Path) -> dict:
    recipe = json.loads(recipe_path.read_text())
    metadata = json.loads(source.read_text())
    if recipe.get("source_pack_sha256") != digest(source):
        raise ValueError("Composition recipe source pack mismatch")
    recipes = recipe.get("composites")
    if not isinstance(recipes, dict) or not recipes:
        raise ValueError("Composition requires explicit composite weights")
    pack = LayerVectorPack(source, metadata["model"], require_calibrated=False)
    composed = {}
    for name, weights in recipes.items():
        if name not in metadata["emotions"] or name in EMOTION_ORDER:
            raise ValueError("Composition target must be an existing non-base concept")
        if not isinstance(weights, dict) or not weights:
            raise ValueError("Composite requires nonempty base weights")
        result = np.zeros_like(next(iter(pack.arrays.values())), dtype=np.float64)
        valid = np.ones(result.shape[:-1], dtype=bool)
        for base, weight in weights.items():
            if base not in EMOTION_ORDER or base not in pack.arrays:
                raise ValueError("Composition sources must be measured base emotions")
            if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not np.isfinite(weight) or weight == 0:
                raise ValueError("Composition weights must be finite nonzero numbers")
            base_valid = np.asarray(metadata["emotions"][base]["valid_directions"], dtype=bool)
            base_norms = np.linalg.norm(pack.arrays[base], axis=-1)
            if not np.all(np.isclose(base_norms[base_valid], 1.0, atol=1e-4)):
                raise ValueError("Composition requires unit-norm valid base directions")
            result += weight * pack.arrays[base]
            valid &= base_valid
        norms = np.linalg.norm(result, axis=-1)
        valid &= norms >= 1e-10
        result /= np.maximum(norms[..., None], 1e-10)
        result[~valid] = 0
        composed[name] = (result.astype(np.float32), norms, valid)
    # Validate everything before creating the immutable output directory.
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(recipe_path, output / "composition_recipe.json")
    shutil.copyfile(source, output / "source_vector_pack.json")
    shutil.copyfile(Path(__file__), output / "generator.py.txt")
    result_metadata = {key: value for key, value in metadata.items()
                       if key not in ("emotions", "profiles", "calibration", "acceptance")}
    result_metadata.update({
        "method": "unit_normalized_base_composition",
        "status": "uncalibrated",
        "source_pack_sha256": digest(source),
        "composition_recipe_sha256": digest(recipe_path),
        "generator_sha256": digest(Path(__file__)),
        "composition_validation": "not_measured",
        "emotions": {},
    })
    for name, entry in metadata["emotions"].items():
        if name in composed:
            vectors, norms, valid = composed[name]
            filename = name + ".npz"
            np.savez_compressed(output / filename, vectors=vectors, raw_norms=norms)
            result_metadata["emotions"][name] = {
                "vector_file": filename,
                "sha256": digest(output / filename),
                "valid_directions": valid.tolist(),
                "method": "unit_normalized_base_composition",
                "base_weights": recipes[name],
                "heldout_projection_mean": None,
                "heldout_positive_fraction": None,
                "validation_count": 0,
            }
        else:
            shutil.copyfile(source.parent / entry["vector_file"], output / entry["vector_file"])
            result_metadata["emotions"][name] = entry
    (output / "vector_pack.json").write_text(json.dumps(result_metadata, indent=2) + "\n")
    LayerVectorPack(output / "vector_pack.json", metadata["model"], require_calibrated=False)
    return result_metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--recipe", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = compose(args.pack, args.recipe, args.output)
    print(f"Composed {len(json.loads(args.recipe.read_text())['composites'])} concepts; {result['status']}")
