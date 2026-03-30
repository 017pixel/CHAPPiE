from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends

from api.services.command_service import build_visualizer_payload
from api.dependencies import get_backend
from api.schemas import HealthResponse, StatusResponse
from config.config import settings

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def get_health(backend=Depends(get_backend)):
    status = backend.get_status()
    return HealthResponse(
        ok=True,
        brain_available=status["brain_available"],
        model=status["model"],
        provider=settings.llm_provider.value,
    )


@router.get("/status", response_model=StatusResponse)
def get_status(backend=Depends(get_backend)):
    return StatusResponse(**backend.get_status())


@router.get("/life")
def get_life(backend=Depends(get_backend)):
    return backend.life_simulation.get_snapshot()


@router.get("/growth")
def get_growth(backend=Depends(get_backend)):
    snapshot = backend.life_simulation.get_snapshot()
    return {
        "planning_state": snapshot.get("planning_state", {}),
        "forecast_state": snapshot.get("forecast_state", {}),
        "social_arc": snapshot.get("social_arc", {}),
        "timeline_history": snapshot.get("timeline_history", []),
        "timeline_summary": snapshot.get("timeline_summary", {}),
        "development": snapshot.get("development", {}),
        "habit_dynamics": snapshot.get("habit_dynamics", {}),
    }


@router.get("/debug")
def get_debug(backend=Depends(get_backend)):
    active_session = backend.chat_manager.load_active_session()
    last_assistant_message = next(
        (msg for msg in reversed(active_session.get("messages", [])) if msg.get("role") == "assistant"),
        None,
    )
    return {
        "enabled": backend.debug_logger.enabled,
        "entries": backend.debug_logger.get_entries_as_dict(),
        "formatted_log": backend.debug_logger.get_formatted_log() if backend.debug_logger.enabled else "",
        "last_assistant_message": last_assistant_message,
    }


@router.get("/visualizer")
def get_visualizer_state(backend=Depends(get_backend)):
    return build_visualizer_payload(backend)
