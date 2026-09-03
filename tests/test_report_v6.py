#!/usr/bin/env python3
"""Standalone regression test for report v6."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from forschung.report.validate_report_v6 import validate  # noqa: E402


REPORT = ROOT / "forschung" / "report" / "CHAPPiE-Forschungsbericht-v6.html"


def test_report_v6_contract() -> None:
    assert validate() == []


def test_report_v6_documents_follow_up_work_without_rewriting_results() -> None:
    html = REPORT.read_text(encoding="utf-8")
    assert 'id="weiterarbeit"' in html
    assert "Die Experimente dieses Berichts bleiben als historische Vergleichsbasis unverändert." in html
    assert "Neue stabile CHAPPiE-Version" in html
    assert "bestehenden V6-Ergebnissen verglichen" in html


if __name__ == "__main__":
    test_report_v6_contract()
    test_report_v6_documents_follow_up_work_without_rewriting_results()
    print("OK: report v6 contract")
