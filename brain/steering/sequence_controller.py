"""Translate selected emotion axes into small lexical suggestions."""

import math

from config.config import get_steering_runtime_config

# Candidate vocabulary is experimental. Its efficacy must be measured independently.
LEXICON = {
    "happiness": ["froh", "schön", "freue"],
    "trust": ["vertraue", "zuverlässig"],
    "energy": ["los", "bereit"],
    "curiosity": ["interessant", "warum"],
    "motivation": ["anpacken", "weiter"],
    "frustration": ["nervt", "genug", "ärgerlich"],
    "sadness": ["traurig", "schwer"],
    "affection": ["gern", "nah"],
    "anxiety": ["unsicher", "besorgt"],
    "calm": ["ruhig", "gelassen"],
}


def build_sequence_specs(vectors: list[dict]) -> list[dict]:
    config = get_steering_runtime_config()
    specs = []
    for vector in vectors:
        words = LEXICON.get(vector["name"], [])
        if not words or vector.get("direction") == "negative":
            continue
        # Measured profiles express the state independently of physical alpha.
        # Keep the historical raw-strength mapping only for legacy vectors.
        coefficient = (float(vector["coefficient"]) if "coefficient" in vector else
                       float(vector["strength"]) / config["sequence_reference_strength"])
        if not math.isfinite(coefficient):
            raise ValueError("Sequence coefficient must be finite")
        weight = min(1.0, max(0.0, coefficient))
        if weight == 0:
            continue
        specs.append(
            {
                "type": "soft_sequence_steering",
                "concept": vector["name"],
                "token_candidates": [
                    {"text": word, "weight": weight} for word in words
                ],
                "phrase_candidates": [],
                "start_token": 0,
                "end_token": config["sequence_window"],
                "max_logit_bias": config["sequence_max_bias"],
                "decay": config["sequence_decay"],
            }
        )
    return specs
