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

from .base_agent import BaseAgent, AgentResult
from config.config import LLMProvider


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
        super().__init__(
            name="memory_agent",
            model_id="nvidia/llama-3.1-nemotron-70b",
            provider=LLMProvider.NVIDIA
        )
    
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
        
        system_prompt = """DU BIST DER MEMORY AGENT VON CHAPPiE.

Deine Aufgabe: Entscheide, welche Informationen in die Context-Dateien geschrieben werden sollen.

DATEIEN:
1. soul.md - CHAPPiE's Identitaet und Selbstwahrnehmung
   - trust_level (0-100)
   - evolution_note (Wichtiges ueber sich selbst gelernt)
   - new_value (Neue Werte/Ueberzeugungen)

2. user.md - Benutzerprofil
   - name (Falls User Namen nennt)
   - key_moment (Wichtige gemeinsame Momente)
   - learning (Was CHAPPiE ueber User gelernt hat)

3. CHAPPiEsPreferences.md - CHAPPiE's eigene Vorlieben
   - new_preference (Neue Praeferenz)
   - category (My Personality Preferences, Topics I Find Interesting, etc.)
   - reflection (Selbstreflexion)

REGELN:
- Schreibe NUR wenn wirklich neue, wichtige Information
- Vermeide Duplikate
- Persoenliche Infos vom User -> user.md
- CHAPPiE lernt ueber sich selbst -> soul.md
- CHAPPiE entwickelt Meinung -> preferences.md

ANTWORTE NUR MIT JSON:
{
  "tool_calls": [
    {
      "tool": "update_user_profile|update_soul|update_preferences",
      "action": "update",
      "data": {
        "key": "value"
      },
      "priority": "high|medium|low",
      "reason": "Warum diese Aenderung"
    }
  ],
  "soul_updates": {
    "trust_level": int (optional),
    "evolution_note": "text" (optional),
    "new_value": "text" (optional)
  },
  "user_updates": {
    "name": "text" (optional),
    "key_moment": "text" (optional),
    "learning": "text" (optional)
  },
  "preferences_updates": {
    "new_preference": "text" (optional),
    "category": "text" (optional),
    "reflection": "text" (optional)
  },
  "no_update_needed": true|false,
  "rationale": "Erklaerung der Entscheidungen",
  "confidence": 0.0-1.0
}"""

        user_prompt = f"""User Input: {user_input}

CHAPPiE Response: {chappie_response[:300]}

Aktueller Soul Content:
{current_soul[:400]}

Aktueller User Content:
{current_user[:400]}

Aktuelle Preferences:
{current_preferences[:400]}

Emotionale Analyse:
- Primary Emotion: {amygdala.get('primary_emotion', 'neutral')}
- Sentiment: {amygdala.get('sentiment', 'neutral')}
- Personal Relevance: {amygdala.get('personal_relevance', 0.5)}

Memory Analysis:
- Should Encode: {hippocampus.get('should_encode', False)}
- Memory Type: {hippocampus.get('encoding_decision', {}).get('memory_type', 'episodic')}

Reward Signal:
- Satisfaction: {basal_ganglia.get('satisfaction_score', 0.5)}
- Quality: {basal_ganglia.get('interaction_quality', 'neutral')}

Entscheide ueber Tool Calls (NUR JSON):"""

        response = self._generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            max_tokens=768,
            provider_override=LLMProvider.NVIDIA
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
