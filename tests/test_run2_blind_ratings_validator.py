"""Regression tests for the Run-2 blind-rating scale contract."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = (
    ROOT
    / "forschung"
    / "runs"
    / "run-2-20260723-1108-cb6d011"
    / "validate_blind_ratings.py"
)
PACK_BUILDER = VALIDATOR.with_name("build_blinded_review_pack.py")
SHARDED_PACK_BUILDER = VALIDATOR.with_name("build_120b_sharded_blind_pack.py")


def load_validator():
    spec = spec_from_file_location("run2_blind_rating_validator", VALIDATOR)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_pack_builder():
    spec = spec_from_file_location("run2_blind_pack_builder", PACK_BUILDER)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    validator = load_validator()
    assert validator.RANGES["quality"] == (0, 5, False)
    assert validator.scale_value_valid("0", 0, 5, False)
    assert validator.scale_value_valid("5", 0, 5, False)
    assert not validator.scale_value_valid("-1", 0, 5, False)
    assert not validator.scale_value_valid("6", 0, 5, False)
    assert not validator.scale_value_valid("NA", 0, 5, False)
    assert validator.scale_value_valid("NA", 0, 3, True)
    assert not validator.scale_value_valid("", 0, 3, True)
    pack_builder = load_pack_builder()
    assert pack_builder.BLIND_RUBRIC_SCALE["quality"].startswith(
        "0 unusable"
    )
    assert set(pack_builder.BLIND_RUBRIC_SCALE) == set(validator.RANGES)
    sharded_source = SHARDED_PACK_BUILDER.read_text(encoding="utf-8")
    assert '"dangerous_method_text_redacted": True' in sharded_source
    print("OK: Run-2 blind-rating builder and validator share the 0–5 quality contract")


if __name__ == "__main__":
    main()
