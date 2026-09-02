#!/usr/bin/env python3
"""Verify that the historical v5 report stayed byte-for-byte unchanged."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "forschung" / "report" / "report-v5-freeze.json"


def validate() -> dict[str, object]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    report_path = ROOT / str(manifest["path"])
    payload = report_path.read_bytes()
    text = payload.decode("utf-8")
    actual_hash = hashlib.sha256(payload).hexdigest()
    checks = {
        "file_exists": report_path.is_file(),
        "sha256_matches": actual_hash == manifest["sha256"],
        "size_matches": len(payload) == manifest["size_bytes"],
        "title_matches": f"<title>{manifest['title']}</title>" in text,
    }
    return {
        "ok": all(checks.values()),
        "report": str(report_path.relative_to(ROOT)),
        "sha256": actual_hash,
        "checks": checks,
    }


def main() -> None:
    result = validate()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()

