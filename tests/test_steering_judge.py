"""Exact annotation reuse retains provenance and never retries identical invalid scales."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from forschung.steering_v17 import judge

CONTEXT = {"schema_version": 2, "runtime_provenance": {"model_revision": "r1"}}


def rows():
    return [{"prompt": "Wie geht es dir?", "response": {"id": str(i), "choices": [{"message": {"content": "Ruhig."}}]}} for i in range(2)]


def test_invalid_answer_is_not_judged_repeatedly():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "generations.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows()))
        invalid = {"error": "Invalid scale", "response": {"raw": "score 5"}, "method": "blind_automated_local"}
        with patch.object(sys, "argv", ["judge", "--run", directory]), patch.object(judge, "rate", return_value=invalid) as rate, patch.object(judge.httpx, "Client", MagicMock()), patch.object(judge, "read_judge_context", return_value=CONTEXT):
            judge.main()
        result = list(map(json.loads, (root / "blind_ratings_v2.jsonl").read_text().splitlines()))
        assert rate.call_count == 1
        assert len(result) == 2 and all("error" in row and "rating" not in row for row in result)
        assert result[1]["cached_from_response_id"] == "0"


def test_reference_requires_exact_prompt_and_answer():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        cases = rows() + [{"prompt": "Andere Frage", "response": {"id": "2", "choices": [{"message": {"content": "Ruhig."}}]}}]
        (root / "generations.jsonl").write_text("".join(json.dumps(row) + "\n" for row in cases))
        reference = root / "reference.jsonl"
        key = judge.input_hash("Wie geht es dir?", "Ruhig.", judge.context_hash(CONTEXT))
        rating = {key: 0 for key in judge.RATING_KEYS}
        reference.write_text(json.dumps({"response_id": "historical", "input_hash": key, "context_hash": judge.context_hash(CONTEXT), "rating": rating}) + "\n")
        with patch.object(sys, "argv", ["judge", "--run", directory, "--reference-ratings", str(reference)]), patch.object(judge, "rate", return_value={"rating": rating}) as rate, patch.object(judge.httpx, "Client", MagicMock()), patch.object(judge, "read_judge_context", return_value=CONTEXT):
            judge.main()
        result = list(map(json.loads, (root / "blind_ratings_v2.jsonl").read_text().splitlines()))
        assert rate.call_count == 1 and rate.call_args.args[1] == "Andere Frage"
        for row in result[:2]:
            assert row["cached_from_response_id"] == "historical"
            assert row["reference_ratings_sha256"] == hashlib.sha256(reference.read_bytes()).hexdigest()
            assert row["independent_human_rating"] is False



def test_changed_recipe_cannot_resume_and_bad_reference_is_ignored():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "generations.jsonl").write_text(json.dumps(rows()[0]) + "\n")
        rating = {key: 0 for key in judge.RATING_KEYS}
        key = judge.input_hash("Wie geht es dir?", "Ruhig.", judge.context_hash(CONTEXT))
        reference = root / "reference.jsonl"
        reference.write_text(json.dumps({"response_id": "old", "input_hash": key,
            "context_hash": judge.context_hash(CONTEXT), "rating": {**rating, "calm": 5}}) + "\n")
        with patch.object(sys, "argv", ["judge", "--run", directory, "--reference-ratings", str(reference)]), patch.object(judge, "rate", return_value={"rating": rating}) as rate, patch.object(judge.httpx, "Client", MagicMock()), patch.object(judge, "read_judge_context", return_value=CONTEXT):
            judge.main()
            assert rate.call_count == 1
        with patch.object(sys, "argv", ["judge", "--run", directory]), patch.object(judge, "read_judge_context", return_value={**CONTEXT, "rubric": "changed"}):
            try:
                judge.main()
            except ValueError as exc:
                assert "recipe changed" in str(exc)
            else:
                raise AssertionError("Changed judge recipe reused existing annotations")


def test_generic_evaluation_does_not_merge_sweeps_or_claim_missing_slt():
    from forschung.steering_v17.evaluate import evaluate_rows
    try:
        evaluate_rows([{"layers": [1], "strength": .2}])
    except ValueError:
        pass
    else:
        raise AssertionError("Sweep configurations would be silently merged")
    row = {**rows()[0], "mode": "off", "case_id": "a", "seed": 42, "elapsed_ms": 1}
    result = evaluate_rows([row], {"unrelated": {}})
    assert result["semantic_slt_available"] is False


def test_paired_ranking_removes_prompt_effect_and_exposes_missing_bounds():
    from forschung.steering_v17.rank_layers import rank
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        run, off = root / "run", root / "off"
        run.mkdir()
        off.mkdir()
        generations, controls, annotations = [], [], []
        for index in range(8):
            row = {"case_id": str(index), "prompt": f"Question {index}", "category": "neutral_control" if index < 2 else "emotional",
                   "layers": [26], "strength": .15, "request": {"seed": 42, "temperature": .7, "max_tokens": 96},
                   "response": {"id": str(index)}}
            generations.append(row)
            controls.append({**row, "mode": "off", "seed": 42})
            annotations.append({"response_id": str(index), "context_hash": "same", "rating": {key: 4 for key in judge.RATING_KEYS}})
        for target, data in ((run, generations), (off, controls)):
            (target / "server_provenance.json").write_text('{"model_revision":"r1"}')
            (target / "generations.jsonl").write_text("".join(json.dumps(row) + "\n" for row in data))
            (target / "blind_ratings_v2.jsonl").write_text("".join(json.dumps(row) + "\n" for row in annotations))
        result = rank(run, rating_file="blind_ratings_v2.jsonl", control_run=off)
        assert result["ranking"][0]["semantic_selection_score"] == 0
        assert result["ranking"][0]["emotion_change_vs_off"] == 0
        assert result["production_acceptance"] is False
        annotations[-1] = {"response_id": "7", "context_hash": "same", "error": "invalid scale"}
        (run / "blind_ratings_v2.jsonl").write_text("".join(json.dumps(row) + "\n" for row in annotations))
        result = rank(run, rating_file="blind_ratings_v2.jsonl", control_run=off)
        assert not result["ranking"] and result["missing_rating_bias_unresolved"]
        bound = result["missing_rating_score_bounds"][0]
        assert bound["score_min"] < bound["score_max"]
        controls[0]["request"] = {**controls[0]["request"], "max_tokens": 128}
        (off / "generations.jsonl").write_text("".join(json.dumps(row) + "\n" for row in controls))
        try:
            rank(run, rating_file="blind_ratings_v2.jsonl", control_run=off)
        except ValueError as exc:
            assert "generation parameter" in str(exc)
        else:
            raise AssertionError("Mismatched OFF token budget accepted")


def test_fatal_judge_provenance_cannot_be_negative_cached_on_resume():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "generations.jsonl").write_text(json.dumps(rows()[0]) + "\n")
        (root / "blind_ratings_v2_manifest.json").write_text(json.dumps(CONTEXT))
        (root / "blind_ratings_v2.jsonl").write_text(json.dumps({"response_id": "0",
            "context_hash": judge.context_hash(CONTEXT), "fatal_provenance_error": True,
            "error": "changed model", "response": {"raw": "retained"}}) + "\n")
        with patch.object(sys, "argv", ["judge", "--run", directory]), patch.object(judge, "read_judge_context", return_value=CONTEXT):
            try:
                judge.main()
            except ValueError as exc:
                assert "provenance failure" in str(exc)
            else:
                raise AssertionError("Fatal provenance failure was silently cached")


def test_ranking_keeps_all_seeds():
    from forschung.steering_v17.rank_layers import rank
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        generations, ratings = [], []
        for seed, expression in ((42, 0), (43, 4)):
            for index in range(8):
                identity = f"{index}:{seed}"
                generations.append({"case_id": str(index), "prompt": "Test", "category": "emotional",
                    "layers": [26], "strength": .15, "seed": seed, "response": {"id": identity}})
                ratings.append({"response_id": identity, "rating": {**{key: 4 for key in judge.RATING_KEYS}, "frustration": expression}})
        (root / "generations.jsonl").write_text("".join(json.dumps(row) + "\n" for row in generations))
        (root / "blind_ratings.jsonl").write_text("".join(json.dumps(row) + "\n" for row in ratings))
        (root / "manifest.json").write_text(json.dumps({"seeds": [42, 43]}))
        result = rank(root)
        assert result["ranking"][0]["cases"] == 16
        assert result["ranking"][0]["emotion_expression"] == .5

if __name__ == "__main__":
    test_ranking_keeps_all_seeds()
    test_fatal_judge_provenance_cannot_be_negative_cached_on_resume()
    test_paired_ranking_removes_prompt_effect_and_exposes_missing_bounds()
    test_changed_recipe_cannot_resume_and_bad_reference_is_ignored()
    test_generic_evaluation_does_not_merge_sweeps_or_claim_missing_slt()
    test_invalid_answer_is_not_judged_repeatedly()
    test_reference_requires_exact_prompt_and_answer()
    print("Blind annotation cache regressions passed")
