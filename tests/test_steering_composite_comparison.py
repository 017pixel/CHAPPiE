"""Paired composite evidence must bind actual prompts, recipes and responses."""
import copy
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from forschung.steering_v17.compare_composites import validated_rows
from forschung.steering_v17.judge import RATING_KEYS, context_hash, input_hash


def check():
    with tempfile.TemporaryDirectory() as temp:
        run = Path(temp)
        recipe = {"version": 2}
        context = context_hash(recipe)
        protocol = {"reference_server_provenance": {"model": "test"}, "dataset_sha256": "dataset", "pack_sha256": {"direct": "pack"}, "temperature": .7, "max_tokens": 256, "ranking": [{"layers": [21], "strength": .2}], "pooling": "last_four_tokens", "expected_per_arm_concept": 1}
        manifest = {"dataset_hash": "dataset", "pack_hash": "pack"}
        for name, value in (("manifest.json", manifest), ("server_provenance.json", protocol["reference_server_provenance"]), ("blind_ratings_v2_manifest.json", recipe)):
            (run / name).write_text(json.dumps(value))
        row = {"case_id": "case", "seed": 42, "prompt": "Hallo", "emotion": "warm", "layers": [21], "strength": .2,
               "request": {"seed": 42, "temperature": .7, "max_tokens": 256, "messages": [{"role": "user", "content": "Hallo"}], "chat_template_kwargs": {"enable_thinking": False}, "steering": {"mode": "activation", "enabled": True, "sequences": [], "vectors": [{"name": "warm", "strength": .2, "direction": "positive", "vector": {"pack_hash": "pack", "pooling": "last_four_tokens", "layers": {"21": [1., 0.]}}}]}},
               "response": {"id": "response", "choices": [{"message": {"content": "Guten Tag"}, "finish_reason": "stop"}]}}
        rating = {"response_id": "response", "rating": dict.fromkeys(RATING_KEYS, 2), "context_hash": context, "input_hash": input_hash("Hallo", "Guten Tag", context)}
        def write(observation, annotation):
            (run / "generations.jsonl").write_text(json.dumps(observation) + "\n")
            (run / "blind_ratings_v2.jsonl").write_text(json.dumps(annotation) + "\n")
        write(row, rating)
        assert len(validated_rows(run, protocol, "direct", "warm")[0]) == 1
        mutations = [
            lambda r: r["request"].update(seed=43),
            lambda r: r["request"].update(max_tokens=96),
            lambda r: r["request"]["messages"][0].update(content="Andere Frage"),
            lambda r: r["response"]["choices"][0]["message"].update(content="Andere Antwort"),
            lambda r: r["request"]["steering"]["vectors"][0].update(strength=.4),
            lambda r: r["request"]["steering"].update(mode="combined"),
        ]
        for mutate in mutations:
            changed = copy.deepcopy(row)
            mutate(changed)
            write(changed, rating)
            try:
                validated_rows(run, protocol, "direct", "warm")
            except ValueError:
                pass
            else:
                raise AssertionError("Mismatched composite evidence accepted")
        write(row, rating)
        with (run / "generations.jsonl").open("a") as stream:
            stream.write(json.dumps(row) + "\n")
        try:
            validated_rows(run, protocol, "direct", "warm")
        except ValueError:
            pass
        else:
            raise AssertionError("Duplicate treated as another paired observation")
        off = copy.deepcopy(row)
        off["mode"] = "off"
        off["request"]["steering"] = {"enabled": False, "vectors": []}
        write(off, rating)
        assert len(validated_rows(run, protocol)[0]) == 1
    print("PASS composite paired evidence binding and duplicates")


if __name__ == "__main__":
    check()
