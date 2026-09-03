#!/usr/bin/env python3
"""Standalone regression test for the GitHub Pages artifact contract."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"


def test_pages_workflow_publishes_v6_at_root() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "'.github/workflows/pages.yml'" in workflow
    assert "mkdir -p _site" in workflow
    assert "cp -R forschung/report/. _site/" in workflow
    assert "cp forschung/report/CHAPPiE-Forschungsbericht-v6.html _site/index.html" in workflow
    assert "path: _site" in workflow


if __name__ == "__main__":
    test_pages_workflow_publishes_v6_at_root()
    print("OK: GitHub Pages publishes report v6 at root")
