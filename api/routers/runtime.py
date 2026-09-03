from __future__ import annotations

import json
from typing import Any, Dict
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_backend
from api.schemas import EmotionLayerUpdate, EmotionStateUpdate, SettingsSnapshot, SettingsUpdate
from config.config import settings
from config.emotions import emotion_metadata

router = APIRouter(tags=["runtime"])


def _enum_value(value):
    return value.value if value is not None else None


def _settings_snapshot() -> SettingsSnapshot:
    return SettingsSnapshot(
        llm_provider=settings.llm_provider.value,
        ollama_host=settings.ollama_host,
        ollama_model=settings.ollama_model,
        vllm_url=settings.vllm_url,
        vllm_model=settings.vllm_model,
        gemma4_model=settings.gemma4_model,
        gemma4_steering_model=settings.gemma4_steering_model,
        vllm_force_single_model=settings.vllm_force_single_model,
        groq_model=settings.groq_model,
        groq_format_model=settings.groq_format_model,
        groq_memory_model=settings.groq_memory_model,
        groq_auxiliary_enabled=settings.groq_auxiliary_enabled,
        groq_format_timeout_seconds=settings.groq_format_timeout_seconds,
        intent_provider=_enum_value(settings.intent_provider),
        intent_processor_model_groq=settings.intent_processor_model_groq,
        intent_processor_model_ollama=settings.intent_processor_model_ollama,
        intent_processor_model_vllm=settings.intent_processor_model_vllm,
        query_extraction_provider=_enum_value(settings.query_extraction_provider),
        query_extraction_ollama_model=settings.query_extraction_ollama_model,
        query_extraction_vllm_model=settings.query_extraction_vllm_model,
        query_extraction_groq_model=settings.query_extraction_groq_model,
        query_extraction_min_words_for_llm=settings.query_extraction_min_words_for_llm,
        emotion_analysis_model=settings.emotion_analysis_model,
        emotion_analysis_host=settings.emotion_analysis_host,
        emotion_analysis_provider=_enum_value(settings.emotion_analysis_provider),
        emotion_analysis_timeout_seconds=settings.emotion_analysis_timeout_seconds,
        embedding_model=settings.embedding_model,
        training_use_global_settings=settings.training_use_global_settings,
        training_chappie_provider=_enum_value(settings.training_chappie_provider),
        training_chappie_model=settings.training_chappie_model,
        training_trainer_provider=_enum_value(settings.training_trainer_provider),
        training_trainer_model=settings.training_trainer_model,
        memory_top_k=settings.memory_top_k,
        memory_min_relevance=settings.memory_min_relevance,
        memory_consolidation_enabled=settings.memory_consolidation_enabled,
        memory_consolidation_max_tokens=settings.memory_consolidation_max_tokens,
        enable_steering=settings.enable_steering,
        steering_provider=_enum_value(settings.steering_provider),
        steering_model=settings.steering_model,
        steering_quantize=settings.steering_quantize,
        steering_context_length=settings.steering_context_length,
        use_model_defaults=settings.use_model_defaults,
        temperature=settings.temperature,
        top_p=settings.top_p,
        top_k=settings.top_k,
        repetition_penalty=settings.repetition_penalty,
        max_tokens=settings.max_tokens,
        chappie_thinking_token_limit=settings.chappie_thinking_token_limit,
        chappie_answer_token_limit=settings.chappie_answer_token_limit,
        chain_of_thought=settings.chain_of_thought,
        history_max_messages=settings.history_max_messages,
        context_token_limit=settings.context_token_limit,
        context_token_warning_threshold=settings.context_token_warning_threshold,
        enable_two_step_processing=settings.enable_two_step_processing,
        stm_summary_threshold=settings.stm_summary_threshold,
        stm_summary_batch_size=settings.stm_summary_batch_size,
        groq_requests_per_minute=settings.groq_requests_per_minute,
        groq_requests_per_hour=settings.groq_requests_per_hour,
        groq_requests_per_day=settings.groq_requests_per_day,
        groq_tokens_per_minute=settings.groq_tokens_per_minute,
        groq_tokens_per_hour=settings.groq_tokens_per_hour,
        groq_tokens_per_day=settings.groq_tokens_per_day,
    )


def _steering_base_url() -> str:
    return str(settings.vllm_url or "http://127.0.0.1:8000/v1").replace("/v1", "").rstrip("/")


def _proxy_steering_request(method: str, path: str, payload: Dict[str, Any] | None = None, timeout: int = 15) -> Dict[str, Any]:
    url = f"{_steering_base_url()}{path}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = UrlRequest(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"} if payload is not None else {},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8") or str(exc)
        raise HTTPException(status_code=exc.code, detail=detail) from exc
    except TimeoutError as exc:
        if method == "GET" and path.endswith("/restart-status"):
            return {
                "status": "loading",
                "progress": 25,
                "current_step": "Steering Server laedt Modell...",
                "estimated_remaining": 60,
                "error": "",
            }
        raise HTTPException(status_code=504, detail="Steering Server Timeout") from exc
    except URLError as exc:
        raise HTTPException(status_code=502, detail=f"Steering Server nicht erreichbar: {exc.reason}") from exc
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


@router.get("/settings", response_model=SettingsSnapshot)
def get_settings():
    return _settings_snapshot()


@router.post("/settings", response_model=SettingsSnapshot)
def save_settings(request: SettingsUpdate, backend=Depends(get_backend)):
    payload = request.model_dump(exclude_none=True)
    settings.update_from_ui(**payload)
    backend.apply_runtime_settings(force=True)
    return _settings_snapshot()


@router.post("/v1/steering/restart")
def restart_steering(payload: Dict[str, Any]):
    return _proxy_steering_request("POST", "/v1/steering/restart", payload, timeout=20)


@router.get("/v1/steering/restart-status")
def steering_restart_status():
    return _proxy_steering_request("GET", "/v1/steering/restart-status", timeout=5)


@router.get("/emotion-layer-config")
def get_emotion_layer_config(backend=Depends(get_backend)):
    return backend.get_emotion_layer_config()


@router.post("/emotion-layer-config")
def update_emotion_layer_config(request: EmotionLayerUpdate, backend=Depends(get_backend)):
    backend.update_emotion_layer_config(
        request.emotion_name,
        request.layer_start,
        request.layer_end,
        request.default_alpha,
    )
    return backend.get_emotion_layer_config()


@router.get("/emotions/state")
def get_emotion_state(backend=Depends(get_backend)):
    emotions = backend.get_emotions_snapshot()
    steering_report = backend.steering_manager.build_debug_report(emotions)
    return {
        "emotions": emotions,
        "steering": steering_report,
    }


@router.get("/emotions/metadata")
def get_emotion_metadata():
    return {"emotions": emotion_metadata()}


@router.post("/emotions/state")
def set_emotion_state(request: EmotionStateUpdate, backend=Depends(get_backend)):
    updates = request.model_dump(exclude_none=True)
    for emotion_name, value in updates.items():
        backend.emotions.set_emotion(emotion_name, value)
    emotions = backend.get_emotions_snapshot()
    steering_report = backend.steering_manager.build_debug_report(emotions)
    return {
        "emotions": emotions,
        "steering": steering_report,
    }


@router.post("/emotions/reset")
def reset_emotion_state(backend=Depends(get_backend)):
    backend.emotions.reset()
    emotions = backend.get_emotions_snapshot()
    steering_report = backend.steering_manager.build_debug_report(emotions)
    return {
        "emotions": emotions,
        "steering": steering_report,
    }
