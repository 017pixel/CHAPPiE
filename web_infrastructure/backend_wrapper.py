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
from memory.intent_processor import get_intent_processor
from memory.debug_logger import get_debug_logger
from brain import get_brain
from brain.base_brain import GenerationConfig, Message
from brain.response_parser import parse_chain_of_thought
from brain.deep_think import DeepThinkEngine


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
        
        def reinit_brain_if_needed(self):
            """Prüfe ob der Provider gewechselt wurde und initialisiere Brain neu."""
            if settings.llm_provider != self._current_provider:
                print(f"🔄 Provider wechsel erkannt: {self._current_provider} -> {settings.llm_provider}")
                self.brain = get_brain()
                self._current_provider = settings.llm_provider
                self.deep_think_engine = DeepThinkEngine(
                    memory_engine=self.memory,
                    emotions_engine=self.emotions,
                    brain=self.brain
                )
                # Intent Processor auch neu laden
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
            }

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
                # Immer an für CLI, standardmäßig aus für Web UI (außer explizit an)
                if not settings.cli_debug_always_on:
                    self.debug_logger.disable()

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
            emotions_after = self._apply_emotion_updates(
                emotions_before, 
                intent_result.emotions_update
            )
            
            # === AUSFÜHRUNG: Short-Term Entries ===
            self._add_short_term_entries(intent_result.short_term_entries)
            
            # === AUSFÜHRUNG: Migration ===
            migrated = self.short_term_memory_v2.migrate_expired_entries()
            if migrated > 0:
                self.debug_logger.log_migration(migrated)
            
            # === CONTEXT AUFBAUEN ===
            context = self._build_context(intent_result.context_requirements)
            
            # === STEP 2: Response Generation ===
            self.debug_logger.log_step2_start(get_active_model())
            
            response_data = self._generate_response(
                user_input=user_input,
                history=history,
                context=context,
                emotions=emotions_after
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
            
            # === ERGEBNIS ZUSAMMENSTELLEN ===
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
                    delta = update_data.delta
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
                        update_data.reason
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
                              context: str, emotions: Dict[str, int]) -> Dict[str, Any]:
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
