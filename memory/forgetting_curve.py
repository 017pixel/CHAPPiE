"""
CHAPPiE - Forgetting Curve Implementation
=========================================
Ebbinghaus forgetting curve for memory management.

Neuroscience Basis:
- Hermann Ebbinghaus (1885) discovered the forgetting curve
- 42% lost after 20 minutes
- 56% lost after 1 hour
- 67% lost after 1 day
- 79% lost after 1 month
- Spaced repetition flattens the curve
"""

import math
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class MemoryStrength:
    """Represents memory strength over time."""
    initial_strength: float = 1.0
    current_strength: float = 1.0
    recall_count: int = 0
    last_recall_time: Optional[datetime] = None
    creation_time: Optional[datetime] = None


class EbbinghausForgettingCurve:
    """
    Implements the Ebbinghaus forgetting curve.
    
    Formula: R = e^(-t/S)
    - R = Retention (0-1)
    - t = Time since learning (hours)
    - S = Strength of memory (reinforced by repetition)
    """
    
    EBBINGHAUS_DATA = {
        "20min": 0.58,
        "1h": 0.44,
        "9h": 0.36,
        "1day": 0.33,
        "2days": 0.28,
        "6days": 0.25,
        "31days": 0.21,
    }
    
    def __init__(self):
        self.decay_constant = 0.3
        self.boost_per_recall = 0.5
        self.max_strength = 10.0
        self.min_retention = 0.1
    
    def calculate_retention(self, time_hours: float, strength: float = 1.0) -> float:
        """
        Calculate retention based on time and memory strength.
        
        Args:
            time_hours: Time since learning in hours
            strength: Memory strength (1.0-10.0)
            
        Returns:
            Retention value (0.0-1.0)
        """
        if time_hours <= 0:
            return 1.0
        
        adjusted_decay = self.decay_constant / max(strength, 0.1)
        retention = math.exp(-adjusted_decay * time_hours)
        
        return max(self.min_retention, min(1.0, retention))
    
    def calculate_strength_boost(self, current_strength: float, 
                                  recall_count: int = 0) -> float:
        """
        Calculate strength boost from recall.
        
        Spaced repetition: Each recall strengthens the memory,
        but with diminishing returns.
        """
        boost = self.boost_per_recall * (0.9 ** recall_count)
        new_strength = current_strength + boost
        return min(self.max_strength, new_strength)
    
    def get_optimal_review_time(self, current_strength: float,
                                 target_retention: float = 0.7) -> float:
        """
        Calculate optimal time for next review.
        
        Args:
            current_strength: Current memory strength
            target_retention: Desired retention level (default 0.7)
            
        Returns:
            Hours until optimal review time
        """
        if current_strength <= 0:
            return 0
        
        adjusted_decay = self.decay_constant / current_strength
        
        if target_retention >= 1.0:
            return 0
        
        time_to_target = -math.log(target_retention) / adjusted_decay
        return max(0, time_to_target)
    
    def calculate_relevance_score(self, memory: Dict[str, Any]) -> float:
        """
        Calculate overall relevance score for a memory.
        
        Combines:
        - Base relevance (from embedding similarity)
        - Retention factor
        - Emotional boost
        - Recall bonus
        """
        base_relevance = memory.get("relevance", 0.5)
        
        created_at = memory.get("created_at")
        if created_at:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            time_hours = (datetime.now() - created_at).total_seconds() / 3600
        else:
            time_hours = 24
        
        strength = memory.get("strength", 1.0)
        retention = self.calculate_retention(time_hours, strength)
        
        emotional_boost = memory.get("emotional_boost", 1.0)
        recall_count = memory.get("recall_count", 0)
        recall_bonus = 1.0 + (recall_count * 0.1)
        
        final_score = base_relevance * retention * emotional_boost * recall_bonus
        
        return min(1.0, final_score)
    
    def get_memories_for_review(self, memories: List[Dict[str, Any]],
                                  target_retention: float = 0.5) -> List[Dict[str, Any]]:
        """
        Get memories that need review based on retention threshold.
        
        Args:
            memories: List of memory dictionaries
            target_retention: Threshold retention level
            
        Returns:
            List of memories needing review, sorted by urgency
        """
        review_candidates = []
        
        for memory in memories:
            score = self.calculate_relevance_score(memory)
            
            if score < target_retention:
                memory["calculated_relevance"] = score
                memory["review_urgency"] = target_retention - score
                review_candidates.append(memory)
        
        review_candidates.sort(key=lambda m: m["review_urgency"], reverse=True)
        
        return review_candidates
    
    def get_spaced_repetition_schedule(self, initial_time: datetime,
                                        strength: float = 1.0) -> List[datetime]:
        """
        Generate spaced repetition schedule.
        
        Based on optimal intervals:
        - 1 hour
        - 12 hours
        - 1 day
        - 3 days
        - 1 week
        - 2 weeks
        - 1 month
        """
        base_intervals = [1, 12, 24, 72, 168, 336, 720]
        
        schedule = []
        for interval_hours in base_intervals:
            adjusted_interval = interval_hours / max(strength, 0.5)
            review_time = initial_time + timedelta(hours=adjusted_interval)
            schedule.append(review_time)
        
        return schedule


class MemoryDecayManager:
    """
    Manages memory decay and archiving based on forgetting curve.
    """
    
    def __init__(self):
        self.forgetting_curve = EbbinghausForgettingCurve()
        self.archive_threshold = 0.1
        self.strength_threshold = 0.3
    
    def process_memories(self, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process memories and determine which to archive.
        
        Returns:
            Dict with active, archive, and update lists
        """
        result = {
            "active": [],
            "archive": [],
            "update": [],
            "stats": {
                "total": len(memories),
                "active_count": 0,
                "archive_count": 0,
                "update_count": 0
            }
        }
        
        for memory in memories:
            relevance = self.forgetting_curve.calculate_relevance_score(memory)
            memory["calculated_relevance"] = relevance
            
            if relevance < self.archive_threshold:
                result["archive"].append(memory)
                result["stats"]["archive_count"] += 1
            else:
                result["active"].append(memory)
                result["stats"]["active_count"] += 1
                
                if relevance < self.strength_threshold:
                    result["update"].append({
                        "memory": memory,
                        "action": "boost_recommended",
                        "relevance": relevance
                    })
                    result["stats"]["update_count"] += 1
        
        return result
    
    def apply_recall_boost(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply recall boost to a memory.
        
        Call this when a memory is retrieved/used.
        """
        current_strength = memory.get("strength", 1.0)
        recall_count = memory.get("recall_count", 0)
        
        new_strength = self.forgetting_curve.calculate_strength_boost(
            current_strength, recall_count
        )
        
        memory["strength"] = new_strength
        memory["recall_count"] = recall_count + 1
        memory["last_recall_time"] = datetime.now().isoformat()
        
        return memory


_forgetting_curve = None
_decay_manager = None


def get_forgetting_curve() -> EbbinghausForgettingCurve:
    """Get EbbinghausForgettingCurve singleton."""
    global _forgetting_curve
    if _forgetting_curve is None:
        _forgetting_curve = EbbinghausForgettingCurve()
    return _forgetting_curve


def get_decay_manager() -> MemoryDecayManager:
    """Get MemoryDecayManager singleton."""
    global _decay_manager
    if _decay_manager is None:
        _decay_manager = MemoryDecayManager()
    return _decay_manager
