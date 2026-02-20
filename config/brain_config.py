"""
CHAPPiE - Brain Configuration
=============================
Model configuration for all brain agents.

NVIDIA models are prioritized due to higher free tier limits.
"""

from dataclasses import dataclass
from typing import Dict, Optional
from config.config import LLMProvider


@dataclass
class AgentModelConfig:
    """Configuration for a single agent's model."""
    model_id: str
    provider: LLMProvider
    temperature: float = 0.3
    max_tokens: int = 1024
    description: str = ""


BRAIN_AGENT_CONFIGS: Dict[str, AgentModelConfig] = {
    "sensory_cortex": AgentModelConfig(
        model_id="meta/llama-3.3-70b-instruct",
        provider=LLMProvider.NVIDIA,
        temperature=0.1,
        max_tokens=512,
        description="Input classification - fast and accurate"
    ),
    "amygdala": AgentModelConfig(
        model_id="nvidia/llama-3.1-nemotron-70b",
        provider=LLMProvider.NVIDIA,
        temperature=0.2,
        max_tokens=512,
        description="Emotional analysis - nuanced understanding"
    ),
    "hippocampus": AgentModelConfig(
        model_id="nvidia/llama-3.1-nemotron-70b",
        provider=LLMProvider.NVIDIA,
        temperature=0.2,
        max_tokens=768,
        description="Memory operations - careful decision making"
    ),
    "prefrontal_cortex": AgentModelConfig(
        model_id="z-ai/glm5",
        provider=LLMProvider.NVIDIA,
        temperature=0.3,
        max_tokens=1024,
        description="Main orchestration - complex reasoning"
    ),
    "basal_ganglia": AgentModelConfig(
        model_id="meta/llama-3.3-70b-instruct",
        provider=LLMProvider.NVIDIA,
        temperature=0.2,
        max_tokens=512,
        description="Reward evaluation - learning signals"
    ),
    "neocortex": AgentModelConfig(
        model_id="meta/llama-3.3-70b-instruct",
        provider=LLMProvider.NVIDIA,
        temperature=0.2,
        max_tokens=768,
        description="Memory consolidation - long-term storage"
    ),
    "memory_agent": AgentModelConfig(
        model_id="nvidia/llama-3.1-nemotron-70b",
        provider=LLMProvider.NVIDIA,
        temperature=0.2,
        max_tokens=768,
        description="Tool call decisions - context file updates"
    ),
}

NVIDIA_MODEL_CATEGORIES = {
    "flagship_reasoning": [
        ("z-ai/glm5", "GLM 5 - 744B MoE, best for complex reasoning"),
    ],
    "high_quality": [
        ("nvidia/llama-3.1-nemotron-70b", "Nemotron 70B - NVIDIA optimized"),
        ("meta/llama-3.3-70b-instruct", "Llama 3.3 70B - balanced quality"),
        ("deepseek-ai/deepseek-v3.1-terminus", "DeepSeek V3.1 - reasoning focused"),
    ],
    "multimodal": [
        ("moonshotai/kimi-k2.5", "Kimi K2.5 - multimodal understanding"),
        ("nvidia/nemotron-nano-12b-v2-vl", "Nemotron Nano VL - vision-language"),
    ],
    "reasoning": [
        ("deepseek-ai/deepseek-r1", "DeepSeek R1 - chain-of-thought reasoning"),
    ],
}

SLEEP_PHASE_CONFIG = {
    "triggers": {
        "time_based": {
            "enabled": True,
            "interval_hours": 24
        },
        "interaction_based": {
            "enabled": True,
            "interval_interactions": 100
        },
        "idle_based": {
            "enabled": False,
            "idle_minutes": 30
        },
        "manual": {
            "enabled": True,
            "command": "/sleep"
        }
    },
    "consolidation": {
        "min_memory_age_hours": 1,
        "max_consolidation_depth": 1,
        "require_original_interaction": True,
        "batch_size": 50
    }
}

FORGETTING_CURVE_CONFIG = {
    "ebbinghaus": {
        "retention_after_20min": 0.58,
        "retention_after_1h": 0.44,
        "retention_after_1day": 0.33,
        "retention_after_1month": 0.21
    },
    "memory_strength": {
        "initial": 1.0,
        "max": 10.0,
        "boost_per_recall": 0.5,
        "decay_rate": 0.1
    },
    "spaced_repetition": {
        "intervals_hours": [1, 12, 24, 72, 168, 336, 720],
        "min_strength_for_archive": 0.3
    }
}


def get_agent_config(agent_name: str) -> Optional[AgentModelConfig]:
    """Get configuration for a specific agent."""
    return BRAIN_AGENT_CONFIGS.get(agent_name)


def get_all_agent_configs() -> Dict[str, AgentModelConfig]:
    """Get all agent configurations."""
    return BRAIN_AGENT_CONFIGS.copy()


def get_sleep_config() -> Dict:
    """Get sleep phase configuration."""
    return SLEEP_PHASE_CONFIG.copy()


def get_forgetting_curve_config() -> Dict:
    """Get forgetting curve configuration."""
    return FORGETTING_CURVE_CONFIG.copy()
