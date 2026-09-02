#!/usr/bin/env python3
"""Validate that .claude project skills mirror the canonical .agents skills."""

from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / ".agents" / "skills"
MIRROR = ROOT / ".claude" / "skills"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate() -> list[str]:
    errors: list[str] = []
    canonical_names = {path.parent.name for path in CANONICAL.glob("*/SKILL.md")}
    mirror_names = {path.parent.name for path in MIRROR.glob("*/SKILL.md")}

    if canonical_names != mirror_names:
        missing = sorted(canonical_names - mirror_names)
        unexpected = sorted(mirror_names - canonical_names)
        if missing:
            errors.append(f"Fehlende Spiegel: {', '.join(missing)}")
        if unexpected:
            errors.append(f"Unerwartete Spiegel: {', '.join(unexpected)}")

    for name in sorted(canonical_names & mirror_names):
        source = CANONICAL / name / "SKILL.md"
        mirror = MIRROR / name / "SKILL.md"
        if _digest(source) != _digest(mirror):
            errors.append(f"Skill nicht synchron: {name}")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"FEHLER: {error}")
        return 1
    print("OK: Projekt-Skills sind synchron")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
