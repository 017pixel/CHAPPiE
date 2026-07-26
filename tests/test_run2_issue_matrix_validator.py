"""Regression test for malformed extra columns in the Run-2 issue CSV."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
VALIDATOR_PATH = (
    PROJECT_ROOT
    / "forschung"
    / "runs"
    / "run-2-20260723-1108-cb6d011"
    / "validate_issue_matrix.py"
)


def load_validator():
    spec = spec_from_file_location("run2_issue_matrix_validator", VALIDATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_extra_csv_columns_are_rejected():
    validator = load_validator()
    clean = {"issue_id": "MF-001", None: None}
    malformed = {
        "issue_id": "MF-002",
        None: ["unexpected thirteenth column"],
    }

    assert validator.extra_column_rows([clean]) == {}
    assert validator.extra_column_rows([clean, malformed]) == {
        "MF-002": ["unexpected thirteenth column"]
    }


def test_evidence_path_gate_requires_a_real_project_path():
    validator = load_validator()
    assert validator.existing_evidence_paths(
        "missing/path.json | tests/test_run2_issue_matrix_validator.py"
    ) == ["tests/test_run2_issue_matrix_validator.py"]
    assert validator.existing_evidence_paths("missing/path.json") == []


if __name__ == "__main__":
    test_extra_csv_columns_are_rejected()
    test_evidence_path_gate_requires_a_real_project_path()
    print("OK: Run-2 issue-matrix extra-column and evidence-path gates")
