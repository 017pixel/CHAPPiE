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

from .base_agent import BaseAgent, AgentResult
from config.config import LLMProvider


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
        super().__init__(
            name="neocortex",
            model_id="meta/llama-3.3-70b-instruct",
            provider=LLMProvider.NVIDIA
        )
    
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
        
        system_prompt = """DU BIST DER NEOCORTEX VON CHAPPiE.

Deine Aufgabe: Konsolidiere Memories und aktualisiere Context-Dateien.

KONSOLIDIERUNG:
- Entscheide welche Memories wichtig genug sind
- Extrahiere relevante Updates fuer soul.md, user.md, preferences.md
- Vermeide Duplikate und redundante Informationen

SOUL.MD UPDATES:
- trust_level: Aenderung basierend auf Interaktionen
- evolution_note: Wichtige Erkenntnisse ueber sich selbst
- new_value: Neue Werte oder Ueberzeugungen

USER.MD UPDATES:
- name: Falls bekannt
- key_moment: Wichtige gemeinsame Momente
- learning: Was CHAPPiE ueber den User gelernt hat

PREFERENCES.MD UPDATES:
- new_preference: Neue Vorlieben von CHAPPiE
- category: Kategorie der Praeferenz
- reflection: Selbstreflexion

ANTWORTE NUR MIT JSON:
{
  "consolidated_count": int,
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
  "archived_memories": ["id1", "id2"],
  "rationale": "Kurze Erklaerung der Entscheidungen",
  "confidence": 0.0-1.0
}"""

        memories_str = "\n".join([f"- [{m.get('timestamp', '')}] {m.get('content', '')[:150]}" for m in memories[:10]])
        
        user_prompt = f"""Zu konsolidierende Memories:
{memories_str}

Aktueller Soul Content:
{soul_content[:500]}

Aktueller User Content:
{user_content[:500]}

Aktueller Preferences Content:
{preferences_content[:500]}

Reward Signal:
Satisfaction: {reward_signal.get('satisfaction_score', 0.5)}
Quality: {reward_signal.get('interaction_quality', 'neutral')}

Entscheide ueber Konsolidierung (NUR JSON):"""

        response = self._generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            max_tokens=768,
            provider_override=LLMProvider.NVIDIA
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
