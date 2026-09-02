"""
CHAPPiE Brain Agents - Multi-Agent Cognitive Architecture
=========================================================

Brain-Inspired Agent System:
- Sensory Cortex: Input processing and classification
- Amygdala: Emotional processing and memory enhancement  
- Hippocampus: Memory encoding and retrieval
- Prefrontal Cortex: Central orchestration and working memory
- Basal Ganglia: Reward-based learning
- Neocortex: Long-term memory storage
- Memory Agent: Tool call decisions for context files
"""

from .base_agent import BaseAgent, AgentResult
from .sensory_cortex import SensoryCortexAgent
from .amygdala import AmygdalaAgent
from .hippocampus import HippocampusAgent
from .prefrontal_cortex import PrefrontalCortexAgent
from .basal_ganglia import BasalGangliaAgent
from .neocortex import NeocortexAgent
from .memory_agent import MemoryAgent
from .orchestrator import BrainOrchestrator

__all__ = [
    "BaseAgent",
    "AgentResult",
    "SensoryCortexAgent",
    "AmygdalaAgent", 
    "HippocampusAgent",
    "PrefrontalCortexAgent",
    "BasalGangliaAgent",
    "NeocortexAgent",
    "MemoryAgent",
    "BrainOrchestrator",
]
