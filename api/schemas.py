from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    ok: bool
    brain_available: bool
    model: str
    provider: str


class StatusResponse(BaseModel):
    brain_available: bool
    model: str
    emotions: Dict[str, int]
    daily_info_count: int
    two_step_enabled: bool
    life_snapshot: Dict[str, Any]
    life_state: Dict[str, Any]


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str = Field(min_length=1)
    debug_mode: bool = False
    command_mode: bool = False
    client_context: Dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    session_id: str
    message_id: str
    user_message: Dict[str, Any]
    assistant_message: Dict[str, Any]
    metadata: Dict[str, Any]
    life_snapshot: Dict[str, Any]
    emotion_snapshot: Dict[str, int]
    debug_entries: List[Dict[str, Any]]
    sleep_status: Dict[str, Any]
    retry_history: List[Dict[str, Any]]


class CommandRequest(BaseModel):
    command: str = Field(min_length=1)
    session_id: Optional[str] = None


class CommandResponse(BaseModel):
    session_id: Optional[str] = None
    output: str
    session: Optional[Dict[str, Any]] = None


class SessionCreateRequest(BaseModel):
    title: Optional[str] = None


class SessionUpdateRequest(BaseModel):
    title: Optional[str] = None
    messages: Optional[List[Dict[str, Any]]] = None


class MemoryRecord(BaseModel):
    id: str
    content: str
    role: str
    timestamp: str
    mem_type: str
    relevance_score: float
    label: str


class EmotionLayerUpdate(BaseModel):
    emotion_name: str
    layer_start: int
    layer_end: int
    default_alpha: float


class TrainingActionRequest(BaseModel):
    action: Literal["start", "stop", "restart", "logs", "clear_logs"]
    focus: Optional[str] = None
    new: bool = False
    lines: int = 200
    config_overrides: Dict[str, Any] = Field(default_factory=dict)


class TrainingActionResponse(BaseModel):
    success: bool
    message: str
    snapshot: Dict[str, Any]
    logs: Optional[str] = None


class SettingsSnapshot(BaseModel):
    llm_provider: str
    ollama_host: str
    ollama_model: str
    vllm_url: str
    vllm_model: str
    vllm_force_single_model: bool
    groq_model: str
    cerebras_model: str
    nvidia_model: str
    intent_provider: Optional[str]
    intent_processor_model_groq: str
    intent_processor_model_cerebras: str
    intent_processor_model_ollama: str
    intent_processor_model_vllm: str
    intent_processor_model_nvidia: str
    query_extraction_provider: Optional[str]
    query_extraction_groq_model: str
    query_extraction_ollama_model: str
    query_extraction_vllm_model: str
    query_extraction_nvidia_model: str
    query_extraction_cerebras_model: str
    emotion_analysis_model: str
    emotion_analysis_host: str
    embedding_model: str
    training_use_global_settings: bool
    training_chappie_provider: Optional[str]
    training_chappie_model: str
    training_trainer_provider: Optional[str]
    training_trainer_model: str
    memory_top_k: int
    memory_min_relevance: float
    enable_steering: bool
    steering_provider: Optional[str]
    steering_model: str
    temperature: float
    max_tokens: int
    chain_of_thought: bool
    enable_two_step_processing: bool


class SettingsUpdate(BaseModel):
    llm_provider: Optional[str] = None
    groq_api_key: Optional[str] = None
    cerebras_api_key: Optional[str] = None
    nvidia_api_key: Optional[str] = None
    groq_model: Optional[str] = None
    cerebras_model: Optional[str] = None
    nvidia_model: Optional[str] = None
    vllm_model: Optional[str] = None
    vllm_url: Optional[str] = None
    vllm_force_single_model: Optional[bool] = None
    ollama_model: Optional[str] = None
    ollama_host: Optional[str] = None
    intent_provider: Optional[str] = None
    intent_processor_model_groq: Optional[str] = None
    intent_processor_model_cerebras: Optional[str] = None
    intent_processor_model_ollama: Optional[str] = None
    intent_processor_model_vllm: Optional[str] = None
    intent_processor_model_nvidia: Optional[str] = None
    query_extraction_provider: Optional[str] = None
    query_extraction_groq_model: Optional[str] = None
    query_extraction_ollama_model: Optional[str] = None
    query_extraction_vllm_model: Optional[str] = None
    query_extraction_nvidia_model: Optional[str] = None
    query_extraction_cerebras_model: Optional[str] = None
    emotion_analysis_model: Optional[str] = None
    emotion_analysis_host: Optional[str] = None
    embedding_model: Optional[str] = None
    training_use_global_settings: Optional[bool] = None
    training_chappie_provider: Optional[str] = None
    training_chappie_model: Optional[str] = None
    training_trainer_provider: Optional[str] = None
    training_trainer_model: Optional[str] = None
    memory_top_k: Optional[int] = None
    memory_min_relevance: Optional[float] = None
    enable_steering: Optional[bool] = None
    steering_provider: Optional[str] = None
    steering_model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    chain_of_thought: Optional[bool] = None
    enable_two_step_processing: Optional[bool] = None
