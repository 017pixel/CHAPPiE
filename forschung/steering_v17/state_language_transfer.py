"""Exploratory paired state-to-language components, never a production gate.

D and I are dependent observations; the optional equal-weight mean is descriptive.
Only frustration has a separate behavioral index in the current blind rubric.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean

from forschung.steering_v17.judge import valid_rating, input_hash, context_hash
from forschung.steering_v17.evaluate import response_text

LEVELS = ("low", "medium", "high")
BEHAVIOR_AXES = ("directness", "hostility", "sarcasm", "insult")


def measure(rows, ratings, cases, modes, seeds):
    if "off" not in modes:
        raise ValueError("Paired SLT requires planned OFF controls")
    latest = {(row.get("case_id"), row.get("mode"), row.get("seed")): row for row in rows}
    planned = {}
    for case in cases:
        if case.get("control_level") not in LEVELS or not case.get("control_axis"):
            raise ValueError("SLT requires a predefined controlled-state dataset")
        key = (case["control_group"], case["control_axis"])
        levels = planned.setdefault(key, {})
        if case["control_level"] in levels:
            raise ValueError("Duplicate planned control level")
        levels[case["control_level"]] = case
    for levels in planned.values():
        if set(levels) != set(LEVELS) or len({case["prompt"] for case in levels.values()}) != 1:
            raise ValueError("Planned triplets must contain three levels with an identical prompt")
        axis = levels["low"]["control_axis"]
        states = [levels[level]["state"][axis] for level in LEVELS]
        if not states[0] < states[1] < states[2]:
            raise ValueError("Planned state levels must strictly increase")
    details = []
    for mode in modes:
        if mode == "off":
            continue
        for seed in seeds:
            for (group, axis), levels in planned.items():
                observations, provenance, contexts, input_hashes = {}, [], [], []
                recipes, other_states = [], []
                issue = None
                for condition in ("off", mode):
                    observations[condition] = []
                    for level in LEVELS:
                        case = levels[level]
                        row = latest.get((case["id"], condition, seed), {})
                        entry = ratings.get(row.get("response", {}).get("id"), {})
                        if (not row or "error" in row or row.get("prompt") != case["prompt"]
                                or row.get("control_axis") != axis or row.get("control_group") != group
                                or row.get("control_level") != level
                                or row.get("state", {}).get(axis) != case["state"][axis]
                                or not valid_rating(entry) or not entry.get("context_hash")):
                            issue = "missing_or_mismatched_generation_or_rating"
                            continue
                        request = row.get("request", {})
                        steering = request.get("steering", {})
                        requested_mode = steering.get("mode", "off" if not steering.get("enabled") else None)
                        if (request.get("seed") != seed
                                or request.get("messages") != [{"role": "user", "content": case["prompt"]}]
                                or requested_mode != condition
                                or (condition == "off" and (steering.get("enabled") or steering.get("vectors") or steering.get("sequences")))
                                or entry.get("input_hash") != input_hash(case["prompt"], response_text(row), entry["context_hash"])):
                            issue = "request_or_rating_not_bound_to_planned_case"
                            continue
                        actual = row.get("response", {}).get("runtime_provenance")
                        if not actual:
                            issue = "missing_inference_provenance"
                            continue
                        request = row.get("request", {})
                        recipes.append({key: request.get(key) for key in ("seed", "temperature", "max_tokens", "chat_template_kwargs")})
                        other_states.append({key: value for key, value in row["state"].items() if key != axis})
                        provenance.append(actual)
                        contexts.append(entry["context_hash"])
                        input_hashes.append(entry.get("input_hash"))
                        observations[condition].append(entry["rating"])
                if not issue and (any(item != provenance[0] for item in provenance) or len(set(contexts)) != 1):
                    issue = "mixed_inference_or_judge_provenance"
                if not issue and (any(item != recipes[0] for item in recipes) or any(item != other_states[0] for item in other_states)):
                    issue = "mismatched_generation_recipe_or_other_emotions"
                detail = {"mode": mode, "seed": seed, "group": group, "axis": axis, "complete": not issue}
                if issue:
                    detail["unresolved_reason"] = issue
                    details.append(detail)
                    continue
                observed, off = observations[mode], observations["off"]
                values = [rating[axis] for rating in observed]
                off_values = [rating[axis] for rating in off]
                delta = (values[2] - values[0]) - (off_values[2] - off_values[0])
                monotonic = values[0] <= values[1] <= values[2] and values[0] < values[2]
                direction = float(delta > 0)
                intensity = min(1, max(0, delta / 4)) if monotonic else 0.0
                behavioral = None
                raw_behavior = None
                if axis == "frustration":
                    def index(rating):
                        return mean(rating[name] / 4 for name in BEHAVIOR_AXES)
                    raw_behavior = (index(observed[2]) - index(observed[0])) - (index(off[2]) - index(off[0]))
                    behavioral = min(1, max(0, raw_behavior))
                content = mean(rating["content_preservation"] / 4 for rating in observed)
                naturalness = mean(rating["naturalness"] / 4 for rating in observed)
                components = {"direction": direction, "intensity": intensity, "behavior": behavioral,
                              "content": content, "naturalness": naturalness}
                detail.update(components=components, observed_low_medium_high=values,
                              off_low_medium_high=off_values, signed_axis_delta_vs_off=delta / 4,
                              monotonic_with_nonzero_change=monotonic, signed_behavior_delta_vs_off=raw_behavior,
                              boundary_setting_low_medium_high=[r["boundary_setting"] / 4 for r in observed],
                              content_change_vs_off=content - mean(r["content_preservation"] / 4 for r in off),
                              naturalness_change_vs_off=naturalness - mean(r["naturalness"] / 4 for r in off),
                              judge_input_hashes=input_hashes,
                              descriptive_slt=mean(components.values()) if behavioral is not None else None)
                details.append(detail)
    groups = {}
    for mode in modes:
        if mode == "off":
            continue
        for axis in sorted({axis for _, axis in planned}):
            subset = [row for row in details if row["mode"] == mode and row["axis"] == axis]
            complete = [row for row in subset if row["complete"]]
            coverage = len(complete) / len(subset) if subset else 0
            components = {}
            for name in ("direction", "intensity", "behavior", "content", "naturalness"):
                values = [row["components"][name] for row in complete]
                components[name] = mean(values) if coverage == 1 and values and all(v is not None for v in values) else None
            groups[f"{mode}:{axis}"] = {"planned_triplets": len(subset), "complete_triplets": len(complete),
                "coverage": coverage, "components": components,
                "descriptive_slt": mean(components.values()) if all(v is not None for v in components.values()) else None,
                "unique_judge_inputs": len({key for row in complete for key in row["judge_input_hashes"] if key})}
    return {"method": "paired_controlled_slt_components_v1", "exploratory": True, "validated": False,
            "production_acceptance": False, "independent_human_rating": False,
            "behavior_weights_frustration": {axis: .25 for axis in BEHAVIOR_AXES},
            "formula": "D=positive paired LOW/HIGH change; I=positive paired change/4 only for monotonic nonflat triplets; B=paired LOW/HIGH change of equal-weight frustration behavior index; C,N=mean quality/4; descriptive SLT=mean(D,I,B,C,N)",
            "limitations": ["D and I are dependent; equal weights are a research choice", "High quality can mask absent transfer in the descriptive mean; inspect components", "Other emotion axes lack an independent behavior measure, so B and total remain null", "Missing triplets prevent aggregate scores; cached ratings are not independent replications"],
            "groups": groups, "triplets": details}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--rating-file", default="blind_ratings_v2.jsonl")
    args = parser.parse_args()
    if Path(args.rating_file).name != args.rating_file:
        raise ValueError("Rating filename must be a basename")
    manifest = json.loads((args.run / "manifest.json").read_text())
    dataset = Path(manifest["dataset_path"])
    if hashlib.sha256(dataset.read_bytes()).hexdigest() != manifest["dataset_hash"]:
        raise ValueError("SLT dataset differs from the planned experiment")
    generations = args.run / "generations.jsonl"
    rating_path = args.run / args.rating_file
    def read(path):
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    recipe = json.loads((args.run / (Path(args.rating_file).stem + "_manifest.json")).read_text())
    recipe_hash = context_hash(recipe)
    annotations = read(rating_path)
    if any(entry.get("context_hash") != recipe_hash for entry in annotations):
        raise ValueError("SLT ratings differ from their judge recipe manifest")
    ratings = {entry["response_id"]: entry for entry in annotations}
    result = measure(read(generations), ratings, read(dataset), manifest["modes"], manifest["seeds"])
    result["generations_sha256"] = hashlib.sha256(generations.read_bytes()).hexdigest()
    result["ratings_sha256"] = hashlib.sha256(rating_path.read_bytes()).hexdigest()
    result["dataset_sha256"] = manifest["dataset_hash"]
    result["judge_context_sha256"] = recipe_hash
    output = args.run / (Path(args.rating_file).stem + "_slt.json")
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["groups"], indent=2))


if __name__ == "__main__":
    main()
