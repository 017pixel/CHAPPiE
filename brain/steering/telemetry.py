"""Inference provenance and observed termination, independent of emotion scores."""
import hashlib
from pathlib import Path


def runtime_source_fingerprint():
    root = Path(__file__).resolve().parents[2]
    paths = [root / "brain/steering_backend.py", root / "brain/steering_api_server.py",
             root / "config/config.py", root / "config/prompts.py", root / "config/emotions.py"]
    paths += sorted((root / "brain/steering").glob("*.py"))
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path.relative_to(root)).encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def generation_end_metadata(token_ids, limit, eos_token_ids, preempted=False):
    eos = eos_token_ids if isinstance(eos_token_ids, (list, tuple, set)) else [eos_token_ids]
    ids = [int(token) for token in token_ids]
    natural_eos = bool(ids and ids[-1] in eos)
    return {"finish_reason": "stop" if natural_eos or len(ids) < limit else "length",
            "natural_eos": natural_eos, "completion_tokens": len(ids),
            "effective_max_tokens": limit, "background_preempted": bool(preempted)}


def cached_model_revision(model_name):
    """Read the content-addressed cached snapshot before loading any model files."""
    if Path(model_name).is_dir():
        # Local directories are mutable and do not have a Hub commit identity.
        return None
    from huggingface_hub import try_to_load_from_cache
    path = try_to_load_from_cache(model_name, "config.json")
    if isinstance(path, str):
        snapshot = Path(path).parent
        if snapshot.parent.name == "snapshots":
            return snapshot.name
    return None


def model_artifact_hash(directory):
    """Hash local weights and configuration without loading them into memory."""
    root = Path(directory).resolve()
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix in {".json", ".safetensors", ".bin", ".model"}:
            digest.update(str(path.relative_to(root)).encode() + b"\0")
            with path.open("rb") as source:
                while chunk := source.read(1024 * 1024):
                    digest.update(chunk)
            digest.update(b"\0")
    return digest.hexdigest()


def loaded_quantization(model):
    """Report the loaded model's state, independently of the requested setting."""
    if getattr(model, "is_loaded_in_4bit", False):
        return "4bit"
    if getattr(model, "is_loaded_in_8bit", False):
        return "8bit"
    return "other" if getattr(model, "is_quantized", False) else "none"
