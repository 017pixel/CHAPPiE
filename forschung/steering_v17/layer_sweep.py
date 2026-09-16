"""Single-layer, strength and layer-combination experiments using measured vectors.

Writes all raw requests/responses. Ranking diagnostics are explicitly lexical;
production promotion requires held-out semantic evaluation and quality gates.
"""

from __future__ import annotations
import argparse
import itertools
import json
import time
from pathlib import Path

import httpx
import numpy as np

from brain.steering.vector_pack import LayerVectorPack
from config.config import get_steering_runtime_config
from forschung.steering_v17.benchmark import create_manifest, load_cases, digest, record_server_provenance, ProvenanceMismatch, freeze_source
from forschung.steering_v17.evaluate import response_text, lexical_diagnostics


def configurations(stage, pack, emotion, pooling, previous, top_configurations=3, strengths=None):
    cap = float(get_steering_runtime_config()["research_alpha_cap"])
    if strengths is not None and (not strengths or any(not np.isfinite(value) or not 0 < value <= cap for value in strengths)):
        raise ValueError(f"Research strengths must be finite in (0,{cap:g}]")
    strengths = list(dict.fromkeys(strengths)) if strengths is not None else None
    pool = pack.metadata["poolings"].index(pooling)
    valid = pack.metadata["emotions"][emotion]["valid_directions"][pool]
    if stage == "screen":
        return [([layer], 0.2) for layer in range(pack.layers) if valid[layer]]
    if previous is None:
        raise ValueError("Strength/combinations require a previous metrics file")
    ranking = json.loads(previous.read_text())["ranking"]
    if stage in ("pooling", "refine"):
        # Compare the same selected sites and doses, changing extraction only.
        selected = []
        for row in ranking:
            candidate = (list(row["layers"]), row["strength"])
            duplicate = any(prior[0] == candidate[0] for prior in selected) if stage == "refine" else candidate in selected
            if not duplicate:
                selected.append(candidate)
            if len(selected) == top_configurations:
                break
        if not selected:
            raise ValueError("Pooling comparison has no valid candidate configuration")
        if any(not valid[layer] for layers, _ in selected for layer in layers):
            raise ValueError("Fixed pooling candidates contain an invalid direction; comparison is incomplete")
        if stage == "refine":
            return [(layers, strength) for layers, _ in selected
                    for strength in (strengths or [.40, .55, .70])]
        return selected
    top = [row["layers"][0] for row in ranking if len(row["layers"]) == 1]
    top = list(dict.fromkeys(top))[:8]
    if stage == "strength":
        return [
            ([layer], strength)
            for layer, strength in itertools.product(
                top, strengths or [0.05, 0.10, 0.15, 0.20, 0.30, 0.40]
            )
        ]
    if not top:
        raise ValueError("Previous sweep contains no valid layers")
    strength = ranking[0]["strength"]
    # Use actual architecture types, never a proportionally remapped guess.
    layer_types = pack.metadata.get("layer_types", [])
    full = [
        layer
        for layer in top
        if layer < len(layer_types) and layer_types[layer] == "full_attention"
    ]
    linear = [
        layer
        for layer in top
        if layer < len(layer_types) and layer_types[layer] == "linear_attention"
    ]
    windows = [list(range(max(0, top[0] - 1), min(pack.layers, top[0] + 2)))]
    mixed = [linear[0], full[0]] if linear and full else []
    groups = [[top[0]], top[:2], top[:3], full[:3], linear[:3], mixed, *windows]
    return [
        (list(group), strength)
        for group in sorted(
            {tuple(g) for g in groups if g and all(valid[layer] for layer in g)}
        )
    ]


