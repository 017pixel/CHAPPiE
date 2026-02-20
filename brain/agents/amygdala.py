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

from .base_agent import BaseAgent, AgentResult
from config.config import LLMProvider


class AmygdalaAgent(BaseAgent):
    """
    Amygdala - Emotional Processing Center.
    
    Inspired by the amygdala's role in:
    - Emotional valence assessment
    - Memory enhancement for emotional content
    - Trust and social bonding
    """
    
    def __init__(self):
        super().__init__(
            name="amygdala",
            model_id="nvidia/llama-3.1-nemotron-70b",
            provider=LLMProvider.NVIDIA
        )
    
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
        
        system_prompt = """DU BIST DIE AMYGDALA VON CHAPPiE.

Deine Aufgabe: Analysiere die emotionale Valenz und Intensitaet des Inputs.

EMOTIONEN (Skala 0-100):
- joy: Freude, Humor, positive Stimmung
- sadness: Trauer, Melancholie
- anger: AErger, Frustration
- fear: Angst, Sorge
- surprise: Ueberraschung, Neuheit
- trust: Vertrauen, Offenheit
- disgust: Ablehnung, Ekel

MEMORY BOOST:
- Faktor 1.0-3.0 basierend auf emotionaler Intensitaet
- Hohe Emotion = staerkere Speicherung
- Positive Emotionen = staerkere Vertrauensbildung

ANTWORTE NUR MIT JSON:
{
  "primary_emotion": "joy|sadness|anger|fear|surprise|neutral",
  "emotional_intensity": 0.0-1.0,
  "memory_boost_factor": 1.0-3.0,
  "emotional_tags": ["tag1", "tag2"],
  "emotions_update": {
    "happiness": {"delta": -10 bis +10, "reason": "Grund"},
    "trust": {"delta": -10 bis +10, "reason": "Grund"},
    "energy": {"delta": -10 bis +10, "reason": "Grund"},
    "curiosity": {"delta": -10 bis +10, "reason": "Grund"},
    "frustration": {"delta": -10 bis +10, "reason": "Grund"},
    "motivation": {"delta": -10 bis +10, "reason": "Grund"}
  },
  "sentiment": "positive|negative|neutral",
  "personal_relevance": 0.0-1.0,
  "confidence": 0.0-1.0
}"""

        emotions_str = "\n".join([f"- {k}: {v}" for k, v in current_emotions.items()])
        
        user_prompt = f"""User Input: {user_input}

Aktuelle Emotionen:
{emotions_str}

Analysiere die emotionalen Aspekte (NUR JSON):"""

        response = self._generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            max_tokens=512,
            provider_override=LLMProvider.NVIDIA
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
        """Validate and clamp emotion values."""
        data["emotional_intensity"] = max(0.0, min(1.0, data.get("emotional_intensity", 0.5)))
        data["memory_boost_factor"] = max(1.0, min(3.0, data.get("memory_boost_factor", 1.0)))
        data["personal_relevance"] = max(0.0, min(1.0, data.get("personal_relevance", 0.5)))
        data["confidence"] = max(0.0, min(1.0, data.get("confidence", 0.5)))
        
        if "emotions_update" not in data:
            data["emotions_update"] = {}
        
        for emotion in ["happiness", "trust", "energy", "curiosity", "frustration", "motivation"]:
            if emotion not in data["emotions_update"]:
                data["emotions_update"][emotion] = {"delta": 0, "reason": ""}
            else:
                delta = data["emotions_update"][emotion].get("delta", 0)
                data["emotions_update"][emotion]["delta"] = max(-10, min(10, delta))
        
        return data
    
    def _default_emotion_result(self) -> Dict[str, Any]:
        """Return default emotion result."""
        return {
            "primary_emotion": "neutral",
            "emotional_intensity": 0.3,
            "memory_boost_factor": 1.0,
            "emotional_tags": [],
            "emotions_update": {
                "happiness": {"delta": 0, "reason": ""},
                "trust": {"delta": 0, "reason": ""},
                "energy": {"delta": 0, "reason": ""},
                "curiosity": {"delta": 0, "reason": ""},
                "frustration": {"delta": 0, "reason": ""},
                "motivation": {"delta": 0, "reason": ""}
            },
            "sentiment": "neutral",
            "personal_relevance": 0.5,
            "confidence": 0.5
        }
