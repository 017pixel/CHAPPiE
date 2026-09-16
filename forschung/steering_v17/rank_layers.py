"""Provisional sweep ranking, optionally paired against identical OFF controls."""
import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean

from forschung.steering_v17.judge import valid_rating


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def rank(run, emotion="frustration", rating_file="blind_ratings.jsonl", control_run=None):
    generation_path, rating_path = run / "generations.jsonl", run / rating_file
    rows = read_rows(generation_path)
    ratings = {row["response_id"]: row for row in read_rows(rating_path)}
    controls, control_ratings = {}, {}
    if control_run is not None:
        if json.loads((run / "server_provenance.json").read_text()) != json.loads((control_run / "server_provenance.json").read_text()):
            raise ValueError("OFF controls use different inference provenance")
        controls = {(row["case_id"], row["seed"]): row for row in read_rows(control_run / "generations.jsonl") if row.get("mode") == "off"}
        control_ratings = {row["response_id"]: row for row in read_rows(control_run / rating_file)}
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    seeds = manifest.get("seeds") or sorted({row.get("seed", row.get("request", {}).get("seed", 42)) for row in rows})
    expected_cases = 8 * len(seeds)
    groups = {}
    for row in rows:
        groups.setdefault((tuple(row["layers"]), row["strength"]), {})[(row["case_id"], row.get("seed", row.get("request", {}).get("seed", 42)))] = row
    ranking, excluded, bounds = [], [], []
    for (layers, strength), cases in groups.items():
        pairs, reference = [], []
        for row in cases.values():
            annotation = ratings.get(row.get("response", {}).get("id"), {})
            pairs.append((row, annotation))
            if control_run is not None:
                seed = row.get("seed", row.get("request", {}).get("seed"))
                control = controls.get((row["case_id"], seed), {})
                control_annotation = control_ratings.get(control.get("response", {}).get("id"), {})
                if ("error" in control or control.get("prompt") != row["prompt"]
                        or not valid_rating(control_annotation)):
                    raise ValueError(f"Missing valid paired OFF control: {row['case_id']} seed {seed}")
                for parameter in ("temperature", "max_tokens", "chat_template_kwargs"):
                    if control.get("request", {}).get(parameter) != row.get("request", {}).get(parameter):
                        raise ValueError(f"OFF controls use different generation parameter: {parameter}")
                if annotation and (not annotation.get("context_hash") or annotation.get("context_hash") != control_annotation.get("context_hash")):
                    raise ValueError("Steering and OFF ratings use different judge recipes")
                reference.append((row, control_annotation))
        if len(pairs) != expected_cases:
            excluded.append({"layers": list(layers), "strength": strength, "reason": "incomplete_generation_configuration"})
            continue

        def aggregates(observations, missing):
            values = [(row, entry["rating"] if valid_rating(entry) and "error" not in row else {emotion: missing * 4, "content_preservation": missing * 4, "naturalness": missing * 4}) for row, entry in observations]
            return (mean(value[emotion] / 4 for row, value in values if row["category"] != "neutral_control"),
                    mean(value["content_preservation"] / 4 for _, value in values),
                    mean(value["naturalness"] / 4 for _, value in values))

        off_effect, off_content, off_naturalness = aggregates(reference, 0) if reference else (0, 1, 1)

        def score(values):
            effect, content, naturalness = values
            return effect - off_effect - .25 * max(0, off_content - content) - .25 * max(0, off_naturalness - naturalness)

        low, high = aggregates(pairs, 0), aggregates(pairs, 1)
        bounds.append({"layers": list(layers), "strength": strength,
                       "score_min": score(low), "score_max": score(high)})
        if any("error" in row or not valid_rating(annotation) for row, annotation in pairs):
            excluded.append({"layers": list(layers), "strength": strength, "reason": "missing_or_invalid_blind_rating"})
            continue
        effect, content, naturalness = low
        ranking.append({"layers": list(layers), "strength": strength, "cases": expected_cases,
                        "semantic_selection_score": score(low), "emotion_expression": effect,
                        "emotion_change_vs_off": effect - off_effect if reference else None,
                        "content_preservation": content, "naturalness": naturalness})
    ranking.sort(key=lambda row: row["semantic_selection_score"], reverse=True)
    result = {"ranking_method": "paired_blind_emotion_change_with_quality_loss_penalty" if controls else "blind_local_emotion_minus_content_and_naturalness_penalty",
              "formula": "emotion - OFF emotion - .25*max(0, OFF content-content) - .25*max(0, OFF naturalness-naturalness)" if controls else "emotion - .25*(1-content) - .25*(1-naturalness)",
              "production_acceptance": False, "independent_human_rating": False,
              "selection_status": "provisional_paired" if controls else "provisional_unpaired",
              "seeds": seeds, "expected_cases_per_configuration": expected_cases,
              "missing_rating_bias_unresolved": bool(excluded),
              "emotion": emotion, "ranking": ranking, "excluded": excluded,
              "missing_rating_score_bounds": bounds,
              "generations_sha256": digest(generation_path), "ratings_sha256": digest(rating_path)}
    if controls:
        result["control_generations_sha256"] = digest(control_run / "generations.jsonl")
        result["control_ratings_sha256"] = digest(control_run / rating_file)
    output_name = "semantic_layer_metrics.json" if rating_file == "blind_ratings.jsonl" else Path(rating_file).stem + "_layer_metrics.json"
    if controls:
        output_name = "paired_" + output_name
    (run / output_name).write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--emotion', default='frustration')
    parser.add_argument('--rating-file', default='blind_ratings.jsonl')
    parser.add_argument('--control-run', type=Path)
    args = parser.parse_args()
    result = rank(args.run, args.emotion, args.rating_file, args.control_run)
    print(json.dumps({"top": result['ranking'][:8], "excluded": len(result['excluded'])}, indent=2))
    manifest = json.loads((args.run / "manifest.json").read_text())
    minimum = 8 if manifest.get("stage") == "screen" else 1
    if len(result['ranking']) < minimum:
        raise SystemExit(f'Fewer than {minimum} completely rated layer configurations')
