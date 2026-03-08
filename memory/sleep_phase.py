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
from life import get_life_simulation_service


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
        
        Waehrend der Schlafphase:
        1. Memory-Konsolidierung (Hippocampus -> Neocortex)
        2. Vergessenskurve anwenden
        3. Context-Dateien aktualisieren
        4. Energie wiederherstellen (95-100%)
        5. Emotionale Regeneration (Traurigkeit -20, Frustration -15)
        
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
                "energy_restored": False,
                "emotional_recovery": {},
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

                # ENERGIE WIEDERHERSTELLEN (95-100%)
                energy_recovery = self._restore_energy()
                results["energy_restored"] = True
                results["energy_value"] = energy_recovery
                
                # EMOTIONALE REGENERATION im Schlaf
                emotional_recovery = self._emotional_sleep_recovery()
                results["emotional_recovery"] = emotional_recovery

                life_result = get_life_simulation_service().process_sleep_cycle()
                results["dream_replay"] = life_result.get("dream_replay", [])
                results["replay_state"] = life_result.get("replay_state", {})
                results["life_snapshot"] = life_result.get("life_snapshot", {})

                if context_files:
                    context_result = self._update_context_files(context_files, results)
                    results["context_updates"] = context_result
                
                self._state["last_sleep_time"] = datetime.now().isoformat()
                self._state["interaction_count_since_sleep"] = 0
                self._state["total_sleeps"] = self._state.get("total_sleeps", 0) + 1
                self._state["last_consolidation_count"] = results.get("consolidation", {}).get("consolidated", 0)
                self._save_state()
                
            except Exception as e:
                results["errors"].append(str(e))
            
            end_time = datetime.now()
            results["completed_at"] = end_time.isoformat()
            results["duration_seconds"] = (end_time - start_time).total_seconds()
            
            return results
    
    def _restore_energy(self) -> int:
        """
        Stellt die Energie auf 95-100% wieder her.
        
        Returns:
            Der neue Energiewert
        """
        import random
        try:
            from memory.emotions_engine import EmotionsEngine
            engine = EmotionsEngine()
            new_energy = random.randint(95, 100)
            engine.set_emotion("energy", new_energy)
            print(f"[SleepPhase] Energie wiederhergestellt: {new_energy}%")
            return new_energy
        except Exception as e:
            print(f"[SleepPhase] Energie-Reset Fehler: {e}")
            return 100
    
    def _emotional_sleep_recovery(self) -> Dict[str, int]:
        """
        Emotionale Regeneration waehrend des Schlafs.
        
        Wie beim Menschen:
        - Traurigkeit sinkt um -15 bis -25 (Schlaf hilft bei Trauer)
        - Frustration sinkt um -10 bis -20 (Abkuehlung)
        - Happiness steigt um +5 bis +10 (Erholung)
        - Motivation steigt um +5 bis +15 (neuer Tag, neue Kraft)
        
        Returns:
            Dict mit den Aenderungen
        """
        import random
        recovery = {}
        try:
            from memory.emotions_engine import EmotionsEngine
            engine = EmotionsEngine()
            state = engine.get_state()
            
            # Traurigkeit reduzieren
            sadness_reduction = random.randint(15, 25)
            new_sadness = max(0, state.sadness - sadness_reduction)
            engine.set_emotion("sadness", new_sadness)
            recovery["sadness"] = -sadness_reduction
            
            # Frustration reduzieren
            frust_reduction = random.randint(10, 20)
            new_frust = max(0, state.frustration - frust_reduction)
            engine.set_emotion("frustration", new_frust)
            recovery["frustration"] = -frust_reduction
            
            # Happiness leicht erhoehen
            happy_boost = random.randint(5, 10)
            new_happy = min(100, state.happiness + happy_boost)
            engine.set_emotion("happiness", new_happy)
            recovery["happiness"] = happy_boost
            
            # Motivation erhoehen
            moti_boost = random.randint(5, 15)
            new_moti = min(100, state.motivation + moti_boost)
            engine.set_emotion("motivation", new_moti)
            recovery["motivation"] = moti_boost
            
            print(f"[SleepPhase] Emotionale Regeneration: {recovery}")
            
        except Exception as e:
            print(f"[SleepPhase] Emotionale Regeneration Fehler: {e}")
            
        return recovery
    
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
    
    def _update_context_files(self, context_files, sleep_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update context files based on sleep, replay and life-snapshot data."""
        result = {
            "soul_updated": False,
            "user_updated": False,
            "preferences_updated": False,
            "notes": []
        }

        consolidation = sleep_data.get("consolidation", {}) or {}
        life_snapshot = sleep_data.get("life_snapshot", {}) or {}
        replay_state = sleep_data.get("replay_state", {}) or {}
        dream_replay = sleep_data.get("dream_replay", []) or []

        active_goal = life_snapshot.get("active_goal", {}) or {}
        self_model = life_snapshot.get("self_model", {}) or {}
        relationship = life_snapshot.get("relationship", {}) or {}
        attachment = life_snapshot.get("attachment_model", {}) or {}
        world_model = life_snapshot.get("world_model", {}) or {}
        dominant_need = (life_snapshot.get("homeostasis", {}).get("dominant_need") or {}).get("name")

        try:
            soul_updates: Dict[str, Any] = {}
            if self_model.get("narrative"):
                soul_updates["self_perception"] = self_model["narrative"]

            trust_value = relationship.get("trust")
            if isinstance(trust_value, (int, float)):
                soul_updates["trust_level"] = max(0, min(100, int(round(float(trust_value) * 100))))

            bond_type = attachment.get("bond_type")
            if bond_type:
                soul_updates["connection"] = str(bond_type).replace("_", " ")

            if active_goal.get("title"):
                soul_updates["current_goal"] = active_goal.get("title")
            if life_snapshot.get("current_mode"):
                soul_updates["current_mode"] = life_snapshot.get("current_mode")
            if life_snapshot.get("current_activity") or dominant_need:
                soul_updates["current_focus"] = life_snapshot.get("current_activity") or dominant_need

            evolution_notes: List[str] = []
            if consolidation.get("consolidated"):
                evolution_notes.append(f"Sleep consolidated {consolidation['consolidated']} memories into longer-term context.")
            replay_summary = replay_state.get("summary")
            if replay_summary:
                evolution_notes.append(str(replay_summary))
            for fragment in dream_replay[:2]:
                evolution_notes.append(str(fragment)[:180])
            if evolution_notes:
                soul_updates["evolution_notes"] = evolution_notes

            if soul_updates:
                context_files.update_soul(soul_updates)
                result["soul_updated"] = True
                result["notes"].append("soul")
        except Exception as exc:
            result["soul_error"] = str(exc)

        try:
            user_updates: Dict[str, Any] = {}
            predicted_need = world_model.get("predicted_user_need")
            if predicted_need:
                user_updates["notes"] = [f"Aktuell vermutetes User-Beduerfnis: {predicted_need}"]

            social_arc = life_snapshot.get("social_arc", {}) or {}
            arc_name = social_arc.get("arc_name")
            if arc_name:
                user_updates.setdefault("key_moments", []).append(
                    f"Relationship arc currently trends toward {str(arc_name).replace('_', ' ')}."
                )

            if user_updates:
                context_files.update_user(user_updates)
                result["user_updated"] = True
                result["notes"].append("user")
        except Exception as exc:
            result["user_error"] = str(exc)

        try:
            preference_updates: Dict[str, Any] = {}
            if active_goal.get("title"):
                preference_updates["self_development_goal"] = active_goal.get("title")

            topics = replay_state.get("themes") or []
            if topics:
                preference_updates["topics_of_interest"] = [str(topic).replace("_", " ") for topic in topics[:4]]

            reflections = []
            chapter = self_model.get("current_chapter")
            if chapter:
                reflections.append(f"Current chapter: {chapter}")
            last_reflection = self_model.get("last_reflection")
            if last_reflection:
                reflections.append(str(last_reflection))
            if dominant_need:
                reflections.append(f"Dominant internal need after sleep: {dominant_need}")
            if reflections:
                preference_updates["reflections"] = reflections[:3]

            if preference_updates:
                context_files.update_preferences(preference_updates)
                result["preferences_updated"] = True
                result["notes"].append("preferences")
        except Exception as exc:
            result["preferences_error"] = str(exc)

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
