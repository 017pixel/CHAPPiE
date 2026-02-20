"""
CHAPPiE - Brain Processing Integration
======================================
Integration layer between the new brain agent system and the existing backend.

This module provides:
- BrainPipeline: Main processing class that coordinates all agents
- Integration with existing memory and context systems
- Async background processing
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import threading

from brain.agents import (
    SensoryCortexAgent,
    AmygdalaAgent,
    HippocampusAgent,
    PrefrontalCortexAgent,
    BasalGangliaAgent,
    NeocortexAgent,
    MemoryAgent,
)
from brain.agents.base_agent import AgentResult
from memory.sleep_phase import get_sleep_phase_handler
from memory.forgetting_curve import get_forgetting_curve, get_decay_manager
from config.config import settings, LLMProvider


class BrainPipeline:
    """
    Main processing pipeline for the brain-inspired agent system.
    
    Processing Flow:
    1. Sensory Cortex: Input classification
    2. Amygdala + Hippocampus: Parallel processing (emotions + memory)
    3. Prefrontal Cortex: Orchestration and response strategy
    4. Background: Basal Ganglia (reward), Neocortex (consolidation), Memory Agent
    """
    
    def __init__(self):
        self.sensory_cortex = SensoryCortexAgent()
        self.amygdala = AmygdalaAgent()
        self.hippocampus = HippocampusAgent()
        self.prefrontal_cortex = PrefrontalCortexAgent()
        self.basal_ganglia = BasalGangliaAgent()
        self.neocortex = NeocortexAgent()
        self.memory_agent = MemoryAgent()
        
        self.sleep_handler = get_sleep_phase_handler()
        self.forgetting_curve = get_forgetting_curve()
        self.decay_manager = get_decay_manager()
        
        self._processing_count = 0
        self._background_thread: Optional[threading.Thread] = None
    
    def process(
        self,
        user_input: str,
        history: List[Dict],
        current_emotions: Dict[str, int],
        memory_engine=None,
        context_files=None,
        run_background: bool = True
    ) -> Dict[str, Any]:
        """
        Process user input through the multi-agent pipeline.
        
        Args:
            user_input: User's input text
            history: Chat history
            current_emotions: Current emotional state
            memory_engine: Memory engine instance
            context_files: Context files manager
            run_background: Whether to run background processing
            
        Returns:
            Dict with all processing results
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
        amygdala_result = self.amygdala.process(amygdala_input)
        
        hippocampus_input = {
            **input_data,
            "sensory_result": sensory_result.data,
            "amygdala_result": amygdala_result.data
        }
        hippocampus_result = self.hippocampus.process(hippocampus_input)
        
        memories = []
        if memory_engine and hippocampus_result.data.get("search_query"):
            try:
                memories = memory_engine.search_memory(
                    hippocampus_result.data["search_query"],
                    top_k=settings.memory_top_k
                )
            except Exception as e:
                print(f"[BrainPipeline] Memory search error: {e}")
        
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
        
        short_term_entries = hippocampus_result.data.get("short_term_entries", [])
        tool_calls = self._convert_to_tool_calls(short_term_entries)
        
        self._processing_count += 1
        self.sleep_handler.increment_interaction()
        
        total_time = (datetime.now() - start_time).total_seconds() * 1000
        
        result = {
            "success": True,
            "sensory": sensory_result,
            "amygdala": amygdala_result,
            "hippocampus": hippocampus_result,
            "prefrontal": prefrontal_result,
            "emotions_after": emotions_after,
            "tool_calls": tool_calls,
            "memories_found": len(memories),
            "processing_time_ms": total_time,
            "processing_count": self._processing_count,
        }
        
        if run_background:
            self._start_background_processing(
                user_input=user_input,
                response="",  # Will be filled by main response
                emotions_before=current_emotions,
                emotions_after=emotions_after,
                context_files=context_files,
                amygdala_result=amygdala_result,
                hippocampus_result=hippocampus_result,
                prefrontal_result=prefrontal_result
            )
        
        return result
    
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
    
    def _apply_emotion_updates(
        self, 
        emotions: Dict[str, int], 
        updates: Dict[str, Dict]
    ) -> Dict[str, int]:
        """Apply emotion updates from amygdala."""
        result = emotions.copy()
        
        for emotion, update in updates.items():
            if emotion in result:
                delta = update.get("delta", 0)
                new_value = result[emotion] + delta
                result[emotion] = max(0, min(100, new_value))
        
        return result
    
    def _convert_to_tool_calls(self, entries: List[Dict]) -> List[Dict]:
        """Convert short term entries to tool call format."""
        tool_calls = []
        for entry in entries:
            tool_calls.append({
                "tool": "add_short_term_memory",
                "action": "add",
                "data": {
                    "content": entry.get("content", ""),
                    "category": entry.get("category", "general"),
                    "importance": entry.get("importance", "normal")
                },
                "priority": "medium" if entry.get("importance") == "normal" else "high",
                "reason": "Processed by Hippocampus Agent"
            })
        return tool_calls
    
    def _start_background_processing(
        self,
        user_input: str,
        response: str,
        emotions_before: Dict,
        emotions_after: Dict,
        context_files=None,
        **kwargs
    ):
        """Start background processing in a separate thread."""
        def background_task():
            try:
                basal_input = {
                    "user_input": user_input,
                    "response": response,
                    "emotions_before": emotions_before,
                    "emotions_after": emotions_after
                }
                self.basal_ganglia.process(basal_input)
                
                if context_files:
                    memory_input = {
                        "user_input": user_input,
                        "chappie_response": response,
                        "current_soul": context_files.get_soul_context(),
                        "current_user": context_files.get_user_context(),
                        "current_preferences": context_files.get_preferences_context(),
                        "amygdala_result": kwargs.get("amygdala_result", AgentResult("", True)).data,
                        "hippocampus_result": kwargs.get("hippocampus_result", AgentResult("", True)).data,
                        "basal_ganglia_result": {}
                    }
                    self.memory_agent.process(memory_input)
                
                if self.sleep_handler.should_run_sleep():
                    self.sleep_handler.execute_sleep_phase()
                    
            except Exception as e:
                print(f"[BrainPipeline] Background processing error: {e}")
        
        thread = threading.Thread(target=background_task, daemon=True)
        thread.start()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current pipeline status."""
        return {
            "processing_count": self._processing_count,
            "sleep_status": self.sleep_handler.get_status(),
            "provider": settings.llm_provider.value,
            "model": settings.nvidia_model if settings.llm_provider == LLMProvider.NVIDIA else "unknown"
        }


_brain_pipeline = None
_brain_pipeline_lock = threading.Lock()


def get_brain_pipeline() -> BrainPipeline:
    """Get BrainPipeline singleton instance."""
    global _brain_pipeline
    with _brain_pipeline_lock:
        if _brain_pipeline is None:
            _brain_pipeline = BrainPipeline()
        return _brain_pipeline
