#!/usr/bin/env python3
"""Remove stale active short-term transcript artefacts safely.

The long-term Chroma repair is independent from the JSON short-term cache.
This utility keeps the historical/migrated rows for recovery, but removes
currently active rows from failed chat/training runs.  A new conversation then
repopulates STM from the repaired pipeline instead of replaying old answers.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _is_active(entry: dict, now: datetime) -> bool:
    if bool(entry.get("migrated")):
        return False
    try:
        expires = datetime.fromisoformat(str(entry.get("expires_at", "")))
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return False
    return expires > now


def repair(path: Path) -> dict[str, int | str]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        raise ValueError(f"Ungueltiges Short-Term-Format: {path}")

    now = datetime.now(timezone.utc)
    entries = [entry for entry in data["entries"] if isinstance(entry, dict)]
    kept = [entry for entry in entries if not _is_active(entry, now)]
    removed = len(entries) - len(kept)
    data["entries"] = kept
    data["last_cleanup"] = now.isoformat()

    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)

    return {
        "path": str(path),
        "before": len(entries),
        "removed_active": removed,
        "after": len(kept),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--path",
        type=Path,
        default=PROJECT_ROOT / "data" / "short_term_memory.json",
    )
    args = parser.parse_args()
    path = args.path if args.path.is_absolute() else PROJECT_ROOT / args.path
    if not path.is_file():
        raise FileNotFoundError(path)
    print(json.dumps(repair(path), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
