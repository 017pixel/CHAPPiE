"""
CHAPPiE - Hippocampus Agent
===========================
Memory encoding, retrieval, and consolidation.

Neuroscience Basis:
- Episodic memory formation
- Memory retrieval via pattern completion
- Transfer to neocortex during sleep (systems consolidation)
- Query optimization for memory search
"""

import json
import re
from typing import Dict, Any, List
from datetime import datetime

from config.prompts import HIPPOCAMPUS_SYSTEM_PROMPT, HIPPOCAMPUS_USER_PROMPT_TEMPLATE  # from config/prompts.py
from .base_agent import BaseAgent, AgentResult


class HippocampusAgent(BaseAgent):
    """
    Hippocampus - Memory Operations Center.
    
    Inspired by the hippocampus's role in:
    - Episodic memory encoding
    - Memory retrieval and pattern completion
    - Short-term to long-term memory transfer
    - Spatial and contextual memory
    """
    
    def __init__(self):
        super().__init__(name="hippocampus")
    
    def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Process memory operations.
        
        Args:
            input_data: {
                "user_input": str,
                "sensory_result": Dict,
                "amygdala_result": Dict,
                "memory_engine": MemoryEngine (optional)
            }
            
        Returns:
            AgentResult with memory decisions
        """
        start_time = datetime.now()
        user_input = input_data.get("user_input", "")
        sensory_result = input_data.get("sensory_result", {})
        amygdala_result = input_data.get("amygdala_result", {})
        
        try:
            result = self._process_memory_operations(
                user_input, 
                sensory_result, 
                amygdala_result
            )
            
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
    
    def _process_memory_operations(
        self, 
        user_input: str, 
        sensory_result: Dict[str, Any],
        amygdala_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Determine memory operations."""
        
        emotional_boost = amygdala_result.get("memory_boost_factor", 1.0)
        requires_memory = sensory_result.get("requires_memory_search", True)
        system_prompt = HIPPOCAMPUS_SYSTEM_PROMPT
        user_prompt = HIPPOCAMPUS_USER_PROMPT_TEMPLATE.format(
            user_input=user_input,
            input_type=sensory_result.get('input_type', 'conversation'),
            requires_memory=requires_memory,
            primary_emotion=amygdala_result.get('primary_emotion', 'neutral'),
            emotional_boost=emotional_boost,
            personal_relevance=amygdala_result.get('personal_relevance', 0.5),
        )

        response = self._generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        
        return self._parse_memory_response(response, emotional_boost)
    
    def _parse_memory_response(self, response: str, emotional_boost: float) -> Dict[str, Any]:
        """Parse memory operation response."""
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        
        if json_match:
            try:
                data = json.loads(json_match.group())
                return self._validate_memory_data(data, emotional_boost)
            except json.JSONDecodeError:
                pass
        
        return self._default_memory_result(emotional_boost)
    
    def _validate_memory_data(self, data: Dict[str, Any], emotional_boost: float) -> Dict[str, Any]:
        """Validate memory operation data."""
        data["confidence"] = max(0.0, min(1.0, data.get("confidence", 0.5)))
        
        if "encoding_decision" in data:
            data["encoding_decision"]["emotional_boost"] = emotional_boost
        
        if "short_term_entries" not in data:
            data["short_term_entries"] = []
        
        if "context_relevance" not in data:
            data["context_relevance"] = {
                "need_soul_context": True,
                "need_user_context": True,
                "need_preferences": False,
                "need_short_term_memory": True,
                "need_long_term_memory": True
            }
        
        return data
    
    def _default_memory_result(self, emotional_boost: float) -> Dict[str, Any]:
        """Return default memory result."""
        return {
            "should_encode": True,
            "encoding_decision": {
                "importance": "medium",
                "memory_type": "episodic",
                "emotional_boost": emotional_boost,
                "content_to_store": "",
                "tags": []
            },
            "search_query": "",
            "related_concepts": [],
            "context_relevance": {
                "need_soul_context": True,
                "need_user_context": True,
                "need_preferences": False,
                "need_short_term_memory": True,
                "need_long_term_memory": True
            },
            "short_term_entries": [],
            "confidence": 0.5
        }
