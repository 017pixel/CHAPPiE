"""Paired SLT does not mistake prompts, missing states or good grammar for transfer."""
from copy import deepcopy
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from forschung.steering_v17.judge import RATING_KEYS, input_hash
from forschung.steering_v17.state_language_transfer import measure, LEVELS, BEHAVIOR_AXES


def fixture(axis="frustration", values=(0, 2, 4), off_values=(0, 0, 0)):
    cases, rows, ratings = [], [], {}
    for level, state in zip(LEVELS, (10, 50, 85)):
        case = {"id": level, "prompt": "Wie reagierst du?", "state": {axis: state},
                "control_axis": axis, "control_group": "g", "control_level": level}
        cases.append(case)
        for mode, scores in (("off", off_values), ("activation", values)):
            response_id = f"{mode}:{level}"
            observed = scores[LEVELS.index(level)]
            answer = f"{axis}:{observed}"
            rows.append({**case, "state": dict(case["state"]), "case_id": level, "mode": mode, "seed": 42,
                         "request": {"seed": 42, "max_tokens": 96, "temperature": .7,
                                     "messages": [{"role": "user", "content": case["prompt"]}],
                                     "steering": {"mode": mode, "enabled": mode != "off"}},
                         "response": {"id": response_id, "choices": [{"message": {"content": answer}}],
                                      "runtime_provenance": {"model_revision": "r1"}}})
            observed = scores[LEVELS.index(level)]
            ratings[response_id] = {"context_hash": "recipe1", "input_hash": input_hash(case["prompt"], answer, "recipe1"),
                "rating": {**{key: 0 for key in RATING_KEYS}, axis: observed,
                           **{key: observed for key in BEHAVIOR_AXES}, "content_preservation": 4, "naturalness": 4}}
    return rows, ratings, cases


def evaluate(fixture_data, seeds=(42,)):
    return measure(*fixture_data, ["off", "activation"], seeds)


def test_direction_intensity_and_behavior_are_paired():
    result = evaluate(fixture())
    group = result["groups"]["activation:frustration"]
    assert group["coverage"] == 1 and group["descriptive_slt"] == 1
    assert result["validated"] is False and result["production_acceptance"] is False
    unchanged = evaluate(fixture(off_values=(0, 2, 4)))["groups"]["activation:frustration"]
    assert unchanged["components"]["direction"] == unchanged["components"]["intensity"] == unchanged["components"]["behavior"] == 0
    assert unchanged["descriptive_slt"] == .4  # Quality cannot establish transfer.
    nonmonotonic = evaluate(fixture(values=(0, 4, 2)))["groups"]["activation:frustration"]
    assert nonmonotonic["components"]["intensity"] == 0
    other = evaluate(fixture(axis="happiness"))["groups"]["activation:happiness"]
    assert other["components"]["behavior"] is None and other["descriptive_slt"] is None


def test_missing_or_mismatched_evidence_prevents_aggregate():
    data = fixture()
    missing_seed = evaluate(data, (42, 43))["groups"]["activation:frustration"]
    assert missing_seed["coverage"] == .5 and missing_seed["descriptive_slt"] is None
    for field in ("state", "context", "model", "recipe", "seed", "messages", "mode", "hash"):

        rows, ratings, cases = deepcopy(data)
        if field == "state":
            rows[-1]["state"]["frustration"] = 84
        elif field == "context":
            ratings["activation:high"]["context_hash"] = "different"
        elif field == "model":
            rows[-1]["response"]["runtime_provenance"] = {"model_revision": "r2"}
        elif field == "recipe":
            rows[-1]["request"]["max_tokens"] = 128
        elif field == "seed":
            for row in rows:
                row["request"]["seed"] = 99
        elif field == "messages":
            rows[-1]["request"]["messages"].append({"role": "system", "content": "Be angry"})
        elif field == "mode":
            rows[-1]["request"]["steering"]["mode"] = "combined"
        else:
            ratings["activation:high"].pop("input_hash")
        result = evaluate((rows, ratings, cases))["groups"]["activation:frustration"]
        assert result["coverage"] == 0 and result["descriptive_slt"] is None


if __name__ == "__main__":
    test_direction_intensity_and_behavior_are_paired()
    test_missing_or_mismatched_evidence_prevents_aggregate()
    print("Exploratory paired SLT regressions passed")
