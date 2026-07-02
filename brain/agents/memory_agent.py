"""
CHAPPiE - Memory Agent
======================
Dedicated agent for tool call decisions.

Separate from the main processing pipeline,
this agent specifically handles decisions about
what should be written to soul.md, user.md, and preferences.md.
"""

import json
import re
from typing import Dict, Any, List
from datetime import datetime

from config.prompts import MEMORY_AGENT_SYSTEM_PROMPT, MEMORY_AGENT_USER_PROMPT_TEMPLATE  # from config/prompts.py
from .base_agent import BaseAgent, AgentResult


class MemoryAgent(BaseAgent):
    """
    Memory Agent - Tool Call Decision Maker.
    
    Specifically handles:
    - Deciding what goes into soul.md
    - Deciding what goes into user.md
    - Deciding what goes into preferences.md
    - Avoiding duplicates and conflicts
    """
    
    def __init__(self):
        super().__init__(name="memory_agent")
    
    def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Analyze and decide on tool calls.
        
        Args:
            input_data: {
                "user_input": str,
                "chappie_response": str,
                "current_soul": str,
                "current_user": str,
                "current_preferences": str,
                "amygdala_result": Dict,
                "hippocampus_result": Dict,
                "basal_ganglia_result": Dict
            }
            
        Returns:
            AgentResult with tool call decisions
        """
        start_time = datetime.now()
        
        try:
            result = self._analyze_tool_calls(input_data)
            
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
    
    def _analyze_tool_calls(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze and generate tool call decisions."""
        
        user_input = input_data.get("user_input", "")
        chappie_response = input_data.get("chappie_response", "")
        current_soul = input_data.get("current_soul", "")
        current_user = input_data.get("current_user", "")
        current_preferences = input_data.get("current_preferences", "")
        amygdala = input_data.get("amygdala_result", {})
        hippocampus = input_data.get("hippocampus_result", {})
        basal_ganglia = input_data.get("basal_ganglia_result", {})
        
        system_prompt = MEMORY_AGENT_SYSTEM_PROMPT
        user_prompt = MEMORY_AGENT_USER_PROMPT_TEMPLATE.format(
            user_input=user_input,
            chappie_response=chappie_response[:300],
            current_soul=current_soul[:400],
            current_user=current_user[:400],
            current_preferences=current_preferences[:400],
            primary_emotion=amygdala.get('primary_emotion', 'neutral'),
            sentiment=amygdala.get('sentiment', 'neutral'),
            personal_relevance=amygdala.get('personal_relevance', 0.5),
            should_encode=hippocampus.get('should_encode', False),
            memory_type=hippocampus.get('encoding_decision', {}).get('memory_type', 'episodic'),
            satisfaction=basal_ganglia.get('satisfaction_score', 0.5),
            quality=basal_ganglia.get('interaction_quality', 'neutral'),
        )

        response = self._generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        
        return self._parse_tool_calls(response)
    
    def _parse_tool_calls(self, response: str) -> Dict[str, Any]:
        """Parse tool call decisions."""
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        
        if json_match:
            try:
                data = json.loads(json_match.group())
                return self._validate_tool_calls(data)
            except json.JSONDecodeError:
                pass
        
        return self._default_tool_calls()
    
    def _validate_tool_calls(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate tool call data."""
        valid_tools = ["update_user_profile", "update_soul", "update_preferences"]
        
        tool_calls = data.get("tool_calls", [])
        validated_calls = []
        
        for tc in tool_calls:
            if tc.get("tool") in valid_tools:
                if "data" not in tc or not isinstance(tc["data"], dict):
                    tc["data"] = {}
                if tc.get("priority") not in ["high", "medium", "low"]:
                    tc["priority"] = "medium"
                if "reason" not in tc:
                    tc["reason"] = ""
                if "action" not in tc:
                    tc["action"] = "update"
                validated_calls.append(tc)
        
        data["tool_calls"] = validated_calls
        data["confidence"] = max(0.0, min(1.0, data.get("confidence", 0.5)))
        
        if "soul_updates" not in data:
            data["soul_updates"] = {}
        if "user_updates" not in data:
            data["user_updates"] = {}
        if "preferences_updates" not in data:
            data["preferences_updates"] = {}
        if "no_update_needed" not in data:
            data["no_update_needed"] = len(validated_calls) == 0
        
        return data
    
    def _default_tool_calls(self) -> Dict[str, Any]:
        """Return default (no updates)."""
        return {
            "tool_calls": [],
            "soul_updates": {},
            "user_updates": {},
            "preferences_updates": {},
            "no_update_needed": True,
            "rationale": "Keine Updates erforderlich",
            "confidence": 0.5
        }
