"""
CHAPPiE - Prefrontal Cortex Agent
=================================
Central orchestration and working memory.

Neuroscience Basis:
- 6 PFC networks for cognitive control
- Working memory maintains active information
- Executive function for decision making
- Agent coordination and context assembly
"""

import json
import re
from typing import Dict, Any, List
from datetime import datetime

from config.prompts import PREFRONTAL_SYSTEM_PROMPT, PREFRONTAL_USER_PROMPT_TEMPLATE  # from config/prompts.py
from .base_agent import BaseAgent, AgentResult


class PrefrontalCortexAgent(BaseAgent):
    """
    Prefrontal Cortex - Central Orchestrator.
    
    Inspired by the PFC's role in:
    - Working memory (context assembly)
    - Executive function (decision making)
    - Cognitive control (agent coordination)
    - Response strategy selection
    """
    
    def __init__(self):
        super().__init__(name="prefrontal_cortex")
    
    def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Orchestrate response generation.
        
        Args:
            input_data: {
                "user_input": str,
                "sensory_result": Dict,
                "amygdala_result": Dict,
                "hippocampus_result": Dict,
                "memories": List,
                "context": str,
                "current_emotions": Dict
            }
            
        Returns:
            AgentResult with response strategy
        """
        start_time = datetime.now()
        
        try:
            result = self._orchestrate_response(input_data)
            
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
    
    def _orchestrate_response(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrate the response generation."""
        
        user_input = input_data.get("user_input", "")
        sensory = input_data.get("sensory_result", {})
        amygdala = input_data.get("amygdala_result", {})
        hippocampus = input_data.get("hippocampus_result", {})
        memories = input_data.get("memories", [])
        context = input_data.get("context", "")
        emotions = input_data.get("current_emotions", {})
        life_context = input_data.get("life_context", {})
        global_workspace = input_data.get("global_workspace", {})
        
        memories_str = "\n".join([f"- {m.get('content', m)[:100]}" for m in memories[:5]]) if memories else "Keine relevanten Memories"
        system_prompt = PREFRONTAL_SYSTEM_PROMPT
        user_prompt = PREFRONTAL_USER_PROMPT_TEMPLATE.format(
            user_input=user_input,
            input_type=sensory.get('input_type', 'conversation'),
            urgency=sensory.get('urgency', 'medium'),
            primary_emotion=amygdala.get('primary_emotion', 'neutral'),
            emotional_intensity=amygdala.get('emotional_intensity', 0.3),
            sentiment=amygdala.get('sentiment', 'neutral'),
            memories=memories_str,
            context=context[:500] if context else 'Kein Context',
            emotions=json.dumps(emotions, indent=2),
            life_context=json.dumps(life_context, indent=2)[:1200] if life_context else 'Keine Life-Simulation aktiv',
            global_workspace=json.dumps(global_workspace, indent=2)[:1000] if global_workspace else 'Kein Workspace verfuegbar',
        )

        response = self._generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        
        return self._parse_orchestration(response)
    
    def _parse_orchestration(self, response: str) -> Dict[str, Any]:
        """Parse orchestration response."""
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        
        if json_match:
            try:
                data = json.loads(json_match.group())
                return self._validate_orchestration(data)
            except json.JSONDecodeError:
                pass
        
        return self._default_orchestration()
    
    def _validate_orchestration(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate orchestration data."""
        valid_strategies = ["conversational", "informative", "emotional", "technical", "creative"]
        if data.get("response_strategy") not in valid_strategies:
            data["response_strategy"] = "conversational"
        
        valid_tones = ["friendly", "formal", "casual", "enthusiastic", "calm"]
        if data.get("tone") not in valid_tones:
            data["tone"] = "friendly"
        
        data["confidence"] = max(0.0, min(1.0, data.get("confidence", 0.5)))
        valid_modes = ["stabilizing", "explorative", "goal_directed", "supportive"]
        if data.get("planning_mode") not in valid_modes:
            data["planning_mode"] = "goal_directed"
        if not isinstance(data.get("response_actions"), list):
            data["response_actions"] = []
        data.setdefault("life_alignment", "Halte innere Konsistenz zwischen Emotion, Aufmerksamkeit und Antwort.")
        data.setdefault("attention_summary", "Priorisiere den aktuell dominantesten Reiz.")
        
        return data
    
    def _default_orchestration(self) -> Dict[str, Any]:
        """Return default orchestration."""
        return {
            "response_strategy": "conversational",
            "tone": "friendly",
            "key_topics": [],
            "relevant_memories": [],
            "emotional_tone_adjustment": {
                "happiness": 0,
                "trust": 0,
                "empathy": 50
            },
            "context_priorities": {
                "soul": 0.5,
                "user": 0.5,
                "preferences": 0.3,
                "memories": 0.7
            },
            "response_guidance": "Antworte freundlich und hilfsbereit.",
            "confidence": 0.5,
            "planning_mode": "goal_directed",
            "life_alignment": "Stimme Antwort mit Homeostasis und Zielzustand ab.",
            "attention_summary": "Fokus auf aktuelle User-Anfrage und innere Stabilität.",
            "response_actions": ["Antwort klar strukturieren", "Auf innere Konsistenz achten"],
        }
