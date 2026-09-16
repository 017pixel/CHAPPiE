"""Optional blind local/Groq semantic ratings, separately stored from diagnostics."""

from __future__ import annotations
import hashlib
import argparse
import json
from pathlib import Path

import httpx

from config.prompts import STEERING_V17_JUDGE_PROMPT
from forschung.steering_v17.evaluate import response_text

RATING_KEYS = (
    "happiness",
    "trust",
    "energy",
    "curiosity",
    "motivation",
    "frustration",
    "sadness",
    "affection",
    "anxiety",
    "calm",
    "directness",
    "hostility",
    "sarcasm",
    "insult",
    "boundary_setting",
    "content_preservation",
    "naturalness",
)


def valid_rating(item):
    rating = item.get("rating", {})
    return "error" not in item and all(type(rating.get(key)) is int and 0 <= rating[key] <= 4 for key in RATING_KEYS)


def read_judge_context(endpoint, model):
    response = httpx.get(endpoint.rstrip("/") + "/health", timeout=30)
    response.raise_for_status()
    provenance = response.json().get("runtime_provenance", {})
    if provenance.get("model") != model or not provenance.get("model_revision"):
        raise ValueError("Blind judge requires pinned loaded-model provenance")
    return {"schema_version": 2, "runtime_provenance": provenance,
            "rubric": STEERING_V17_JUDGE_PROMPT, "model": model,
            "temperature": 0, "seed": 1042, "max_tokens": 512,
            "enable_thinking": False, "steering_mode": "off"}


def context_hash(context):
    return hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()


def input_hash(prompt, answer, context_id):
    return hashlib.sha256(json.dumps([prompt, answer, context_id]).encode()).hexdigest()


def rate(client, prompt: str, answer: str, *, endpoint: str, model: str, max_tokens: int = 512, expected_provenance=None) -> dict:
    request = {
        "model": model,
        "messages": [
            {"role": "system", "content": STEERING_V17_JUDGE_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {"prompt": prompt, "answer": answer}, ensure_ascii=False
                ),
            },
        ],
        "temperature": 0,
        "seed": 1042,
        "max_tokens": max_tokens,
        "chat_template_kwargs": {"enable_thinking": False},
        "steering": {"enabled": False, "mode": "off", "vectors": [], "sequences": []},
    }
    response = client.post(endpoint.rstrip("/") + "/v1/chat/completions", json=request)
    response.raise_for_status()
    payload = response.json()
    result = {"request": request, "response": payload, "method": "blind_automated_local",
              "independent_human_rating": False}
    if expected_provenance is not None and payload.get("runtime_provenance") != expected_provenance:
        result.update(error="Judge inference provenance changed", fatal_provenance_error=True)
        return result
    try:
        text = payload["choices"][0]["message"]["content"]
        first, last = text.find("{"), text.rfind("}")
        if first < 0 or last < first:
            raise ValueError("Judge did not return JSON")
        rating = json.loads(text[first:last+1])
        if any(type(rating.get(key)) is not int or not 0 <= rating[key] <= 4 for key in RATING_KEYS):
            raise ValueError("Judge returned invalid or missing rating dimensions")
        result["rating"] = {key: rating[key] for key in RATING_KEYS}
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        result["error"] = str(exc)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8000")
    parser.add_argument("--model", default="Qwen/Qwen3.5-4B")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--reference-ratings", type=Path)
    parser.add_argument("--rating-file", default="blind_ratings_v2.jsonl")
    args = parser.parse_args()
    if Path(args.rating_file).name != args.rating_file:
        raise ValueError("Rating filename must be a basename")
    context = read_judge_context(args.endpoint, args.model)
    context_id = context_hash(context)
    manifest_path = args.run / (Path(args.rating_file).stem + "_manifest.json")
    if manifest_path.exists() and json.loads(manifest_path.read_text()) != context:
        raise ValueError("Judge recipe changed; use a new rating filename")
    path = args.run / args.rating_file
    if path.exists() and not manifest_path.exists():
        raise ValueError("Existing ratings have no recipe manifest; use a new rating filename")
    manifest_path.write_text(json.dumps(context, indent=2) + "\n")
    rows = [
        json.loads(line)
        for line in (args.run / "generations.jsonl").read_text().splitlines()
    ]
    prior = (
        [json.loads(line) for line in path.read_text().splitlines()]
        if path.exists()
        else []
    )
    if any(row.get("fatal_provenance_error") for row in prior):
        raise ValueError("Prior judge provenance failure requires a new rating filename")
    done = {(row["response_id"], row.get("input_hash")) for row in prior
            if valid_rating(row) and row.get("context_hash") == context_id}
    cache = {item["input_hash"]: item for item in prior if item.get("context_hash") == context_id and "input_hash" in item
             and (valid_rating(item) or ("error" in item and "response" in item))}
    if args.reference_ratings:
        reference_hash = hashlib.sha256(args.reference_ratings.read_bytes()).hexdigest()
        for item in map(json.loads, args.reference_ratings.read_text().splitlines()):
            if valid_rating(item) and item.get("context_hash") == context_id and "input_hash" in item:
                cache.setdefault(item["input_hash"], {**item, "reference_sha256": reference_hash})
    count = 0
    with httpx.Client(timeout=120) as client, path.open("a") as log:
        for row in rows:
            if "error" in row:
                continue
            response_id = row["response"].get("id")
            key = input_hash(row["prompt"], response_text(row), context_id)
            if not response_id or (response_id, key) in done:
                continue
            rated = {"response_id": response_id, "input_hash": key, "context_hash": context_id}
            if key in cache:
                source = cache[key]
                rated.update({**{key: source[key] for key in ("rating", "error") if key in source}, "method": "blind_automated_local_cached",
                              "independent_human_rating": False, "cached_from_response_id": source["response_id"]})
                if source.get("reference_sha256"):
                    rated["reference_ratings_sha256"] = source["reference_sha256"]
                    rated["reference_ratings_path"] = str(args.reference_ratings)
                log.write(json.dumps(rated, ensure_ascii=False) + "\n")
                log.flush()
                done.add((response_id, key))
                continue
            try:
                rated.update(
                    rate(
                        client,
                        row["prompt"],
                        response_text(row),
                        endpoint=args.endpoint,
                        model=args.model,
                        expected_provenance=context["runtime_provenance"],
                    )
                )
            except (httpx.HTTPError, ValueError, KeyError) as exc:
                rated["error"] = str(exc)
            log.write(json.dumps(rated, ensure_ascii=False) + "\n")
            log.flush()
            if rated.get("fatal_provenance_error"):
                raise RuntimeError(rated["error"])
            if valid_rating(rated) or ("error" in rated and "response" in rated):
                cache[key] = rated
            if "rating" in rated:
                done.add((response_id, key))
            count += 1
            print(response_id, "error" if "error" in rated else "rated", flush=True)
            if args.limit and count >= args.limit:
                break


if __name__ == "__main__":
    main()
