from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_backend

router = APIRouter(tags=["context"])


@router.get("/context-files")
def get_context_files(backend=Depends(get_backend)):
    return backend.context_files.get_all_context()


@router.get("/context-files/{context_name}")
def get_context_file(context_name: str, backend=Depends(get_backend)):
    normalized = context_name.lower()
    if normalized == "soul":
        return {"name": "soul", "content": backend.context_files.get_soul_context()}
    if normalized == "user":
        return {"name": "user", "content": backend.context_files.get_user_context()}
    if normalized in {"preferences", "prefs"}:
        return {"name": "preferences", "content": backend.context_files.get_preferences_context()}
    raise HTTPException(status_code=404, detail="Unbekannte Kontextdatei.")
