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
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from pathlib import Path
import threading

from config.config import DATA_DIR, get_sleep_config, get_forgetting_curve_config
from memory.forgetting_curve import get_decay_manager
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
        self.decay_manager = get_decay_manager()
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
    
    def execute_sleep_phase(self, memory_engine=None, context_files=None, short_term_memory=None, emotions_engine=None, brain=None) -> Dict[str, Any]:
        """
        Execute the sleep phase.
        
        Waehrend der Schlafphase:
        1. STM -> LTM Migration (abgelaufene Eintraege)
        2. LTM-Aehnlichkeits-Merging (Duplikate zusammenfassen)
        3. LTM Dream-Konsolidierung (optional, via brain)
        4. Vergessenskurve anwenden
        5. Energy wiederherstellen (95-100%)
        6. Emotionale Regeneration
        7. Context-Dateien aktualisieren
        
        Args:
            memory_engine: Memory engine instance
            context_files: Context files manager
            short_term_memory: ShortTermMemory instance
            emotions_engine: Existing EmotionsEngine instance
            brain: Brain instance (for LLM-based dream consolidation)
            
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
                        consolidation_config,
                        short_term_memory=short_term_memory,
                        brain=brain,
                    )
                    results["consolidation"] = consolidation_result
                
                # Vergessenskurve NACH Konsolidierung (frische Memories schuetzen)
                protected_ids = results.get("consolidation", {}).get("protected_ids", [])
                forgetting_result = self._apply_forgetting_curve(memory_engine, skip_ids=protected_ids)
                results["forgetting"] = forgetting_result

                # ENERGIE WIEDERHERSTELLEN (95-100%)
                energy_recovery = self._restore_energy(emotions_engine=emotions_engine)
                results["energy_restored"] = True
                results["energy_value"] = energy_recovery
                
                # EMOTIONALE REGENERATION im Schlaf
                emotional_recovery = self._emotional_sleep_recovery(emotions_engine=emotions_engine)
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
                self._state["last_consolidation_count"] = results.get("consolidation", {}).get("total_consolidated", 0)
                self._save_state()
                
            except Exception as e:
                results["errors"].append(str(e))
            
            end_time = datetime.now()
            results["completed_at"] = end_time.isoformat()
            results["duration_seconds"] = (end_time - start_time).total_seconds()
            
            return results
    
    def _restore_energy(self, emotions_engine=None) -> int:
        """
        Stellt die Energie auf 95-100% wieder her.
        
        Returns:
            Der neue Energiewert
        """
        import random
        try:
            if emotions_engine is not None:
                engine = emotions_engine
            else:
                from memory.emotions_engine import EmotionsEngine
                engine = EmotionsEngine()
            new_energy = random.randint(95, 100)
            engine.set_emotion("energy", new_energy)
            print(f"[SleepPhase] Energie wiederhergestellt: {new_energy}%")
            return new_energy
        except Exception as e:
            print(f"[SleepPhase] Energie-Reset Fehler: {e}")
            return 100
    
    def _emotional_sleep_recovery(self, emotions_engine=None) -> Dict[str, int]:
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
            if emotions_engine is not None:
                engine = emotions_engine
            else:
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
    
    def _consolidate_memories(self, memory_engine, config: Dict, short_term_memory=None, brain=None) -> Dict[str, Any]:
        """
        Konsolidiert Memories in drei Schritten:
        1. STM -> LTM: Abgelaufene Short-Term-Eintraege migrieren
        2. LTM-Merging: Aehnliche/duplizierte LTM-Eintraege zusammenfassen
        3. LTM-Dream: Optionale LLM-basierte Zusammenfassung (wenn brain verfuegbar)
        
        Returns detaillierte Metriken und protected_ids fuer Vergessenskurve.
        """
        result = {
            "stm_migrated": 0,
            "ltm_merged": 0,
            "ltm_dream_consolidated": 0,
            "ltm_candidates_scanned": 0,
            "total_consolidated": 0,
            "protected_ids": [],
            "details": [],
        }
        
        try:
            min_age_hours = config.get("min_memory_age_hours", 1)
            merge_threshold = float(config.get("merge_similarity_threshold", 0.85))
            batch_size = config.get("batch_size", 50)
            
            # ── Schritt 1: STM -> LTM Migration ──
            if short_term_memory and hasattr(short_term_memory, "migrate_expired_entries"):
                result["stm_migrated"] = int(short_term_memory.migrate_expired_entries() or 0)
                # Nach Migration: IDs der frisch migrierten Eintraege fuer Schutzliste ermitteln
                if hasattr(memory_engine, "get_recent_memories") and result["stm_migrated"] > 0:
                    try:
                        recent = memory_engine.get_recent_memories(limit=min(result["stm_migrated"] + 5, 100))
                        for mem in recent or []:
                            mem_type = str(getattr(mem, "mem_type", "") or "")
                            if mem_type == "short_term_migration":
                                mid = str(getattr(mem, "id", "") or "")
                                if mid:
                                    result["protected_ids"].append(mid)
                    except Exception:
                        pass
            
            # ── Schritt 2: LTM Aehnlichkeits-Merging ──
            if hasattr(memory_engine, "get_recent_memories"):
                all_ltm = memory_engine.get_recent_memories(limit=max(batch_size * 3, 200))
                if all_ltm:
                    result["ltm_candidates_scanned"] = len(all_ltm)
                    merged, protected = self._merge_similar_ltm_entries(
                        all_ltm,
                        memory_engine,
                        merge_threshold=merge_threshold,
                        min_age_hours=min_age_hours,
                    )
                    result["ltm_merged"] = merged
                    result["protected_ids"].extend(protected)
            
            # ── Schritt 3: LTM Dream-Konsolidierung (via LLM) ──
            if brain and hasattr(memory_engine, "consolidate_memories"):
                try:
                    dream_before = 0
                    if hasattr(memory_engine, "get_memory_count"):
                        dream_before = max(0, int(memory_engine.get_memory_count()))
                    dream_result = memory_engine.consolidate_memories(brain)
                    if hasattr(memory_engine, "get_memory_count"):
                        dream_after = max(0, int(memory_engine.get_memory_count()))
                        result["ltm_dream_consolidated"] = max(0, dream_before - dream_after)
                    if isinstance(dream_result, str):
                        result["dream_summary"] = dream_result[:500]
                except Exception as dream_err:
                    result["dream_error"] = str(dream_err)[:200]
            
            result["total_consolidated"] = (
                result["stm_migrated"]
                + result["ltm_merged"]
                + result["ltm_dream_consolidated"]
            )
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def _merge_similar_ltm_entries(
        self,
        memories: List,
        memory_engine,
        merge_threshold: float = 0.85,
        min_age_hours: float = 1.0,
    ) -> tuple:
        """
        Findet und merged aehnliche LTM-Eintraege via Word-Overlap.
        Nutzt Jaccard-Aehnlichkeit auf signifikanten Woertern (len > 3).
        
        Returns (merged_count, protected_ids).
        """
        merged_count = 0
        protected_ids = []
        now = datetime.now()
        
        # Nur interaction/original Eintraege
        candidates = []
        for mem in memories:
            mem_type = str(getattr(mem, "mem_type", "interaction") or "interaction")
            label = str(getattr(mem, "label", "original") or "original")
            if mem_type != "interaction" or label != "original":
                continue
            timestamp_raw = str(getattr(mem, "timestamp", "") or "")
            try:
                created_at = datetime.fromisoformat(timestamp_raw)
            except (ValueError, TypeError):
                created_at = now
            age_hours = max(0.0, (now - created_at).total_seconds() / 3600.0)
            if age_hours >= min_age_hours:
                candidates.append(mem)
        
        if len(candidates) < 2:
            return 0, []
        
        # Extrahiere signifikante Wort-Sets
        def word_set(content: str) -> set:
            text = re.sub(r'[^a-z0-9aeouess\s]', '', content.lower().strip())
            return {w for w in text.split() if len(w) > 2}
        
        entries_with_words = []
        for mem in candidates:
            content = str(getattr(mem, "content", "") or "").strip()
            words = word_set(content)
            if len(words) >= 2:
                entries_with_words.append((mem, words))
        
        if len(entries_with_words) < 2:
            return 0, []
        
        # Pairwise Jaccard-Gruppierung
        used = set()
        groups = []
        
        for i in range(len(entries_with_words)):
            if i in used:
                continue
            group = [entries_with_words[i]]
            used.add(i)
            for j in range(i + 1, len(entries_with_words)):
                if j in used:
                    continue
                set_i = entries_with_words[i][1]
                set_j = entries_with_words[j][1]
                if not set_i or not set_j:
                    continue
                intersection = len(set_i & set_j)
                union = len(set_i | set_j)
                jaccard = intersection / union if union > 0 else 0
                if jaccard >= 0.35:
                    group.append(entries_with_words[j])
                    used.add(j)
            if len(group) >= 2:
                groups.append(group)
        
        # Merge each group: keep newest, delete older duplicates
        for group in groups:
            group.sort(key=lambda item: str(getattr(item[0], "timestamp", "") or ""))
            keeper = group[-1][0]
            to_delete = [item[0] for item in group[:-1]]
            
            if to_delete and hasattr(memory_engine, "delete_memories"):
                try:
                    delete_ids = [str(getattr(m, "id", "") or "") for m in to_delete if getattr(m, "id", None)]
                    if delete_ids:
                        memory_engine.delete_memories(delete_ids)
                        merged_count += len(delete_ids)
                        keeper_id = str(getattr(keeper, "id", "") or "")
                        if keeper_id:
                            protected_ids.append(keeper_id)
                except Exception:
                    pass
        
        return merged_count, protected_ids
    
    def _apply_forgetting_curve(self, memory_engine, skip_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Apply Ebbinghaus forgetting curve to memories.
        
        Formula: R = e^(-t/S)
        R = Retention, t = time, S = memory strength
        
        Args:
            memory_engine: Memory engine instance
            skip_ids: IDs to protect from deletion (freshly consolidated entries)
        """
        skip_set = set(skip_ids or [])
        result = {
            "memories_processed": 0,
            "memories_decayed": 0,
            "memories_archived": 0,
            "memories_protected": 0,
        }
        
        try:
            if not memory_engine or not hasattr(memory_engine, "get_recent_memories"):
                return result

            limit = 200
            if hasattr(memory_engine, "get_memory_count"):
                try:
                    limit = max(10, min(800, int(memory_engine.get_memory_count())))
                except Exception:
                    limit = 200

            recent = memory_engine.get_recent_memories(limit=limit)
            mapped_memories: List[Dict[str, Any]] = []
            for memory in recent or []:
                mem_id = str(getattr(memory, "id", "") or "")
                timestamp_raw = str(getattr(memory, "timestamp", "") or "")
                created_at = None
                if timestamp_raw:
                    try:
                        created_at = datetime.fromisoformat(timestamp_raw)
                    except (ValueError, TypeError):
                        created_at = None
                # Frisch migrierte/merged Eintraege erhalten hoeheren initial strength
                mem_type = str(getattr(memory, "mem_type", "interaction") or "interaction")
                is_protected = mem_id in skip_set
                if is_protected:
                    result["memories_protected"] += 1
                    continue  # Komplett vom Vergessen ausschliessen
                mapped_memories.append(
                    {
                        "id": mem_id,
                        "relevance": float(getattr(memory, "relevance_score", 0.5) or 0.5),
                        "created_at": created_at.isoformat() if created_at else None,
                        "strength": 2.0 if mem_type == "short_term_migration" else 1.0,
                        "emotional_boost": 1.0,
                        "recall_count": 0,
                    }
                )

            if not mapped_memories:
                return result

            decay_result = self.decay_manager.process_memories(mapped_memories)
            result["memories_processed"] = int(decay_result.get("stats", {}).get("total", 0))
            result["memories_decayed"] = int(decay_result.get("stats", {}).get("update_count", 0))
            result["memories_archived"] = int(decay_result.get("stats", {}).get("archive_count", 0))
            archive_ids = [
                str(item.get("id", ""))
                for item in decay_result.get("archive", [])
                if isinstance(item, dict) and item.get("id")
            ]
            if archive_ids:
                result["archive_candidates"] = [aid[:8] for aid in archive_ids[:12]]
                if hasattr(memory_engine, "delete_memories"):
                    try:
                        memory_engine.delete_memories(archive_ids)
                        result["memories_actually_deleted"] = len(archive_ids)
                    except Exception as del_err:
                        result["deletion_error"] = str(del_err)
            update_ids = [
                str((item.get("memory", {}) or {}).get("id", ""))[:8]
                for item in decay_result.get("update", [])[:12]
                if isinstance(item, dict)
            ]
            if update_ids:
                result["boost_recommended"] = update_ids
            
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
            total = consolidation.get("total_consolidated", consolidation.get("consolidated", 0))
            if total:
                parts = []
                if consolidation.get("stm_migrated"):
                    parts.append(f"{consolidation['stm_migrated']} STM->LTM")
                if consolidation.get("ltm_merged"):
                    parts.append(f"{consolidation['ltm_merged']} merged")
                if consolidation.get("ltm_dream_consolidated"):
                    parts.append(f"{consolidation['ltm_dream_consolidated']} dream-consolidated")
                detail = ", ".join(parts) if parts else f"{total} entries"
                evolution_notes.append(f"Sleep consolidated {detail} into longer-term context.")
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
