"""
CHAPPiE - Brain Orchestrator
============================
Central coordinator for all brain agents.

Coordinates the multi-agent cognitive pipeline:
1. Sensory Cortex -> 2. Amygdala + Hippocampus (parallel) -> 3. Prefrontal Cortex -> 4. Response
Background: Basal Ganglia + Neocortex + Memory Agent
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
from dataclasses import dataclass

from config.config import settings
from .base_agent import AgentResult
from .sensory_cortex import SensoryCortexAgent
from .amygdala import AmygdalaAgent
from .hippocampus import HippocampusAgent
from .prefrontal_cortex import PrefrontalCortexAgent
from .basal_ganglia import BasalGangliaAgent
from .neocortex import NeocortexAgent
from .memory_agent import MemoryAgent


@dataclass
class BrainProcessingResult:
    """Complete result from brain processing."""
    response: str
    sensory_result: AgentResult
    amygdala_result: AgentResult
    hippocampus_result: AgentResult
    prefrontal_result: AgentResult
    basal_ganglia_result: Optional[AgentResult]
    neocortex_result: Optional[AgentResult]
    memory_agent_result: Optional[AgentResult]
    total_processing_time_ms: float
    emotions: Dict[str, int]
    tool_calls: List[Dict[str, Any]]


class BrainOrchestrator:
    """
    Central coordinator for the brain-inspired multi-agent system.
    
    Pipeline:
    1. Sensory Cortex: Input classification (fast)
    2. Amygdala + Hippocampus: Parallel emotional and memory processing
    3. Prefrontal Cortex: Orchestration and response strategy
    4. Response Generation: Final output
    Background: Basal Ganglia, Neocortex, Memory Agent
    """
    
    def __init__(self):
        self.sensory_cortex = SensoryCortexAgent()
        self.amygdala = AmygdalaAgent()
        self.hippocampus = HippocampusAgent()
        self.prefrontal_cortex = PrefrontalCortexAgent()
        self.basal_ganglia = BasalGangliaAgent()
        self.neocortex = NeocortexAgent()
        self.memory_agent = MemoryAgent()
        
        self._processing_count = 0
        self._last_sleep_time: Optional[datetime] = None
    
    def process(self, user_input: str, history: List[Dict], 
                current_emotions: Dict[str, int],
                memory_engine=None, context_files=None) -> BrainProcessingResult:
        """
        Process user input through the multi-agent pipeline.
        
        Args:
            user_input: User's input text
            history: Chat history
            current_emotions: Current emotional state
            memory_engine: Memory engine instance
            context_files: Context files manager
            
        Returns:
            BrainProcessingResult with all agent results
        """
        start_time = datetime.now()
        
        input_data = {
            "user_input": user_input,
            "history": history,
            "current_emotions": current_emotions
        }
        
        sensory_result = self.sensory_cortex.process(input_data)
        
        amygdala_input = {
            **input_data,
            "sensory_result": sensory_result.data
        }
        hippocampus_input = {
            **input_data,
            "sensory_result": sensory_result.data,
            "amygdala_result": {}
        }
        
        amygdala_result = self.amygdala.process(amygdala_input)
        
        hippocampus_input["amygdala_result"] = amygdala_result.data
        hippocampus_result = self.hippocampus.process(hippocampus_input)
        
        memories = []
        if memory_engine and hippocampus_result.data.get("search_query"):
            memories = memory_engine.search_memory(
                hippocampus_result.data["search_query"],
                top_k=settings.memory_top_k,
                min_relevance=settings.memory_min_relevance
            )
        
        context = ""
        if context_files:
            context = self._build_context(
                context_files,
                hippocampus_result.data.get("context_relevance", {})
            )
        
        prefrontal_input = {
            **input_data,
            "sensory_result": sensory_result.data,
            "amygdala_result": amygdala_result.data,
            "hippocampus_result": hippocampus_result.data,
            "memories": memories,
            "context": context
        }
        
        prefrontal_result = self.prefrontal_cortex.process(prefrontal_input)
        
        emotions_after = self._apply_emotion_updates(
            current_emotions,
            amygdala_result.data.get("emotions_update", {})
        )
        
        tool_calls = hippocampus_result.data.get("short_term_entries", [])
        
        basal_ganglia_result = None
        neocortex_result = None
        memory_agent_result = None
        
        self._processing_count += 1
        
        total_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return BrainProcessingResult(
            response="",
            sensory_result=sensory_result,
            amygdala_result=amygdala_result,
            hippocampus_result=hippocampus_result,
            prefrontal_result=prefrontal_result,
            basal_ganglia_result=basal_ganglia_result,
            neocortex_result=neocortex_result,
            memory_agent_result=memory_agent_result,
            total_processing_time_ms=total_time,
            emotions=emotions_after,
            tool_calls=tool_calls
        )
    
    def process_background(self, user_input: str, response: str,
                           emotions_before: Dict, emotions_after: Dict,
                           context_files=None) -> Dict[str, AgentResult]:
        """
        Process background tasks after response is sent.
        
        Args:
            user_input: User's input
            response: CHAPPiE's response
            emotions_before: Emotions before processing
            emotions_after: Emotions after processing
            context_files: Context files manager
            
        Returns:
            Dict with background agent results
        """
        results = {}
        
        basal_ganglia_input = {
            "user_input": user_input,
            "response": response,
            "emotions_before": emotions_before,
            "emotions_after": emotions_after
        }
        results["basal_ganglia"] = self.basal_ganglia.process(basal_ganglia_input)
        
        if context_files:
            memory_agent_input = {
                "user_input": user_input,
                "chappie_response": response,
                "current_soul": context_files.get_soul_context(),
                "current_user": context_files.get_user_context(),
                "current_preferences": context_files.get_preferences_context(),
                "basal_ganglia_result": results["basal_ganglia"].data
            }
            results["memory_agent"] = self.memory_agent.process(memory_agent_input)
        
        return results
    
    def _build_context(self, context_files, context_relevance: Dict) -> str:
        """Build context string from context files."""
        parts = []
        
        if context_relevance.get("need_soul_context", True):
            soul = context_files.get_soul_context()
            if soul:
                parts.append(f"=== CHAPPiE'S SOUL ===\n{soul[:500]}")
        
        if context_relevance.get("need_user_context", True):
            user = context_files.get_user_context()
            if user:
                parts.append(f"=== USER PROFILE ===\n{user[:500]}")
        
        if context_relevance.get("need_preferences", False):
            prefs = context_files.get_preferences_context()
            if prefs:
                parts.append(f"=== CHAPPiE'S PREFERENCES ===\n{prefs[:500]}")
        
        return "\n\n".join(parts)
    
    def _apply_emotion_updates(self, emotions: Dict[str, int], 
                                updates: Dict[str, Dict]) -> Dict[str, int]:
        """Apply emotion updates from amygdala."""
        result = emotions.copy()
        
        for emotion, update in updates.items():
            if emotion in result:
                delta = update.get("delta", 0)
                new_value = result[emotion] + delta
                result[emotion] = max(0, min(100, new_value))
        
        return result
    
    def get_processing_count(self) -> int:
        """Return total processing count."""
        return self._processing_count
    
    def should_run_sleep_phase(self, interval_interactions: int = 100) -> bool:
        """Check if sleep phase should run based on interaction count."""
        return self._processing_count > 0 and self._processing_count % interval_interactions == 0


def get_brain_orchestrator() -> BrainOrchestrator:
    """Factory function for BrainOrchestrator singleton."""
    global _brain_orchestrator
    if '_brain_orchestrator' not in globals():
        _brain_orchestrator = BrainOrchestrator()
    return _brain_orchestrator
