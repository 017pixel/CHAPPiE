from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query

from api.dependencies import get_backend
from config.config import settings

router = APIRouter(tags=["memory"])


def _memory_to_dict(entry):
    return {
        "id": entry.id,
        "content": entry.content,
        "role": entry.role,
        "timestamp": entry.timestamp,
        "mem_type": entry.mem_type,
        "relevance_score": entry.relevance_score,
        "label": entry.label,
    }


def _short_term_to_dict(entry):
    def format_timestamp(value: str) -> str:
        if not value:
            return value
        try:
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(ZoneInfo("Europe/Berlin")).isoformat()
        except ValueError:
            return value

    return {
        "id": entry.id,
        "content": entry.content,
        "category": entry.category,
        "importance": entry.importance,
        "created_at": format_timestamp(entry.created_at),
        "expires_at": format_timestamp(entry.expires_at),
        "migrated": getattr(entry, "migrated", False),
    }


@router.get("/memories")
def get_memories(
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    mem_type_filter: str | None = Query(default=None),
    label_filter: str | None = Query(default=None),
    backend=Depends(get_backend),
):
    if q:
        results = backend.memory.search_memory(q, top_k=limit, min_relevance=settings.memory_min_relevance)
        total = len(results)
    else:
        results = backend.memory.get_recent_memories(
            limit=limit,
            offset=offset,
            mem_type_filter=mem_type_filter,
            label_filter=label_filter,
        )
        total = backend.memory.get_filtered_memory_count(mem_type_filter=mem_type_filter, label_filter=label_filter)
    return {
        "items": [_memory_to_dict(entry) for entry in results],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/memories/health")
def get_memory_health(backend=Depends(get_backend)):
    return backend.memory.health_check()


@router.get("/memories/short-term")
def get_short_term_memories(
    category: str | None = Query(default=None),
    q: str | None = Query(default=None),
    backend=Depends(get_backend),
):
    items = backend.short_term_memory_v2.get_active_entries(category=category, query=q)
    return {
        "count": len(items),
        "items": [_short_term_to_dict(entry) for entry in items],
    }


@router.post("/memories/short-term/cleanup")
def cleanup_short_term_memories(backend=Depends(get_backend)):
    migrated = backend.short_term_memory_v2.migrate_expired_entries()
    return {"migrated": migrated, "count": backend.short_term_memory_v2.get_count()}


@router.delete("/memories")
def clear_memories(backend=Depends(get_backend)):
    deleted = backend.memory.clear_memory()
    return {"deleted": deleted}
