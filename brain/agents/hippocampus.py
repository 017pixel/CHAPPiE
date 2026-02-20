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

from .base_agent import BaseAgent, AgentResult
from config.config import LLMProvider


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
        super().__init__(
            name="hippocampus",
            model_id="nvidia/llama-3.1-nemotron-70b",
            provider=LLMProvider.NVIDIA
        )
    
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
        
        system_prompt = """DU BIST DER HIPPOCAMPUS VON CHAPPiE.

Deine Aufgabe: Entscheide ueber Memory-Operationen.

MEMORY-TYPEN:
- episodic: Persoenliche Erlebnisse, Gespraeche
- semantic: Faktenwissen, Konzepte
- procedural: Skills, Ablaeufe

ENCODING ENTSCHEIDUNG:
- Soll diese Info gespeichert werden?
- Wie wichtig ist sie? (importance: high/medium/low)
- Welcher Memory-Typ?

QUERY EXTRACTION:
- Optimiere die Suchquery fuer Vektor-Datenbank
- Extrahiere Schluesselkonzepte

ANTWORTE NUR MIT JSON:
{
  "should_encode": true|false,
  "encoding_decision": {
    "importance": "high|medium|low",
    "memory_type": "episodic|semantic|procedural",
    "emotional_boost": 1.0-3.0,
    "content_to_store": "Zusammenzufassender Inhalt",
    "tags": ["tag1", "tag2"]
  },
  "search_query": "Optimierte Suchquery",
  "related_concepts": ["konzept1", "konzept2"],
  "context_relevance": {
    "need_soul_context": true|false,
    "need_user_context": true|false,
    "need_preferences": true|false,
    "need_short_term_memory": true|false,
    "need_long_term_memory": true|false
  },
  "short_term_entries": [
    {
      "content": "Kurzzeit-Info",
      "category": "user|event|topic|technical",
      "importance": "high|medium|low"
    }
  ],
  "confidence": 0.0-1.0
}"""

        emotional_boost = amygdala_result.get("memory_boost_factor", 1.0)
        requires_memory = sensory_result.get("requires_memory_search", True)
        
        user_prompt = f"""User Input: {user_input}

Sensory Klassifikation:
- Input Type: {sensory_result.get('input_type', 'conversation')}
- Requires Memory Search: {requires_memory}

Emotionale Analyse:
- Primary Emotion: {amygdala_result.get('primary_emotion', 'neutral')}
- Emotional Boost Factor: {emotional_boost}
- Personal Relevance: {amygdala_result.get('personal_relevance', 0.5)}

Entscheide ueber Memory-Operationen (NUR JSON):"""

        response = self._generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            max_tokens=768,
            provider_override=LLMProvider.NVIDIA
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
