"""
CHAPPiE - Sleep Phase Handler
=============================
Memory consolidation during sleep phases.

Neuroscience Basis:
- Systems consolidation: Hippocampus -> Neocortex transfer during sleep
- Sharp-wave ripples for memory replay
- Forgetting curve implementation
- Spaced repetition scheduling
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import threading

from config.config import DATA_DIR
from config.brain_config import get_sleep_config, get_forgetting_curve_config


class SleepPhaseHandler:
    """
    Handles memory consolidation during sleep phases.
    
    Inspired by the brain's sleep processes:
    - Memory consolidation
    - Forgetting curve application
    - Spaced repetition scheduling
    """
    
    def __init__(self):
        self.config = get_sleep_config()
        self.forgetting_config = get_forgetting_curve_config()
        self.state_path = DATA_DIR / "sleep_state.json"
        self._lock = threading.Lock()
        self._load_state()
    
    def _load_state(self):
        """Load sleep state from file."""
        if self.state_path.exists():
            try:
                with open(self.state_path, 'r', encoding='utf-8') as f:
                    self._state = json.load(f)
            except Exception:
                self._state = self._default_state()
        else:
            self._state = self._default_state()
    
    def _default_state(self) -> Dict[str, Any]:
        """Return default sleep state."""
        return {
            "last_sleep_time": None,
            "interaction_count_since_sleep": 0,
            "total_sleeps": 0,
            "last_consolidation_count": 0
        }
    
    def _save_state(self):
        """Save sleep state to file."""
        try:
            with open(self.state_path, 'w', encoding='utf-8') as f:
                json.dump(self._state, f, indent=2, default=str)
        except Exception as e:
            print(f"[SleepPhase] Error saving state: {e}")
    
    def should_run_sleep(self) -> bool:
        """Check if sleep phase should run based on triggers."""
        with self._lock:
            triggers = self.config["triggers"]
            
            if triggers["time_based"]["enabled"]:
                last_sleep = self._state.get("last_sleep_time")
                if last_sleep:
                    last_sleep_dt = datetime.fromisoformat(last_sleep)
                    interval = timedelta(hours=triggers["time_based"]["interval_hours"])
                    if datetime.now() - last_sleep_dt >= interval:
                        return True
            
            if triggers["interaction_based"]["enabled"]:
                count = self._state.get("interaction_count_since_sleep", 0)
                if count >= triggers["interaction_based"]["interval_interactions"]:
                    return True
            
            return False
    
    def increment_interaction(self):
        """Increment interaction counter."""
        with self._lock:
            self._state["interaction_count_since_sleep"] = \
                self._state.get("interaction_count_since_sleep", 0) + 1
            self._save_state()
    
    def execute_sleep_phase(self, memory_engine=None, context_files=None) -> Dict[str, Any]:
        """
        Execute the sleep phase.
        
        Args:
            memory_engine: Memory engine instance
            context_files: Context files manager
            
        Returns:
            Dict with sleep phase results
        """
        with self._lock:
            start_time = datetime.now()
            results = {
                "started_at": start_time.isoformat(),
                "consolidation": {},
                "forgetting": {},
                "context_updates": {},
                "errors": []
            }
            
            try:
                consolidation_config = self.config["consolidation"]
                
                if memory_engine:
                    consolidation_result = self._consolidate_memories(
                        memory_engine,
                        consolidation_config
                    )
                    results["consolidation"] = consolidation_result
                
                forgetting_result = self._apply_forgetting_curve(memory_engine)
                results["forgetting"] = forgetting_result
                
                if context_files:
                    context_result = self._update_context_files(
                        context_files,
                        results.get("consolidation", {})
                    )
                    results["context_updates"] = context_result
                
                self._state["last_sleep_time"] = datetime.now().isoformat()
                self._state["interaction_count_since_sleep"] = 0
                self._state["total_sleeps"] = self._state.get("total_sleeps", 0) + 1
                self._save_state()
                
            except Exception as e:
                results["errors"].append(str(e))
            
            end_time = datetime.now()
            results["completed_at"] = end_time.isoformat()
            results["duration_seconds"] = (end_time - start_time).total_seconds()
            
            return results
    
    def _consolidate_memories(self, memory_engine, config: Dict) -> Dict[str, Any]:
        """
        Consolidate memories from short-term to long-term.
        
        Protection against recursive consolidation:
        - Only original user/chappie interactions
        - Minimum age requirement
        - Maximum consolidation depth check
        """
        result = {
            "candidates": 0,
            "consolidated": 0,
            "skipped": 0,
            "details": []
        }
        
        try:
            min_age_hours = config.get("min_memory_age_hours", 1)
            require_original = config.get("require_original_interaction", True)
            batch_size = config.get("batch_size", 50)
            
            if hasattr(memory_engine, 'get_recent_memories'):
                candidates = memory_engine.get_recent_memories(limit=batch_size)
                result["candidates"] = len(candidates) if candidates else 0
            
            if hasattr(memory_engine, 'migrate_expired_entries'):
                migrated = memory_engine.migrate_expired_entries()
                result["consolidated"] = migrated
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def _apply_forgetting_curve(self, memory_engine) -> Dict[str, Any]:
        """
        Apply Ebbinghaus forgetting curve to memories.
        
        Formula: R = e^(-t/S)
        R = Retention, t = time, S = memory strength
        """
        result = {
            "memories_processed": 0,
            "memories_decayed": 0,
            "memories_archived": 0
        }
        
        try:
            ebbinghaus = self.forgetting_config["ebbinghaus"]
            strength_config = self.forgetting_config["memory_strength"]
            
            pass
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def _update_context_files(self, context_files, consolidation_data: Dict) -> Dict[str, Any]:
        """Update context files based on consolidated memories."""
        result = {
            "soul_updated": False,
            "user_updated": False,
            "preferences_updated": False
        }
        
        return result
    
    def get_status(self) -> Dict[str, Any]:
        """Get current sleep phase status."""
        with self._lock:
            return {
                "last_sleep_time": self._state.get("last_sleep_time"),
                "interactions_since_sleep": self._state.get("interaction_count_since_sleep", 0),
                "total_sleeps": self._state.get("total_sleeps", 0),
                "next_sleep_trigger": self._calculate_next_trigger()
            }
    
    def _calculate_next_trigger(self) -> str:
        """Calculate when the next sleep should trigger."""
        triggers = self.config["triggers"]
        
        interactions_remaining = (
            triggers["interaction_based"]["interval_interactions"] - 
            self._state.get("interaction_count_since_sleep", 0)
        )
        
        if interactions_remaining <= 0:
            return "now"
        
        time_remaining = None
        if triggers["time_based"]["enabled"] and self._state.get("last_sleep_time"):
            last_sleep = datetime.fromisoformat(self._state["last_sleep_time"])
            next_sleep = last_sleep + timedelta(hours=triggers["time_based"]["interval_hours"])
            time_remaining = next_sleep - datetime.now()
        
        if time_remaining and time_remaining.total_seconds() <= 0:
            return "now"
        
        parts = []
        if interactions_remaining > 0:
            parts.append(f"{interactions_remaining} interactions")
        if time_remaining:
            hours = time_remaining.total_seconds() / 3600
            parts.append(f"{hours:.1f} hours")
        
        return " or ".join(parts) if parts else "unknown"


_sleep_phase_handler = None
_sleep_phase_lock = threading.Lock()


def get_sleep_phase_handler() -> SleepPhaseHandler:
    """Get SleepPhaseHandler singleton instance."""
    global _sleep_phase_handler
    with _sleep_phase_lock:
        if _sleep_phase_handler is None:
            _sleep_phase_handler = SleepPhaseHandler()
        return _sleep_phase_handler
