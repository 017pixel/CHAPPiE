"""Shared entry orchestration for normal and streamed chat turns."""

from __future__ import annotations

import json
import re
import time
from datetime import datetime
from typing import Any, Callable, Dict, Generator, List, Optional

from config.config import settings
from config.emotions import normalize_emotion_state
from config.prompts import (
    format_consolidated_memories,
)
from memory.emotions_engine import analyze_sentiment_simple, calculate_emotion_transition
from brain.response_parser import (
    looks_like_model_error,
    sanitize_visible_response,
)
from web_infrastructure.generation import response_memory_top_k_for_intent
from web_infrastructure.turn_context import (
    context_allows_long_term_memory,
    is_isolated_request,
    is_self_contained_math_query,
    is_transient_problem_statement,
)


from typing import TYPE_CHECKING

from web_infrastructure.contracts import ResponseEnvelope, StreamEvent, TurnContext

if TYPE_CHECKING:
    from web_infrastructure.chappie_runtime import CHAPPiERuntime


class TurnPipeline:
    """Run the common turn setup and select only the output adapter."""

    def __init__(self, runtime: "CHAPPiERuntime") -> None:
        self._runtime = runtime

    def process(self, turn: TurnContext) -> ResponseEnvelope:
        self._runtime._begin_turn(turn, streaming=False)
        return self._runtime._process_two_step(
            turn.user_input,
            turn.history,
            status_callback=turn.status_callback,
            temporal_context=turn.temporal_context,
        )

    def process_stream(self, turn: TurnContext) -> Generator[StreamEvent, None, None]:
        self._runtime._begin_turn(turn, streaming=True)
        yield from self._runtime._process_two_step_stream(
            turn.user_input,
            turn.history,
            turn.status_callback,
            temporal_context=turn.temporal_context,
        )



