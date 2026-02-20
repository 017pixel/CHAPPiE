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

from .base_agent import BaseAgent, AgentResult
from config.config import settings, LLMProvider


class SensoryCortexAgent(BaseAgent):
    """
    Sensory Cortex - First processing stage.
    
    Inspired by the sensory cortex which processes all incoming stimuli
    before routing to higher cognitive areas.
    """
    
    def __init__(self):
        super().__init__(
            name="sensory_cortex",
            model_id="nvidia/llama-3.1-nemotron-70b",
            provider=LLMProvider.NVIDIA
        )
    
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
        
        system_prompt = """DU BIST DER SENSORY CORTEX VON CHAPPiE.

Deine Aufgabe: Klassifiziere den User-Input und entscheide, welche Agenten benoetigt werden.

KATEGORIEN:
- conversation: Normale Konversation, Smalltalk
- information: Informationsanfrage, Wissensfrage  
- emotional: Emotionale Inhalte, persoenliches Teilen
- task: Aufgaben, Anfragen die Tools benoetigen
- memory_query: Frage nach vergangenen Gesprachen/Erinnerungen
- urgent: Dringende Anfrage, needs immediate attention

ROUTING:
- amygdala: Bei emotionalen Inhalten
- hippocampus: Bei Memory-Queries oder wichtigen Infos zum Speichern
- prefrontal: Immer (Hauptverarbeitung)

ANTWORTE NUR MIT JSON:
{
  "input_type": "conversation|information|emotional|task|memory_query|urgent",
  "language": "de|en",
  "urgency": "high|medium|low",
  "emotional_content": true|false,
  "requires_memory_search": true|false,
  "requires_tools": true|false,
  "suggested_agents": ["amygdala", "hippocampus", "prefrontal"],
  "preprocessed_text": "Bereinigter Input",
  "confidence": 0.0-1.0
}"""

        user_prompt = f"""User Input: {user_input}

Letzte Nachrichten (Kontext):
{self._format_history(history)}

Klassifiziere den Input (NUR JSON):"""

        response = self._generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=512,
            provider_override=LLMProvider.NVIDIA
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
