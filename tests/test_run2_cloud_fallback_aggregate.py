#!/usr/bin/env python3
"""Regression test for Run-2 cloud aggregate provenance path handling."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "forschung"
    / "runs"
    / "run-2-20260723-1108-cb6d011"
    / "build_cloud_fallback_aggregate.py"
)


def main() -> None:
    spec = importlib.util.spec_from_file_location("run2_cloud_aggregate", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    relative_validation = (
        "forschung/runs/run-2-20260723-1108-cb6d011/"
        "processed/gpt-oss-20b-five-seed-validation.json"
    )
    assert module.project_path(Path(relative_validation)) == relative_validation
    assert module.project_path(ROOT / relative_validation) == relative_validation

    outside = Path("/tmp/run2-external-validation.json")
    assert module.project_path(outside) == str(outside)
    print("OK: cloud aggregate normalizes relative, absolute and external provenance paths")


if __name__ == "__main__":
    main()
