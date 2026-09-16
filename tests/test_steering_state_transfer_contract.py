"""Mixer contracts are mechanical; semantic transfer requires real generation runs."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.steering.mixer import mix_emotions
from brain.steering.activation_controller import ActivationController
from config.emotions import EMOTION_DEFAULTS, EMOTION_ORDER

class Pack:
    layers = 4
    path = Path("measured-test-pack.json")
    metadata = {"status": "calibrated", "calibration": {"profiles": {
        name: {"layers": [1, 3], "pooling": "target_segment", "strength": .4}
        for name in (*EMOTION_ORDER, "crashout")}}}
    def vector_spec(self, emotion, layers, pooling):
        return {"type": "layer_vectors", "layers": {str(layer): [1, 0] for layer in layers}}

def main():
    baseline = dict(EMOTION_DEFAULTS)
    state = {**baseline, "frustration": 68}
    before = mix_emotions(state)[0]
    acute = mix_emotions(state, {"frustration": {"applied_delta": 18}})[0]
    assert acute["coefficient"] > before["coefficient"]
    assert mix_emotions(state)[0] == before, "Acute boost persisted into later turn"
    many = {name: 100 if value <= 50 else 0 for name, value in baseline.items()}
    assert len(mix_emotions(many)) == 3
    controller = ActivationController(Pack())
    for mode, activations, sequences in (("off", False, False), ("activation", True, False), ("sequence", False, True), ("combined", True, True)):
        payload = controller.payload(state, mode=mode)["steering"]
        assert bool(payload["vectors"]) == activations
        assert bool(payload["sequences"]) == sequences
    low = controller.payload({**baseline, "trust": 0}, mode="activation")["steering"]["vectors"][0]
    assert low["direction"] == "negative"
    mixed = controller.payload(many, composites=[{"name": "crashout", "strength": .9}] * 3)["steering"]
    assert len(mixed["base_vectors"]) == 3 and len(mixed["composite_vectors"]) == 1
    assert all(0 <= vector["strength"] <= .4 for vector in mixed["vectors"])
    assert all(set(vector["vector"]["layers"]) == {"1", "3"} for vector in mixed["vectors"])
    assert not controller.payload(baseline)["steering"]["enabled"]
    for invalid in (float("nan"), float("inf")):
        try:
            mix_emotions({**baseline, "frustration": invalid})
        except ValueError:
            pass
        else:
            raise AssertionError("Nonfinite state accepted")
    from copy import deepcopy
    high_pack = Pack()
    high_pack.metadata = deepcopy(Pack.metadata)
    high_pack.metadata["calibration"]["profiles"]["frustration"]["strength"] = .7
    high_state = {**baseline, "frustration": 100}
    try:
        ActivationController(high_pack).payload(high_state, mode="activation")
    except ValueError as exc:
        assert "production cap" in str(exc)
    else:
        raise AssertionError("Research dose was accepted as a production profile")
    research = ActivationController(high_pack, research=True).payload(high_state, mode="activation")["steering"]
    assert research["vectors"][0]["strength"] == .7 and research["profile_policy"] == "research"
    for value in (50, 100):
        sequence_state = {**baseline, "frustration": value}
        high_pack.metadata["calibration"]["profiles"]["frustration"]["strength"] = .7
        stronger_sequence = ActivationController(high_pack, research=True).payload(sequence_state, mode="sequence")["steering"]["sequences"]
        high_pack.metadata["calibration"]["profiles"]["frustration"]["strength"] = .2
        weaker_sequence = ActivationController(high_pack, research=True).payload(sequence_state, mode="sequence")["steering"]["sequences"]
        assert stronger_sequence == weaker_sequence, "Activation calibration changed sequence-only dose"
        assert stronger_sequence[0]["token_candidates"][0]["weight"] == value / 100
    from brain.steering.sequence_controller import build_sequence_specs
    legacy = build_sequence_specs([{"name": "frustration", "strength": .2}])
    assert legacy[0]["token_candidates"][0]["weight"] == .5
    assert not build_sequence_specs([{"name": "frustration", "coefficient": 0, "strength": .2}])
    try:
        build_sequence_specs([{"name": "frustration", "coefficient": float("nan"), "strength": .2}])
    except ValueError:
        pass
    else:
        raise AssertionError("Nonfinite sequence coefficient accepted")
    high_pack.metadata["calibration"]["profiles"]["frustration"]["strength"] = 2.1
    assert ActivationController(high_pack, research=True).payload(high_state, mode="activation")["steering"]["vectors"][0]["strength"] == 2.1
    try:
        ActivationController(high_pack).payload(high_state, mode="activation")
    except ValueError:
        pass
    else:
        raise AssertionError("Reference-RMS research dose entered production")
    from config.config import get_steering_runtime_config
    high_pack.metadata["calibration"]["profiles"]["frustration"]["strength"] = get_steering_runtime_config()["research_alpha_cap"] + .1
    try:
        ActivationController(high_pack, research=True).payload(high_state, mode="activation")
    except ValueError as exc:
        assert "research cap" in str(exc)
    else:
        raise AssertionError("Unbounded research dose accepted")
    print("Mixer: transient delta, top-3 plus one, negative direction, mode and strength caps passed; no semantic claim")
if __name__ == "__main__":
    main()
