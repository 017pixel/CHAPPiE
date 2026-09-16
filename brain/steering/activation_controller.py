"""Compose validated per-layer vectors with bounded state coefficients."""
from pathlib import Path
from brain.steering.modes import SteeringMode
from brain.steering.mixer import mix_emotions
from brain.steering.sequence_controller import build_sequence_specs
from brain.steering.vector_pack import LayerVectorPack
from config.config import get_steering_runtime_config

class ActivationController:
    def __init__(self, pack: LayerVectorPack, *, research: bool = False):
        self.pack = pack
        self.research = research
        self.profiles = pack.metadata.get("calibration", {}).get("profiles", {})
        if not self.profiles:
            raise ValueError("Vector pack has no measured layer/strength profiles")

    @classmethod
    def load(cls, path, model):
        return cls(LayerVectorPack(Path(path), model, require_calibrated=True))

    def payload(self, state, recent_changes=None, composites=None, mode="combined"):
        selected_mode = SteeringMode(mode)
        if selected_mode == SteeringMode.OFF:
            return {"steering": {"enabled": False, "mode": "off", "vectors": [], "sequences": []}}
        config = get_steering_runtime_config()
        bases = []
        for axis in mix_emotions(state, recent_changes):
            profile = self.profiles.get(axis["name"])
            if profile is None:
                raise ValueError(f"Missing calibrated profile: {axis['name']}")
            bases.append(self._vector(axis, profile, config))
        composite_vectors = []
        for composite in sorted(composites or [], key=lambda item: item.get("strength", 0), reverse=True):
            name = composite["name"]
            if name not in self.profiles:
                continue
            coefficient = min(1, max(0, float(composite.get("strength", 0)) / config["max_composite_strength"]))
            if coefficient < config["minimum_mixer_coefficient"]:
                continue
            composite_vectors.append(self._vector({"name": name, "coefficient": coefficient,
                                                   "source": "measured_composite"}, self.profiles[name], config))
            if len(composite_vectors) >= config["max_composite_vectors"]:
                break
        selected = bases + composite_vectors
        vectors = selected if selected_mode.activation else []
        sequences = build_sequence_specs(bases) if selected_mode.sequence else []
        dominant = max(selected, key=lambda v: v["strength"], default={})
        return {"steering": {"enabled": bool(vectors or sequences), "mode": selected_mode.value,
                             "model_layers": self.pack.layers, "vectors": vectors, "sequences": sequences,
                             "base_vectors": bases, "selected_base_vectors": bases,
                             "composite_vectors": composite_vectors, "composite_modes": composites or [],
                             "dominant": dominant.get("name", "neutral"),
                             "dominant_strength": dominant.get("strength", 0),
                             "emotion_state": dict(state), "pack_status": self.pack.metadata["status"],
                             "method": "measured_diffmean", "pack_path": str(self.pack.path),
                             "profile_policy": "research" if self.research else "production"}}

    def _vector(self, axis, profile, config):
        maximum = float(profile["strength"])
        cap = config["research_alpha_cap"] if self.research else config["production_alpha_cap"]
        if not 0 < maximum <= cap:
            raise ValueError("Selected strength exceeds research cap" if self.research else "Calibrated strength exceeds production cap")
        coefficient = axis["coefficient"]
        layers, pooling = profile["layers"], profile["pooling"]
        spec = self.pack.vector_spec(axis["name"], layers, pooling)
        return {**axis, "vector": spec, "layers": layers,
                "layer_range": [min(layers), max(layers)],
                "strength": min(cap, abs(coefficient) * maximum),
                "direction": "negative" if coefficient < 0 else "positive"}
