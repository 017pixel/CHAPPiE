"""Serial, resumable generation capture. No app memory or state is touched.

Inputs are JSONL cases with id, prompt and optional state/steering payload.
Explicit payloads permit replaying frozen baseline interventions after changes.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import subprocess
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[2]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_files():
    """Include new untracked source modules, excluding data and secrets."""
    paths = (
        subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=ROOT,
        )
        .decode()
        .split("\0")
    )
    prefixes = (
        "brain/",
        "config/",
        "memory/",
        "life/",
        "web_infrastructure/", "api/", "cli/",
        "forschung/steering_v17/",
    )
    for name in sorted(set(paths)):
        path = ROOT / name
        if name.endswith(".py") and (name.startswith(prefixes) or name == "chappie_brain_cli.py") and path.is_file():
            yield name, path.read_bytes()


def source_fingerprint() -> str:
    result = hashlib.sha256()
    for name, content in source_files():
        result.update(name.encode() + b"\0" + content + b"\0")
    return result.hexdigest()


def freeze_source(output, manifest):
    """Keep the exact dirty source used by a new run, without a Git commit."""
    path = output / "source.zip"
    if path.exists():
        try:
            snapshot = json.loads((output / "source_snapshot.json").read_text())
            fingerprint = hashlib.sha256()
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                if len(names) != len(set(names)):
                    raise ValueError("Duplicate source snapshot entries")
                for name in sorted(names):
                    fingerprint.update(name.encode() + b"\0" + archive.read(name) + b"\0")
            if (snapshot["sha256"] != digest(path)
                    or snapshot["file_count"] != len(names)
                    or snapshot["source_tree_sha256"] != fingerprint.hexdigest()
                    or manifest["source_tree_sha256"] != fingerprint.hexdigest()):
                raise ValueError("Source snapshot hash does not match the run")
        except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
            raise ProvenanceMismatch(f"Invalid existing source snapshot: {exc}") from exc
        return
    files = list(source_files())
    fingerprint = hashlib.sha256()
    for name, content in files:
        fingerprint.update(name.encode() + b"\0" + content + b"\0")
    if fingerprint.hexdigest() != manifest["source_tree_sha256"]:
        raise ProvenanceMismatch("Source changed before the run snapshot was frozen")
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files:
            archive.writestr(name, content)
    (output / "source_snapshot.json").write_text(json.dumps({"sha256": digest(path),
        "source_tree_sha256": fingerprint.hexdigest(), "file_count": len(files),
        "scope": "Python inference/runtime/configuration/research sources; excludes ignored secrets and data"}, indent=2) + "\n")


def create_manifest(
    dataset: Path,
    *,
    model: str,
    modes: list[str],
    seeds: list[int],
    temperature: float,
    max_tokens: int,
) -> dict[str, Any]:
    versions = {}
    for package in ("torch", "transformers", "httpx", "numpy"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return {
        "schema_version": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "repo_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "source_diff_sha256": hashlib.sha256(
            subprocess.check_output(["git", "diff", "HEAD"], cwd=ROOT)
        ).hexdigest(),
        "source_tree_sha256": source_fingerprint(),
        "model": model,
        "dataset_hash": digest(dataset),
        "dataset_path": str(dataset.resolve()),
        "versions": versions,
        "modes": modes,
        "seeds": seeds,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "isolation": {"memory": False, "history": False, "sleep": False, "life": False},
        "model_revision": None,
        "vector_pack": None,
    }


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    ids = [str(case["id"]) for case in cases]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate case ids")
    if not cases or any(
        not isinstance(c.get("prompt"), str) or not c["prompt"].strip() for c in cases
    ):
        raise ValueError("Dataset requires nonempty prompts")
    return cases


class ProvenanceMismatch(RuntimeError):
    """An experiment must stop if its loaded inference implementation changes."""


def record_server_provenance(output: Path, response: dict):
    provenance = response.get("runtime_provenance")
    path = output / "server_provenance.json"
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    if not provenance:
        if manifest.get("model_revision"):
            raise ProvenanceMismatch("Pinned experiment requires inference server provenance")
        if path.exists():
            raise ProvenanceMismatch("Inference server stopped reporting its recorded provenance")
        return  # Older checkpoints explicitly lack loaded-server provenance.
    if manifest:
        for key in ("model", "model_revision"):
            if manifest.get(key) and provenance.get(key) != manifest[key]:
                raise ProvenanceMismatch(f"Inference server does not match manifest: {key}")
    if path.exists() and json.loads(path.read_text()) != provenance:
        raise ProvenanceMismatch("Loaded inference server changed during the run")
    if not path.exists():
        path.write_text(json.dumps(provenance, indent=2) + "\n")


def run(
    dataset: Path,
    output: Path,
    *,
    endpoint: str,
    model: str,
    modes: list[str],
    seeds: list[int],
    temperature: float = 0.7,
    max_tokens: int = 128,
    vector_pack: Path | None = None,
    profiles: Path | None = None,
) -> dict[str, Any]:
    from brain.steering_manager import SteeringManager
    from config.config import LLMProvider
    from config.emotions import EMOTION_DEFAULTS

    cases = load_cases(dataset)
    manifest = create_manifest(
        dataset,
        model=model,
        modes=modes,
        seeds=seeds,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    controller = None
    if vector_pack is not None:
        from brain.steering.vector_pack import LayerVectorPack
        from brain.steering.activation_controller import ActivationController
        pack = LayerVectorPack(vector_pack, model, require_calibrated=False)
        if profiles is not None:
            pack.metadata["calibration"] = {"profiles": json.loads(profiles.read_text())["profiles"]}
        controller = ActivationController(pack, research=True)
        manifest["vector_pack"] = {"path": str(vector_pack), "sha256": digest(vector_pack), "status": pack.metadata["status"],
                                   "profiles_sha256": digest(profiles) if profiles else None, "profile_policy": "research"}
        manifest["model_revision"] = pack.metadata["model_revision"]
    output.mkdir(parents=True, exist_ok=True)
    freeze_source(output, manifest)
    manifest_path = output / "manifest.json"
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text())
        for key in (
            "dataset_hash",
            "model",
            "modes",
            "seeds",
            "temperature",
            "max_tokens",
            "source_tree_sha256", "vector_pack",
        ):
            if old.get(key) != manifest.get(key):
                raise ValueError(f"Resume configuration changed: {key}")
    else:
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    generations = output / "generations.jsonl"
    rows = (
        [json.loads(line) for line in generations.read_text().splitlines()]
        if generations.exists()
        else []
    )
    completed = {
        (str(r["case_id"]), r["mode"], r["seed"]) for r in rows if "error" not in r
    }
    manager = SteeringManager()
    with httpx.Client(timeout=120) as client, generations.open("a") as log:
        for case in cases:
            for mode in modes:
                for seed in seeds:
                    key = (str(case["id"]), mode, seed)
                    if key in completed:
                        continue
                    state = {**EMOTION_DEFAULTS, **case.get("state", {})}
                    if mode == "off":
                        steering = {"steering": {"enabled": False, "vectors": []}}
                    elif mode == "replay":
                        steering = case["steering_payload"]
                    elif controller is not None:
                        changes = case.get("recent_changes", {})
                        intensities = manager.compute_emotion_intensity(state, model=model, recent_changes=changes)
                        composites = manager._build_composite_modes(state, intensities, model=model, recent_changes=changes)
                        steering = controller.payload(state, changes, composites, mode)
                    else:
                        steering = manager.get_steering_payload(
                            state,
                            force=True,
                            provider=LLMProvider.VLLM,
                            model=model,
                            user_input=case["prompt"],
                            steering_mode=mode,
                        )
                    request = {
                        "model": model,
                        "messages": [{"role": "user", "content": case["prompt"]}],
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "seed": seed,
                        "chat_template_kwargs": {"enable_thinking": False},
                        **steering,
                    }
                    row = {
                        "case_id": case["id"],
                        "category": case.get("category"),
                        "mode": mode,
                        "seed": seed,
                        "state": state,
                        "prompt": case["prompt"],
                        "expected_answer": case.get("expected_answer", case.get("expected")),
                        "control_axis": case.get("control_axis"),
                        "control_level": case.get("control_level"),
                        "control_group": case.get("control_group"),
                        "request": request,
                    }
                    started = time.perf_counter()
                    provenance_error = None
                    try:
                        response = client.post(
                            endpoint.rstrip("/") + "/v1/chat/completions", json=request
                        )
                        response.raise_for_status()
                        row["response"] = response.json()
                        record_server_provenance(output, row["response"])
                    except ProvenanceMismatch as exc:
                        row["error"] = str(exc)
                        provenance_error = exc
                    except (httpx.HTTPError, ValueError) as exc:
                        row["error"] = str(exc)
                    row["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 3)
                    log.write(json.dumps(row, ensure_ascii=False) + "\n")
                    log.flush()
                    rows.append(row)
                    if provenance_error is not None:
                        raise provenance_error
                    print(
                        f"{case['id']} {mode} {seed}: {'ERROR' if 'error' in row else 'ok'}",
                        flush=True,
                    )
    latest = {(str(row["case_id"]), row["mode"], row["seed"]): row for row in rows}
    summary = {
        "expected": len(cases) * len(modes) * len(seeds),
        "recorded": sum("error" not in row for row in latest.values()),
        "errors": sum("error" in row for row in latest.values()),
        "attempts": len(rows),
        "historical_errors": sum("error" in row for row in rows),
    }
    (output / "completion.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--vector-pack", type=Path)
    parser.add_argument("--profiles", type=Path)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8000")
    parser.add_argument("--model", default="Qwen/Qwen3.5-4B")
    parser.add_argument(
        "--modes",
        nargs="+",
        choices=["off", "replay", "activation", "sequence", "combined"],
        default=["off", "activation", "sequence", "combined"],
    )
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44, 45, 46])
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--max-tokens", type=int, default=128)
    args = parser.parse_args()
    result = run(
        args.dataset,
        args.output,
        endpoint=args.endpoint,
        model=args.model,
        modes=args.modes,
        seeds=args.seeds,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        vector_pack=args.vector_pack,
        profiles=args.profiles,
    )
    print(json.dumps(result))
    if result["errors"] or result["expected"] != result["recorded"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
