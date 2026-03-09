import streamlit as st
import os
import re
import time
import threading
from datetime import datetime, timezone

from typing import Dict, Any, List, Callable, Optional

# CHAPiE imports
from config.config import settings, get_active_model, PROJECT_ROOT, LLMProvider
from config.prompts import get_system_prompt_with_emotions, get_personality_context, get_function_calling_instruction
from memory.memory_engine import MemoryEngine
from memory.emotions_engine import EmotionsEngine, analyze_sentiment_simple, calculate_emotion_transition
from memory.chat_manager import ChatManager
from memory.short_term_memory import ShortTermMemory
from memory.short_term_memory_v2 import get_short_term_memory_v2
from memory.personality_manager import PersonalityManager
from memory.function_registry import get_function_registry
from memory.context_files import get_context_files_manager
from memory.intent_processor import get_intent_processor, reset_intent_processor
from memory.debug_logger import get_debug_logger
from memory.sleep_phase import get_sleep_phase_handler
from brain import get_brain
from brain.action_response import ActionResponseLayer
from brain.agents.steering_manager import get_steering_manager
from brain.base_brain import GenerationConfig, Message
from brain.global_workspace import GlobalWorkspace
from brain.response_parser import extract_tagged_block, parse_chain_of_thought, parse_thinking_tags, looks_like_model_error
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
            self._brain_signature = self._build_brain_signature()

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
            self.sleep_handler = get_sleep_phase_handler()
            self._sleep_job_lock = threading.Lock()

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
            self._intent_signature = self._build_intent_signature()

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
            self.steering_manager = get_steering_manager()
            self._chat_jobs: Dict[str, threading.Thread] = {}
            self._chat_jobs_lock = threading.RLock()

        @staticmethod
        def _chat_job_key(session_id: str, message_id: str) -> str:
            return f"{session_id}:{message_id}"

        def _set_last_memory_timestamp(self):
            try:
                st.session_state.last_memory_timestamp = datetime.now(timezone.utc).isoformat()
            except Exception:
                return

        def _run_sleep_phase_job(self):
            try:
                result = self.sleep_handler.execute_sleep_phase(
                    memory_engine=self.memory,
                    context_files=self.context_files,
                )
                self.debug_logger.log_info(
                    "SLEEP",
                    "Automatische Schlafphase abgeschlossen",
                    {
                        "context_updates": result.get("context_updates", {}),
                        "duration_seconds": result.get("duration_seconds", 0),
                        "dream_fragments": len(result.get("dream_replay", [])),
                    },
                )
            except Exception as exc:
                self.debug_logger.log_error("SLEEP", f"Automatische Schlafphase fehlgeschlagen: {exc}")
            finally:
                try:
                    self._sleep_job_lock.release()
                except RuntimeError:
                    pass

        def _schedule_sleep_phase_if_due(self) -> Dict[str, Any]:
            self.sleep_handler.increment_interaction()
            status = self.sleep_handler.get_status()
            if not self.sleep_handler.should_run_sleep():
                return {"triggered": False, "status": status}

            if not self._sleep_job_lock.acquire(blocking=False):
                return {"triggered": False, "status": status, "already_running": True}

            worker = threading.Thread(target=self._run_sleep_phase_job, daemon=True, name="chappie-sleep-phase")
            worker.start()
            return {"triggered": True, "status": self.sleep_handler.get_status()}

        @staticmethod
        def _serialize_rag_memories(memories: List[Any] | None) -> List[Dict[str, Any]]:
            formatted_memories = []
            for memory in memories or []:
                formatted_memories.append({
                    "content": memory.content,
                    "relevance_score": memory.relevance_score,
                    "role": memory.role,
                    "label": getattr(memory, "label", "original"),
                    "id": memory.id,
                    "timestamp": getattr(memory, "timestamp", ""),
                    "type": getattr(memory, "mem_type", "interaction"),
                })
            return formatted_memories

        def _build_assistant_message(self, user_input: str, result: Dict[str, Any], message_id: Optional[str] = None) -> Dict[str, Any]:
            intent_raw = result.get("intent_raw_json", {})
            tool_calls_raw = intent_raw.get("tool_calls", []) if isinstance(intent_raw, dict) else []
            metadata = {
                "thought_process": result.get("thought_process"),
                "model_reasoning": result.get("model_reasoning"),
                "reasoning_only": result.get("reasoning_only", False),
                "rag_memories": self._serialize_rag_memories(result.get("rag_memories")),
                "emotions": result.get("emotions", {}),
                "emotions_delta": result.get("emotions_delta", {}),
                "emotions_before": result.get("emotions_before", {}),
                "input_analysis": result.get("input_analysis", user_input),
                "intent_type": result.get("intent_type"),
                "intent_confidence": result.get("intent_confidence"),
                "tool_calls_executed": result.get("tool_calls_executed", 0),
                "available_tools": result.get("available_tools", []),
                "selected_tools": result.get("selected_tools", []),
                "unused_tools": result.get("unused_tools", []),
                "intent_raw_json": intent_raw,
                "tool_calls": tool_calls_raw,
                "short_term_count": result.get("short_term_count", 0),
                "processing_time_ms": result.get("processing_time_ms", 0),
                "life_snapshot": result.get("life_snapshot", {}),
                "global_workspace": result.get("global_workspace", {}),
                "action_plan": result.get("action_plan", {}),
                "emotion_steering": result.get("emotion_steering", {}),
                "prompt_emotion_mode": result.get("prompt_emotion_mode", ""),
                "dream_fragments": result.get("dream_fragments", []),
                "debug_entries": result.get("debug_entries", []),
                "debug_log": result.get("debug_log"),
                "provider": result.get("provider", ""),
                "model": result.get("model", ""),
                "auto_sleep_triggered": result.get("auto_sleep_triggered", False),
                "sleep_status": result.get("sleep_status", {}),
                "pending": False,
                "status_text": "",
                "retry_history": result.get("retry_history", []),
            }
            assistant_msg = {
                "role": "assistant",
                "content": result.get("response_text", ""),
                "metadata": metadata,
            }
            if message_id:
                assistant_msg["id"] = message_id
            return assistant_msg

        def _build_pending_message(self, message_id: str) -> Dict[str, Any]:
            return {
                "id": message_id,
                "role": "assistant",
                "content": "_CHAPPiE denkt nach..._",
                "metadata": {
                    "pending": True,
                    "status_text": "Nachricht wird verarbeitet...",
                    "retry_history": [],
                },
            }
        
        def _provider_runtime_signature(self, provider: LLMProvider, model: str):
            if provider == LLMProvider.OLLAMA:
                return (provider.value, model, settings.ollama_host)
            if provider == LLMProvider.VLLM:
                return (provider.value, model, settings.vllm_url)
            if provider == LLMProvider.GROQ:
                return (provider.value, model, settings.groq_api_key)
            if provider == LLMProvider.CEREBRAS:
                return (provider.value, model, settings.cerebras_api_key)
            if provider == LLMProvider.NVIDIA:
                return (provider.value, model, settings.nvidia_api_key)
            return (provider.value, model)

        def _build_brain_signature(self):
            return self._provider_runtime_signature(settings.llm_provider, get_active_model())

        def _build_intent_signature(self):
            provider = settings.get_effective_provider(settings.intent_provider)
            model = settings.get_intent_model(settings.intent_provider)
            return (
                settings.intent_provider.value if settings.intent_provider else "auto",
                *self._provider_runtime_signature(provider, model),
            )

        def apply_runtime_settings(self, force: bool = False):
            changed = False
            brain_signature = self._build_brain_signature()
            if force or brain_signature != self._brain_signature:
                print(f"Runtime-Reload Hauptmodell: {self._brain_signature} -> {brain_signature}")
                self.brain = get_brain(provider=settings.llm_provider, model=get_active_model())
                self._brain_signature = brain_signature
                self._current_provider = settings.llm_provider
                self.deep_think_engine = DeepThinkEngine(
                    memory_engine=self.memory,
                    emotions_engine=self.emotions,
                    brain=self.brain
                )
                self.steering_manager.refresh_runtime_profile(get_active_model())
                changed = True

            intent_signature = self._build_intent_signature()
            if force or changed or intent_signature != self._intent_signature:
                print(f"Runtime-Reload Intent: {self._intent_signature} -> {intent_signature}")
                reset_intent_processor()
                self.intent_processor = get_intent_processor()
                self._intent_signature = intent_signature
                changed = True
            return changed

        def reinit_brain_if_needed(self):
            """Abwärtskompatibler Alias für Runtime-Reload."""
            return self.apply_runtime_settings()

        def _error_prefix_for_active_provider(self) -> str:
            if settings.llm_provider == LLMProvider.OLLAMA:
                return "Ollama Fehler"
            if settings.llm_provider == LLMProvider.GROQ:
                return "Groq Fehler"
            if settings.llm_provider == LLMProvider.CEREBRAS:
                return "Cerebras Fehler"
            if settings.llm_provider == LLMProvider.NVIDIA:
                return "NVIDIA Fehler"
            if settings.llm_provider == LLMProvider.VLLM:
                return "vLLM Fehler"
            return "LLM Fehler"

        def _format_generation_error(self, phase: str, raw_error: str = "") -> str:
            prefix = self._error_prefix_for_active_provider()
            provider = settings.llm_provider.value
            model = get_active_model()
            stage = phase or "Antwortgenerierung"
            detail = (raw_error or "").strip()
            detail_lower = detail.lower()

            cause = "Unbekannter Laufzeitfehler"
            if not detail:
                cause = "Leere Modellantwort"
            elif "timeout" in detail_lower:
                cause = "Timeout"
            elif "connection" in detail_lower or "verbind" in detail_lower:
                cause = "Verbindungsfehler"
            elif "reasoning_content" in detail_lower:
                cause = "Nur Reasoning-Ausgabe ohne finalen Antworttext"
            elif "tool-call" in detail_lower or "tool_calls" in detail_lower:
                cause = "Nur Tool-Calls ohne Textantwort"
            elif "http" in detail_lower:
                cause = "HTTP-Fehler"

            if detail:
                trimmed_detail = detail if len(detail) <= 320 else detail[:317] + "..."
                return (
                    f"{prefix}: {stage} fehlgeschlagen ({cause}) "
                    f"[Provider={provider}, Modell={model}]. Detail: {trimmed_detail}"
                )
            return (
                f"{prefix}: {stage} fehlgeschlagen ({cause}) "
                f"[Provider={provider}, Modell={model}]."
            )

        def _extract_display_response(self, raw_response: Any, phase: str = "Antwortgenerierung"):
            raw_text = raw_response if isinstance(raw_response, str) else str(raw_response or "")
            if not raw_text.strip():
                return self._format_generation_error(phase), "", ""

            if looks_like_model_error(raw_text):
                return self._format_generation_error(phase, raw_text), "", ""

            model_reasoning_block = extract_tagged_block(raw_text, ["model_reasoning", "provider_reasoning"])
            content_without_model_reasoning = model_reasoning_block.remaining

            parsed = parse_chain_of_thought(content_without_model_reasoning)
            alt_parsed = parse_thinking_tags(content_without_model_reasoning)
            display_response = parsed.answer.strip() or alt_parsed.answer.strip() or content_without_model_reasoning.strip()
            thought = parsed.thought or alt_parsed.thought or ""
            model_reasoning = model_reasoning_block.content or ""

            if not display_response:
                display_response = "CHAPPiE schweigt..." if (thought or model_reasoning) else self._format_generation_error(phase, raw_text)
            return display_response, thought, model_reasoning

        def _build_prompt_runtime(self, emotions: Dict[str, int]) -> Dict[str, Any]:
            model_name = get_active_model()
            force_steering = self.steering_manager.should_force_local_emotion_steering(
                settings.llm_provider,
                model_name,
            )
            steering_payload = self.steering_manager.get_steering_payload(emotions, force=force_steering)
            use_prompt_emotions = self.steering_manager.should_use_prompt_emotions(
                settings.llm_provider,
                model_name,
            )
            emotion_steering = self.steering_manager.build_debug_report(
                emotions,
                steering_payload=steering_payload,
                force=force_steering,
            )
            response_plan = {
                "response_strategy": "conversational",
                "response_guidance": "Bleibe hilfreich, kohärent und lebensnah.",
            }
            if use_prompt_emotions:
                response_plan["tone"] = "friendly"
            else:
                response_plan["response_guidance"] = "Beantworte die konkrete Anfrage direkt, kohärent und ohne kuenstliche Gefuehlsansagen."

            return {
                "model_name": model_name,
                "force_steering": force_steering,
                "steering_payload": steering_payload,
                "use_prompt_emotions": use_prompt_emotions,
                "emotion_steering": emotion_steering,
                "prompt_emotion_mode": "api_prompt_rules" if use_prompt_emotions else "local_layer_only",
                "response_plan": response_plan,
            }

        @staticmethod
        def _is_valid_intent_result(intent_result: Any) -> bool:
            return intent_result is not None and hasattr(intent_result, "intent_type")

        def _is_valid_generation_result(self, response_data: Dict[str, Any]) -> bool:
            response_text = str((response_data or {}).get("response_text", "") or "").strip()
            return bool(response_text and not looks_like_model_error(response_text))

        def _run_with_retries(
            self,
            *,
            step_number: int,
            step_name: str,
            action: Callable[[], Any],
            validator: Callable[[Any], bool],
            status_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
            max_attempts: int = 3,
            retry_delay_seconds: float = 1.0,
        ) -> Any:
            last_error = "Leere Modellantwort"

            for attempt in range(1, max_attempts + 1):
                try:
                    result = action()
                    if not validator(result):
                        response_text = ""
                        if isinstance(result, dict):
                            response_text = str(result.get("response_text", "") or "")
                        last_error = response_text or "Leere Modellantwort"
                        raise ValueError(last_error)
                    return result
                except Exception as exc:
                    last_error = str(exc) or last_error
                    if attempt >= max_attempts:
                        raise ValueError(last_error) from exc

                    retry_text = (
                        f"Fehler bei Schritt {step_number}: {step_name}. "
                        f"Erneuter Versuch {attempt + 1}/{max_attempts}."
                    )
                    if status_callback:
                        status_callback(
                            {
                                "step": step_number,
                                "step_name": step_name,
                                "attempt": attempt,
                                "max_attempts": max_attempts,
                                "error": last_error,
                                "status_text": retry_text,
                            }
                        )
                    time.sleep(retry_delay_seconds)

        def is_chat_job_active(self, session_id: str, message_id: str) -> bool:
            job_key = self._chat_job_key(session_id, message_id)
            with self._chat_jobs_lock:
                job = self._chat_jobs.get(job_key)
                return bool(job and job.is_alive())

        def start_async_chat(
            self,
            *,
            session_id: str,
            message_id: str,
            user_input: str,
            history: List[Dict[str, Any]],
            debug_mode: bool = False,
        ) -> bool:
            normalized_session_id = self.chat_manager.ensure_session_id(session_id)
            job_key = self._chat_job_key(normalized_session_id, message_id)
            with self._chat_jobs_lock:
                existing_job = self._chat_jobs.get(job_key)
                if existing_job and existing_job.is_alive():
                    return False

                worker = threading.Thread(
                    target=self._run_chat_job,
                    kwargs={
                        "session_id": normalized_session_id,
                        "message_id": message_id,
                        "user_input": user_input,
                        "history": history,
                        "debug_mode": debug_mode,
                    },
                    daemon=True,
                )
                self._chat_jobs[job_key] = worker
                worker.start()
                return True

        def _run_chat_job(
            self,
            *,
            session_id: str,
            message_id: str,
            user_input: str,
            history: List[Dict[str, Any]],
            debug_mode: bool,
        ):
            retry_history: List[Dict[str, Any]] = []

            def status_callback(event: Dict[str, Any]):
                retry_history.append(dict(event))
                self.chat_manager.update_message(
                    session_id,
                    message_id,
                    metadata_updates={
                        "pending": True,
                        "status_text": event.get("status_text", "Nachricht wird verarbeitet..."),
                        "retry_history": retry_history,
                        "current_step": event.get("step"),
                    },
                )

            try:
                result = self.process(user_input, history, debug_mode=debug_mode, status_callback=status_callback)
                result["retry_history"] = retry_history
                assistant_msg = self._build_assistant_message(user_input, result, message_id=message_id)
                self.chat_manager.update_message(
                    session_id,
                    message_id,
                    content=assistant_msg["content"],
                    role="assistant",
                    metadata_updates=assistant_msg["metadata"],
                )
            except Exception as exc:
                error_text = self._format_generation_error("Nachricht", str(exc))
                self.chat_manager.update_message(
                    session_id,
                    message_id,
                    content=error_text,
                    role="assistant",
                    metadata_updates={
                        "pending": False,
                        "status_text": "",
                        "retry_history": retry_history,
                        "provider": settings.llm_provider.value,
                        "model": get_active_model(),
                    },
                )
            finally:
                job_key = self._chat_job_key(session_id, message_id)
                with self._chat_jobs_lock:
                    self._chat_jobs.pop(job_key, None)

        def get_status(self) -> Dict[str, Any]:
            try:
                brain_ok = self.brain.is_available()
            except:
                brain_ok = False

            return {
                "brain_available": brain_ok,
                "model": get_active_model(),
                "emotions": self._get_emotions_snapshot(),
                "daily_info_count": self.short_term_memory_v2.get_count(),
                "two_step_enabled": settings.enable_two_step_processing,
                "life_snapshot": self.life_simulation.get_snapshot(),
            }

        def get_emotion_layer_config(self, current_emotions: Optional[Dict[str, int]] = None) -> List[Dict[str, Any]]:
            snapshot = current_emotions or self._get_emotions_snapshot()
            return self.steering_manager.get_emotion_layer_config(snapshot)

        def update_emotion_layer_config(self, emotion_name: str, layer_start: int, layer_end: int, default_alpha: float) -> Optional[Dict[str, Any]]:
            return self.steering_manager.update_vector_config(
                emotion_name,
                layer_start=layer_start,
                layer_end=layer_end,
                default_alpha=default_alpha,
            )

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

        def _get_available_step1_tools(self) -> List[str]:
            return [
                "update_user_profile",
                "update_soul",
                "update_preferences",
                "add_short_term_memory",
            ]

        def _get_emotions_snapshot(self) -> Dict[str, int]:
            """Erstellt einen Snapshot der aktuellen Emotionen."""
            state = self.emotions.get_state()
            return {
                "happiness": state.happiness,
                "trust": state.trust,
                "energy": state.energy,
                "curiosity": state.curiosity,
                "frustration": state.frustration,
                "motivation": state.motivation,
                "sadness": state.sadness,
            }

        def process(
            self,
            user_input: str,
            history: List[Dict],
            debug_mode: bool = False,
            status_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        ) -> Dict[str, Any]:
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

            if self.debug_logger.enabled:
                self.debug_logger.clear()
                self.debug_logger.log_info(
                    "TURN",
                    "Neuer Turn gestartet",
                    {
                        "provider": settings.llm_provider.value,
                        "model": get_active_model(),
                        "history_messages": len(history or []),
                    },
                )

            self.apply_runtime_settings()
            
            self._processing_start_time = datetime.now()

            # === STEP 1: Intent Analysis (wenn aktiviert) ===
            if settings.enable_two_step_processing:
                return self._process_two_step(user_input, history, status_callback=status_callback)
            else:
                # Fallback: Altes System
                return self._process_legacy(user_input, history, status_callback=status_callback)

        def _process_two_step(
            self,
            user_input: str,
            history: List[Dict],
            status_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        ) -> Dict[str, Any]:
            """
            Zwei-Schritte Verarbeitung.
            Step 1: Intent Analysis mit kleinem Modell
            Step 2: Response Generation mit Hauptmodell
            """
            self.debug_logger.log_step1_start()
            
            # Emotionen Snapshot
            emotions_before = self._get_emotions_snapshot()
            life_context = self.life_simulation.prepare_turn(user_input, history, emotions_before)
            self.debug_logger.log_info(
                "LIFE_PREP",
                "Life-Kontext vorbereitet",
                {
                    "phase": life_context.get("clock", {}).get("phase_label", "---"),
                    "activity": life_context.get("current_activity", "---"),
                    "mode": life_context.get("current_mode", "---"),
                    "dominant_need": (life_context.get("homeostasis", {}).get("dominant_need") or {}).get("name", "stability"),
                },
            )
            
            # === STEP 1: Intent Analysis ===
            intent_result = self._run_with_retries(
                step_number=1,
                step_name="Intent-Analyse",
                action=lambda: self.intent_processor.process(
                    user_input=user_input,
                    history=history,
                    current_emotions=emotions_before,
                ),
                validator=self._is_valid_intent_result,
                status_callback=status_callback,
            )
            
            self.debug_logger.log_step1_complete(
                intent_result.intent_type.value,
                intent_result.confidence
            )
            self.debug_logger.log_step1_json(intent_result.raw_json)
            available_tools = self._get_available_step1_tools()
            selected_tool_names = [tc.tool for tc in intent_result.tool_calls]
            unused_tool_names = [tool for tool in available_tools if tool not in selected_tool_names]
            self.debug_logger.log_info(
                "TOOL_DECISION",
                "Tool-Auswahl aus Step 1 analysiert",
                {
                    "available_tools": available_tools,
                    "selected_tools": selected_tool_names,
                    "unused_tools": unused_tool_names,
                },
            )
            
            # === AUSFÜHRUNG: Tool Calls ===
            self._execute_step1_tool_calls(intent_result.tool_calls)
            
            # === AUSFÜHRUNG: Emotions Updates ===
            combined_updates = dict(intent_result.emotions_update)
            for emotion_name, delta in life_context.get("homeostasis", {}).get("emotion_adjustments", {}).items():
                if emotion_name not in combined_updates:
                    combined_updates[emotion_name] = {"delta": delta, "reason": "homeostasis"}
            emotions_after, emotion_transitions = self._apply_emotion_updates(emotions_before, combined_updates)
            
            # === AUSFÜHRUNG: Short-Term Entries ===
            self._add_short_term_entries(intent_result.short_term_entries)
            
            # === AUSFÜHRUNG: Migration ===
            migrated = self.short_term_memory_v2.migrate_expired_entries()
            if migrated > 0:
                self.debug_logger.log_migration(migrated)
            
            # === CONTEXT AUFBAUEN ===
            context = self._build_context(intent_result.context_requirements)
            workspace = self._build_workspace_from_intent(intent_result, life_context)
            self.debug_logger.log_info(
                "CONTEXT",
                "Kontext und Workspace aufgebaut",
                {
                    "context_requirements": intent_result.context_requirements,
                    "context_chars": len(context or ""),
                    "workspace_focus": (workspace.get("dominant_focus") or {}).get("label", "---"),
                    "workspace_broadcast": workspace.get("broadcast", "---"),
                    "workspace_math_steps": len(workspace.get("math_trace", [])),
                },
            )
            
            # === STEP 2: Response Generation ===
            self.debug_logger.log_step2_start(get_active_model())
            
            response_data = self._run_with_retries(
                step_number=2,
                step_name="Antwortgenerierung",
                action=lambda: self._generate_response(
                    user_input=user_input,
                    history=history,
                    context=context,
                    emotions=emotions_after,
                    life_context=life_context,
                    global_workspace=workspace,
                ),
                validator=self._is_valid_generation_result,
                status_callback=status_callback,
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

            self.memory.add_memory(user_input, role="user")
            if response_data["response_text"].strip() and not looks_like_model_error(response_data["response_text"]):
                self.memory.add_memory(response_data["response_text"], role="assistant")
            self._set_last_memory_timestamp()
            
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
            sleep_result = self._schedule_sleep_phase_if_due()
            
            start_time_dt = datetime.now()
            processing_time_ms = 0
            if hasattr(self, '_processing_start_time'):
                processing_time_ms = (start_time_dt - self._processing_start_time).total_seconds() * 1000
            
            return {
                "response_text": response_data["response_text"],
                "emotions": emotions_after,
                "emotions_before": emotions_before,
                "emotions_delta": emotion_transitions,
                "thought_process": response_data.get("thought_process", ""),
                "model_reasoning": response_data.get("model_reasoning", ""),
                "reasoning_only": response_data.get("reasoning_only", False),
                "rag_memories": response_data.get("rag_memories", []),
                "emotion_steering": response_data.get("emotion_steering", {}),
                "prompt_emotion_mode": response_data.get("prompt_emotion_mode", ""),
                "intent_type": intent_result.intent_type.value,
                "intent_confidence": intent_result.confidence,
                "tool_calls_executed": len(intent_result.tool_calls),
                "available_tools": available_tools,
                "selected_tools": selected_tool_names,
                "unused_tools": unused_tool_names,
                "short_term_count": self.short_term_memory_v2.get_count(),
                "debug_log": self.debug_logger.get_formatted_log() if self.debug_logger.enabled else None,
                "debug_entries": self.debug_logger.get_entries_as_dict() if self.debug_logger.enabled else [],
                "intent_raw_json": intent_result.raw_json if hasattr(intent_result, 'raw_json') else {},
                "processing_time_ms": processing_time_ms,
                "life_snapshot": final_life_snapshot,
                "global_workspace": workspace,
                "action_plan": response_data.get("action_plan", {}),
                "dream_fragments": final_life_snapshot.get("dream_fragments", []),
                "provider": settings.llm_provider.value,
                "model": get_active_model(),
                "auto_sleep_triggered": sleep_result.get("triggered", False),
                "sleep_status": sleep_result.get("status", {}),
            }

        def _execute_step1_tool_calls(self, tool_calls: List[Any]):
            """Führt Tool Calls aus Step 1 aus."""
            from memory.context_files import ContextFilesManager

            if not tool_calls:
                self.debug_logger.log_info(
                    "TOOL_CALL",
                    "Keine Tool-Calls auszufuehren",
                    {"executed": 0},
                )
                return
             
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
                                   emotion_updates: Dict[str, Any]) -> tuple[Dict[str, int], Dict[str, Any]]:
            """Wendet Emotions Updates an."""
            emotions_after = emotions_before.copy()
            transition_meta: Dict[str, Any] = {}
            
            for emotion_name, update_data in emotion_updates.items():
                if emotion_name in emotions_after:
                    delta = getattr(update_data, "delta", update_data.get("delta", 0) if isinstance(update_data, dict) else 0)
                    reason = getattr(update_data, "reason", update_data.get("reason", "") if isinstance(update_data, dict) else "")
                    transition = calculate_emotion_transition(emotion_name, emotions_after[emotion_name], delta)
                    new_value = transition["after"]
                    
                    emotions_after[emotion_name] = new_value
                    transition_meta[emotion_name] = {
                        **transition,
                        "reason": reason,
                    }
                    
                    # Update im EmotionsEngine
                    if hasattr(self.emotions.state, emotion_name):
                        setattr(self.emotions.state, emotion_name, new_value)
                    
                    # Log
                    reason_text = reason or "intent/homeostasis"
                    if transition["softened"]:
                        reason_text = f"{reason_text} | raw {transition['raw_delta']:+d} -> angewendet {transition['applied_delta']:+d}"
                    self.debug_logger.log_emotion_update(
                        emotion_name,
                        emotions_before[emotion_name],
                        new_value,
                        reason_text
                    )

            if transition_meta:
                try:
                    self.emotions._save_state()
                except Exception:
                    pass
            
            return emotions_after, transition_meta

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
            self.debug_logger.log_info(
                "RAG",
                "Memory-Retrieval abgeschlossen",
                {
                    "top_k": settings.memory_top_k,
                    "memories_found": len(memories or []),
                    "memory_ids": [str(getattr(m, "id", ""))[:8] for m in (memories or [])[:8]],
                },
            )

            prompt_runtime = self._build_prompt_runtime(emotions)
            self.debug_logger.log_info(
                "EMOTION_STEERING",
                "Emotionssteuerung fuer Schritt 2 vorbereitet",
                {
                    "prompt_emotion_mode": prompt_runtime["prompt_emotion_mode"],
                    "forced_local_qwen_steering": prompt_runtime["force_steering"],
                    "steering_active": prompt_runtime["emotion_steering"].get("steering_active", False),
                    "dominant_vector": prompt_runtime["emotion_steering"].get("dominant_vector", "neutral"),
                    "dominant_strength": prompt_runtime["emotion_steering"].get("dominant_strength", 0.0),
                    "summary": prompt_runtime["emotion_steering"].get("summary", ""),
                    "emotion_state": prompt_runtime["emotion_steering"].get("emotion_state", {}),
                    "emotion_intensities": prompt_runtime["emotion_steering"].get("emotion_intensities", {}),
                    "base_vectors": prompt_runtime["emotion_steering"].get("base_vectors", []),
                    "active_vectors": prompt_runtime["emotion_steering"].get("active_vectors", []),
                    "composite_vectors": prompt_runtime["emotion_steering"].get("composite_vectors", []),
                    "composite_modes": prompt_runtime["emotion_steering"].get("composite_modes", []),
                },
            )
            
            # System Prompt bauen
            system_prompt = get_system_prompt_with_emotions(
                happiness=emotions["happiness"],
                trust=emotions["trust"],
                energy=emotions["energy"],
                curiosity=emotions["curiosity"],
                frustration=emotions["frustration"],
                motivation=emotions["motivation"],
                sadness=emotions["sadness"],
                include_emotion_status=prompt_runtime["use_prompt_emotions"],
                use_chain_of_thought=settings.chain_of_thought
            )
            
            # Context hinzufügen
            if context:
                system_prompt += f"\\n\\n{context}"

            system_prompt += "\\n\\n" + self.action_response.build_prompt_suffix(
                prompt_runtime["response_plan"],
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
                extra_body=prompt_runtime["steering_payload"] or None,
            )
            
            raw_response = self.brain.generate(messages, config=gen_config)
            display_response, thought, model_reasoning = self._extract_display_response(raw_response, phase="Schritt 2: Antwortgenerierung")
            self.debug_logger.log_info(
                "MODEL_OUTPUT",
                "Schritt-2-Ausgabe ausgewertet",
                {
                    "response_chars": len(display_response or ""),
                    "model_reasoning_chars": len(model_reasoning or ""),
                    "thought_chars": len(thought or ""),
                    "looks_like_error": looks_like_model_error(display_response or ""),
                },
            )
            
            return {
                "response_text": display_response,
                "thought_process": thought,
                "model_reasoning": model_reasoning,
                "reasoning_only": bool((thought or model_reasoning) and display_response.strip() == "CHAPPiE schweigt..."),
                "rag_memories": memories,
                "emotion_steering": prompt_runtime["emotion_steering"],
                "prompt_emotion_mode": prompt_runtime["prompt_emotion_mode"],
                "action_plan": self.action_response.build_action_plan(
                    {
                        "response_strategy": "conversational",
                        "tone": prompt_runtime["response_plan"].get("tone", "state_driven"),
                        "response_guidance": "Erzeuge eine kohärente Antwort, die innere Zustände berücksichtigt.",
                    },
                    life_context or {},
                    global_workspace or {},
                ),
            }

        def _extract_legacy_generation(
            self,
            messages: List[Message],
            gen_config: GenerationConfig,
            memories: List[Any],
        ) -> Dict[str, Any]:
            raw_response = self.brain.generate(messages, config=gen_config)
            display_response, thought, model_reasoning = self._extract_display_response(raw_response, phase="Legacy-Antwortgenerierung")
            return {
                "response_text": display_response,
                "thought_process": thought,
                "model_reasoning": model_reasoning,
                "reasoning_only": bool((thought or model_reasoning) and display_response.strip() == "CHAPPiE schweigt..."),
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

        def _process_legacy(
            self,
            user_input: str,
            history: List[Dict],
            status_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        ) -> Dict[str, Any]:
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
            prompt_runtime = self._build_prompt_runtime(state.__dict__)
            self.debug_logger.log_info(
                "EMOTION_STEERING",
                "Legacy-Emotionssteuerung vorbereitet",
                {
                    "prompt_emotion_mode": prompt_runtime["prompt_emotion_mode"],
                    "forced_local_qwen_steering": prompt_runtime["force_steering"],
                    "steering_active": prompt_runtime["emotion_steering"].get("steering_active", False),
                    "dominant_vector": prompt_runtime["emotion_steering"].get("dominant_vector", "neutral"),
                    "dominant_strength": prompt_runtime["emotion_steering"].get("dominant_strength", 0.0),
                    "summary": prompt_runtime["emotion_steering"].get("summary", ""),
                    "emotion_state": prompt_runtime["emotion_steering"].get("emotion_state", {}),
                    "emotion_intensities": prompt_runtime["emotion_steering"].get("emotion_intensities", {}),
                    "base_vectors": prompt_runtime["emotion_steering"].get("base_vectors", []),
                    "composite_vectors": prompt_runtime["emotion_steering"].get("composite_vectors", []),
                },
            )
            system_prompt = get_system_prompt_with_emotions(
                **state.__dict__,
                include_emotion_status=prompt_runtime["use_prompt_emotions"],
                use_chain_of_thought=settings.chain_of_thought
            )
            system_prompt += "\n\n" + self.action_response.build_prompt_suffix(
                prompt_runtime["response_plan"],
                life_context,
                {"broadcast": "legacy-path", "dominant_focus": {"label": "Legacy Input"}, "guidance": "Halte das Verhalten stabil."},
            )
            
            messages = self.brain.build_prompt(system_prompt, memories_for_prompt, user_input, history)
            
            # Generierung
            gen_config = GenerationConfig(
                max_tokens=settings.max_tokens,
                temperature=settings.temperature,
                stream=False,
                extra_body=prompt_runtime["steering_payload"] or None,
            )
            legacy_response = self._run_with_retries(
                step_number=2,
                step_name="Legacy-Antwortgenerierung",
                action=lambda: self._extract_legacy_generation(messages, gen_config, memories),
                validator=self._is_valid_generation_result,
                status_callback=status_callback,
            )
            display_response = legacy_response["response_text"]
            thought = legacy_response.get("thought_process", "")
            self.debug_logger.log_info(
                "LEGACY",
                "Legacy-Antwort generiert",
                {
                    "response_chars": len(display_response or ""),
                    "thought_chars": len(thought or ""),
                    "memories_found": len(legacy_response.get("rag_memories") or []),
                },
            )
            
            # Speichern
            self.memory.add_memory(user_input, role="user")
            if display_response.strip() and not looks_like_model_error(display_response):
                self.memory.add_memory(display_response, role="assistant")
            self._set_last_memory_timestamp()
            
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
            sleep_result = self._schedule_sleep_phase_if_due()
            
            return {
                "response_text": display_response,
                "emotions": emotions_after,
                "emotions_before": emotions_before,
                "emotions_delta": self._calculate_emotion_delta(emotions_before, emotions_after),
                "thought_process": thought,
                "model_reasoning": legacy_response.get("model_reasoning", ""),
                "reasoning_only": legacy_response.get("reasoning_only", False),
                "rag_memories": legacy_response.get("rag_memories", memories),
                "emotion_steering": prompt_runtime["emotion_steering"],
                "prompt_emotion_mode": prompt_runtime["prompt_emotion_mode"],
                "intent_type": "legacy",
                "intent_confidence": 1.0,
                "tool_calls_executed": 0,
                "available_tools": self._get_available_step1_tools(),
                "selected_tools": [],
                "unused_tools": self._get_available_step1_tools(),
                "short_term_count": self.short_term_memory_v2.get_count(),
                "debug_log": self.debug_logger.get_formatted_log() if self.debug_logger.enabled else None,
                "debug_entries": self.debug_logger.get_entries_as_dict() if self.debug_logger.enabled else [],
                "life_snapshot": final_life_snapshot,
                "global_workspace": {"broadcast": "legacy-path"},
                "action_plan": {"strategy": "conversational", "tone": prompt_runtime["response_plan"].get("tone", "state_driven")},
                "dream_fragments": final_life_snapshot.get("dream_fragments", []),
                "provider": settings.llm_provider.value,
                "model": get_active_model(),
                "auto_sleep_triggered": sleep_result.get("triggered", False),
                "sleep_status": sleep_result.get("status", {}),
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

