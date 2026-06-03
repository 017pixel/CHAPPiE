"""API router for Fine-Tune model management."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from api.schemas.finetune_schemas import (
    ActiveAdapterRequest,
    ActiveAdapterResponse,
    FinetuneModelInfo,
    TrainingConfigRequest,
    TrainingStatusResponse,
    ChatScanResult,
)
from brain.models_manager import (
    list_models,
    switch_active_model,
    start_training,
    get_training_status,
    stop_training,
    delete_model,
)
from brain.whatsapp_finetune_trainer import (
    extract_chat_from_zip,
    parse_messages,
    filter_media,
    detect_participants,
    build_conversation_pairs,
)
from config.config import settings

router = APIRouter(prefix="/finetune", tags=["finetune"])


@router.get("/models", response_model=List[FinetuneModelInfo])
def get_models() -> List[FinetuneModelInfo]:
    return [FinetuneModelInfo(**m) for m in list_models()]


@router.get("/models/{name}/status", response_model=TrainingStatusResponse)
def get_model_status(name: str) -> TrainingStatusResponse:
    status = get_training_status(name)
    if not status:
        raise HTTPException(status_code=404, detail="Modell oder Status nicht gefunden")
    return TrainingStatusResponse(**status)


@router.delete("/models/{name}")
def delete_model_endpoint(name: str) -> Dict[str, Any]:
    result = delete_model(name)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/models/{name}/train")
def train_model_endpoint(name: str) -> Dict[str, Any]:
    config_path = Path(settings.finetune_models_dir) / name / "training_config.json"
    if not config_path.exists():
        raise HTTPException(status_code=404, detail="Training-Config nicht gefunden")
    result = start_training(str(config_path))
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@router.post("/models/{name}/stop")
def stop_model_training(name: str) -> Dict[str, Any]:
    result = stop_training(name)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@router.put("/active", response_model=ActiveAdapterResponse)
def set_active_adapter(request: ActiveAdapterRequest) -> ActiveAdapterResponse:
    result = switch_active_model(request.model_name)
    return ActiveAdapterResponse(**result)


@router.get("/active")
def get_active_adapter() -> Dict[str, Any]:
    adapter = settings.finetune_active_adapter
    models = list_models()
    active_name = None
    if adapter:
        for m in models:
            if m.get("adapter_path") == adapter:
                active_name = m["name"]
                break
    return {
        "active_adapter": adapter,
        "active_model_name": active_name,
        "base_model": settings.vllm_model,
    }


@router.post("/chats/scan", response_model=List[ChatScanResult])
def scan_chats() -> List[ChatScanResult]:
    chats_dir = Path(settings.finetune_chats_dir)
    if not chats_dir.exists():
        return []
    results = []
    for zip_path in chats_dir.glob("*.zip"):
        try:
            raw = extract_chat_from_zip(str(zip_path))
            messages = parse_messages(raw)
            messages = filter_media(messages)
            participants = detect_participants(messages)
            results.append(ChatScanResult(
                zip_filename=zip_path.name,
                participants=participants,
                message_count=len(messages),
            ))
        except Exception:
            continue
    return results


@router.post("/chats/analyze/{zip_name}")
def analyze_chat(zip_name: str, target_person: str) -> Dict[str, Any]:
    chats_dir = Path(settings.finetune_chats_dir)
    zip_path = chats_dir / zip_name
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Chat-ZIP nicht gefunden")
    try:
        raw = extract_chat_from_zip(str(zip_path))
        messages = parse_messages(raw)
        messages = filter_media(messages)
        pairs = build_conversation_pairs(messages, target_person)
        return {
            "zip_name": zip_name,
            "target_person": target_person,
            "total_messages": len(messages),
            "total_pairs": len(pairs),
            "single_turn": sum(1 for p in pairs if p["type"] == "single"),
            "multi_turn": sum(1 for p in pairs if p["type"] == "multi"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prepare")
def prepare_training(request: TrainingConfigRequest) -> Dict[str, Any]:
    """Erstellt Training-Config und Dataset, startet aber NICHT das Training."""
    import json

    # Modellname mit Timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H.%M")
    model_name = request.model_name or f"{request.target_person}_{timestamp}"
    model_dir = Path(settings.finetune_models_dir) / model_name
    model_dir.mkdir(parents=True, exist_ok=True)

    # Erstelle training_config.json
    config = {
        "model_name": settings.vllm_model,
        "adapter_output_dir": str(model_dir / "adapter"),
        "chat_zips": request.chat_zips,
        "target_person": request.target_person,
        "epochs": request.epochs,
        "learning_rate": request.learning_rate,
        "lora_r": request.lora_r,
        "lora_alpha": request.lora_alpha,
        "batch_size": request.batch_size,
        "grad_accum": request.grad_accum,
        "max_seq_length": request.max_seq_length,
        "general_de_ratio": request.general_de_ratio,
        "bf16": request.bf16,
        "status_path": str(model_dir / "training_status.json"),
        "meta_path": str(model_dir / "meta.json"),
    }
    config_path = model_dir / "training_config.json"
    config_path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Meta-Datei
    meta = {
        "name": model_name,
        "target_person": request.target_person,
        "status": "preparing",
        "created": datetime.now().isoformat(),
        "config": config,
    }
    (model_dir / "meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return {
        "success": True,
        "message": f"Training vorbereitet: {model_name}",
        "model_name": model_name,
        "config_path": str(config_path),
    }
