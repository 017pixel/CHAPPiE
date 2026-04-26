from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import chat, context, memory, runtime, system, training


def _parse_cors_origins() -> list[str]:
    defaults = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]
    raw_extra = os.getenv("CHAPPIE_CORS_ORIGINS", "")
    extra = [origin.strip() for origin in raw_extra.split(",") if origin.strip()]

    merged: list[str] = []
    for origin in defaults + extra:
        if origin not in merged:
            merged.append(origin)
    return merged


ALLOW_ORIGIN_REGEX = (
    r"^https?://("
    r"localhost|"
    r"127\.0\.0\.1|"
    r"(?:\[[0-9a-fA-F:]+\])|"
    r"(?:[A-Za-z0-9-]+\.)*[A-Za-z0-9-]+|"
    r"10(?:\.\d{1,3}){3}|"
    r"192\.168(?:\.\d{1,3}){2}|"
    r"172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2}|"
    r"100(?:\.\d{1,3}){3}"
    r")(?::\d+)?$"
)

app = FastAPI(
    title="CHAPPiE App API",
    version="15.3.2026-api",
    description="FastAPI-Schicht fuer CHAPPiEs React-Frontend.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(),
    allow_origin_regex=ALLOW_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(system.router)
app.include_router(memory.router)
app.include_router(context.router)
app.include_router(chat.router)
app.include_router(runtime.router)
app.include_router(training.router)
