"""
CHAPPiE - Neocortex Agent
=========================
Long-term memory storage and semantic knowledge.

Neuroscience Basis:
- Systems consolidation: Hippocampus -> Neocortex transfer
- Semantic memory storage
- Schema formation and conceptual knowledge
- Soul, User, and Preferences management
"""

import json
import re
from typing import Dict, Any, List
from datetime import datetime

from config.prompts import NEOCORTEX_SYSTEM_PROMPT, NEOCORTEX_USER_PROMPT_TEMPLATE  # from config/prompts.py
from .base_agent import BaseAgent, AgentResult


class NeocortexAgent(BaseAgent):
    """
    Neocortex - Long-Term Memory Storage.
    
    Inspired by the neocortex's role in:
    - Permanent memory storage
    - Semantic knowledge
    - Schema and concept formation
    - Identity and self-model (soul.md)
    """
    
    def __init__(self):
        super().__init__(name="neocortex")
    
    def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Process long-term memory consolidation.
        
        Args:
            input_data: {
                "memories_to_consolidate": List,
                "soul_content": str,
                "user_content": str,
                "preferences_content": str,
                "basal_ganglia_signal": Dict
            }
            
        Returns:
            AgentResult with consolidation decisions
        """
        start_time = datetime.now()
        
        try:
            result = self._consolidate_memories(input_data)
            
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
    
    def _consolidate_memories(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Consolidate memories into long-term storage."""
        
        memories = input_data.get("memories_to_consolidate", [])
        soul_content = input_data.get("soul_content", "")
        user_content = input_data.get("user_content", "")
        preferences_content = input_data.get("preferences_content", "")
        reward_signal = input_data.get("basal_ganglia_signal", {})
        
        if not memories:
            return {
                "consolidated_count": 0,
                "soul_updates": {},
                "user_updates": {},
                "preferences_updates": {},
                "archived_memories": []
            }
        
        memories_str = "\n".join([f"- [{m.get('timestamp', '')}] {m.get('content', '')[:150]}" for m in memories[:10]])
        system_prompt = NEOCORTEX_SYSTEM_PROMPT
        user_prompt = NEOCORTEX_USER_PROMPT_TEMPLATE.format(
            memories=memories_str,
            soul_content=soul_content[:500],
            user_content=user_content[:500],
            preferences_content=preferences_content[:500],
            satisfaction=reward_signal.get('satisfaction_score', 0.5),
            quality=reward_signal.get('interaction_quality', 'neutral'),
        )

        response = self._generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        
        return self._parse_consolidation(response)
    
    def _parse_consolidation(self, response: str) -> Dict[str, Any]:
        """Parse consolidation response."""
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        
        if json_match:
            try:
                data = json.loads(json_match.group())
                return self._validate_consolidation(data)
            except json.JSONDecodeError:
                pass
        
        return self._default_consolidation()
    
    def _validate_consolidation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate consolidation data."""
        data["consolidated_count"] = max(0, data.get("consolidated_count", 0))
        data["confidence"] = max(0.0, min(1.0, data.get("confidence", 0.5)))
        
        if "soul_updates" not in data:
            data["soul_updates"] = {}
        if "user_updates" not in data:
            data["user_updates"] = {}
        if "preferences_updates" not in data:
            data["preferences_updates"] = {}
        if "archived_memories" not in data:
            data["archived_memories"] = []
        
        if "trust_level" in data["soul_updates"]:
            data["soul_updates"]["trust_level"] = max(0, min(100, data["soul_updates"]["trust_level"]))
        
        return data
    
    def _default_consolidation(self) -> Dict[str, Any]:
        """Return default consolidation."""
        return {
            "consolidated_count": 0,
            "soul_updates": {},
            "user_updates": {},
            "preferences_updates": {},
            "archived_memories": [],
            "rationale": "Keine Konsolidierung noetig",
            "confidence": 0.5
        }
