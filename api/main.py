from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routers import chat, context, memory, runtime, system, training
from api.dependencies import get_backend
from Chappies_Trainingspartner import daemon_manager
from config.config import settings, get_active_model


app = FastAPI(
    title="CHAPPiE App API",
    version="15.4.2026-api",
    description="FastAPI-Schicht fuer CHAPPiEs React-Frontend.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)
app.include_router(memory.router)
app.include_router(context.router)
app.include_router(chat.router)
app.include_router(runtime.router)
app.include_router(training.router)


@app.get("/", include_in_schema=False)
@app.get("/api", include_in_schema=False)
def root_overview():
    try:
        backend = get_backend()
        status = backend.get_status()
        emotions = backend._get_emotions_snapshot()
        life = backend.life_simulation.get_snapshot()
        training = daemon_manager.get_training_snapshot()
        memory_count = backend.memory.get_memory_count()
        stm_count = backend.short_term_memory_v2.get_count()
        sessions = backend.chat_manager.list_sessions()
    except Exception as e:
        return JSONResponse({
            "app": "CHAPPiE",
            "status": "error",
            "error": str(e),
        })

    return JSONResponse({
        "app": {
            "name": "CHAPPiE App API",
            "version": "15.4.2026-api",
            "docs": "/docs",
            "openapi": "/openapi.json",
        },
        "brain": {
            "available": status.get("brain_available"),
            "model": get_active_model(),
            "provider": settings.llm_provider.value,
            "temperature": settings.temperature,
            "max_tokens": settings.max_tokens,
            "steering_enabled": settings.enable_steering,
            "two_step_processing": settings.enable_two_step_processing,
            "chain_of_thought": settings.chain_of_thought,
        },
        "emotions": emotions,
        "life": {
            "phase": life.get("clock", {}).get("phase_label"),
            "activity": life.get("current_activity"),
            "mode": life.get("current_mode"),
            "dominant_need": (life.get("homeostasis", {}).get("dominant_need") or {}).get("name"),
            "stage": life.get("development", {}).get("stage"),
        },
        "memory": {
            "ltm_entries": memory_count,
            "stm_entries": stm_count,
            "daily_info_count": status.get("daily_info_count"),
        },
        "training": {
            "running": training.get("running"),
            "pid": training.get("pid"),
            "status": training.get("status_label"),
            "loops": training.get("loops"),
            "memory_count": training.get("memory_count"),
            "errors": training.get("errors"),
            "focus": training.get("focus"),
        },
        "sessions": {
            "total": len(sessions),
        },
    })
