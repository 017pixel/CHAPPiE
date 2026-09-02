#!/usr/bin/env python3
"""Standalone regression test for report v6."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from forschung.report.validate_report_v6 import validate  # noqa: E402


def test_report_v6_contract() -> None:
    assert validate() == []


if __name__ == "__main__":
    test_report_v6_contract()
    print("OK: report v6 contract")
