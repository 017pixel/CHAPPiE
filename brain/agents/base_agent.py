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
        self.name = name
        self.model_id = model_id
        self.provider = provider or settings.llm_provider
        self._brain = None
        
    def _get_brain(self, force_provider: Optional[LLMProvider] = None):
        """Get brain instance with optional provider override."""
        if force_provider:
            original = settings.llm_provider
            settings.llm_provider = force_provider
            brain = get_brain()
            settings.llm_provider = original
            return brain
        
        if self._brain is None:
            if self.provider != settings.llm_provider:
                original = settings.llm_provider
                settings.llm_provider = self.provider
                self._brain = get_brain()
                settings.llm_provider = original
            else:
                self._brain = get_brain()
        
        return self._brain
    
    def _generate(
        self, 
        system_prompt: str, 
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
        provider_override: Optional[LLMProvider] = None
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
        brain = self._get_brain(force_provider=provider_override)
        
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt)
        ]
        
        config = GenerationConfig(
            max_tokens=max_tokens,
            temperature=temperature,
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
