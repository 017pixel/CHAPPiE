from __future__ import annotations

from fastapi import APIRouter

from Chappies_Trainingspartner import daemon_manager
from Chappies_Trainingspartner.training_config_utils import curriculum_to_text, parse_curriculum_text
from api.schemas import TrainingActionRequest, TrainingActionResponse

router = APIRouter(prefix="/training", tags=["training"])


@router.get("/status")
def get_training_status():
    return daemon_manager.get_training_snapshot()


@router.get("/config")
def get_training_config():
    config = daemon_manager.load_training_config()
    return {
        **config,
        "curriculum_text": curriculum_to_text(config.get("curriculum", [])),
    }


@router.post("/config")
def save_config(payload: dict):
    normalized = dict(payload)
    if "curriculum_text" in normalized:
        normalized["curriculum"] = parse_curriculum_text(
            normalized.pop("curriculum_text", ""),
            normalized.get("focus_area", ""),
        )
    return daemon_manager.save_training_config(normalized)


@router.post("/action", response_model=TrainingActionResponse)
def post_training_action(request: TrainingActionRequest):
    logs = None
    if request.action == "start":
        result = daemon_manager.start_daemon(
            focus=request.focus,
            new=request.new,
            config_overrides=request.config_overrides or None,
        )
    elif request.action == "stop":
        result = daemon_manager.stop_daemon()
    elif request.action == "restart":
        result = daemon_manager.restart_daemon(
            focus=request.focus,
            new=request.new,
            config_overrides=request.config_overrides or None,
        )
    elif request.action == "logs":
        logs = daemon_manager.get_daemon_logs(request.lines)
        result = {"success": True, "message": "Logs geladen"}
    else:
        daemon_manager.clear_logs()
        result = {"success": True, "message": "Logs geloescht"}

    return TrainingActionResponse(
        success=bool(result.get("success", True)),
        message=result.get("message", ""),
        snapshot=daemon_manager.get_training_snapshot(),
        logs=logs,
    )
