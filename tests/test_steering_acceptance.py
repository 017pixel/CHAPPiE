"""Acceptance cannot turn ties, invalid ratings or missing evidence into success."""
import sys
from pathlib import Path
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from forschung.steering_v17.acceptance import controlled_transfer, neutral_answer_correct, quality_controls
from forschung.steering_v17.benchmark import record_server_provenance, ProvenanceMismatch


def test_controlled_transfer():
    rows = [{"case_id": level, "mode": "activation", "seed": 42,
             "control_group": "same-prompt", "control_axis": "frustration", "control_level": level,
             "response": {"id": level}} for level in ("low", "medium", "high")]
    def score(values):
        ratings = {level: {"rating": {"frustration": value}} for level, value in zip(("low", "medium", "high"), values)}
        return controlled_transfer(rows, ratings, rows)["groups"]["activation"]
    assert score([0, 2, 4])["passes_80_percent"]
    assert score([0, 0, 4])["passes_80_percent"]
    assert not score([2, 2, 2])["passes_80_percent"]
    assert score([2, 2, 2])["flat_triples"] == 1
    assert not score([0, 4, 2])["passes_80_percent"]
    assert score([0, 2, 5])["coverage"] == 0
    assert score([0, 2, True])["coverage"] == 0
    planned = rows + [{**r, "control_group": "missing-group", "case_id": "missing-" + r["case_id"]} for r in rows]
    ratings = {level: {"rating": {"frustration": value}} for level, value in zip(("low", "medium", "high"), (0, 2, 4))}
    result = controlled_transfer(rows, ratings, planned)["groups"]["activation"]
    assert result["expected_triples"] == 2 and result["coverage"] == .5
    assert not result["passes_80_percent"]
    assert controlled_transfer(rows, ratings)["groups"]["activation"]["passes_80_percent"] is None
    assert not controlled_transfer(rows[:2], {"low": {"rating": {"frustration": 0}}, "medium": {"rating": {"frustration": 2}}})["groups"]["activation"]["passes_80_percent"]


def test_oracles_and_observed_eos():
    assert neutral_answer_correct("42", "42")
    assert not neutral_answer_correct("142", "42")
    assert not neutral_answer_correct("Nicht 42, sondern 43.", "42")
    assert not neutral_answer_correct("Paris ist falsch; die Hauptstadt ist Lyon.", "Paris")
    assert not neutral_answer_correct("Nicht drei, sondern vier", "3")
    assert neutral_answer_correct("H₂O", "H2O")
    assert neutral_answer_correct(' {"zahl": 7} ', "json:7")
    assert not neutral_answer_correct('{"zahl": true}', "json:7")
    assert not neutral_answer_correct('Hier: {"zahl": 7}', "json:7")
    assert not neutral_answer_correct("blau und rot", "blau")
    assert neutral_answer_correct("2, 5, 9", "2, 5, 9")
    assert not neutral_answer_correct("9, 2, 5", "2, 5, 9")
    assert not neutral_answer_correct("Nicht 2, 5, 9", "2, 5, 9")
    row = {"mode": "off", "case_id": "a", "seed": 42, "category": "neutral_control", "expected_answer": "42",
           "response": {"choices": [{"message": {"content": "42"}, "finish_reason": "stop"}],
                        "usage": {"completion_tokens": 2}}}
    assert quality_controls([row])["off"]["termination_observed"] == 0
    row["response"]["generation"] = {"natural_eos": True}
    assert quality_controls([row])["off"]["short_natural_eos"] == 1
    assert quality_controls([row])["off"]["neutral_accuracy"] == 1
    explanation = "17 + 25 = 42. Ich addiere zuerst 20 und anschließend 5."
    assert neutral_answer_correct(explanation, "42") is None
    unresolved = {**row, "response": {"choices": [{"message": {"content": explanation}}]}}
    controls = quality_controls([unresolved])["off"]
    assert controls["neutral_unresolved"] == 1 and controls["neutral_accuracy"] is None
    assert controls["neutral_accuracy_lower_bound"] == 0 and controls["neutral_accuracy_upper_bound"] == 1
    assert controls["neutral_quality_passes_10pp"] is None
    row["error"] = "provider failed"
    assert quality_controls([row])["off"]["neutral_accuracy"] == 0


def test_server_provenance_drift_stops():
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory)
        record_server_provenance(output, {"runtime_provenance": {"model_revision": "a"}})
        record_server_provenance(output, {"runtime_provenance": {"model_revision": "a"}})
        try:
            record_server_provenance(output, {})
        except ProvenanceMismatch:
            pass
        else:
            raise AssertionError("Missing provenance after a recorded identity was accepted")
        try:
            record_server_provenance(output, {"runtime_provenance": {"model_revision": "b"}})
        except ProvenanceMismatch:
            pass
        else:
            raise AssertionError("Mixed inference revisions were accepted")



def test_complete_context_upper_bound_is_conservative():
    from forschung.steering_v17.acceptance import context_preparation_upper_bound
    timing = {"total_ms": 1000, "intent_ms": 200, "emotion_appraisal_ms": 10,
              "generation_ms": 500, "formatting_ms": 20,
              "memory_retrieval_ms": 30, "memory_context_build_ms": 10}
    assert abs(context_preparation_upper_bound(timing) - 270.005) < .000001
    # Partial memory spans are not mistaken for the complete preparation.
    assert context_preparation_upper_bound(timing) > 40
    assert context_preparation_upper_bound({"total_ms": 1000, "generation_ms": 500}) == 500.005
    assert context_preparation_upper_bound({"total_ms": 1000}) is None
    assert context_preparation_upper_bound({"total_ms": 100, "generation_ms": 500}) is None
    assert context_preparation_upper_bound({"total_ms": float("nan"), "generation_ms": 50}) is None

if __name__ == "__main__":
    test_complete_context_upper_bound_is_conservative()
    test_controlled_transfer()
    test_oracles_and_observed_eos()
    test_server_provenance_drift_stops()
    print("Research acceptance regressions passed")
