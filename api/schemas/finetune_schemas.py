"""Pydantic schemas for the Fine-Tune API."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class FinetuneModelInfo(BaseModel):
    name: str
    target_person: str
    status: str
    adapter_ready: bool
    created: str
    total_pairs: int
    final_loss: Optional[float] = None
    adapter_path: Optional[str] = None


class TrainingConfigRequest(BaseModel):
    chat_zips: List[str]
    target_person: str
    model_name: Optional[str] = None
    epochs: int = 1
    learning_rate: float = 2e-4
    lora_r: int = 16
    lora_alpha: int = 32
    batch_size: int = 4
    grad_accum: int = 4
    max_seq_length: int = 512
    general_de_ratio: float = 0.15
    bf16: bool = True


class TrainingStatusResponse(BaseModel):
    status: str
    progress_pct: float
    current_step: int
    total_steps: int
    current_loss: Optional[float] = None
    eval_loss: Optional[float] = None
    elapsed_seconds: int
    eta_seconds: int


class ChatScanResult(BaseModel):
    zip_filename: str
    participants: List[str]
    message_count: int


class ActiveAdapterRequest(BaseModel):
    model_name: Optional[str] = None  # None = base model


class ActiveAdapterResponse(BaseModel):
    success: bool
    message: str
    adapter_path: Optional[str] = None