class RuntimeTurnPipelineMixin:
    """Internal mixin extracted from the former backend wrapper."""

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

    def _build_workspace_from_intent(
        self,
        intent_result,
        life_context: Dict[str, Any],
        memories: List[Any] | None = None,
        search_query: str = "",
    ) -> Dict[str, Any]:
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
        query = search_query or " ".join(intent_result.entities[:4])
        hippocampus = {"search_query": query}
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
        return normalize_emotion_state(state.to_dict())

    def _process_two_step(
        self,
        user_input: str,
        history: List[Dict],
        status_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        temporal_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Zwei-Schritte Verarbeitung.
        Step 1: Intent Analysis mit kleinem Modell
        Step 2: Response Generation mit Hauptmodell
        """
        self.debug_logger.log_step1_start()
        
        # Emotionen Snapshot
        emotions_before = self._get_emotions_snapshot()
        life_checkpoint = self._turn_checkpoint()
        life_context = self._prepare_life_turn(user_input, history, emotions_before, temporal_context=temporal_context)
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
        try:
            intent_result = self._run_with_retries(
                step_number=1,
                step_name="Intent-Analyse",
                action=lambda: self.intent_processor.process(
                    user_input=user_input,
                    history=history,
                    current_emotions=emotions_before,
                    deterministic=self.research_mode,
                ),
                validator=self._is_valid_intent_result,
                status_callback=status_callback,
            )
        except Exception:
            self._rollback_failed_turn(emotions_before, life_checkpoint)
            raise
        
        self.debug_logger.log_step1_complete(
            intent_result.intent_type.value,
            intent_result.confidence
        )
        self.debug_logger.log_step1_json(intent_result.raw_json)
        input_classification = self._build_input_classification(intent_result)
        self.debug_logger.log_info(
            "INPUT_CLASSIFICATION",
            "Input-Klassifikation aus Step 1 aufbereitet",
            input_classification,
        )
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
        
        # === AUSFUEHRUNG: Tool Calls ===
        self._execute_step1_tool_calls(intent_result.tool_calls)
        
        # === AUSFUEHRUNG: Emotions Updates ===
        combined_updates = dict(intent_result.emotions_update)
        for emotion_name, delta in life_context.get("homeostasis", {}).get("emotion_adjustments", {}).items():
            if emotion_name not in combined_updates:
                combined_updates[emotion_name] = {"delta": delta, "reason": "homeostasis"}

        emotions_after, emotion_transitions = self._apply_input_emotions(
            emotions_before,
            combined_updates,
            user_input,
        )
        
        # === AUSFUEHRUNG: Short-Term Entries ===
        self._add_short_term_entries(intent_result.short_term_entries)
        
        # === AUSFUEHRUNG: Migration ===
        migrated = self.short_term_memory.migrate_expired_entries()
        if migrated > 0:
            self.debug_logger.log_migration(migrated)

        retrieval_keywords, exact_entities, fact_lookup_intent = self._intent_retrieval_terms(intent_result, input_classification)
        context_requirements = self._effective_context_requirements(user_input, intent_result.context_requirements)
        transient_problem = is_transient_problem_statement(user_input) and not is_self_contained_math_query(user_input)
        memory_allowed = (
            self._feature_enabled("memory")
            and context_allows_long_term_memory(context_requirements)
            and not transient_problem
        )
        isolated_request = is_isolated_request(context_requirements)
        closed_reasoning = is_self_contained_math_query(user_input)
        if closed_reasoning or not memory_allowed:
            retrieval_keywords, exact_entities, fact_lookup_intent = [], [], False
        if transient_problem:
            self.debug_logger.log_info(
                "MEMORY_POLICY",
                "Transiente Problem-/Frustmeldung ohne Alt-Summaries verarbeitet",
                {"memory_context_allowed": False, "reason": "transient_problem_statement"},
            )
        intent_query_source = self._retrieval_query_from_terms(retrieval_keywords, exact_entities, user_input)
        intent_memory_query = intent_query_source if (retrieval_keywords or exact_entities) else self._local_retrieval_query(intent_query_source)
        intent_memories = [] if closed_reasoning or not memory_allowed else self._search_memory(
            intent_memory_query or user_input,
            top_k=min(settings.memory_top_k, 8),
            optimize_query=False,
        )
        intent_memory_trace = self._build_memory_trace(
            query=intent_memory_query,
            memories=intent_memories,
            stage="intent_context",
        )
        self.debug_logger.log_info(
            "MEMORY_TRACE",
            "Intent-nahe Erinnerungen fuer Kontext priorisiert",
            intent_memory_trace,
        )

        # === CONTEXT AUFBAUEN ===
        # The synchronous route must use the same query-aware Context and
        # STM path as streaming. Without the input, short-term recall was
        # silently empty even when Step 1 requested it.
        context = self._build_context(context_requirements, user_input=user_input)
        workspace = self._build_workspace_from_intent(
            intent_result,
            life_context,
            memories=intent_memories,
            search_query=intent_memory_query,
        )
        self.debug_logger.log_info(
            "CONTEXT",
            "Kontext und Workspace aufgebaut",
            {
                "context_requirements": context_requirements,
                "context_chars": len(context or ""),
                "workspace_focus": (workspace.get("dominant_focus") or {}).get("label", "---"),
                "workspace_broadcast": workspace.get("broadcast", "---"),
                "workspace_math_steps": len(workspace.get("math_trace", [])),
            },
        )
        
        # === STEP 2: Response Generation ===
        self.debug_logger.log_step2_start(self._chat_model())
        
        generation_started = time.perf_counter()
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
                preloaded_memories=intent_memories,
                memory_trace_seed=intent_memory_trace,
                intent_type=intent_result.intent_type,
                retrieval_keywords=retrieval_keywords,
                exact_entities=exact_entities,
                fact_lookup_intent=fact_lookup_intent,
                allow_memory_context=memory_allowed,
                isolated_request=isolated_request,
            ),
            validator=self._is_valid_generation_result,
            status_callback=status_callback,
        )
        response_data["timing"] = self._build_generation_timing(
            (time.perf_counter() - generation_started) * 1000,
            response_data.get("formatted_answer") or response_data.get("response_text", ""),
            response_data.get("formatted_cot") or response_data.get("thought_process", "") or response_data.get("model_reasoning", ""),
        )
        final_life_snapshot = self._finalize_life_turn(
            user_input=user_input,
            response_text=response_data["response_text"],
            emotions_after=emotions_after,
            prefrontal=response_data.get("action_plan", {}),
            global_workspace=workspace,
        )
        
        self.debug_logger.log_step2_complete(
            len(response_data["response_text"].split())
        )
        tone_decision = response_data.get("tone_decision", {})
        memory_trace = response_data.get("memory_trace", intent_memory_trace)
        causal_trace = self._build_causal_trace(
            input_classification=input_classification,
            memory_trace=memory_trace,
            emotion_transitions=emotion_transitions,
            emotion_steering=response_data.get("emotion_steering", {}),
            life_context=life_context,
            workspace=workspace,
            tone_decision=tone_decision,
        )
        self.debug_logger.log_info(
            "CAUSAL_TRACE",
            "Ursache-Wirkung-Kette fuer die finale Antwort aufgebaut",
            {"steps": causal_trace},
        )

        self.persistence.persist_exchange(user_input, response_data["response_text"])
        sleep_result = self._schedule_sleep_phase_if_due()
        
        # Auto-periodische Context-Aktualisierung (alle 5 Interaktionen)
        if self.sleep_handler._state.get("interaction_count_since_sleep", 0) % 5 == 4:
            try:
                self.context_files.update_soul({
                    "evolution_note": f"CHAPPiE war aktiv in {intent_result.intent_type.value}-Interaktionen"
                })
            except Exception:
                pass
        
        start_time_dt = datetime.now()
        processing_time_ms = 0
        if hasattr(self, '_processing_start_time'):
            processing_time_ms = (start_time_dt - self._processing_start_time).total_seconds() * 1000
        
        return {
            "response_text": response_data["response_text"],
            "formatted_cot": response_data.get("formatted_cot", ""),
            "formatted_answer": response_data.get("formatted_answer", ""),
            "formatting_failed": response_data.get("formatting_failed", False),
            "formatting_source": response_data.get("formatting_source", "local_fallback"),
            "formatting_model": response_data.get("formatting_model", "?"),
            "timing": response_data.get("timing", {}),
            "emotions": emotions_after,
            "emotions_before": emotions_before,
            "emotions_delta": emotion_transitions,
            "thought_process": response_data.get("thought_process", ""),
            "model_reasoning": response_data.get("model_reasoning", ""),
            "reasoning_only": response_data.get("reasoning_only", False),
            "input_classification": input_classification,
            "rag_memories": response_data.get("rag_memories", []),
            "keyword_rag_memories": response_data.get("keyword_rag_memories", []),
            "emotion_steering": response_data.get("emotion_steering", {}),
            "steering_runtime": response_data.get("steering_runtime", getattr(self.brain, "last_steering_report", {})),
            "memory_trace": memory_trace,
            "tone_decision": tone_decision,
            "causal_trace": causal_trace,
            "prompt_emotion_mode": response_data.get("prompt_emotion_mode", ""),
            "intent_type": intent_result.intent_type.value,
            "intent_confidence": intent_result.confidence,
            "tool_calls_executed": len(intent_result.tool_calls),
            "available_tools": available_tools,
            "selected_tools": selected_tool_names,
            "unused_tools": unused_tool_names,
            "short_term_count": self.short_term_memory.get_count(),
            "debug_log": self.debug_logger.get_formatted_log() if self.debug_logger.enabled else None,
            "debug_entries": self.debug_logger.get_entries_as_dict() if self.debug_logger.enabled else [],
            "intent_raw_json": intent_result.raw_json if hasattr(intent_result, 'raw_json') else {},
            "processing_time_ms": processing_time_ms,
            "life_snapshot": final_life_snapshot,
            "global_workspace": workspace,
            "action_plan": response_data.get("action_plan", {}),
            "dream_fragments": final_life_snapshot.get("dream_fragments", []),
            "provider": self._chat_provider().value,
            "model": self._chat_model(),
            "auto_sleep_triggered": sleep_result.get("triggered", False),
            "sleep_status": sleep_result.get("status", {}),
            "memory_consolidation": response_data.get("memory_consolidation", {}),
            "context_budget": response_data.get("context_budget", {}),
        }

    def _execute_native_tool_calls(self, tool_calls: List[Dict]) -> List[str]:
        """Fuehrt native OpenAI-Format Tool Calls aus. Gibt Ergebnis-Messages zurueck."""
        if self.research_mode:
            return ["Tools im isolierten Research-Modus deaktiviert."]
        results = []
        for tc in tool_calls:
            func = tc.get("function", {})
            name = func.get("name", "")
            try:
                args_str = func.get("arguments", "{}")
                args = json.loads(args_str) if isinstance(args_str, str) else args_str
            except json.JSONDecodeError:
                results.append(f"Tool {name}: JSON Parse Error")
                continue
            try:
                result_text = self.function_registry.execute(name, args)
                results.append(f"Tool {name}: {result_text}")
                self.debug_logger.log_tool_call(name, "native", args, True)
            except Exception as e:
                results.append(f"Tool {name}: Error - {e}")
        return results

    def _execute_step1_tool_calls(self, tool_calls: List[Any]):
        """Fuehrt Tool Calls aus Step 1 aus."""

        if self.research_mode:
            self.debug_logger.log_info(
                "TOOL_CALL",
                "Tool-Ausfuehrung im isolierten Research-Modus deaktiviert",
                {"planned": len(tool_calls or [])},
            )
            return

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
                    
                    self.short_term_memory.add_entry(
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

    def _apply_input_emotions(
        self,
        emotions_before: Dict[str, int],
        combined_updates: Dict[str, Any],
        user_input: str,
    ) -> tuple[Dict[str, int], Dict[str, Any]]:
        """Apply direct input signals and model/life deltas in one turn.

        Previously any non-zero homeostasis update suppressed the direct
        sentiment signal. Since Life always contributes at least one
        adjustment, messages such as "nichts funktioniert" could leave
        the visible emotional state unchanged. The deterministic local
        signal now runs first, then intent/homeostasis is layered on top.
        """
        sentiment = analyze_sentiment_simple(user_input)
        has_any_delta = any(
            (getattr(update, "delta", update.get("delta", 0) if isinstance(update, dict) else 0) != 0)
            for update in combined_updates.values()
        )

        if sentiment != "NEUTRAL":
            self.emotions.update_from_sentiment(sentiment)
        signal_state = self._get_emotions_snapshot()

        if not has_any_delta:
            if sentiment == "NEUTRAL":
                self.emotions.update_from_sentiment(sentiment)
                signal_state = self._get_emotions_snapshot()
            return signal_state, self._calculate_emotion_delta(emotions_before, signal_state)

        emotions_after, emotion_transitions = self._apply_emotion_updates(signal_state, combined_updates)

        # Return the observable before/after result for all ten dimensions;
        # the detailed transition metadata from intent/homeostasis remains
        # available where it exists.
        observable_delta = self._calculate_emotion_delta(emotions_before, emotions_after)
        for emotion_name, delta in observable_delta.items():
            existing = emotion_transitions.get(emotion_name)
            existing_change = 0
            if isinstance(existing, dict):
                existing_change = self._safe_int(
                    existing.get("applied_delta", existing.get("change", 0)),
                    0,
                )
            # Homeostasis may have supplied a zero transition for a
            # dimension that the direct input signal changed. Preserve
            # the actual observable before/after values in that case.
            if not isinstance(existing, dict) or existing_change == 0:
                emotion_transitions[emotion_name] = delta

        return emotions_after, emotion_transitions

    def _add_short_term_entries(self, entries: List[Any]):
        """Fuegt Short-Term Eintraege hinzu."""
        for entry in entries:
            try:
                self.short_term_memory.add_entry(
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
                    f"Fehler beim Hinzufuegen: {str(e)}"
                )

    def _consolidate_memories_for_prompt(
        self, ltm_memories: list, stm_entries: list
    ) -> tuple[str, dict]:
        """Konsolidiert LTM + STM via Groq gpt-oss-120b zu strukturiertem JSON.
        Returns (formatted_prompt_str, consolidation_meta)."""
        if not ltm_memories and not stm_entries:
            return "", {"ltm_loaded": 0, "stm_loaded": 0}

        ltm_raw: list[dict[str, Any]] = []
        for m in ltm_memories:
            ltm_raw.append({
                "id": str(getattr(m, "id", "")),
                "date": str(getattr(m, "created_at", "") or getattr(m, "timestamp", "")),
                "role": str(getattr(m, "role", "unknown")),
                "relevance": float(getattr(m, "relevance_score", 0.0) or 0.0),
                "content": str(getattr(m, "content", "")),
            })
        stm_raw: list[dict[str, Any]] = []
        for e in stm_entries:
            stm_raw.append({
                "id": f"stm_{getattr(e, 'id', '')}",
                "date": str(getattr(e, "created_at", "")),
                "category": str(getattr(e, "category", "general")),
                "importance": str(getattr(e, "importance", "medium")),
                "content": str(getattr(e, "content", "")),
            })

        # A single local vLLM model must never trigger an additional cloud
        # completion while assembling a prompt.  Retrieval remains active;
        # only the optional cloud consolidation is skipped.
        if self._single_local_chat_mode():
            return "", {
                "ltm_loaded": len(ltm_raw),
                "stm_loaded": len(stm_raw),
                "skipped": True,
                "skip_reason": "single_local_model",
            }

        prompt = (
            "Konsolidiere folgende Erinnerungen gemaess System-Prompt in ein JSON-Array.\n\n"
            + json.dumps({"ltm": ltm_raw, "stm": stm_raw}, ensure_ascii=False, indent=2)
        )
        messages = [{"role": "user", "content": prompt}]

        try:
            import openai
            client = openai.OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=settings.groq_api_key,
                timeout=20.0,
            )
            response = client.chat.completions.create(
                model=settings.memory_consolidation_groq_model,
                messages=messages,
                max_tokens=settings.memory_consolidation_max_tokens,
                temperature=0.1,
                stream=False,
            )
            raw = response.choices[0].message.content or ""
            parsed = json.loads(raw)
        except Exception:
            parsed = {}

        formatted = format_consolidated_memories(parsed) if parsed else ""
        meta = {
            "ltm_loaded": len(ltm_raw),
            "stm_loaded": len(stm_raw),
            "ltm_consolidated": len(parsed.get("ltm_consolidated", [])),
            "stm_consolidated": len(parsed.get("stm_consolidated", [])),
            "duplicates_merged": parsed.get("meta", {}).get("duplicates_merged", 0),
            "critical_events": parsed.get("meta", {}).get("critical_events_found", 0),
            "raw_ltm": [{"id": e["id"], "relevance": e["relevance"], "content": e["content"][:200]} for e in ltm_raw],
            "raw_stm": [{"id": e["id"], "category": e["category"], "content": e["content"][:200]} for e in stm_raw],
            "consolidated_json": parsed,
        }
        return formatted, meta

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

    def _process_two_step_stream(
        self,
        user_input: str,
        history: List[Dict],
        status_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        temporal_context: Optional[Dict[str, Any]] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Zwei-Schritte Verarbeitung mit Token-Streaming.
        Step 1: Intent Analysis (synchron)
        Step 2: Response Generation (streaming)
        """
        turn_started = time.perf_counter()

        def _pipeline_status(stage: str, step: int, status_text: str, **details: Any) -> Dict[str, Any]:
            payload = {
                "event": "status",
                "stage": stage,
                "stage_key": stage,
                "step": step,
                "status_text": status_text,
                "elapsed_ms": round((time.perf_counter() - turn_started) * 1000),
                "provider": self._chat_provider().value,
                "model": self._chat_model(),
                **details,
            }
            if status_callback:
                try:
                    status_callback(payload)
                except Exception:
                    pass
            return payload

        yield _pipeline_status("intent", 1, "Intent-Analyse gestartet")
        self.debug_logger.log_step1_start()

        emotions_before = self._get_emotions_snapshot()
        life_checkpoint = self._turn_checkpoint()
        life_context = self._prepare_life_turn(user_input, history, emotions_before, temporal_context=temporal_context)

        # === STEP 1: Intent Analysis ===
        try:
            intent_result = self._run_with_retries(
                step_number=1,
                step_name="Intent-Analyse",
                action=lambda: self.intent_processor.process(
                    user_input=user_input,
                    history=history,
                    current_emotions=emotions_before,
                    deterministic=self.research_mode,
                ),
                validator=self._is_valid_intent_result,
                status_callback=status_callback,
            )
        except Exception:
            self._rollback_failed_turn(emotions_before, life_checkpoint)
            raise

        self.debug_logger.log_step1_complete(
            intent_result.intent_type.value,
            intent_result.confidence
        )
        self.debug_logger.log_step1_json(intent_result.raw_json)
        input_classification = self._build_input_classification(intent_result)
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

        # === AUSFUEHRUNG: Tool Calls ===
        self._execute_step1_tool_calls(intent_result.tool_calls)

        # === AUSFUEHRUNG: Emotions Updates ===
        combined_updates = dict(intent_result.emotions_update)
        for emotion_name, delta in life_context.get("homeostasis", {}).get("emotion_adjustments", {}).items():
            if emotion_name not in combined_updates:
                combined_updates[emotion_name] = {"delta": delta, "reason": "homeostasis"}

        emotions_after, emotion_transitions = self._apply_input_emotions(
            emotions_before,
            combined_updates,
            user_input,
        )

        yield _pipeline_status(
            "memory",
            1,
            "Memory und Kontext werden aufgebaut",
            emotion_state=emotions_after,
            emotion_delta=emotion_transitions,
        )

        # === AUSFUEHRUNG: Short-Term Entries ===
        self._add_short_term_entries(intent_result.short_term_entries)

        # === AUSFUEHRUNG: Migration ===
        migrated = self.short_term_memory.migrate_expired_entries()
        if migrated > 0:
            self.debug_logger.log_migration(migrated)

        retrieval_keywords, exact_entities, fact_lookup_intent = self._intent_retrieval_terms(intent_result, input_classification)
        context_requirements = self._effective_context_requirements(user_input, intent_result.context_requirements)
        transient_problem = is_transient_problem_statement(user_input) and not is_self_contained_math_query(user_input)
        memory_allowed = (
            self._feature_enabled("memory")
            and context_allows_long_term_memory(context_requirements)
            and not transient_problem
        )
        isolated_request = is_isolated_request(context_requirements)
        closed_reasoning = is_self_contained_math_query(user_input)
        if closed_reasoning or not memory_allowed:
            retrieval_keywords, exact_entities, fact_lookup_intent = [], [], False
        if transient_problem:
            self.debug_logger.log_info(
                "MEMORY_POLICY",
                "Transiente Problem-/Frustmeldung ohne Alt-Summaries verarbeitet",
                {"memory_context_allowed": False, "reason": "transient_problem_statement"},
            )
        intent_query_source = self._retrieval_query_from_terms(retrieval_keywords, exact_entities, user_input)
        intent_memory_query = intent_query_source if (retrieval_keywords or exact_entities) else self._local_retrieval_query(intent_query_source)
        intent_memories = [] if closed_reasoning or not memory_allowed else self._search_memory(
            intent_memory_query or user_input,
            top_k=response_memory_top_k_for_intent(
                intent_result.intent_type,
                settings.memory_top_k,
                getattr(settings, "memory_prompt_top_k", 8),
            ),
            optimize_query=False,
        )
        intent_memory_trace = self._build_memory_trace(
            query=intent_memory_query,
            memories=intent_memories,
            stage="intent_context",
        )
        self.debug_logger.log_info(
            "MEMORY_TRACE",
            "Intent-nahe Erinnerungen fuer Kontext priorisiert",
            intent_memory_trace,
        )

        # === CONTEXT AUFBAUEN ===
        context_components = self._build_context_components(context_requirements, user_input=user_input)
        context = "\n\n".join(part for part in context_components.values() if part)
        workspace = self._build_workspace_from_intent(
            intent_result,
            life_context,
            memories=intent_memories,
            search_query=intent_memory_query,
        )
        self.debug_logger.log_info(
            "CONTEXT",
            "Kontext und Workspace aufgebaut",
            {
                "context_requirements": context_requirements,
                "context_chars": len(context or ""),
                "workspace_focus": (workspace.get("dominant_focus") or {}).get("label", "---"),
                "workspace_broadcast": workspace.get("broadcast", "---"),
                "workspace_math_steps": len(workspace.get("math_trace", [])),
            },
        )

        # === STEP 2: Response Generation (streaming) ===
        steering_preview = self._build_prompt_runtime(emotions_after).get("emotion_steering", {})
        yield _pipeline_status(
            "steering",
            2,
            "Emotion-Steering aktiv",
            steering_active=bool(steering_preview.get("steering_active")),
            dominant_vector=steering_preview.get("dominant_vector", "neutral"),
            active_vectors=len(steering_preview.get("active_vectors", []) or []),
            emotion_state=steering_preview.get("emotion_state", emotions_after),
        )
        self.debug_logger.log_step2_start(self._chat_model())
        yield _pipeline_status("ttft", 2, "Antwortgenerierung gestartet", ttft_ms=None, answer_tokens=0)

        timing = {}
        raw_response = ""
        meta: Dict[str, Any] = {}
        streamed_visible = ""
        first_provider_output_at: Optional[float] = None
        gen_start = time.perf_counter()
        last_progress_at = 0.0
        suppress_fact_question_tokens = fact_lookup_intent and (
            "?" in user_input
            or any(marker in user_input.casefold() for marker in ("erinnerst du", "weißt du noch", "weisst du noch"))
        )
        try:
            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                attempt_parts: List[str] = []
                attempt_visible = ""
                attempt_first_output_at: Optional[float] = None
                try:
                    token_generator, attempt_meta = self._generate_response_stream_raw(
                        user_input=user_input,
                        history=history,
                        context=context,
                        emotions=emotions_after,
                        life_context=life_context,
                        global_workspace=workspace,
                        preloaded_memories=intent_memories,
                        memory_trace_seed=intent_memory_trace,
                        intent_type=intent_result.intent_type,
                        retrieval_keywords=retrieval_keywords,
                        exact_entities=exact_entities,
                        fact_lookup_intent=fact_lookup_intent,
                        allow_memory_context=memory_allowed,
                        isolated_request=isolated_request,
                        context_components=context_components,
                    )
                    for raw_part in token_generator:
                        now = time.perf_counter()
                        if attempt_first_output_at is None:
                            attempt_first_output_at = now
                        attempt_parts.append(str(raw_part or ""))
                        raw_candidate = "".join(attempt_parts)
                        visible_candidate = self._stream_visible_candidate(raw_candidate)
                        if not suppress_fact_question_tokens and visible_candidate.startswith(attempt_visible):
                            fragment = visible_candidate[len(attempt_visible):]
                            if fragment:
                                attempt_visible = visible_candidate
                                yield {"event": "token", "content": fragment, "token_type": "answer"}

                        if now - last_progress_at >= 0.12:
                            elapsed = max(0, round((now - gen_start) * 1000))
                            token_count = len(re.findall(r"\S+", attempt_visible))
                            rate = round(token_count / (elapsed / 1000), 1) if token_count and elapsed else 0.0
                            yield _pipeline_status(
                                "streaming" if attempt_visible else "ttft",
                                2,
                                "Antwort wird gestreamt" if attempt_visible else "Warte auf erstes sichtbares Token",
                                ttft_ms=round((attempt_first_output_at - gen_start) * 1000) if attempt_first_output_at else None,
                                token_count=token_count,
                                answer_tokens=token_count,
                                answer_time_ms=elapsed,
                                tokens_per_second=rate,
                            )
                            last_progress_at = now

                    candidate_response = "".join(attempt_parts)
                    attempt_meta = dict(attempt_meta or {})
                    attempt_meta["steering_runtime"] = getattr(self.brain, "last_steering_report", {})
                    streamed_result = {"response_text": candidate_response, "meta": attempt_meta}
                    if not self._is_valid_generation_result(streamed_result):
                        raise ValueError(candidate_response or "Leere Modellantwort")
                    raw_response = candidate_response
                    meta = attempt_meta
                    streamed_visible = attempt_visible
                    first_provider_output_at = attempt_first_output_at
                    break
                except Exception as exc:
                    if attempt >= max_attempts or attempt_visible:
                        raise
                    yield _pipeline_status(
                        "ttft",
                        2,
                        f"Generierung wird wiederholt ({attempt + 1}/{max_attempts})",
                        retry_attempt=attempt + 1,
                        error=str(exc),
                    )
                    time.sleep(1.0)
            else:
                raise ValueError("Leere Modellantwort")

            gen_end = time.perf_counter()
            total_gen_ms = round((gen_end - gen_start) * 1000)
            ttft_ms = round((first_provider_output_at - gen_start) * 1000) if first_provider_output_at else total_gen_ms
            display_response, thought, model_reasoning = self._extract_display_response(raw_response, phase="Schritt 2: Antwortgenerierung")
            keyword_memories = meta.get("keyword_rag_memories", []) if isinstance(meta, dict) else []
            semantic_memories = meta.get("rag_memories", []) if isinstance(meta, dict) else []
            deterministic_fact_answer = self._build_deterministic_fact_answer(
                user_input,
                list(keyword_memories or []) + list(semantic_memories or []),
            )
            if deterministic_fact_answer:
                display_response = deterministic_fact_answer
                formatted_stream = {
                    "cot": "",
                    "answer": deterministic_fact_answer,
                    "formatting_failed": False,
                    "formatting_source": "deterministic_user_memory",
                    "formatting_model": "local_fact_extractor",
                    "answer_is_fallback": False,
                }
            else:
                formatted_stream = self._format_via_groq(raw_response)
            self.debug_logger.log_info(
                "MODEL_OUTPUT",
                "Schritt-2-Ausgabe ausgewertet",
                {
                    "response_chars": len(display_response or ""),
                    "model_reasoning_chars": len(model_reasoning or ""),
                    "thought_chars": len(thought or ""),
                    "looks_like_error": looks_like_model_error(display_response or ""),
                    "formatting_failed": formatted_stream.get("formatting_failed", False),
                    "formatting_source": formatted_stream.get("formatting_source", "local_fallback"),
                    "formatting_model": formatted_stream.get("formatting_model", "?"),
                },
            )
            yield _pipeline_status(
                "format",
                2,
                "Antwort formatiert",
                formatting_failed=bool(formatted_stream.get("formatting_failed", False)),
                token_count=len(re.findall(r"\S+", streamed_visible)),
            )

        except Exception as exc:
            error_text = self._format_generation_error("Antwortgenerierung", str(exc))
            self._rollback_failed_turn(emotions_before, life_checkpoint)
            yield _pipeline_status("done", 2, "Antwort fehlgeschlagen", error=error_text)
            yield {"event": "error", "error": error_text}
            return

        final_life_snapshot = self._finalize_life_turn(
            user_input=user_input,
            response_text=display_response,
            emotions_after=emotions_after,
            prefrontal={"response_strategy": "conversational"},
            global_workspace=workspace,
        )

        tone_decision = meta.get("tone_decision", {}) if 'meta' in dir() else {}
        memory_trace = meta.get("memory_trace", intent_memory_trace) if 'meta' in dir() else intent_memory_trace
        causal_trace = self._build_causal_trace(
            input_classification=input_classification,
            memory_trace=memory_trace,
            emotion_transitions=emotion_transitions,
            emotion_steering=meta.get("emotion_steering", {}) if 'meta' in dir() else {},
            life_context=life_context,
            workspace=workspace,
            tone_decision=tone_decision,
        )

        self.persistence.persist_exchange(
            user_input,
            display_response,
            background_short_term=True,
            deterministic=self.research_mode,
            suppress_short_term_errors=True,
        )
        sleep_result = self._schedule_sleep_phase_if_due()

        start_time_dt = datetime.now()
        processing_time_ms = 0
        if hasattr(self, '_processing_start_time'):
            processing_time_ms = (start_time_dt - self._processing_start_time).total_seconds() * 1000

        # Safety net: wenn Groq kein cot liefert, aber thought/model_reasoning existiert
        safe_cot = formatted_stream.get("cot", "") or thought or model_reasoning or ""
        if formatted_stream.get("answer_is_fallback") and display_response and not self._is_fallback_text(display_response):
            safe_answer = display_response
        else:
            safe_answer = formatted_stream.get("answer", "") or display_response
        safe_answer, final_sanitization = sanitize_visible_response(safe_answer)
        if not safe_answer:
            safe_answer = "Die Modellantwort enthielt interne Steuerdaten und wurde aus Sicherheitsgruenden verworfen."
        if final_sanitization:
            formatted_stream["formatting_failed"] = True
            formatted_stream["output_sanitized"] = final_sanitization
        display_response = safe_answer

        timing = self._build_generation_timing(
            total_gen_ms,
            safe_answer,
            safe_cot if safe_cot != self._FALLBACK_NO_THINK else "",
            ttft_ms=ttft_ms,
        )
        timing["stream_safety_buffered"] = False

        # The visible prefix was already emitted token by token. Only
        # send a suffix created by final formatting or sanitization, so
        # the client never receives the answer twice.
        remaining_answer = safe_answer
        if streamed_visible and safe_answer.startswith(streamed_visible):
            remaining_answer = safe_answer[len(streamed_visible):]
        elif streamed_visible:
            remaining_answer = ""
        for offset in range(0, len(remaining_answer), 96):
            yield {"event": "token", "content": remaining_answer[offset:offset + 96], "token_type": "answer"}

        result = {
            "response_text": display_response,
            "raw_response": raw_response,
            "formatted_cot": safe_cot,
            "formatted_answer": safe_answer,
            "formatting_failed": formatted_stream.get("formatting_failed", False),
            "formatting_source": formatted_stream.get("formatting_source", "local_fallback"),
            "formatting_model": formatted_stream.get("formatting_model", "?"),
            "output_sanitized": formatted_stream.get("output_sanitized", []),
            "cot_leak": self._detect_cot_leakage(safe_answer),
            "context_budget": meta.get("context_budget", {}),
            "prompt_components": meta.get("prompt_components", {}),
            "emotions": emotions_after,
            "emotions_before": emotions_before,
            "emotions_delta": emotion_transitions,
            "thought_process": thought,
            "model_reasoning": model_reasoning,
            "reasoning_only": bool((thought or model_reasoning) and display_response.strip() == self._FALLBACK_SCHWEIGT),
            "input_classification": input_classification,
            "rag_memories": meta.get("rag_memories", []) if 'meta' in dir() else [],
            "keyword_rag_memories": meta.get("keyword_rag_memories", []) if 'meta' in dir() else [],
            "emotion_steering": meta.get("emotion_steering", {}) if 'meta' in dir() else {},
            "steering_runtime": meta.get("steering_runtime", {}) if 'meta' in dir() else {},
            "memory_trace": memory_trace,
            "tone_decision": tone_decision,
            "causal_trace": causal_trace,
            "prompt_emotion_mode": meta.get("prompt_emotion_mode", "") if 'meta' in dir() else "",
            "intent_type": intent_result.intent_type.value,
            "intent_confidence": intent_result.confidence,
            "tool_calls_executed": len(intent_result.tool_calls),
            "available_tools": available_tools,
            "selected_tools": selected_tool_names,
            "unused_tools": unused_tool_names,
            "short_term_count": self.short_term_memory.get_count(),
            "debug_log": self.debug_logger.get_formatted_log() if self.debug_logger.enabled else None,
            "debug_entries": self.debug_logger.get_entries_as_dict() if self.debug_logger.enabled else [],
            "intent_raw_json": intent_result.raw_json if hasattr(intent_result, 'raw_json') else {},
            "processing_time_ms": processing_time_ms,
            "life_snapshot": final_life_snapshot,
            "global_workspace": workspace,
            "action_plan": {"response_strategy": "conversational", "tone": tone_decision.get("tone", "state_driven")},
            "dream_fragments": final_life_snapshot.get("dream_fragments", []),
            "provider": self._chat_provider().value,
            "model": self._chat_model(),
            "timing": timing,
            "auto_sleep_triggered": sleep_result.get("triggered", False),
            "sleep_status": sleep_result.get("status", {}),
            "repetition_events": self._collect_repetition_events(),
        }

        yield _pipeline_status(
            "done",
            2,
            "Turn abgeschlossen",
            ttft_ms=timing.get("ttft_ms"),
            answer_tokens=timing.get("answer_tokens", 0),
            answer_time_ms=timing.get("answer_time_ms", 0),
            total_gen_ms=timing.get("total_gen_ms", 0),
            tokens_per_second=timing.get("tokens_per_second", 0.0),
        )

        yield {"event": "finished", "result": result}
