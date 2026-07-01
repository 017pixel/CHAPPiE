"""Findet oder entfernt Memory-Eintraege mit Backend-Fehlerstrings.

Standard ist Dry-Run. Erst mit --apply werden Chroma-Memories geloescht und
Short-Term-Memory-Eintraege aus der JSON-Datei entfernt.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brain.response_parser import looks_like_model_error, strip_role_prefixes
from config.config import DATA_DIR
from memory.memory_engine import MemoryEngine


def _is_contaminated(text: str) -> bool:
    return looks_like_model_error(strip_role_prefixes(text or ""))


def scan_chroma(memory: MemoryEngine) -> List[Dict[str, Any]]:
    if memory.collection is None:
        return []
    raw = memory.collection.get(include=["documents", "metadatas"])
    ids = raw.get("ids") or []
    docs = raw.get("documents") or []
    metadatas = raw.get("metadatas") or []
    hits: List[Dict[str, Any]] = []
    for idx, doc in enumerate(docs):
        if not _is_contaminated(str(doc or "")):
            continue
        meta = metadatas[idx] if idx < len(metadatas) and isinstance(metadatas[idx], dict) else {}
        hits.append({
            "id": ids[idx] if idx < len(ids) else "",
            "role": meta.get("role", "unknown"),
            "timestamp": meta.get("timestamp", ""),
            "preview": str(doc or "")[:180],
        })
    return hits


def scan_stm(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)
    hits: List[Dict[str, Any]] = []
    for entry in data.get("entries", []):
        content = str(entry.get("content", "") or "")
        if _is_contaminated(content):
            hits.append({
                "id": entry.get("id", ""),
                "category": entry.get("category", ""),
                "created_at": entry.get("created_at", ""),
                "preview": content[:180],
            })
    return hits


def apply_stm_cleanup(path: Path, hit_ids: set[str]) -> int:
    if not path.exists() or not hit_ids:
        return 0
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)
    entries = data.get("entries", [])
    kept = [entry for entry in entries if str(entry.get("id", "")) not in hit_ids]
    data["entries"] = kept
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
    return len(entries) - len(kept)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bereinigt Memory-Fehlerstrings aus Chroma und STM.")
    parser.add_argument("--apply", action="store_true", help="Tatsaechlich loeschen statt nur auflisten")
    args = parser.parse_args()

    memory = MemoryEngine()
    chroma_hits = scan_chroma(memory)
    stm_path = DATA_DIR / "short_term_memory.json"
    stm_hits = scan_stm(stm_path)

    report = {
        "mode": "apply" if args.apply else "dry-run",
        "chroma_hits": chroma_hits,
        "stm_hits": stm_hits,
        "counts": {"chroma": len(chroma_hits), "stm": len(stm_hits)},
    }

    if args.apply:
        chroma_ids = [hit["id"] for hit in chroma_hits if hit.get("id")]
        if chroma_ids:
            memory.delete_memories(chroma_ids)
        stm_deleted = apply_stm_cleanup(stm_path, {str(hit.get("id", "")) for hit in stm_hits})
        report["deleted"] = {"chroma": len(chroma_ids), "stm": stm_deleted}

    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
