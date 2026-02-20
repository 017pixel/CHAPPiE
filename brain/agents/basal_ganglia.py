"""
CHAPPiE - Basal Ganglia Agent
=============================
Reward-based learning and habit formation.

Neuroscience Basis:
- Reward prediction error (dopamine)
- Temporal difference learning
- Habit formation through reinforcement
- Decision value estimation
"""

import json
import re
from typing import Dict, Any
from datetime import datetime

from .base_agent import BaseAgent, AgentResult
from config.config import LLMProvider


class BasalGangliaAgent(BaseAgent):
    """
    Basal Ganglia - Reward and Learning Center.
    
    Inspired by the basal ganglia's role in:
    - Reward prediction and dopamine release
    - Reinforcement learning
    - Habit formation
    - Action selection based on value
    """
    
    def __init__(self):
        super().__init__(
            name="basal_ganglia",
            model_id="meta/llama-3.3-70b-instruct",
            provider=LLMProvider.NVIDIA
        )
        self._interaction_count = 0
        self._reward_history: list = []
    
    def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Process reward signals and learning.
        
        Args:
            input_data: {
                "user_input": str,
                "response": str,
                "user_feedback": str (optional),
                "emotions_before": Dict,
                "emotions_after": Dict
            }
            
        Returns:
            AgentResult with learning signals
        """
        start_time = datetime.now()
        
        try:
            result = self._evaluate_reward(input_data)
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            self._interaction_count += 1
            
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
    
    def _evaluate_reward(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate reward and generate learning signals."""
        
        user_input = input_data.get("user_input", "")
        response = input_data.get("response", "")
        user_feedback = input_data.get("user_feedback", "")
        emotions_before = input_data.get("emotions_before", {})
        emotions_after = input_data.get("emotions_after", {})
        
        system_prompt = """DU BIST DIE BASAL GANGLIA VON CHAPPiE.

Deine Aufgabe: Bewerte die Interaktion und generiere Lernsignale.

REWARD EVALUATION:
- Satisfaction Score: Wie zufrieden war der User?
- Prediction Error: War die Interaktion besser/schlechter als erwartet?
- Learning Signal: Was soll CHAPPiE lernen?

HABIT FORMATION:
- Bei positiver Interaktion: Verstaerke dieses Verhalten
- Bei negativer Interaktion: Reduziere dieses Verhalten

ANTWORTE NUR MIT JSON:
{
  "satisfaction_score": 0.0-1.0,
  "reward_prediction_error": -1.0 bis 1.0,
  "interaction_quality": "excellent|good|neutral|poor|bad",
  "learning_update": {
    "personality_adjustment": {
      "trait": "friendliness|empathy|curiosity|humor|formality",
      "adjustment": -0.1 bis +0.1,
      "reason": "Grund"
    },
    "preference_update": {
      "topic": "Thema",
      "preference_change": "Beschreibung"
    }
  },
  "habit_formation_signal": 0.0-1.0,
  "dopamine_level": 0.0-1.0,
  "confidence": 0.0-1.0
}"""

        emotions_delta = {}
        for key in emotions_before:
            if key in emotions_after:
                emotions_delta[key] = emotions_after[key] - emotions_before.get(key, 0)
        
        user_prompt = f"""User Input: {user_input}

CHAPPiE Response: {response[:300]}

User Feedback: {user_feedback if user_feedback else "Kein explizites Feedback"}

Emotions-Aenderung:
{json.dumps(emotions_delta, indent=2)}

Bewerte die Interaktion (NUR JSON):"""

        response_text = self._generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            max_tokens=512,
            provider_override=LLMProvider.NVIDIA
        )
        
        return self._parse_reward(response_text)
    
    def _parse_reward(self, response: str) -> Dict[str, Any]:
        """Parse reward evaluation."""
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        
        if json_match:
            try:
                data = json.loads(json_match.group())
                return self._validate_reward(data)
            except json.JSONDecodeError:
                pass
        
        return self._default_reward()
    
    def _validate_reward(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate reward data."""
        data["satisfaction_score"] = max(0.0, min(1.0, data.get("satisfaction_score", 0.5)))
        data["reward_prediction_error"] = max(-1.0, min(1.0, data.get("reward_prediction_error", 0.0)))
        data["habit_formation_signal"] = max(0.0, min(1.0, data.get("habit_formation_signal", 0.5)))
        data["dopamine_level"] = max(0.0, min(1.0, data.get("dopamine_level", 0.5)))
        data["confidence"] = max(0.0, min(1.0, data.get("confidence", 0.5)))
        
        return data
    
    def _default_reward(self) -> Dict[str, Any]:
        """Return default reward."""
        return {
            "satisfaction_score": 0.5,
            "reward_prediction_error": 0.0,
            "interaction_quality": "neutral",
            "learning_update": {},
            "habit_formation_signal": 0.5,
            "dopamine_level": 0.5,
            "confidence": 0.5
        }
    
    def get_interaction_count(self) -> int:
        """Return total interaction count."""
        return self._interaction_count
    
    def get_average_satisfaction(self) -> float:
        """Calculate average satisfaction from history."""
        if not self._reward_history:
            return 0.5
        return sum(r.get("satisfaction_score", 0.5) for r in self._reward_history) / len(self._reward_history)
