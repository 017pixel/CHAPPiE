"""Capture layer-input representations with CPU reduction and no retained GPU states."""

from __future__ import annotations
import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import torch

from brain.steering_backend import LocalSteeringEngine
from forschung.steering_v17.benchmark import create_manifest

POOLINGS = ("last_prompt_token", "last_four_tokens", "target_segment")


def capture(engine, text: str, question: str, target_start: int) -> np.ndarray:
    prompt = engine.tokenizer.apply_chat_template(
        [{"role": "user", "content": question}, {"role": "assistant", "content": text}],
        tokenize=False,
        add_generation_prompt=False,
        continue_final_message=True,
        enable_thinking=False,
    )
    encoded = engine.tokenizer(prompt, return_tensors="pt", return_offsets_mapping=True)
    offsets = encoded.pop("offset_mapping")[0].tolist()
    text_start = prompt.rfind(text)
    if text_start < 0:
        raise ValueError("Assistant target missing from rendered template")
    first, last = text_start + target_start, text_start + len(text)
    content_positions = [
        i for i, (a, b) in enumerate(offsets) if b > text_start and a < last and b > a
    ]
    positions = [
        i for i, (a, b) in enumerate(offsets) if b > first and a < last and b > a
    ]
    if not positions:
        raise ValueError("Target segment has no tokens")
    values = {}
    handles = []

    def hook_for(layer):
        def hook(_module, inputs):
            hidden = inputs[0][0]
            # Pool on GPU, copy only three hidden-size vectors immediately.
            values[layer] = (
                torch.stack(
                    (
                        hidden[content_positions[-1]],
                        hidden[content_positions[-4:]].mean(0),
                        hidden[positions].mean(0),
                    )
                )
                .detach()
                .float()
                .cpu()
            )

        return hook

    try:
        for index, layer in enumerate(engine.layers):
            handles.append(layer.register_forward_pre_hook(hook_for(index)))
        tensors = {key: value.to(engine.device) for key, value in encoded.items()}
        with torch.inference_mode():
            output = engine.model(
                **tensors, use_cache=False, output_hidden_states=False, logits_to_keep=1
            )
        del output, tensors
    finally:
        for handle in handles:
            handle.remove()
    if len(values) != len(engine.layers):
        raise ValueError("Not all language layers were captured")
    result = torch.stack(
        [values[index] for index in range(len(engine.layers))], dim=1
    ).numpy()
    if not np.isfinite(result).all():
        raise ValueError("Nonfinite activations")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datasets", nargs="+", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="Qwen/Qwen3.5-4B")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    pairs = [
        json.loads(line)
        for path in args.datasets
        for line in path.read_text().splitlines()
        if line.strip()
    ]
    if args.limit:
        pairs = pairs[: args.limit]
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = create_manifest(
        args.datasets[0],
        model=args.model,
        modes=["capture"],
        seeds=[42],
        temperature=0,
        max_tokens=0,
    )
    manifest.update(
        {
            "dataset_hashes": {
                str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in args.datasets
            },
            "poolings": list(POOLINGS),
            "site": "decoder_layer_input",
            "quantized": True,
        }
    )
    manifest_path = args.output / "manifest.json"
    previous = None
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text())
        for key in (
            "dataset_hashes",
            "model",
            "site",
            "quantized",
            "poolings",
            "source_tree_sha256",
            "versions",
        ):
            if previous[key] != manifest[key]:
                raise ValueError(f"Capture resume mismatch: {key}")
    torch.manual_seed(42)
    engine = LocalSteeringEngine(args.model, quantize=True, context_length=1024)
    engine.model.eval()
    manifest["model_revision"] = engine.model_revision
    manifest["runtime_provenance"] = engine.runtime_provenance
    manifest["model_config"] = engine.model.config.to_dict()
    manifest["cuda"] = torch.version.cuda
    manifest["device"] = (
        torch.cuda.get_device_name() if engine.device.type == "cuda" else "cpu"
    )
    if previous is not None:
        for key in ("model_revision", "model_config", "cuda", "device"):
            if previous.get(key) != manifest[key]:
                engine.close()
                raise ValueError(f"Capture resume mismatch: {key}")
    else:
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    try:
        for index, pair in enumerate(pairs):
            path = args.output / (pair["id"] + ".npz")
            if path.exists():
                with np.load(path, allow_pickle=False) as existing:
                    if (
                        existing["pair_hash"].item()
                        != hashlib.sha256(
                            json.dumps(pair, sort_keys=True).encode()
                        ).hexdigest()
                    ):
                        raise ValueError("Existing pair capture does not match dataset")
                continue
            started = time.perf_counter()
            neutral = capture(
                engine, pair["neutral"], pair["question"], pair["target_start"]
            )
            positive = capture(
                engine, pair["positive"], pair["question"], pair["target_start"]
            )
            temporary = path.with_suffix(".tmp.npz")
            np.savez_compressed(
                temporary,
                neutral=neutral,
                positive=positive,
                pair_hash=hashlib.sha256(
                    json.dumps(pair, sort_keys=True).encode()
                ).hexdigest(),
                emotion=pair["emotion"],
                split=pair["split"],
            )
            temporary.replace(path)
            print(
                f"{index + 1}/{len(pairs)} {pair['id']} {time.perf_counter() - started:.2f}s",
                flush=True,
            )
    finally:
        engine.close()


if __name__ == "__main__":
    main()
