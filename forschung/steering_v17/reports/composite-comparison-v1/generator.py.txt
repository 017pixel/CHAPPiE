"""Paired descriptive affect/quality deltas for frozen direct/composed experiments."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
from statistics import mean

from brain.steering.vector_pack import LayerVectorPack
from forschung.steering_v17.compose_vectors import digest
from forschung.steering_v17.evaluate import response_text
from forschung.steering_v17.judge import RATING_KEYS, context_hash, input_hash, valid_rating


def read_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def validated_rows(run, protocol, arm=None, concept=None):
    manifest = json.loads((run / "manifest.json").read_text())
    provenance = json.loads((run / "server_provenance.json").read_text())
    if provenance != protocol["reference_server_provenance"]:
        raise ValueError("Composite inference provenance mismatch")
    if manifest["dataset_hash"] != protocol["dataset_sha256"]:
        raise ValueError("Composite dataset mismatch")
    if arm is not None and manifest["pack_hash"] != protocol["pack_sha256"][arm]:
        raise ValueError("Composite pack mismatch")
    recipe = json.loads((run / "blind_ratings_v2_manifest.json").read_text())
    recipe_hash = context_hash(recipe)
    ratings = {}
    for rating in read_rows(run / "blind_ratings_v2.jsonl"):
        response_id = rating["response_id"]
        # Repeated exact annotations are safe; conflicting annotations are not.
        if response_id in ratings and ratings[response_id] != rating:
            raise ValueError("Conflicting composite annotations")
        ratings[response_id] = rating
    observations = {}
    for row in read_rows(run / "generations.jsonl"):
        if "error" in row:
            raise ValueError("Failed composite generation")
        key = (row["case_id"], row["seed"])
        if key in observations:
            raise ValueError("Duplicate composite generation")
        request = row["request"]
        for parameter in ("seed", "max_tokens", "temperature"):
            expected = row["seed"] if parameter == "seed" else protocol[parameter]
            if request.get(parameter) != expected:
                raise ValueError("Composite request recipe mismatch")
        if request.get("messages") != [{"role": "user", "content": row["prompt"]}] or request.get("chat_template_kwargs") != {"enable_thinking": False}:
            raise ValueError("Composite prompt/template mismatch")
        steering = request.get("steering", {})
        if arm is None:
            if row.get("mode") != "off" or steering.get("enabled") or steering.get("vectors") or steering.get("sequences") or steering.get("mode", "off") != "off":
                raise ValueError("Control must disable steering")
        else:
            expected = protocol["ranking"][0]
            if row.get("emotion") != concept or row.get("layers") != expected["layers"] or row.get("strength") != expected["strength"]:
                raise ValueError("Composite configuration mismatch")
            vectors = steering.get("vectors", [])
            if steering.get("mode") != "activation" or not steering.get("enabled") or len(vectors) != 1 or steering.get("sequences"):
                raise ValueError("Composite intervention mismatch")
            vector = vectors[0]
            if (vector.get("name") != concept or vector.get("strength") != expected["strength"]
                    or vector.get("direction") != "positive"
                    or vector.get("vector", {}).get("pack_hash") != protocol["pack_sha256"][arm]
                    or vector.get("vector", {}).get("pooling") != protocol["pooling"]
                    or set(vector.get("vector", {}).get("layers", {})) != {str(layer) for layer in expected["layers"]}):
                raise ValueError("Composite vector binding mismatch")
        annotation = ratings.get(row["response"]["id"], {})
        if (not valid_rating(annotation) or annotation.get("context_hash") != recipe_hash
                or annotation.get("input_hash") != input_hash(row["prompt"], response_text(row), recipe_hash)):
            raise ValueError("Composite rating/input binding mismatch")
        observations[key] = (row, annotation["rating"])
    if len(observations) != protocol["expected_per_arm_concept"]:
        raise ValueError("Incomplete composite matrix")
    return observations, recipe_hash


def compare(protocol_path, runs, output):
    protocol = json.loads(protocol_path.read_text())
    dataset = Path(protocol["dataset"])
    if digest(dataset) != protocol["dataset_sha256"]:
        raise ValueError("Frozen composite dataset changed")
    planned = {(case["id"], seed): case["prompt"] for case in read_rows(dataset)[:8] for seed in protocol["seeds"]}
    control_run = Path(protocol["control_run"])
    if digest(control_run / "generations.jsonl") != protocol["control_generations_sha256"]:
        raise ValueError("Frozen composite controls changed")
    controls, control_recipe = validated_rows(control_run, protocol)
    results, sources = {}, {}
    def bind_plan(rows):
        if set(rows) != set(planned) or any(row["prompt"] != planned[key] for key, (row, _) in rows.items()):
            raise ValueError("Composite rows differ from planned prompt/seed matrix")
    bind_plan(controls)
    for concept in protocol["concepts"]:
        arms = {}
        for arm in ("direct", "composed"):
            run = runs / f"{concept}-{arm}"
            source_pack = Path(protocol["packs"][arm])
            if digest(source_pack) != protocol["pack_sha256"][arm]:
                raise ValueError("Frozen composite pack changed")
            model = protocol["reference_server_provenance"]["model"]
            pack = LayerVectorPack(source_pack, model, require_calibrated=False)
            expected_spec = pack.vector_spec(concept, protocol["ranking"][0]["layers"], protocol["pooling"])
            rows, recipe = validated_rows(run, protocol, arm, concept)
            if any(row["request"]["steering"]["vectors"][0]["vector"] != expected_spec for row, _ in rows.values()):
                raise ValueError("Composite request vectors differ from frozen pack")
            if recipe != control_recipe:
                raise ValueError("Composite judge recipes differ")
            bind_plan(rows)
            arms[arm] = rows
            sources[f"{concept}-{arm}"] = {name: digest(run / name) for name in ("manifest.json", "generations.jsonl", "blind_ratings_v2.jsonl", "blind_ratings_v2_manifest.json", "server_provenance.json")}
        result = {}
        for arm, rows in arms.items():
            result[arm] = {
                "cases": len(rows),
                "mean_rating_0_to_1": {axis: mean(rating[axis] / 4 for _, rating in rows.values()) for axis in RATING_KEYS},
                "mean_change_vs_off": {axis: mean((rating[axis] - controls[key][1][axis]) / 4 for key, (_, rating) in rows.items()) for axis in RATING_KEYS},
                "length_limited": sum(row["response"]["choices"][0].get("finish_reason") == "length" for row, _ in rows.values()),
            }
        result["composed_minus_direct"] = {axis: mean((arms["composed"][key][1][axis] - arms["direct"][key][1][axis]) / 4 for key in planned) for axis in RATING_KEYS}
        results[concept] = result
    output.mkdir(parents=True, exist_ok=False)
    report = {"protocol_sha256": digest(protocol_path), "production_acceptance": False,
              "composite_score": None, "limitations": protocol["limitations"], "concepts": results,
              "source_hashes": sources,
              "control_hashes": {name: digest(control_run / name) for name in ("generations.jsonl", "blind_ratings_v2.jsonl", "blind_ratings_v2_manifest.json", "server_provenance.json")}}
    (output / "comparison.json").write_text(json.dumps(report, indent=2) + "\n")
    shutil.copyfile(protocol_path, output / "protocol.json")
    shutil.copyfile(Path(__file__), output / "generator.py.txt")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = compare(args.protocol, args.runs, args.output)
    print(f"Compared {len(result['concepts'])} composites; no production acceptance")