def run(args):
    pack = LayerVectorPack(args.pack, args.model, require_calibrated=False)
    cases = load_cases(args.dataset)[:8]
    configs = configurations(
        args.stage, pack, args.emotion, args.pooling, args.previous, getattr(args, "top_configurations", 3), getattr(args, "strengths", None)
    )
    configs = [[layers, strength] for layers, strength in configs]
    seeds = list(dict.fromkeys(getattr(args, "seeds", [42])))
    if not seeds:
        raise ValueError("Sweep requires at least one seed")
    manifest = create_manifest(
        args.dataset,
        model=args.model,
        modes=["activation"],
        seeds=seeds,
        temperature=0.7,
        max_tokens=args.max_tokens,
    )
    manifest.update(
        {
            "stage": args.stage,
            "emotion": args.emotion,
            "pooling": args.pooling,
            "pack_hash": pack.vector_spec(args.emotion, configs[0][0], args.pooling)[
                "pack_hash"
            ],
            "configurations": configs,
            "previous_metrics_sha256": digest(args.previous) if args.previous else None,
            "model_revision": pack.metadata["model_revision"],
        }
    )
    args.output.mkdir(parents=True, exist_ok=True)
    freeze_source(args.output, manifest)
    path = args.output / "manifest.json"
    if path.exists():
        old = json.loads(path.read_text())
        for key in (
            "source_tree_sha256",
            "dataset_hash",
            "stage",
            "emotion",
            "pooling",
            "pack_hash",
            "max_tokens",
            "previous_metrics_sha256",
            "configurations",
            "model_revision",
            "seeds",
        ):
            if old[key] != manifest[key]:
                raise ValueError(f"Sweep resume mismatch: {key}")
    else:
        path.write_text(json.dumps(manifest, indent=2) + "\n")
    generations = args.output / "generations.jsonl"
    rows = (
        [json.loads(line) for line in generations.read_text().splitlines()]
        if generations.exists()
        else []
    )
    completed = {
        (tuple(row["layers"]), row["strength"], row["case_id"], row.get("seed", row.get("request", {}).get("seed", 42)))
        for row in rows
        if "error" not in row
    }
    with httpx.Client(timeout=120) as client, generations.open("a") as log:
        for layers, strength in configs:
            for case in cases:
                for seed in seeds:
                    key = (tuple(layers), strength, case["id"], seed)
                    if key in completed:
                        continue
                    request = {
                        "model": args.model,
                        "messages": [{"role": "user", "content": case["prompt"]}],
                        "temperature": 0.7,
                        "seed": seed,
                        "max_tokens": args.max_tokens,
                        "chat_template_kwargs": {"enable_thinking": False},
                        **pack.payload(args.emotion, layers, strength, args.pooling),
                    }
                    row = {
                        "case_id": case["id"],
                        "seed": seed,
                        "prompt": case["prompt"],
                        "category": case.get("category"),
                        "emotion": args.emotion,
                        "layers": layers,
                        "strength": strength,
                        "request": request,
                    }
                    started = time.perf_counter()
                    provenance_error = None
                    try:
                        response = client.post(
                            args.endpoint.rstrip("/") + "/v1/chat/completions", json=request
                        )
                        response.raise_for_status()
                        row["response"] = response.json()
                        record_server_provenance(args.output, row["response"])
                    except ProvenanceMismatch as exc:
                        row["error"] = str(exc)
                        provenance_error = exc
                    except (httpx.HTTPError, ValueError) as exc:
                        row["error"] = str(exc)
                    row["elapsed_ms"] = (time.perf_counter() - started) * 1000
                    log.write(json.dumps(row, ensure_ascii=False) + "\n")
                    log.flush()
                    rows.append(row)
                    if provenance_error is not None:
                        raise provenance_error
                    print(
                        layers,
                        strength,
                        case["id"],
                        "error" if "error" in row else "ok",
                        flush=True,
                    )
    latest = {
        (tuple(row["layers"]), row["strength"], row["case_id"], row.get("seed", row.get("request", {}).get("seed", 42))): row for row in rows
    }
    groups = {}
    for row in latest.values():
        groups.setdefault((tuple(row["layers"]), row["strength"]), []).append(row)
    ranking = []
    for (layers, strength), group in groups.items():
        scores = []
        for row in group:
            if "error" in row:
                scores.append(-1)
                continue
            diagnostic = lexical_diagnostics(response_text(row))
            expression = diagnostic["lexical_emotions"].get(args.emotion, 0)
            scores.append(
                expression
                - diagnostic["trigram_repetition"]
                - float(not response_text(row).strip())
            )
        ranking.append(
            {
                "layers": list(layers),
                "strength": strength,
                "lexical_diagnostic_score": float(np.mean(scores)),
                "cases": len(group),
            }
        )
    ranking.sort(key=lambda row: row["lexical_diagnostic_score"], reverse=True)
    metrics = {
        "ranking_method": "lexical_diagnostic_only",
        "semantic_validation_required": True,
        "expected": len(configs) * len(cases) * len(seeds),
        "recorded": len(latest),
        "errors": sum("error" in row for row in latest.values()),
        "ranking": ranking,
    }
    (args.output / "layer_metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n"
    )
    if metrics["errors"] or metrics["recorded"] != metrics["expected"]:
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="Qwen/Qwen3.5-4B")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8000")
    parser.add_argument("--emotion", default="frustration")
    parser.add_argument("--pooling", default="last_four_tokens")
    parser.add_argument(
        "--stage", choices=["screen", "strength", "combinations", "pooling", "refine"], default="screen"
    )
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--max-tokens", type=int, default=96)
    parser.add_argument("--seeds", type=int, nargs="+", default=[42])
    parser.add_argument("--strengths", type=float, nargs="+")
    parser.add_argument("--top-configurations", type=int, choices=range(1, 9), default=3)
    run(parser.parse_args())
