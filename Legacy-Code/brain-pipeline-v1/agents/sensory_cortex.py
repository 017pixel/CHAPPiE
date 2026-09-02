"""
CHAPPiE - Sensory Cortex Agent
==============================
Input processing and classification.
First stage of the cognitive pipeline.

Responsibilities:
- Input classification (text, tool request, memory query)
- Language detection
- Urgency assessment
- Route to appropriate agents
"""

import json
import re
from typing import Dict, Any
from datetime import datetime

from config.prompts import SENSORY_CORTEX_SYSTEM_PROMPT, SENSORY_CORTEX_USER_PROMPT_TEMPLATE  # from config/prompts.py
from .base_agent import BaseAgent, AgentResult


class SensoryCortexAgent(BaseAgent):
    """
    Sensory Cortex - First processing stage.
    
    Inspired by the sensory cortex which processes all incoming stimuli
    before routing to higher cognitive areas.
    """
    
    def __init__(self):
        super().__init__(name="sensory_cortex")
    
    def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Process and classify user input.
        
        Args:
            input_data: {
                "user_input": str,
                "history": List[Dict]
            }
            
        Returns:
            AgentResult with classification data
        """
        start_time = datetime.now()
        user_input = input_data.get("user_input", "")
        history = input_data.get("history", [])
        
        try:
            result = self._classify_input(user_input, history)
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                data=result,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            return AgentResult(
                agent_name=self.name,
                success=False,
                error=str(e)
            )
    
    def _classify_input(self, user_input: str, history: list) -> Dict[str, Any]:
        """Classify the input and determine routing."""
        
        system_prompt = SENSORY_CORTEX_SYSTEM_PROMPT
        user_prompt = SENSORY_CORTEX_USER_PROMPT_TEMPLATE.format(
            user_input=user_input,
            history=self._format_history(history),
        )

        response = self._generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        
        return self._parse_classification(response, user_input)
    
    def _parse_classification(self, response: str, original_input: str) -> Dict[str, Any]:
        """Parse classification response."""
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        
        if json_match:
            try:
                data = json.loads(json_match.group())
                data["original_input"] = original_input
                return data
            except json.JSONDecodeError:
                pass
        
        return {
            "input_type": "conversation",
            "language": "de",
            "urgency": "medium",
            "emotional_content": False,
            "requires_memory_search": True,
            "requires_tools": False,
            "suggested_agents": ["prefrontal"],
            "preprocessed_text": original_input,
            "confidence": 0.5,
            "original_input": original_input
        }
    
    def _format_history(self, history: list, max_messages: int = 3) -> str:
        """Format chat history for prompt."""
        if not history:
            return "Keine vorherigen Nachrichten"
        
        formatted = []
        for msg in history[-max_messages:]:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:100]
            formatted.append(f"{role}: {content}")
        
        return "\n".join(formatted)
