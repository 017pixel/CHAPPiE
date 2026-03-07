import streamlit as st
import os
import re
from datetime import datetime, timezone

from typing import Dict, Any, List

# CHAPiE imports
from config.config import settings, get_active_model, PROJECT_ROOT
from config.prompts import get_system_prompt_with_emotions, get_personality_context, get_function_calling_instruction
from memory.memory_engine import MemoryEngine
from memory.emotions_engine import EmotionsEngine, analyze_sentiment_simple
from memory.chat_manager import ChatManager
from memory.short_term_memory import ShortTermMemory
from memory.short_term_memory_v2 import get_short_term_memory_v2
from memory.personality_manager import PersonalityManager
from memory.function_registry import get_function_registry
from memory.context_files import get_context_files_manager
from memory.intent_processor import get_intent_processor, reset_intent_processor
from memory.debug_logger import get_debug_logger
from brain import get_brain
from brain.action_response import ActionResponseLayer
from brain.base_brain import GenerationConfig, Message
from brain.global_workspace import GlobalWorkspace
from brain.response_parser import parse_chain_of_thought
from brain.deep_think import DeepThinkEngine
from life import get_life_simulation_service


@st.cache_resource
def init_chappie():
    """Initialisiert das Backend mit neuem Zwei-Schritte System."""
    class CHAPPiEBackend:
        def __init__(self):
            # Module init
            self.memory = MemoryEngine()
            self.emotions = EmotionsEngine()
            self.brain = get_brain()
            self._current_provider = settings.llm_provider

            # Chat Manager init
            data_dir = os.path.join(PROJECT_ROOT, "data")
            self.chat_manager = ChatManager(data_dir)

            # Deep Think Engine
            self.deep_think_engine = DeepThinkEngine(
                memory_engine=self.memory,
                emotions_engine=self.emotions,
                brain=self.brain
            )

            # NEU: Context Files Manager (soul.md, user.md, CHAPPiEsPreferences.md)
            self.context_files = get_context_files_manager()

            # NEU: Short-Term Memory V2 (JSON-basiert mit Timestamps)
            self.short_term_memory_v2 = get_short_term_memory_v2(memory_engine=self.memory)
            
            # Migration von abgelaufenen Einträgen beim Start
            try:
                migrated = self.short_term_memory_v2.migrate_expired_entries()
                if migrated > 0:
                    print(f"[CHAPPiE] {migrated} Einträge ins Langzeitgedächtnis migriert")
            except Exception as e:
                print(f"[CHAPPiE] Migration fehlgeschlagen: {e}")

            # LEGACY: Altes Short-Term Memory (für Abwärtskompatibilität)
            self.short_term_memory = ShortTermMemory(memory_engine=self.memory)
            try:
                cleaned = self.short_term_memory.cleanup_expired()
                if cleaned > 0:
                    print(f"[CHAPPiE] Short-Term Memory: {cleaned} abgelaufene Einträge bereinigt")
            except Exception as e:
                print(f"[CHAPPiE] WARNUNG: Short-Term Memory Bereinigung fehlgeschlagen: {e}")

            # NEU: Intent Processor (Step 1)
            self.intent_processor = get_intent_processor()

            # NEU: Debug Logger
            self.debug_logger = get_debug_logger()
            # CLI Debug ist immer an
            if settings.cli_debug_always_on:
                self.debug_logger.enable()

            # Personality Manager
            self.personality_manager = PersonalityManager()

            # Function Registry
            self.function_registry = get_function_registry()
            self.life_simulation = get_life_simulation_service()
            self.global_workspace = GlobalWorkspace()
            self.action_response = ActionResponseLayer()
        
        def reinit_brain_if_needed(self):
            """Pruefe ob der Provider gewechselt wurde und initialisiere Brain neu."""
            if settings.llm_provider != self._current_provider:
                print(f"Provider wechsel erkannt: {self._current_provider} -> {settings.llm_provider}")
                self.brain = get_brain()
                self._current_provider = settings.llm_provider
                self.deep_think_engine = DeepThinkEngine(
                    memory_engine=self.memory,
                    emotions_engine=self.emotions,
                    brain=self.brain
                )
                reset_intent_processor()
                self.intent_processor = get_intent_processor()
                return True
            return False

        def get_status(self) -> Dict[str, Any]:
            state = self.emotions.get_state()
            try:
                brain_ok = self.brain.is_available()
            except:
                brain_ok = False

            return {
                "brain_available": brain_ok,
                "model": get_active_model(),
                "emotions": {
                    "joy": state.happiness,
                    "trust": state.trust,
                    "energy": state.energy,
                    "curiosity": state.curiosity,
                },
                "daily_info_count": self.short_term_memory_v2.get_count(),
                "two_step_enabled": settings.enable_two_step_processing,
                "life_snapshot": self.life_simulation.get_snapshot(),
            }

        def _build_workspace_from_intent(self, intent_result, life_context: Dict[str, Any], memories: List[Any] | None = None) -> Dict[str, Any]:
            sensory = {
                "input_type": intent_result.intent_type.value,
                "urgency": "high" if intent_result.confidence > 0.85 else "medium",
            }
            emotional_delta = max([abs(getattr(update, "delta", 0)) for update in intent_result.emotions_update.values()] or [0])
            amygdala = {
                "primary_emotion": "engaged" if emotional_delta > 0 else "neutral",
                "emotional_intensity": min(1.0, 0.2 + emotional_delta / 10),
                "reasoning": f"Intent {intent_result.intent_type.value} mit Konfidenz {intent_result.confidence:.2f}",
            }
            hippocampus = {"search_query": " ".join(intent_result.entities[:4])}
            return self.global_workspace.build(sensory, amygdala, hippocampus, life_context, memories or [])

        def _get_emotions_snapshot(self) -> Dict[str, int]:
            """Erstellt einen Snapshot der aktuellen Emotionen."""
            state = self.emotions.get_state()
            return {
                "happiness": state.happiness,
                "trust": state.trust,
                "energy": state.energy,
                "curiosity": state.curiosity,
                "frustration": state.frustration,
                "motivation": state.motivation
            }

        def process(self, user_input: str, history: List[Dict], debug_mode: bool = False) -> Dict[str, Any]:
            """
            Hauptverarbeitung mit Zwei-Schritte System.
            
            Args:
                user_input: Eingabe des Users
                history: Chat Verlauf
                debug_mode: Ob Debug Info gesammelt werden soll
                
            Returns:
                Dict mit Response und Metadaten
            """
            # Debug Mode setzen
            if debug_mode:
                self.debug_logger.enable()
            else:
                if not settings.cli_debug_always_on:
                    self.debug_logger.disable()
            
            self._processing_start_time = datetime.now()

            # === STEP 1: Intent Analysis (wenn aktiviert) ===
            if settings.enable_two_step_processing:
                return self._process_two_step(user_input, history)
            else:
                # Fallback: Altes System
                return self._process_legacy(user_input, history)

        def _process_two_step(self, user_input: str, history: List[Dict]) -> Dict[str, Any]:
            """
            Zwei-Schritte Verarbeitung.
            Step 1: Intent Analysis mit kleinem Modell
            Step 2: Response Generation mit Hauptmodell
            """
            self.debug_logger.log_step1_start()
            
            # Emotionen Snapshot
            emotions_before = self._get_emotions_snapshot()
            life_context = self.life_simulation.prepare_turn(user_input, history, emotions_before)
            
            # === STEP 1: Intent Analysis ===
            intent_result = self.intent_processor.process(
                user_input=user_input,
                history=history,
                current_emotions=emotions_before
            )
            
            self.debug_logger.log_step1_complete(
                intent_result.intent_type.value,
                intent_result.confidence
            )
            self.debug_logger.log_step1_json(intent_result.raw_json)
            
            # === AUSFÜHRUNG: Tool Calls ===
            self._execute_step1_tool_calls(intent_result.tool_calls)
            
            # === AUSFÜHRUNG: Emotions Updates ===
            combined_updates = dict(intent_result.emotions_update)
            for emotion_name, delta in life_context.get("homeostasis", {}).get("emotion_adjustments", {}).items():
                if emotion_name not in combined_updates:
                    combined_updates[emotion_name] = {"delta": delta, "reason": "homeostasis"}
            emotions_after = self._apply_emotion_updates(emotions_before, combined_updates)
            
            # === AUSFÜHRUNG: Short-Term Entries ===
            self._add_short_term_entries(intent_result.short_term_entries)
            
            # === AUSFÜHRUNG: Migration ===
            migrated = self.short_term_memory_v2.migrate_expired_entries()
            if migrated > 0:
                self.debug_logger.log_migration(migrated)
            
            # === CONTEXT AUFBAUEN ===
            context = self._build_context(intent_result.context_requirements)
            workspace = self._build_workspace_from_intent(intent_result, life_context)
            
            # === STEP 2: Response Generation ===
            self.debug_logger.log_step2_start(get_active_model())
            
            response_data = self._generate_response(
                user_input=user_input,
                history=history,
                context=context,
                emotions=emotions_after,
                life_context=life_context,
                global_workspace=workspace
            )
            final_life_snapshot = self.life_simulation.finalize_turn(
                user_input=user_input,
                response_text=response_data["response_text"],
                emotions_after=emotions_after,
                prefrontal=response_data.get("action_plan", {}),
                global_workspace=workspace,
            )
            
            self.debug_logger.log_step2_complete(
                len(response_data["response_text"].split())
            )
            
            # === AUTOMATISCH ALLE KONVERSATIONEN SPEICHERN ===
            # User Nachricht
            self.short_term_memory_v2.add_entry(
                content=f"User: {user_input}",
                category="chat",
                importance="normal"
            )
            # CHAPPiE Antwort
            self.short_term_memory_v2.add_entry(
                content=f"CHAPPiE: {response_data['response_text'][:200]}",  # Erste 200 chars
                category="chat",
                importance="normal"
            )
            
            start_time_dt = datetime.now()
            processing_time_ms = 0
            if hasattr(self, '_processing_start_time'):
                processing_time_ms = (start_time_dt - self._processing_start_time).total_seconds() * 1000
            
            return {
                "response_text": response_data["response_text"],
                "emotions": emotions_after,
                "emotions_before": emotions_before,
                "emotions_delta": self._calculate_emotion_delta(emotions_before, emotions_after),
                "thought_process": response_data.get("thought_process", ""),
                "rag_memories": response_data.get("rag_memories", []),
                "intent_type": intent_result.intent_type.value,
                "intent_confidence": intent_result.confidence,
                "tool_calls_executed": len(intent_result.tool_calls),
                "short_term_count": self.short_term_memory_v2.get_count(),
                "debug_log": self.debug_logger.get_formatted_log() if self.debug_logger.enabled else None,
                "intent_raw_json": intent_result.raw_json if hasattr(intent_result, 'raw_json') else {},
                "processing_time_ms": processing_time_ms,
                "life_snapshot": final_life_snapshot,
                "global_workspace": workspace,
                "action_plan": response_data.get("action_plan", {}),
                "dream_fragments": final_life_snapshot.get("dream_fragments", []),
            }

        def _execute_step1_tool_calls(self, tool_calls: List[Any]):
            """Führt Tool Calls aus Step 1 aus."""
            from memory.context_files import ContextFilesManager
            
            for tool_call in tool_calls:
                try:
                    if tool_call.tool == "update_user_profile":
                        # Aktualisiere user.md
                        self.context_files.update_user(tool_call.data)
                        self.debug_logger.log_tool_call(
                            "update_user_profile", 
                            tool_call.action, 
                            tool_call.data, 
                            True
                        )
                        self.debug_logger.log_file_update("user.md", "updated")
                        
                    elif tool_call.tool == "update_soul":
                        # Aktualisiere soul.md
                        self.context_files.update_soul(tool_call.data)
                        self.debug_logger.log_tool_call(
                            "update_soul", 
                            tool_call.action, 
                            tool_call.data, 
                            True
                        )
                        self.debug_logger.log_file_update("soul.md", "updated")
                        
                    elif tool_call.tool == "update_preferences":
                        # Aktualisiere CHAPPiEsPreferences.md
                        self.context_files.update_preferences(tool_call.data)
                        self.debug_logger.log_tool_call(
                            "update_preferences", 
                            tool_call.action, 
                            tool_call.data, 
                            True
                        )
                        self.debug_logger.log_file_update("CHAPPiEsPreferences.md", "updated")
                        
                    elif tool_call.tool == "add_short_term_memory":
                        # Fuege Short-Term Memory Eintrag hinzu
                        content = tool_call.data.get("content", "")
                        category = tool_call.data.get("category", "general")
                        importance = tool_call.data.get("importance", "normal")
                        
                        self.short_term_memory_v2.add_entry(
                            content=content,
                            category=category,
                            importance=importance
                        )
                        self.debug_logger.log_tool_call(
                            "add_short_term_memory",
                            "add",
                            {"content": content[:50], "category": category, "importance": importance},
                            True
                        )
                        self.debug_logger.log_file_update("short_term_memory.json", "added")
                        
                    else:
                        self.debug_logger.log_warning(
                            "TOOL_CALL", 
                            f"Unbekannter Tool: {tool_call.tool}"
                        )
                        
                except Exception as e:
                    self.debug_logger.log_error(
                        "TOOL_CALL", 
                        f"Fehler bei {tool_call.tool}: {str(e)}"
                    )

        def _apply_emotion_updates(self, emotions_before: Dict[str, int], 
                                   emotion_updates: Dict[str, Any]) -> Dict[str, int]:
            """Wendet Emotions Updates an."""
            emotions_after = emotions_before.copy()
            
            for emotion_name, update_data in emotion_updates.items():
                if emotion_name in emotions_after:
                    delta = getattr(update_data, "delta", update_data.get("delta", 0) if isinstance(update_data, dict) else 0)
                    new_value = emotions_after[emotion_name] + delta
                    # Clamp to 0-100
                    new_value = max(0, min(100, new_value))
                    
                    emotions_after[emotion_name] = new_value
                    
                    # Update im EmotionsEngine
                    if hasattr(self.emotions.state, emotion_name):
                        setattr(self.emotions.state, emotion_name, new_value)
                    
                    # Log
                    self.debug_logger.log_emotion_update(
                        emotion_name,
                        emotions_before[emotion_name],
                        new_value,
                        getattr(update_data, "reason", update_data.get("reason", "") if isinstance(update_data, dict) else "")
                    )
            
            return emotions_after

        def _add_short_term_entries(self, entries: List[Any]):
            """Fügt Short-Term Einträge hinzu."""
            for entry in entries:
                try:
                    self.short_term_memory_v2.add_entry(
                        content=entry.content,
                        category=entry.category,
                        importance=entry.importance
                    )
                    self.debug_logger.log_tool_call(
                        "short_term_memory",
                        "add",
                        {"content": entry.content[:50], "category": entry.category},
                        True
                    )
                except Exception as e:
                    self.debug_logger.log_error(
                        "SHORT_TERM",
                        f"Fehler beim Hinzufügen: {str(e)}"
                    )

        def _build_context(self, requirements: Dict[str, bool]) -> str:
            """Baut den Context String basierend auf Requirements."""
            context_parts = []
            
            if requirements.get("need_soul_context", True):
                soul = self.context_files.get_soul_context()
                if soul:
                    context_parts.append(f"=== CHAPPiE'S SOUL ===\\n{soul}")
            
            if requirements.get("need_user_context", True):
                user = self.context_files.get_user_context()
                if user:
                    context_parts.append(f"=== USER PROFILE ===\\n{user}")
            
            if requirements.get("need_preferences", True):
                prefs = self.context_files.get_preferences_context()
                if prefs:
                    context_parts.append(f"=== CHAPPiE'S PREFERENCES ===\\n{prefs}")
            
            if requirements.get("need_short_term_memory", True):
                short_term = self.short_term_memory_v2.get_formatted_for_prompt()
                if short_term:
                    context_parts.append(short_term)
            
            return "\\n\\n".join(context_parts)

        def _generate_response(self, user_input: str, history: List[Dict], 
                              context: str, emotions: Dict[str, int],
                              life_context: Dict[str, Any] | None = None,
                              global_workspace: Dict[str, Any] | None = None) -> Dict[str, Any]:
            """Generiert die finale Antwort (Step 2)."""
            # RAG Memory Search
            memories = self.memory.search_memory(user_input, top_k=settings.memory_top_k)
            memories_for_prompt = self.memory.format_memories_for_prompt(memories)
            
            # System Prompt bauen
            system_prompt = get_system_prompt_with_emotions(
                happiness=emotions["happiness"],
                trust=emotions["trust"],
                energy=emotions["energy"],
                curiosity=emotions["curiosity"],
                frustration=emotions["frustration"],
                motivation=emotions["motivation"],
                use_chain_of_thought=settings.chain_of_thought
            )
            
            # Context hinzufügen
            if context:
                system_prompt += f"\\n\\n{context}"

            system_prompt += "\\n\\n" + self.action_response.build_prompt_suffix(
                {
                    "response_strategy": "conversational",
                    "tone": "friendly",
                    "response_guidance": "Bleibe hilfreich, kohärent und lebensnah.",
                },
                life_context,
                global_workspace,
            )
            
            # Memories hinzufügen
            if memories_for_prompt:
                system_prompt += f"\\n\\n{memories_for_prompt}"
            
            # Messages bauen
            messages = self.brain.build_prompt(system_prompt, "", user_input, history)
            
            # Generierung
            gen_config = GenerationConfig(
                max_tokens=settings.max_tokens,
                temperature=settings.temperature,
                stream=False,
            )
            
            raw_response = self.brain.generate(messages, config=gen_config)
            
            # Parsing (CoT)
            thought = ""
            if settings.chain_of_thought:
                parsed = parse_chain_of_thought(raw_response)
                display_response = parsed.answer
                thought = parsed.thought or ""
            else:
                display_response = raw_response
            
            # In Langzeitgedächtnis speichern
            self.memory.add_memory(user_input, role="user")
            self.memory.add_memory(display_response, role="assistant")
            
            # Aktualisiere den Zeitstempel der letzten Erinnerung im Session State
            
            st.session_state.last_memory_timestamp = datetime.now(timezone.utc).isoformat()
            
            return {
                "response_text": display_response,
                "thought_process": thought,
                "rag_memories": memories,
                "action_plan": self.action_response.build_action_plan(
                    {
                        "response_strategy": "conversational",
                        "tone": "friendly",
                        "response_guidance": "Erzeuge eine kohärente Antwort, die innere Zustände berücksichtigt.",
                    },
                    life_context or {},
                    global_workspace or {},
                ),
            }

        def _calculate_emotion_delta(self, before: Dict[str, int], 
                                     after: Dict[str, int]) -> Dict[str, Any]:
            """Berechnet Emotions Deltas."""
            delta = {}
            for key in before:
                change = after[key] - before[key]
                if change != 0:
                    delta[key] = {
                        "before": before[key],
                        "after": after[key],
                        "change": change
                    }
            return delta

        def _process_legacy(self, user_input: str, history: List[Dict]) -> Dict[str, Any]:
            """Legacy Verarbeitung (altes System als Fallback)."""
            emotions_before = self._get_emotions_snapshot()
            life_context = self.life_simulation.prepare_turn(user_input, history, emotions_before)
            
            # Einfache Emotions Analyse
            self.emotions.update_from_sentiment(analyze_sentiment_simple(user_input))
            emotions_after = self._get_emotions_snapshot()
            
            # RAG
            memories = self.memory.search_memory(user_input, top_k=settings.memory_top_k)
            memories_for_prompt = self.memory.format_memories_for_prompt(memories)
            
            # Prompt
            state = self.emotions.get_state()
            system_prompt = get_system_prompt_with_emotions(
                **state.__dict__,
                use_chain_of_thought=settings.chain_of_thought
            )
            system_prompt += "\n\n" + self.action_response.build_prompt_suffix(
                {
                    "response_strategy": "conversational",
                    "tone": "friendly",
                    "response_guidance": "Bleibe kompatibel mit der Life-Simulation.",
                },
                life_context,
                {"broadcast": "legacy-path", "dominant_focus": {"label": "Legacy Input"}, "guidance": "Halte das Verhalten stabil."},
            )
            
            messages = self.brain.build_prompt(system_prompt, memories_for_prompt, user_input, history)
            
            # Generierung
            gen_config = GenerationConfig(
                max_tokens=settings.max_tokens,
                temperature=settings.temperature,
                stream=False,
            )
            raw_response = self.brain.generate(messages, config=gen_config)
            
            # Parsing
            thought = ""
            if settings.chain_of_thought:
                parsed = parse_chain_of_thought(raw_response)
                display_response = parsed.answer
                thought = parsed.thought or ""
            else:
                display_response = raw_response
            
            # Speichern
            self.memory.add_memory(user_input, role="user")
            self.memory.add_memory(display_response, role="assistant")
            
            # Aktualisiere den Zeitstempel der letzten Erinnerung im Session State
            
            st.session_state.last_memory_timestamp = datetime.now(timezone.utc).isoformat()
            
            # AUTOMATISCH ALLE KONVERSATIONEN SPEICHERN (Legacy Mode)
            self.short_term_memory_v2.add_entry(
                content=f"User: {user_input}",
                category="chat",
                importance="normal"
            )
            self.short_term_memory_v2.add_entry(
                content=f"CHAPPiE: {display_response[:200]}",
                category="chat",
                importance="normal"
            )
            final_life_snapshot = self.life_simulation.finalize_turn(
                user_input=user_input,
                response_text=display_response,
                emotions_after=emotions_after,
                prefrontal={"response_guidance": "Legacy path mit Life-Simulation"},
                global_workspace={"dominant_focus": {"label": "Legacy Input"}},
            )
            
            return {
                "response_text": display_response,
                "emotions": emotions_after,
                "emotions_before": emotions_before,
                "emotions_delta": self._calculate_emotion_delta(emotions_before, emotions_after),
                "thought_process": thought,
                "rag_memories": memories,
                "intent_type": "legacy",
                "intent_confidence": 1.0,
                "tool_calls_executed": 0,
                "short_term_count": self.short_term_memory_v2.get_count(),
                "debug_log": None,
                "life_snapshot": final_life_snapshot,
                "global_workspace": {"broadcast": "legacy-path"},
                "action_plan": {"strategy": "conversational", "tone": "friendly"},
                "dream_fragments": final_life_snapshot.get("dream_fragments", []),
            }

        # === Command Handler ===

        def handle_command(self, command: str) -> str:
            """Verarbeitet Slash-Commands."""
            cmd = command.lower().strip()

            if cmd == "/daily" or cmd == "/shortterm":
                entries = self.short_term_memory_v2.get_active_entries()
                if not entries:
                    return "Keine Einträge im Kurzzeitgedächtnis."
                lines = ["**Kurzzeitgedächtnis (24h):**\\n"]
                for entry in entries[:20]:
                    from datetime import datetime 
                    created = datetime.fromisoformat(entry.created_at)
                    time_str = created.strftime("%d.%m %H:%M")
                    lines.append(f"- [{time_str}] [{entry.importance}] [{entry.category}] {entry.content}")
                return "\\n".join(lines)

            elif cmd == "/personality":
                return self.personality_manager.get_for_prompt()
            
            elif cmd == "/soul":
                return self.context_files.get_soul_context()
            
            elif cmd == "/user":
                return self.context_files.get_user_context()
            
            elif cmd == "/prefs" or cmd == "/preferences":
                return self.context_files.get_preferences_context()

            elif cmd == "/consolidate":
                migrated = self.short_term_memory_v2.migrate_expired_entries()
                return f"Bereinigung abgeschlossen: {migrated} Einträge migriert."

            elif cmd == "/reflect":
                insights = self.personality_manager.get_recent_reflections(limit=3)
                return f"Deine letzten Selbst-Reflexionen:\\n" + "\\n".join(insights) if insights else "Noch keine Reflexionen dokumentiert."

            elif cmd == "/functions":
                funcs = self.function_registry.get_function_names()
                return "Verfügbare Funktionen:\\n" + "\\n".join(f"- {f}" for f in funcs)
            
            elif cmd == "/life":
                snapshot = self.life_simulation.get_snapshot()
                need_lines = [f"- {item['name']}: {item['value']}" for item in snapshot.get("homeostasis", {}).get("active_needs", [])[:6]]
                goal = snapshot.get("active_goal", {})
                world = snapshot.get("world_model", {})
                development = snapshot.get("development", {})
                attachment = snapshot.get("attachment_model", {})
                planning = snapshot.get("planning_state", {})
                social_arc = snapshot.get("social_arc", {})
                return (
                    f"**Life Simulation**\n\n"
                    f"Phase: {snapshot.get('clock', {}).get('phase_label', 'unbekannt')}\n"
                    f"Aktivität: {snapshot.get('current_activity', '---')}\n"
                    f"Modus: {snapshot.get('current_mode', '---')}\n"
                    f"Fokusziel: {goal.get('title', '---')} ({goal.get('progress', 0):.0%})\n"
                    f"Entwicklungsphase: {development.get('stage', '---')} -> {development.get('next_stage', '---')}\n"
                    f"Bindung: {attachment.get('bond_type', '---')} ({attachment.get('attachment_security', 0):.2f})\n"
                    f"Planung: {planning.get('planning_horizon', '---')} | {planning.get('next_milestone', '---')}\n"
                    f"Social Arc: {social_arc.get('arc_name', '---')}\n"
                    f"World Model: {world.get('predicted_user_need', '---')}\n"
                    f"Next Best Action: {world.get('next_best_action', '---')}\n\n"
                    + "\n".join(need_lines)
                )

            elif cmd == "/needs":
                snapshot = self.life_simulation.get_snapshot()
                return "\n".join(
                    f"- {item['name']}: {item['value']} (Druck {item['pressure']})"
                    for item in snapshot.get("homeostasis", {}).get("active_needs", [])
                )

            elif cmd == "/goals":
                snapshot = self.life_simulation.get_snapshot()
                goal_competition = snapshot.get("goal_competition", {})
                lines = ["Goal Competition:"]
                for goal in goal_competition.get("competition_table", [])[:5]:
                    lines.append(f"- {goal.get('title', '---')}: Score {goal.get('score', 0):.2f} | Progress {goal.get('progress', 0):.0%}")
                return "\n".join(lines)

            elif cmd == "/habits":
                snapshot = self.life_simulation.get_snapshot()
                habits = sorted(snapshot.get("habits", {}).items(), key=lambda item: item[1].get("strength", 0), reverse=True)
                lines = ["Habit Engine:"]
                for name, meta in habits[:5]:
                    lines.append(f"- {meta.get('label', name)}: Stärke {meta.get('strength', 0):.2f} | Count {meta.get('count', 0)} | Trend {meta.get('trend', 'stable')}")
                return "\n".join(lines)

            elif cmd == "/stage":
                snapshot = self.life_simulation.get_snapshot()
                development = snapshot.get("development", {})
                lines = [
                    f"Stage: {development.get('stage', '---')}",
                    f"Next Stage: {development.get('next_stage', '---')}",
                    f"Development Score: {development.get('development_score', 0):.2f}",
                    f"Progress To Next: {development.get('progress_to_next', 0):.0%}",
                ]
                for item in development.get("milestones", [])[:4]:
                    lines.append(f"- {item}")
                return "\n".join(lines)

            elif cmd == "/plan":
                snapshot = self.life_simulation.get_snapshot()
                planning = snapshot.get("planning_state", {})
                lines = [
                    f"Planning Horizon: {planning.get('planning_horizon', '---')}",
                    f"Coordination Mode: {planning.get('coordination_mode', '---')}",
                    f"Milestone: {planning.get('next_milestone', '---')}",
                    f"Confidence: {planning.get('plan_confidence', 0):.2f}",
                ]
                for item in planning.get("immediate_steps", [])[:3]:
                    lines.append(f"- {item}")
                for item in planning.get("bottlenecks", [])[:3]:
                    lines.append(f"! {item}")
                return "\n".join(lines)

            elif cmd == "/forecast":
                snapshot = self.life_simulation.get_snapshot()
                forecast = snapshot.get("forecast_state", {})
                lines = [
                    f"Risk Level: {forecast.get('risk_level', '---')}",
                    f"Next Turn: {forecast.get('next_turn_outlook', '---')}",
                    f"Daily Outlook: {forecast.get('daily_outlook', '---')}",
                    f"Stage Trajectory: {forecast.get('stage_trajectory', '---')}",
                ]
                for item in forecast.get("protective_factors", [])[:4]:
                    lines.append(f"- {item}")
                return "\n".join(lines)

            elif cmd == "/arc":
                snapshot = self.life_simulation.get_snapshot()
                social_arc = snapshot.get("social_arc", {})
                lines = [
                    f"Arc Name: {social_arc.get('arc_name', '---')}",
                    f"Phase: {social_arc.get('phase', '---')}",
                    f"Arc Score: {social_arc.get('arc_score', 0):.2f}",
                    f"Episode: {social_arc.get('current_episode', '---')}",
                    f"Guidance: {social_arc.get('guidance', '---')}",
                ]
                for item in social_arc.get("recent_episode_titles", [])[:4]:
                    lines.append(f"- {item}")
                return "\n".join(lines)

            elif cmd == "/timeline":
                snapshot = self.life_simulation.get_snapshot()
                summary = snapshot.get("timeline_summary", {})
                history = snapshot.get("timeline_history", [])
                lines = [
                    f"Entries: {summary.get('entries', 0)}",
                    f"Summary: {summary.get('summary', '---')}",
                ]
                for item in history[-5:]:
                    lines.append(
                        f"- {item.get('phase_label', '---')} | {item.get('source', '---')} | Goal={item.get('goal', '---')} | Stage={item.get('stage', '---')}"
                    )
                return "\n".join(lines)

            elif cmd == "/world":
                snapshot = self.life_simulation.get_snapshot()
                world = snapshot.get("world_model", {})
                risks = world.get("risk_factors", [])
                opportunities = world.get("opportunities", [])
                attachment = snapshot.get("attachment_model", {})
                lines = [
                    f"Interaction Mode: {world.get('interaction_mode', '---')}",
                    f"Predicted User Need: {world.get('predicted_user_need', '---')}",
                    f"Next Best Action: {world.get('next_best_action', '---')}",
                    f"Trajectory: {world.get('expected_trajectory', '---')}",
                    f"Confidence: {world.get('confidence', 0):.2f}",
                    f"Attachment Guidance: {attachment.get('guidance', '---')}",
                ]
                if risks:
                    lines.append("Risks: " + " | ".join(risks))
                if opportunities:
                    lines.append("Opportunities: " + " | ".join(opportunities))
                return "\n".join(lines)

            elif cmd == "/debug":
                # Toggle Debug Mode
                if self.debug_logger.enabled:
                    self.debug_logger.disable()
                    return "Debug Mode: AUS"
                else:
                    self.debug_logger.enable()
                    return "Debug Mode: AN\\n\\n" + self.debug_logger.get_formatted_log()
            
            elif cmd == "/step1":
                # Zeige letzten Step 1 JSON
                entries = self.debug_logger.get_entries_by_category("STEP1_JSON")
                if entries:
                    last_entry = entries[-1]
                    json_preview = last_entry.details.get("json_preview", "Keine Daten")
                    return f"**Letzter Step 1 JSON:**\\n\\n```json\\n{json_preview}\\n```"
                return "Noch kein Step 1 JSON vorhanden."
            
            elif cmd == "/twostep":
                # Toggle Two-Step Processing
                settings.enable_two_step_processing = not settings.enable_two_step_processing
                status = "AN" if settings.enable_two_step_processing else "AUS"
                return f"Zwei-Schritte System: {status}"

            return f"Unbekannter Command: {command}"

    return CHAPPiEBackend()
