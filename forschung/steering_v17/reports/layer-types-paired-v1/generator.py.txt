"""Descriptive architecture comparison of a complete, paired single-layer sweep.

Selected sites are not a random sample of layer types. Equal raw alpha is not
an equal physical dose, and these fixed-state results are not controlled SLT.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean

from forschung.steering_v17.benchmark import digest


def summarize(metrics, layer_types):
    if metrics.get("selection_status") != "provisional_paired" or metrics.get("excluded"):
        raise ValueError("A complete paired sweep is required")
    rows = metrics.get("ranking", [])
    if not rows or any(len(row["layers"]) != 1 for row in rows):
        raise ValueError("Only nonempty single-layer sweeps can compare architecture types")
    strengths = sorted({row["strength"] for row in rows})
    sites = sorted({row["layers"][0] for row in rows})
    keys = {(row["layers"][0], row["strength"]) for row in rows}
    if len(keys) != len(rows) or len(keys) != len(sites) * len(strengths):
        raise ValueError("Every selected site must have exactly the same tested strengths")
    if len({row["cases"] for row in rows}) != 1:
        raise ValueError("Unequal case coverage cannot be averaged")
    if any(not 0 <= site < len(layer_types) for site in sites):
        raise ValueError("Layer missing from pack architecture")
    kinds = {layer_types[site] for site in sites}
    if kinds != {"full_attention", "linear_attention"}:
        raise ValueError("Both known layer types are required")
    groups = []
    for strength in strengths:
        for kind in sorted(kinds):
            selected = [row for row in rows if row["strength"] == strength and layer_types[row["layers"][0]] == kind]
            groups.append({"layer_type": kind, "strength": strength,
                           "layers": sorted(row["layers"][0] for row in selected),
                           "cases_per_layer": selected[0]["cases"],
                           **{key: mean(row[key] for row in selected) for key in (
                               "emotion_change_vs_off", "content_preservation", "naturalness", "semantic_selection_score")}})
    return {"method": "equal_layer_weight_within_each_raw_strength", "groups": groups,
            "controlled_slt": None, "production_acceptance": False,
            "limitations": ["Previously selected sites, not a random architecture sample",
                            "Raw alpha does not match hidden-state RMS dose across layers",
                            "Repeated prompts and judge inputs are not independent human observations",
                            "Fixed-state emotion expression is not controlled state-to-language transfer"]}


def run(run_dir, pack_path, metrics_path, output):
    manifest = json.loads((run_dir / "manifest.json").read_text())
    metrics = json.loads(metrics_path.read_text())
    pack = json.loads(pack_path.read_text())
    if manifest.get("pack_hash") != digest(pack_path):
        raise ValueError("Vector pack differs from frozen sweep")
    if metrics.get("generations_sha256") != digest(run_dir / "generations.jsonl"):
        raise ValueError("Generations differ from paired ranking")
    result = summarize(metrics, pack["layer_types"])
    result["sources"] = {str(path): digest(path) for path in (
        run_dir / "manifest.json", run_dir / "generations.jsonl", metrics_path, pack_path, Path(__file__))}
    output.mkdir(parents=True, exist_ok=False)
    (output / "comparison.json").write_text(json.dumps(result, indent=2) + "\n")
    (output / "generator.py.txt").write_text(Path(__file__).read_text())
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.run, args.pack, args.metrics, args.output), indent=2))
