from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, Depends

from api.dependencies import get_backend
from api.schemas import EmotionLayerUpdate, EmotionStateUpdate, SettingsSnapshot, SettingsUpdate
from config.config import settings

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
        vllm_force_single_model=settings.vllm_force_single_model,
        cerebras_model=settings.cerebras_model,
        intent_provider=_enum_value(settings.intent_provider),
        intent_processor_model_cerebras=settings.intent_processor_model_cerebras,
        intent_processor_model_ollama=settings.intent_processor_model_ollama,
        intent_processor_model_vllm=settings.intent_processor_model_vllm,
        query_extraction_provider=_enum_value(settings.query_extraction_provider),
        query_extraction_ollama_model=settings.query_extraction_ollama_model,
        query_extraction_vllm_model=settings.query_extraction_vllm_model,
        query_extraction_cerebras_model=settings.query_extraction_cerebras_model,
        query_extraction_min_words_for_llm=settings.query_extraction_min_words_for_llm,
        emotion_analysis_model=settings.emotion_analysis_model,
        emotion_analysis_host=settings.emotion_analysis_host,
        embedding_model=settings.embedding_model,
        training_use_global_settings=settings.training_use_global_settings,
        training_chappie_provider=_enum_value(settings.training_chappie_provider),
        training_chappie_model=settings.training_chappie_model,
        training_trainer_provider=_enum_value(settings.training_trainer_provider),
        training_trainer_model=settings.training_trainer_model,
        memory_top_k=settings.memory_top_k,
        memory_min_relevance=settings.memory_min_relevance,
        enable_steering=settings.enable_steering,
        steering_provider=_enum_value(settings.steering_provider),
        steering_model=settings.steering_model,
        temperature=settings.temperature,
        repetition_penalty=settings.repetition_penalty,
        max_tokens=settings.max_tokens,
        chappie_thinking_token_limit=settings.chappie_thinking_token_limit,
        chappie_answer_token_limit=settings.chappie_answer_token_limit,
        chain_of_thought=settings.chain_of_thought,
        enable_two_step_processing=settings.enable_two_step_processing,
        stm_summary_threshold=settings.stm_summary_threshold,
        stm_summary_batch_size=settings.stm_summary_batch_size,
        cerebras_requests_per_minute=settings.cerebras_requests_per_minute,
        cerebras_requests_per_hour=settings.cerebras_requests_per_hour,
        cerebras_requests_per_day=settings.cerebras_requests_per_day,
        cerebras_tokens_per_minute=settings.cerebras_tokens_per_minute,
        cerebras_tokens_per_hour=settings.cerebras_tokens_per_hour,
        cerebras_tokens_per_day=settings.cerebras_tokens_per_day,
    )


@router.get("/settings", response_model=SettingsSnapshot)
def get_settings():
    return _settings_snapshot()


@router.post("/settings", response_model=SettingsSnapshot)
def save_settings(request: SettingsUpdate, backend=Depends(get_backend)):
    payload = request.model_dump(exclude_none=True)
    settings.update_from_ui(**payload)
    backend.apply_runtime_settings(force=True)
    return _settings_snapshot()


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
    emotions = backend._get_emotions_snapshot()
    steering_report = backend.steering_manager.build_debug_report(emotions)
    return {
        "emotions": emotions,
        "steering": steering_report,
    }


@router.post("/emotions/state")
def set_emotion_state(request: EmotionStateUpdate, backend=Depends(get_backend)):
    updates = request.model_dump(exclude_none=True)
    for emotion_name, value in updates.items():
        backend.emotions.set_emotion(emotion_name, value)
    emotions = backend._get_emotions_snapshot()
    steering_report = backend.steering_manager.build_debug_report(emotions)
    return {
        "emotions": emotions,
        "steering": steering_report,
    }
