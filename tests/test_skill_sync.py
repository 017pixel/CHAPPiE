#!/usr/bin/env python3
"""Standalone contract test for project skill mirroring."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_skill_sync import validate  # noqa: E402


def test_project_skills_are_in_sync() -> None:
    assert validate() == []


if __name__ == "__main__":
    test_project_skills_are_in_sync()
    print("OK: project skill sync")
