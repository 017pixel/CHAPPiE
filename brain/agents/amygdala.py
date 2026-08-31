"""
CHAPPiE - Amygdala Agent
========================
Emotional processing and memory enhancement.

Neuroscience Basis:
- Amygdala-Hippocampus interaction enhances emotional memories
- Gamma activity patterns during encoding are reactivated during retrieval
- Emotional intensity affects memory consolidation strength
"""

import json
import re
from typing import Dict, Any
from datetime import datetime

from config.emotions import EMOTION_ORDER, zero_emotion_updates
from config.prompts import AMYGDALA_SYSTEM_PROMPT, AMYGDALA_USER_PROMPT_TEMPLATE  # from config/prompts.py
from .base_agent import BaseAgent, AgentResult


class AmygdalaAgent(BaseAgent):
    """
    Amygdala - Emotional Processing Center.
    
    Inspired by the amygdala's role in:
    - Emotional valence assessment
    - Memory enhancement for emotional content
    - Trust and social bonding
    """
    
    def __init__(self):
        super().__init__(name="amygdala")
    
    def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Process emotional content of input.
        
        Args:
            input_data: {
                "user_input": str,
                "current_emotions": Dict[str, int],
                "sensory_result": Dict (optional)
            }
            
        Returns:
            AgentResult with emotional analysis
        """
        start_time = datetime.now()
        user_input = input_data.get("user_input", "")
        current_emotions = input_data.get("current_emotions", {})
        
        try:
            result = self._analyze_emotions(user_input, current_emotions)
            
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
    
    def _analyze_emotions(self, user_input: str, current_emotions: Dict[str, int]) -> Dict[str, Any]:
        """Analyze emotional content and calculate memory boost."""
        
        emotions_str = "\n".join([f"- {k}: {v}" for k, v in current_emotions.items()])
        system_prompt = AMYGDALA_SYSTEM_PROMPT
        user_prompt = AMYGDALA_USER_PROMPT_TEMPLATE.format(
            user_input=user_input,
            emotions=emotions_str,
        )

        response = self._generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        
        return self._parse_emotional_response(response)
    
    def _parse_emotional_response(self, response: str) -> Dict[str, Any]:
        """Parse emotional analysis response."""
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        
        if json_match:
            try:
                data = json.loads(json_match.group())
                return self._validate_emotion_data(data)
            except json.JSONDecodeError:
                pass
        
        return self._default_emotion_result()
    
    def _validate_emotion_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate, coerce, and clamp model-provided emotion values."""
        if not isinstance(data, dict):
            return self._default_emotion_result()

        def clamped_number(key: str, default: float, lower: float, upper: float) -> float:
            try:
                value = float(data.get(key, default))
            except (TypeError, ValueError):
                value = default
            return max(lower, min(upper, value))

        data["emotional_intensity"] = clamped_number("emotional_intensity", 0.5, 0.0, 1.0)
        data["memory_boost_factor"] = clamped_number("memory_boost_factor", 1.0, 1.0, 3.0)
        data["personal_relevance"] = clamped_number("personal_relevance", 0.5, 0.0, 1.0)
        data["confidence"] = clamped_number("confidence", 0.5, 0.0, 1.0)

        raw_updates = data.get("emotions_update")
        if not isinstance(raw_updates, dict):
            raw_updates = {}
        normalized_updates: Dict[str, Dict[str, Any]] = {}
        for emotion in EMOTION_ORDER:
            entry = raw_updates.get(emotion)
            if not isinstance(entry, dict):
                entry = {}
            try:
                delta = int(round(float(entry.get("delta", 0))))
            except (TypeError, ValueError):
                delta = 0
            normalized_updates[emotion] = {
                **entry,
                "delta": max(-10, min(10, delta)),
                "reason": str(entry.get("reason", "") or ""),
            }
        data["emotions_update"] = normalized_updates
        return data

    def _default_emotion_result(self) -> Dict[str, Any]:
        """Return default emotion result."""
        return {
            "primary_emotion": "neutral",
            "emotional_intensity": 0.3,
            "memory_boost_factor": 1.0,
            "emotional_tags": [],
            "emotions_update": zero_emotion_updates(),
            "steering_hints": {
                "target_emotion": "neutral",
                "alpha": 0.0
            },
            "sentiment": "neutral",
            "personal_relevance": 0.5,
            "confidence": 0.5
        }
