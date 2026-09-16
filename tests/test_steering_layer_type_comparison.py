"""Architecture summaries preserve dose and complete selected-layer coverage."""
import sys
from copy import deepcopy
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from forschung.steering_v17.compare_layer_types import summarize


def main():
    metrics = {"selection_status": "provisional_paired", "excluded": [], "ranking": []}
    for site in range(3):
        for strength in (.1, .2):
            metrics["ranking"].append({"layers": [site], "strength": strength, "cases": 8,
                "emotion_change_vs_off": site / 10, "content_preservation": .9,
                "naturalness": .8, "semantic_selection_score": site / 10})
    types = ["linear_attention", "linear_attention", "full_attention"]
    result = summarize(metrics, types)
    assert len(result["groups"]) == 4
    linear = next(row for row in result["groups"] if row["layer_type"] == "linear_attention")
    assert linear["layers"] == [0, 1] and linear["emotion_change_vs_off"] == .05
    assert result["controlled_slt"] is None and not result["production_acceptance"]
    invalid = []
    missing = deepcopy(metrics)
    missing["ranking"].pop()
    invalid.append(missing)
    duplicate = deepcopy(metrics)
    duplicate["ranking"].append(duplicate["ranking"][0])
    invalid.append(duplicate)
    partial = deepcopy(metrics)
    partial["excluded"] = [{}]
    invalid.append(partial)
    mixed = deepcopy(metrics)
    mixed["ranking"][0]["layers"] = [0, 1]
    invalid.append(mixed)
    coverage = deepcopy(metrics)
    coverage["ranking"][0]["cases"] = 7
    invalid.append(coverage)
    for value in invalid:
        try:
            summarize(value, types)
        except ValueError:
            pass
        else:
            raise AssertionError("Incomplete or mixed comparison accepted")
    print("Layer-type comparison: matched doses, equal weights and missing-evidence guards passed")


if __name__ == "__main__":
    main()
