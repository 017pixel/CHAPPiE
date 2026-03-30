from __future__ import annotations

from fastapi import APIRouter, Depends

from api.dependencies import get_backend
from api.schemas import EmotionLayerUpdate, SettingsSnapshot, SettingsUpdate
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
        groq_model=settings.groq_model,
        cerebras_model=settings.cerebras_model,
        nvidia_model=settings.nvidia_model,
        intent_provider=_enum_value(settings.intent_provider),
        intent_processor_model_groq=settings.intent_processor_model_groq,
        intent_processor_model_cerebras=settings.intent_processor_model_cerebras,
        intent_processor_model_ollama=settings.intent_processor_model_ollama,
        intent_processor_model_vllm=settings.intent_processor_model_vllm,
        intent_processor_model_nvidia=settings.intent_processor_model_nvidia,
        query_extraction_provider=_enum_value(settings.query_extraction_provider),
        query_extraction_groq_model=settings.query_extraction_groq_model,
        query_extraction_ollama_model=settings.query_extraction_ollama_model,
        query_extraction_vllm_model=settings.query_extraction_vllm_model,
        query_extraction_nvidia_model=settings.query_extraction_nvidia_model,
        query_extraction_cerebras_model=settings.query_extraction_cerebras_model,
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
        max_tokens=settings.max_tokens,
        chain_of_thought=settings.chain_of_thought,
        enable_two_step_processing=settings.enable_two_step_processing,
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
