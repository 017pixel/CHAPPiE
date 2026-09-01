#!/usr/bin/env python3
"""Rebuild a readable Chroma collection from a damaged local store.

Chroma keeps documents and metadata in SQLite but stores the vector index in
native HNSW files.  If that index is damaged, opening the collection can
segfault before application code gets a chance to handle the error.  This
script therefore reads only the SQLite metadata from the source and writes a
fresh persistent collection with newly calculated local embeddings.

The source is never modified.  Contaminated model/training artefacts are
quarantined by the same policy used during normal retrieval; the remaining
user, assistant and system memories keep their original ids and metadata.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.config import DEFAULT_CHROMA_COLLECTION, LEGACY_CHROMA_COLLECTION, settings
from memory.memory_engine import MemoryEngine


def _value(row: sqlite3.Row) -> Any:
    if row[0] is not None:
        return row[0]
    if row[1] is not None:
        return row[1]
    if row[2] is not None:
        return row[2]
    if row[3] is not None:
        return bool(row[3])
    return None


def _read_records(source_db: Path, collection_name: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Read documents and metadata without opening Chroma's vector index."""
    connection = sqlite3.connect(f"file:{source_db.resolve()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        collection = connection.execute(
            "SELECT id, name FROM collections WHERE name = ?",
            (collection_name,),
        ).fetchone()
        if collection is None and collection_name != LEGACY_CHROMA_COLLECTION:
            collection = connection.execute(
                "SELECT id, name FROM collections WHERE name = ?",
                (LEGACY_CHROMA_COLLECTION,),
            ).fetchone()
        if collection is None:
            raise RuntimeError(f"Keine Chroma-Sammlung in {source_db}: {collection_name}")

        rows = connection.execute(
            """
            SELECT e.id AS row_id, e.embedding_id, m.key,
                   m.string_value, m.int_value, m.float_value, m.bool_value
            FROM embeddings AS e
            JOIN segments AS s ON s.id = e.segment_id
            JOIN embedding_metadata AS m ON m.id = e.id
            WHERE s.collection = ? AND s.scope = 'METADATA'
            ORDER BY e.id
            """,
            (collection["id"],),
        ).fetchall()
    finally:
        connection.close()

    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        record = grouped.setdefault(
            str(row["embedding_id"]),
            {"id": str(row["embedding_id"]), "metadata": {}},
        )
        value = _value((row["string_value"], row["int_value"], row["float_value"], row["bool_value"]))
        if row["key"] == "chroma:document":
            record["content"] = str(value or "")
        else:
            record["metadata"][str(row["key"])] = value

    usable: list[dict[str, Any]] = []
    quarantined = 0
    roles: dict[str, int] = {}
    for record in grouped.values():
        content = str(record.get("content", "")).strip()
        metadata = dict(record.get("metadata") or {})
        role = str(metadata.get("role", "unknown"))
        if MemoryEngine._is_memory_contaminated(
            content,
            role=role,
            source=str(metadata.get("source", "")),
            label=str(metadata.get("label", "")),
        ):
            quarantined += 1
            continue
        metadata.pop("chroma:document", None)
        # Chroma accepts only scalar metadata values.  Legacy rows are all
        # strings, but normalise an unexpected NULL defensively.
        metadata = {key: (value if value is not None else "") for key, value in metadata.items()}
        usable.append({"id": record["id"], "content": content, "metadata": metadata})
        roles[role] = roles.get(role, 0) + 1

    return usable, {
        "source_collection": collection["name"],
        "source_records": len(grouped),
        "usable_records": len(usable),
        "quarantined_records": quarantined,
        "usable_by_role": roles,
    }


def _write_collection(destination: Path, records: list[dict[str, Any]], batch_size: int) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"Ziel existiert bereits: {destination}")

    staging = Path(tempfile.mkdtemp(prefix=f"{destination.name}.staging-", dir=destination.parent))
    try:
        embedder = SentenceTransformer(settings.embedding_model, device="cpu")
        client = chromadb.PersistentClient(
            path=str(staging),
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
                is_persistent=True,
            ),
        )
        collection = client.get_or_create_collection(
            name=DEFAULT_CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine", "description": "CHAPiE episodic memory"},
        )

        for start in range(0, len(records), batch_size):
            batch = records[start:start + batch_size]
            embeddings = embedder.encode(
                [item["content"] for item in batch],
                batch_size=min(64, batch_size),
                convert_to_numpy=True,
                normalize_embeddings=False,
                show_progress_bar=False,
            ).tolist()
            collection.add(
                ids=[item["id"] for item in batch],
                embeddings=embeddings,
                documents=[item["content"] for item in batch],
                metadatas=[item["metadata"] for item in batch],
            )

        if collection.count() != len(records):
            raise RuntimeError(
                f"Validierung fehlgeschlagen: {collection.count()} statt {len(records)} Eintraege"
            )
        destination_metadata = {
            "collection": DEFAULT_CHROMA_COLLECTION,
            "embedding_model": settings.embedding_model,
            "memory_count": collection.count(),
        }
        (staging / "repair_manifest.json").write_text(
            json.dumps(destination_metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        staging.rename(destination)
    except Exception:
        # The staging directory is intentionally left intact for diagnostics;
        # no existing production data is touched on a failed rebuild.
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-db",
        type=Path,
        default=PROJECT_ROOT / "data" / "chroma_db" / "chroma.sqlite3",
    )
    parser.add_argument(
        "--destination",
        type=Path,
        default=PROJECT_ROOT / "data" / "chroma_db_repaired",
    )
    parser.add_argument("--collection", default=DEFAULT_CHROMA_COLLECTION)
    parser.add_argument("--batch-size", type=int, default=128)
    args = parser.parse_args()

    source_db = args.source_db if args.source_db.is_absolute() else PROJECT_ROOT / args.source_db
    destination = args.destination if args.destination.is_absolute() else PROJECT_ROOT / args.destination
    if not source_db.is_file():
        raise FileNotFoundError(source_db)
    if args.batch_size < 1:
        raise ValueError("--batch-size muss groesser als 0 sein")

    records, report = _read_records(source_db, args.collection)
    _write_collection(destination, records, args.batch_size)
    report.update({"destination": str(destination), "destination_collection": DEFAULT_CHROMA_COLLECTION})
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
