"""
CHAPPiE - Base Agent Class
==========================
Abstract base class for all brain agents.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime

from config.config import settings, LLMProvider
from config.brain_config import get_agent_config
from brain import get_brain
from brain.base_brain import GenerationConfig, Message


@dataclass
class AgentResult:
    """Result from an agent's processing."""
    agent_name: str
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    processing_time_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class BaseAgent(ABC):
    """
    Abstract base class for all brain agents.
    
    Each agent represents a cognitive function inspired by brain regions.
    """
    
    def __init__(self, name: str, model_id: Optional[str] = None, provider: Optional[LLMProvider] = None):
        """
        Initialize the agent.
        
        Args:
            name: Agent name (e.g., "sensory_cortex")
            model_id: Specific model to use (optional)
            provider: LLM provider to use (optional, defaults to main provider)
        """
        agent_config = get_agent_config(name)

        self.name = name
        self.model_id = model_id or (agent_config.model_id if agent_config else None)
        self.provider = provider or (agent_config.provider if agent_config else settings.llm_provider)
        self.default_temperature = agent_config.temperature if agent_config else 0.3
        self.default_max_tokens = agent_config.max_tokens if agent_config else 1024
        self._brain_cache: Dict[tuple[str, str], Any] = {}
        
    def _get_brain(
        self,
        force_provider: Optional[LLMProvider] = None,
        force_model: Optional[str] = None,
    ):
        """Get brain instance with optional provider/model override."""
        effective_provider = force_provider or self.provider or settings.llm_provider
        effective_model = force_model or self.model_id

        cache_key = (effective_provider.value, effective_model or "")
        if cache_key not in self._brain_cache:
            self._brain_cache[cache_key] = get_brain(
                provider=effective_provider,
                model=effective_model,
            )

        return self._brain_cache[cache_key]
    
    def _generate(
        self, 
        system_prompt: str, 
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        provider_override: Optional[LLMProvider] = None,
        model_override: Optional[str] = None,
    ) -> str:
        """
        Generate response from LLM.
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            temperature: Generation temperature
            max_tokens: Max tokens to generate
            provider_override: Override provider for this call
            
        Returns:
            Generated text
        """
        brain = self._get_brain(
            force_provider=provider_override,
            force_model=model_override,
        )
        
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt)
        ]
        
        config = GenerationConfig(
            max_tokens=max_tokens if max_tokens is not None else self.default_max_tokens,
            temperature=temperature if temperature is not None else self.default_temperature,
            stream=False
        )
        
        try:
            response = brain.generate(messages, config)
            if isinstance(response, str):
                return response
            return "".join(list(response))
        except Exception as e:
            return f"ERROR: {str(e)}"
    
    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Process input data and return result.
        
        Args:
            input_data: Input data dictionary
            
        Returns:
            AgentResult with processing output
        """
        pass
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name='{self.name}'>"
