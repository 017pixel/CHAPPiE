"""Provider invocation boundary for the active runtime."""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional

from config.config import LLMProvider, settings
from config.emotions import EMOTION_DEFAULTS, EMOTION_ORDER
from config.prompts import (
    ISOLATED_LAYER_TEST_SYSTEM_PROMPT,
    format_multi_question_instruction,
    format_response_plan_instruction,
    get_system_prompt_with_emotions,
)
from brain.base_brain import GenerationConfig, Message
from brain.steering_manager import (
    STEERING_CONTEXT_EMOTION_SELF_REPORT,
    STEERING_CONTEXT_CONSCIOUSNESS,
    STEERING_CONTEXT_IDENTITY,
    STEERING_CONTEXT_IDENTITY_AND_EMOTION,
    STEERING_CONTEXT_GENERAL,
    classify_steering_context,
)
from brain.response_parser import (
    direct_self_report_needs_retry,
    resolve_visible_answer,
    stabilize_direct_self_report,
    sanitize_visible_response,
)
from web_infrastructure.formatting import normalize_multi_question_answer
from brain.token_counter import ModelTokenCounter, TokenizerUnavailableError
from web_infrastructure.turn_context import is_self_contained_math_query


from typing import Iterable


class GenerationGateway:
    """Resolve the current brain lazily so runtime hot reload stays compatible."""

    def __init__(self, brain_getter: Callable[[], Any]) -> None:
        self._brain_getter = brain_getter

    @property
    def brain(self) -> Any:
        return self._brain_getter()

    def generate(self, messages: Iterable[Any], *, config: Any) -> Any:
        return self.brain.generate(messages, config=config)

    def generate_with_tools(
        self,
        messages: Iterable[Any],
        *,
        config: Any,
        tools: Optional[list[dict[str, Any]]] = None,
    ) -> Any:
        return self.brain.generate_with_tools(messages, config=config, tools=tools or [])


def filter_isolated_layer_history(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Haelt Mess-Turns sichtbar, aber aus spaeteren Modellprompts heraus.

    Direkte Identitaets-/Gefuehlsantworten werden stark layer-gesteuert. Bei
    kleinen Modellen wuerde ihre Wiederholung im Prompt nachfolgende Sachfragen
    auf genau diese Formulierungen festlegen. Der emotionale Zustand bleibt
    davon unberuehrt und wird separat persistent weitergefuehrt.
    """
    filtered: List[Dict[str, Any]] = []
    skip_next_assistant = False
    for message in history or []:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role") or "")
        content = str(message.get("content") or "")
        if role == "user":
            skip_next_assistant = classify_steering_context(content) != STEERING_CONTEXT_GENERAL
            if skip_next_assistant:
                continue
        elif role == "assistant" and skip_next_assistant:
            skip_next_assistant = False
            continue
        else:
            skip_next_assistant = False
        filtered.append(message)
    return filtered




def response_memory_top_k_for_intent(
    intent_type: Any,
    default_top_k: int,
    prompt_top_k: int = 8,
) -> int:
    """Bound prompt RAG without changing the larger search/index setting.

    Exact keyword/entity facts use their own prioritized block, so the semantic
    block can remain small and relevance-sorted for every intent.
    """
    del intent_type
    return max(1, min(int(default_top_k), int(prompt_top_k)))

def measure_prompt_components(
    counter: ModelTokenCounter,
    components: Dict[str, str],
    history: List[Dict[str, Any]],
    messages_before_budget: list,
    messages_after_budget: list,
) -> Dict[str, Any]:
    """Measure prompt parts with the active model tokenizer.

    Component token counts are exact for each text fragment. Chat-template,
    role and fragment-join tokens are reported separately because tokenization
    is not additive across concatenation boundaries.
    """
    token_counts = {
        name: counter.count_text(str(value or "")) if value else 0
        for name, value in components.items()
    }
    history_text_tokens = sum(
        counter.count_text(str(item.get("content", "") or ""))
        for item in history
        if isinstance(item, dict)
    )
    token_counts["history"] = history_text_tokens
    component_sum = sum(token_counts.values())
    before_total = counter.count_messages(messages_before_budget)
    after_total = counter.count_messages(messages_after_budget)
    return {
        "token_count_source": "model_tokenizer",
        "tokenizer_model": counter.model_name,
        "components": token_counts,
        "component_sum_tokens": component_sum,
        "chat_template_total_tokens_before_budget": before_total,
        "chat_template_total_tokens_after_budget": after_total,
        "chat_template_and_join_overhead_tokens": before_total - component_sum,
        "history_messages": len(history),
    }

def calculate_generation_timing(
    total_gen_ms: int | float,
    answer_tokens: int,
    reasoning_tokens: int = 0,
    ttft_ms: int | float | None = None,
) -> Dict[str, Any]:
    """Build stable latency and effective-throughput metrics.

    Provider streams can deliver a completed answer in one buffered chunk.  In
    that case ``total - TTFT`` is only a few milliseconds and must not be used
    as the throughput denominator.  The effective rate therefore covers the
    complete measured generation window, including the wait for the first
    provider output.
    """
    total_ms = max(0, int(round(float(total_gen_ms or 0))))
    first_token_ms = total_ms if ttft_ms is None else max(0, int(round(float(ttft_ms))))
    first_token_ms = min(first_token_ms, total_ms) if total_ms else first_token_ms
    answer_count = max(0, int(answer_tokens or 0))
    reasoning_count = max(0, int(reasoning_tokens or 0))
    stream_ms = max(0, total_ms - first_token_ms)
    effective_ms = max(1, total_ms) if answer_count else 0
    rate = round(answer_count / (effective_ms / 1000), 1) if effective_ms else 0.0
    return {
        "ttft_ms": first_token_ms,
        "total_gen_ms": total_ms,
        "total_tokens": reasoning_count + answer_count,
        "reasoning_tokens": reasoning_count,
        "answer_tokens": answer_count,
        "reasoning_time_ms": first_token_ms,
        "answer_time_ms": stream_ms,
        "rate_duration_ms": effective_ms,
        "tokens_per_second": rate,
        "rate_basis": "answer_tokens_over_total_generation",
    }

class RuntimeGenerationMixin:
    """Internal mixin extracted from the former backend wrapper."""

    _token_counter: ModelTokenCounter | None
    _token_counter_model: str | None

    def _active_token_counter(self) -> ModelTokenCounter:
        model_name = str(getattr(self.brain, "model", "") or self._chat_model())
        if self._token_counter is None or self._token_counter_model != model_name:
            self._token_counter = ModelTokenCounter(model_name)
            self._token_counter_model = model_name
        return self._token_counter

    def _count_text_tokens_safe(self, text: str) -> int:
        try:
            return self._active_token_counter().count_text(text or "")
        except (TokenizerUnavailableError, TypeError, ValueError):
            return len(re.findall(r"\S+", text or ""))

    def _build_generation_timing(
        self,
        total_gen_ms: int | float,
        answer_text: str,
        reasoning_text: str = "",
        ttft_ms: int | float | None = None,
    ) -> Dict[str, Any]:
        """Build one stable timing shape for sync and streamed answers."""
        answer_tokens = self._count_text_tokens_safe(answer_text)
        reasoning_tokens = self._count_text_tokens_safe(reasoning_text) if reasoning_text else 0
        return calculate_generation_timing(
            total_gen_ms,
            answer_tokens,
            reasoning_tokens,
            ttft_ms=ttft_ms,
        )

    def _measure_prompt_components(
        self,
        components: Dict[str, str],
        history: List[Dict[str, Any]],
        messages_before_budget: list,
        messages_after_budget: list,
    ) -> Dict[str, Any]:
        """Keep optional prompt telemetry from aborting an otherwise valid turn."""
        model_name = str(getattr(self.brain, "model", "") or self._chat_model())
        try:
            return measure_prompt_components(
                self._active_token_counter(),
                components,
                history,
                messages_before_budget,
                messages_after_budget,
            )
        except TokenizerUnavailableError as exc:
            return {
                "token_count_source": "unavailable",
                "tokenizer_model": model_name,
                "tokenizer_error": str(exc),
                "components": {},
                "component_sum_tokens": None,
                "chat_template_total_tokens_before_budget": None,
                "chat_template_total_tokens_after_budget": None,
                "chat_template_and_join_overhead_tokens": None,
                "history_messages": len(history),
            }

    def _enforce_context_budget(self, messages: list) -> tuple[list, dict]:
        """Count with the real tokenizer and trim until the request fits."""
        if not messages:
            return messages, {
                "estimated_tokens": 0,
                "token_limit": settings.context_token_limit,
                "was_trimmed": False,
                "near_limit": False,
                "token_count_source": "model_tokenizer",
            }

        token_limit = max(256, int(settings.context_token_limit))
        try:
            estimated = self._estimate_total_tokens(messages)
        except TokenizerUnavailableError as exc:
            return messages, {
                "estimated_tokens": None,
                "trimmed_tokens": None,
                "token_limit": token_limit,
                "was_trimmed": False,
                "near_limit": False,
                "context_budget_failed": True,
                "token_count_source": "unavailable",
                "tokenizer_model": str(getattr(self.brain, "model", "") or self._chat_model()),
                "tokenizer_error": str(exc),
            }
        budget_info = {
            "estimated_tokens": estimated,
            "token_limit": token_limit,
            "was_trimmed": False,
            "near_limit": estimated > settings.context_token_warning_threshold,
            "context_budget_failed": False,
            "token_count_source": "model_tokenizer",
            "tokenizer_model": self._active_token_counter().model_name,
        }
        if estimated <= token_limit:
            budget_info["trimmed_tokens"] = estimated
            budget_info["removed_messages"] = 0
            return messages, budget_info

        system_msg = messages[0]
        current_user = messages[-1]
        trimmed = [system_msg, current_user] if len(messages) > 1 else [system_msg]
        system_was_truncated = False
        user_was_truncated = False

        # Preserve the newest history that fits. Aggregate counts are used
        # for every decision because chat-template overhead is not additive.
        kept_history_reversed: list[Any] = []
        for msg in reversed(messages[1:-1]):
            candidate = [system_msg, msg, *reversed(kept_history_reversed), current_user]
            if self._estimate_total_tokens(candidate) <= token_limit:
                kept_history_reversed.append(msg)
        trimmed = [system_msg, *reversed(kept_history_reversed), current_user]

        if self._estimate_total_tokens(trimmed) > token_limit and len(trimmed) > 1:
            trimmed, changed = self._shrink_message_in_context(trimmed, 0, token_limit)
            system_was_truncated = changed
        if self._estimate_total_tokens(trimmed) > token_limit:
            trimmed, changed = self._shrink_message_in_context(trimmed, len(trimmed) - 1, token_limit)
            user_was_truncated = changed

        trimmed_tokens = self._estimate_total_tokens(trimmed)
        removed_messages = max(0, len(messages) - len(trimmed))
        budget_info["was_trimmed"] = bool(removed_messages or system_was_truncated or user_was_truncated)
        budget_info["original_tokens"] = estimated
        budget_info["trimmed_tokens"] = trimmed_tokens
        budget_info["removed_messages"] = removed_messages
        budget_info["system_was_truncated"] = system_was_truncated
        budget_info["user_was_truncated"] = user_was_truncated
        budget_info["context_budget_failed"] = trimmed_tokens > token_limit
        return trimmed, budget_info

    @staticmethod
    def _msg_content(msg) -> str:
        content = getattr(msg, "content", None)
        if content is None and isinstance(msg, dict):
            content = msg.get("content", "")
        return str(content or "")

    @staticmethod
    def _msg_role(msg) -> str:
        role = getattr(msg, "role", None)
        if role is None and isinstance(msg, dict):
            role = msg.get("role", "user")
        return str(role or "user")

    @staticmethod
    def _copy_msg_with_content(msg, content: str):
        if isinstance(msg, Message):
            return Message(role=msg.role, content=content)
        if isinstance(msg, dict):
            new_msg = dict(msg)
            new_msg["content"] = content
            return new_msg
        return Message(role=RuntimeGenerationMixin._msg_role(msg), content=content)

    def _estimate_total_tokens(self, messages: list) -> int:
        return self._active_token_counter().count_messages(messages)

    def _get_context_tools(self) -> List[Dict[str, Any]]:
        """Returns OpenAI-compatible tools for context file updates."""
        return self.function_registry.get_openai_tools()

    def _build_context_components(
        self,
        requirements: Dict[str, bool],
        user_input: str = "",
    ) -> Dict[str, str]:
        """Build separately measurable persona and short-term context."""
        persona_parts = []
        
        if self._feature_enabled("persona") and requirements.get("need_soul_context", True):
            soul = self.context_files.get_soul_context()
            if soul:
                persona_parts.append(f"=== CHAPPiE'S SOUL ===\n{soul}")

        if self._feature_enabled("persona") and requirements.get("need_user_context", True):
            user = self.context_files.get_user_context()
            if user:
                persona_parts.append(f"=== USER PROFILE ===\n{user}")

        if self._feature_enabled("persona") and requirements.get("need_preferences", True):
            prefs = self.context_files.get_preferences_context()
            if prefs:
                persona_parts.append(f"=== CHAPPiE'S PREFERENCES ===\n{prefs}")

        short_term = ""
        if self._feature_enabled("memory") and requirements.get("need_short_term_memory", True):
            short_term = self.short_term_memory.get_formatted_for_prompt(
                query=user_input,
                limit=getattr(settings, "stm_prompt_top_k", 8),
            )

        return {
            "persona": "\n\n".join(persona_parts),
            "short_term_memory": short_term,
        }

    def _build_context(self, requirements: Dict[str, bool], user_input: str = "") -> str:
        """Baut den Context String basierend auf Requirements."""
        components = self._build_context_components(requirements, user_input=user_input)
        return "\n\n".join(part for part in components.values() if part)

    @staticmethod
    def _effective_context_requirements(user_input: str, requirements: Dict[str, bool]) -> Dict[str, bool]:
        effective = dict(requirements or {})
        # Direkte Fragen nach dem eigenen Befinden oder der eigenen Identitaet
        # sind ein kontrollierter Layer-Editing-Test. Alte Persona-, Memory-
        # und Lebenskontexte konkurrieren hier mit dem aktuellen Kontrastpaar
        # und koennen aus einer Befindensantwort einen biografischen Plantext
        # machen. Die Layer bleiben aktiv; nur der Textkontext wird isoliert.
        steering_context = classify_steering_context(user_input)
        isolated_self_query = steering_context in {
            STEERING_CONTEXT_EMOTION_SELF_REPORT,
            STEERING_CONTEXT_CONSCIOUSNESS,
            STEERING_CONTEXT_IDENTITY,
            STEERING_CONTEXT_IDENTITY_AND_EMOTION,
        }
        if is_self_contained_math_query(user_input) or isolated_self_query:
            for key in (
                "need_soul_context",
                "need_user_context",
                "need_preferences",
                "need_short_term_memory",
                "need_long_term_memory",
            ):
                effective[key] = False
        return effective

    def _generate_response(self, user_input: str, history: List[Dict], 
                          context: str, emotions: Dict[str, int],
                          life_context: Dict[str, Any] | None = None,
                          global_workspace: Dict[str, Any] | None = None,
                          preloaded_memories: Optional[List[Any]] = None,
                          memory_trace_seed: Optional[Dict[str, Any]] = None,
                          intent_type: Any = None,
                          retrieval_keywords: Optional[List[str]] = None,
                          exact_entities: Optional[List[str]] = None,
                          fact_lookup_intent: bool = False,
                          allow_memory_context: bool = True,
                          isolated_request: bool = False,
                          emotion_changes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generiert die finale Antwort (Step 2)."""
        closed_reasoning = is_self_contained_math_query(user_input)
        memory_suppressed = closed_reasoning or not allow_memory_context
        # RAG Memory Search
        memory_top_k = response_memory_top_k_for_intent(intent_type, settings.memory_top_k)
        generation_query_source = self._retrieval_query_from_terms(retrieval_keywords or [], exact_entities or [], user_input)
        generation_query = generation_query_source if (retrieval_keywords or exact_entities) else self._local_retrieval_query(user_input)
        fresh_memories = [] if memory_suppressed else self._search_memory(
            generation_query or user_input, top_k=memory_top_k, optimize_query=False,
        )
        memories = self._merge_memories(
            preferred=[] if memory_suppressed else (preloaded_memories or []),
            secondary=fresh_memories,
            limit=memory_top_k,
        )
        keyword_memories = [] if memory_suppressed else self._search_memory_keywords(
            query=user_input,
            keywords=retrieval_keywords or [],
            entities=exact_entities or [],
            top_k=5,
            min_score=0.18 if fact_lookup_intent else 0.25,
        )
        keyword_ids = {str(getattr(memory, "id", "") or "") for memory in keyword_memories or []}
        semantic_prompt_memories = [memory for memory in memories or [] if str(getattr(memory, "id", "") or "") not in keyword_ids]
        if fact_lookup_intent and keyword_memories:
            # A concrete recall question must not be diluted by loosely
            # related assistant prose. The exact USER/keyword block is
            # the authoritative source for names, preferences and facts.
            semantic_prompt_memories = []
        keyword_memories_for_prompt = self.memory.format_keyword_memories_for_prompt(keyword_memories)
        memories_for_prompt = self.memory.format_memories_for_prompt(semantic_prompt_memories) if semantic_prompt_memories else ""
        
        # === LTM+STM KONSOLIDIERUNG (via Groq gpt-oss-120b) ===
        stm_entries: list[Any] = []
        consolidation_meta = {}
        if settings.memory_consolidation_enabled and self._feature_enabled("memory") and not memory_suppressed:
            stm_entries = self.short_term_memory.get_active_entries() if hasattr(self, 'short_term_memory') and self.short_term_memory else []
            consolidated_prompt, consolidation_meta = self._consolidate_memories_for_prompt(
                ltm_memories=memories or [],
                stm_entries=stm_entries or [],
            )
            if consolidated_prompt:
                memories_for_prompt = consolidated_prompt
                if context and "=== AKTUELLE SHORT-TERM ERINNERUNGEN" in context:
                    context = re.sub(
                        r"=== AKTUELLE SHORT-TERM ERINNERUNGEN.*?(?=\n\n===|\n\n\[|\Z)",
                        "",
                        context,
                        flags=re.DOTALL,
                    ).strip()
            self.debug_logger.log_info(
                "MEMORY_CONSOLIDATION",
                "LTM+STM-Konsolidierung abgeschlossen",
                consolidation_meta if consolidation_meta else {"enabled": False},
            )

        memory_trace = {
            "seed": memory_trace_seed or {},
            "generation": self._build_memory_trace(
                query=generation_query,
                memories=fresh_memories,
                stage="generation",
            ),
            "merged": self._build_memory_trace(
                query=generation_query,
                memories=memories,
                stage="merged_context",
            ),
            "keyword": {
                **self._build_memory_trace(
                    query=self._retrieval_query_from_terms(retrieval_keywords or [], exact_entities or [], user_input),
                    memories=keyword_memories,
                    stage="keyword_facts",
                ),
                "retrieval_keywords": retrieval_keywords or [],
                "exact_entities": exact_entities or [],
                "fact_lookup_intent": fact_lookup_intent,
            },
        }
        self.debug_logger.log_info(
            "RAG",
            "Memory-Retrieval abgeschlossen",
            {
                "top_k": settings.memory_top_k,
                "effective_top_k": memory_top_k,
                "memories_found": len(memories or []),
                "keyword_memories_found": len(keyword_memories or []),
                "memory_ids": [str(getattr(m, "id", ""))[:8] for m in (memories or [])[:8]],
                "keyword_memory_ids": [str(getattr(m, "id", ""))[:8] for m in (keyword_memories or [])[:5]],
                "query": generation_query,
            },
        )
        self.debug_logger.log_info(
            "MEMORY_TRACE",
            "Kombinierte Memory-Spur fuer Antwortgenerierung",
            memory_trace,
        )

        prompt_runtime = self._build_prompt_runtime(
            emotions,
            emotion_changes=emotion_changes,
            user_input=user_input,
        )
        tone_decision = prompt_runtime.get("response_plan", {})
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
        self.debug_logger.log_info(
            "TONE_DECISION",
            "Antwortton aus Emotion, Memory und Steering abgeleitet",
            {
                "tone": tone_decision.get("tone", "grounded_neutral"),
                "tone_reason": tone_decision.get("tone_reason", ""),
                "tone_drivers": tone_decision.get("tone_drivers", []),
            },
        )
        
        # System Prompt bauen
        system_prompt = get_system_prompt_with_emotions(
            **{key: emotions.get(key, EMOTION_DEFAULTS[key]) for key in EMOTION_ORDER},
            include_emotion_status=prompt_runtime["use_prompt_emotions"],
            use_chain_of_thought=self._use_prompt_chain_of_thought(),
            persona_enabled=self._feature_enabled("persona") and not isolated_request,
        )
        if isolated_request:
            system_prompt = ISOLATED_LAYER_TEST_SYSTEM_PROMPT
        if not isolated_request:
            system_prompt = self._append_response_style_instruction(
                system_prompt,
                intent_type,
                tone_decision if prompt_runtime["use_prompt_emotions"] else None,
                user_input=user_input,
            )

        life_prompt_context = "" if isolated_request else self._build_life_prompt_context(life_context, global_workspace)
        if life_prompt_context:
            system_prompt += f"\n\n{life_prompt_context}"
        
        # Context hinzufuegen
        if context:
            system_prompt += f"\n\n{context}"

        if keyword_memories_for_prompt:
            system_prompt += f"\n\n{keyword_memories_for_prompt}"

        # Memories hinzufuegen
        if memories_for_prompt:
            system_prompt += f"\n\n{memories_for_prompt}"
        
        # Messages bauen — Chat-History gecapped
        prompt_history = (
            []
            if isolated_request or closed_reasoning
            else filter_isolated_layer_history(history)
        )
        messages = self.brain.build_prompt(
            system_prompt, "", user_input, prompt_history,
            max_history=settings.history_max_messages,
        )
        
        # === TOKEN-BUDGET MONITOR ===
        messages, budget_info = self._enforce_context_budget(messages)
        if budget_info.get("near_limit") or budget_info.get("was_trimmed"):
            self.debug_logger.log_info(
                "CONTEXT_BUDGET",
                "Token-Budget geprueft",
                budget_info,
            )
        
        # Lokale Emotionen duerfen den finalen Modelllauf nur ueber Vektoren
        # beeinflussen. Promptbasierte Provider behalten den Legacy-Pfad.
        adj = self._get_emotion_adjusted_config(
            emotions,
            apply_emotion_adjustments=prompt_runtime["use_prompt_emotions"],
        )
        gen_config = GenerationConfig(
            # Direct self-reports are intentionally short. A small local model
            # otherwise spends the full budget repeating an identity disclaimer
            # instead of answering the one requested state question.
            max_tokens=min(adj["max_tokens"], 64) if (closed_reasoning or isolated_request) else adj["max_tokens"],
            temperature=0.35 if isolated_request else adj["temperature"],
            repetition_penalty=adj["repetition_penalty"],
            stream=False,
            seed=getattr(self, "generation_seed", None),
            extra_body=prompt_runtime["steering_payload"] or None,
            # The web response contract requires a visible final answer. Some
            # Qwen3.5 builds emit an untagged prose scratchpad when native
            # thinking is enabled, so keep that mode opt-in for direct brain
            # callers while the local web turn uses bounded layer steering.
            enable_thinking=False if self._chat_provider() == LLMProvider.VLLM and prompt_runtime["force_steering"] else None,
        )
        
        # Native Tool Calling: Kontext-File-Tools an Brain uebergeben
        tools = self._get_context_tools() if settings.llm_provider == LLMProvider.GROQ else None
        tool_call_results = []
        if tools and hasattr(self.brain, "generate_with_tools"):
            tool_response = self.generation.generate_with_tools(messages, config=gen_config, tools=tools)
            raw_response = tool_response.get("content", "")
            native_tool_calls = tool_response.get("tool_calls")
            if native_tool_calls:
                tool_call_results = self._execute_native_tool_calls(native_tool_calls)
                # Simuliere Tool-Ergebnisse als System-Message
                if tool_call_results:
                    messages.append(Message(role="system", content="\n".join(tool_call_results)[:800]))
                    raw_response = self.generation.generate(messages, config=gen_config)
        else:
            raw_response = self.generation.generate(messages, config=gen_config)
        display_response, thought, model_reasoning = self._extract_display_response(raw_response, phase="Schritt 2: Antwortgenerierung")
        steering_context = classify_steering_context(user_input)
        display_response, self_report_stabilized = stabilize_direct_self_report(
            display_response,
            steering_context,
        )
        semantic_retry_count = 0
        if (
            self._chat_provider() == LLMProvider.VLLM
            and steering_context in {
                STEERING_CONTEXT_EMOTION_SELF_REPORT,
                STEERING_CONTEXT_CONSCIOUSNESS,
                STEERING_CONTEXT_IDENTITY,
                STEERING_CONTEXT_IDENTITY_AND_EMOTION,
            }
        ):
            for retry_level in (1, 2):
                if not direct_self_report_needs_retry(
                    display_response,
                    steering_context,
                    str(prompt_runtime["emotion_steering"].get("dominant_vector", "")),
                ):
                    break
                prompt_runtime = self._build_prompt_runtime(
                    emotions,
                    emotion_changes=emotion_changes,
                    user_input=user_input,
                    steering_retry_level=retry_level,
                )
                gen_config.extra_body = prompt_runtime["steering_payload"] or None
                raw_response = self.generation.generate(messages, config=gen_config)
                display_response, thought, model_reasoning = self._extract_display_response(
                    raw_response,
                    phase=f"Schritt 2: Layer-Selbstbericht Wiederholung {retry_level}",
                )
                display_response, retry_stabilized = stabilize_direct_self_report(
                    display_response,
                    steering_context,
                )
                self_report_stabilized = self_report_stabilized or retry_stabilized
                semantic_retry_count = retry_level
        deterministic_fact_answer = self._build_deterministic_fact_answer(
            user_input,
            list(keyword_memories or []) + list(memories or []),
        )
        if deterministic_fact_answer:
            display_response = deterministic_fact_answer
            formatted = {
                "cot": "",
                "answer": deterministic_fact_answer,
                "formatting_failed": False,
                "formatting_source": "deterministic_user_memory",
                "formatting_model": "local_fact_extractor",
                "answer_is_fallback": False,
            }
        else:
            formatted = self._format_via_groq(display_response)

        # Safety net: wenn Groq kein cot liefert, aber thought/model_reasoning existiert
        safe_cot = formatted.get("cot", "") or thought or model_reasoning or ""
        if formatted.get("answer_is_fallback") and display_response and not self._is_fallback_text(display_response):
            safe_answer = display_response
        else:
            safe_answer = formatted.get("answer", "") or display_response

        safe_answer, paragraph_normalized = normalize_multi_question_answer(user_input, safe_answer)
        if paragraph_normalized:
            formatted["multi_question_paragraph_normalized"] = True
        if self_report_stabilized:
            formatted["direct_self_report_stabilized"] = True

        # The local formatter is intentionally regex-only, so sanitize its
        # result as well.  The user-visible response and the debug/API
        # formatted answer must not disagree about prompt fragments.
        safe_answer, formatted_sanitization = sanitize_visible_response(safe_answer)
        if formatted_sanitization:
            formatted["output_sanitized"] = formatted_sanitization
        # Nie still verwerfen: Fallback-Kette zeigt immer den besten Rohtext.
        safe_answer, fallback_info = resolve_visible_answer(
            safe_answer,
            display_response=display_response,
            raw_response=raw_response if isinstance(raw_response, str) else "",
            sanitization_reasons=formatted_sanitization,
        )
        formatted["sanitization_fallback"] = bool(fallback_info.get("sanitization_fallback"))
        formatted["sanitization_reasons"] = list(fallback_info.get("sanitization_reasons", []))
        display_response = safe_answer

        # Detektiere unerwartetes CoT-Leakage in der Antwort
        cot_leak = self._detect_cot_leakage(safe_answer)

        return {
            "response_text": display_response,
            "raw_response": raw_response,
            "formatted_cot": safe_cot,
            "formatted_answer": safe_answer,
            "formatting_failed": formatted.get("formatting_failed", False),
            "formatting_warning": formatted.get("formatting_warning", ""),
            "formatting_error": formatted.get("formatting_error", ""),
            "formatting_source": formatted.get("formatting_source", "local_fallback"),
            "formatting_model": formatted.get("formatting_model", "?"),
            "output_sanitized": formatted.get("output_sanitized", getattr(self, "_last_output_sanitization", [])),
            "sanitization_fallback": formatted.get("sanitization_fallback", False),
            "sanitization_reasons": formatted.get("sanitization_reasons", []),
            "multi_question_paragraph_normalized": formatted.get("multi_question_paragraph_normalized", False),
            "direct_self_report_stabilized": formatted.get("direct_self_report_stabilized", False),
            "semantic_retry_count": semantic_retry_count,
            "thought_process": thought,
            "model_reasoning": model_reasoning,
            "cot_leak": cot_leak,
            "reasoning_only": bool((thought or model_reasoning) and display_response.strip() == self._FALLBACK_SCHWEIGT),
            "rag_memories": memories,
            "keyword_rag_memories": keyword_memories,
            "memory_trace": memory_trace,
            "memory_consolidation": consolidation_meta,
            "context_budget": budget_info,
            "emotion_steering": prompt_runtime["emotion_steering"],
            "steering_runtime": getattr(self.brain, "last_steering_report", {}),
            "prompt_emotion_mode": prompt_runtime["prompt_emotion_mode"],
            "tone_decision": tone_decision,
            "repetition_events": self._collect_repetition_events(),
            "action_plan": self.action_response.build_action_plan(
                {
                    "response_strategy": "conversational",
                    "tone": tone_decision.get("tone", "state_driven"),
                    "response_guidance": tone_decision.get(
                        "response_guidance",
                        "Erzeuge eine kohaerente Antwort, die innere Zustaende beruecksichtigt.",
                    ),
                },
                life_context or {},
                global_workspace or {},
            ),
        }

    def _generate_response_stream_raw(
        self,
        user_input: str,
        history: List[Dict],
        context: str,
        emotions: Dict[str, int],
        life_context: Dict[str, Any] | None = None,
        global_workspace: Dict[str, Any] | None = None,
        preloaded_memories: Optional[List[Any]] = None,
        memory_trace_seed: Optional[Dict[str, Any]] = None,
        intent_type: Any = None,
        retrieval_keywords: Optional[List[str]] = None,
        exact_entities: Optional[List[str]] = None,
        fact_lookup_intent: bool = False,
        allow_memory_context: bool = True,
        isolated_request: bool = False,
        context_components: Optional[Dict[str, str]] = None,
        emotion_changes: Optional[Dict[str, Any]] = None,
        steering_retry_level: int = 0,
    ):
        """Bereitet Step-2-Generierung vor und gibt einen Token-Generator zurueck."""
        closed_reasoning = is_self_contained_math_query(user_input)
        memory_suppressed = closed_reasoning or not allow_memory_context
        memory_top_k = response_memory_top_k_for_intent(
            intent_type,
            settings.memory_top_k,
            getattr(settings, "memory_prompt_top_k", 8),
        )
        # Preloaded memories aus Step 1 direkt nutzen – kein zweiter LLM-Call
        memories = [] if memory_suppressed else list(preloaded_memories or [])
        if not memories and not memory_suppressed:
            generation_query_source = self._retrieval_query_from_terms(retrieval_keywords or [], exact_entities or [], user_input)
            generation_query = generation_query_source if (retrieval_keywords or exact_entities) else self._local_retrieval_query(user_input)
            memories = self._search_memory(
                generation_query or user_input,
                top_k=memory_top_k,
                optimize_query=False,
            )
        else:
            generation_query = self._retrieval_query_from_terms(retrieval_keywords or [], exact_entities or [], user_input)
        keyword_memories = [] if memory_suppressed else self._search_memory_keywords(
            query=user_input,
            keywords=retrieval_keywords or [],
            entities=exact_entities or [],
            top_k=5,
            min_score=0.18 if fact_lookup_intent else 0.25,
        )
        keyword_ids = {str(getattr(memory, "id", "") or "") for memory in keyword_memories or []}
        semantic_prompt_memories = [memory for memory in memories or [] if str(getattr(memory, "id", "") or "") not in keyword_ids]
        if fact_lookup_intent and keyword_memories:
            # A concrete recall question must not be diluted by loosely
            # related assistant prose. The exact USER/keyword block is
            # the authoritative source for names, preferences and facts.
            semantic_prompt_memories = []
        keyword_memories_for_prompt = self.memory.format_keyword_memories_for_prompt(keyword_memories)
        memories_for_prompt = self.memory.format_memories_for_prompt(semantic_prompt_memories) if semantic_prompt_memories else ""
        memory_trace = {
            "seed": memory_trace_seed or {},
            "merged": self._build_memory_trace(
                query=generation_query,
                memories=memories,
                stage="merged_context",
            ),
            "keyword": {
                **self._build_memory_trace(
                    query=self._retrieval_query_from_terms(retrieval_keywords or [], exact_entities or [], user_input),
                    memories=keyword_memories,
                    stage="keyword_facts",
                ),
                "retrieval_keywords": retrieval_keywords or [],
                "exact_entities": exact_entities or [],
                "fact_lookup_intent": fact_lookup_intent,
            },
        }

        prompt_runtime = self._build_prompt_runtime(
            emotions,
            emotion_changes=emotion_changes,
            user_input=user_input,
            steering_retry_level=steering_retry_level,
        )
        tone_decision = prompt_runtime.get("response_plan", {})

        base_system_prompt = get_system_prompt_with_emotions(
            **{key: emotions.get(key, EMOTION_DEFAULTS[key]) for key in EMOTION_ORDER},
            include_emotion_status=prompt_runtime["use_prompt_emotions"],
            use_chain_of_thought=self._use_prompt_chain_of_thought(),
            persona_enabled=self._feature_enabled("persona") and not isolated_request,
        )
        if isolated_request:
            base_system_prompt = ISOLATED_LAYER_TEST_SYSTEM_PROMPT
        response_style_instruction = "" if isolated_request else self._response_style_instruction(intent_type)
        multi_question_instruction = "" if isolated_request else format_multi_question_instruction(user_input)
        response_plan_instruction = format_response_plan_instruction(
            str(tone_decision.get("tone", "grounded_neutral")),
            str(tone_decision.get("response_guidance", "Antworte klar und praezise.")),
        ) if tone_decision and prompt_runtime["use_prompt_emotions"] else ""
        generation_budget_instruction = "" if isolated_request else self._generation_budget_instruction()
        life_prompt_context = "" if isolated_request else self._build_life_prompt_context(life_context, global_workspace)
        system_prompt = "\n\n".join(part for part in (
            base_system_prompt,
            response_style_instruction,
            multi_question_instruction,
            response_plan_instruction,
            generation_budget_instruction,
            life_prompt_context,
        ) if part)

        if context:
            system_prompt += f"\n\n{context}"

        if keyword_memories_for_prompt:
            system_prompt += f"\n\n{keyword_memories_for_prompt}"

        if memories_for_prompt:
            system_prompt += f"\n\n{memories_for_prompt}"

        prompt_history = (
            []
            if isolated_request or closed_reasoning
            else filter_isolated_layer_history(history)
        )
        messages = self.brain.build_prompt(
            system_prompt,
            "",
            user_input,
            prompt_history,
            max_history=settings.history_max_messages,
        )
        messages_before_budget = list(messages)
        messages, budget_info = self._enforce_context_budget(messages)
        measured_context = context_components or {"persona": context, "short_term_memory": ""}
        prompt_components = self._measure_prompt_components(
            {
                "system": base_system_prompt,
                "persona": measured_context.get("persona", ""),
                "semantic_memory": memories_for_prompt,
                "keyword_memory": keyword_memories_for_prompt,
                "short_term_memory": measured_context.get("short_term_memory", ""),
                "life": life_prompt_context,
                "user": user_input,
                "generation_budget": generation_budget_instruction,
                "response_style": response_style_instruction,
                "multi_question": multi_question_instruction,
                "response_plan": response_plan_instruction,
            },
            prompt_history[-settings.history_max_messages:],
            messages_before_budget,
            messages,
        )

        adj = self._get_emotion_adjusted_config(
            emotions,
            apply_emotion_adjustments=prompt_runtime["use_prompt_emotions"],
        )
        gen_config = GenerationConfig(
            max_tokens=min(adj["max_tokens"], 64) if (closed_reasoning or isolated_request) else adj["max_tokens"],
            temperature=0.35 if isolated_request else adj["temperature"],
            repetition_penalty=adj["repetition_penalty"],
            stream=True,
            seed=getattr(self, "generation_seed", None),
            extra_body=prompt_runtime["steering_payload"] or None,
            enable_thinking=False if self._chat_provider() == LLMProvider.VLLM and prompt_runtime["force_steering"] else None,
        )

        return self.generation.generate(messages, config=gen_config), {
            "memory_trace": memory_trace,
            "tone_decision": tone_decision,
            "emotion_steering": prompt_runtime["emotion_steering"],
            "steering_runtime": getattr(self.brain, "last_steering_report", {}),
            "prompt_emotion_mode": prompt_runtime["prompt_emotion_mode"],
            "provider": self._chat_provider().value,
            "model": self._chat_model(),
            "rag_memories": memories,
            "keyword_rag_memories": keyword_memories,
            "context_budget": budget_info,
            "prompt_components": prompt_components,
            "effective_memory_top_k": memory_top_k,
        }

    def _stream_visible_candidate(self, raw_text: str) -> str:
        """Return only the currently safe answer prefix from raw tokens."""
        if not isinstance(raw_text, str) or not raw_text.strip():
            return ""

        source = raw_text
        private_open = re.search(
            r"<\s*(think|thinking|thought|reasoning|model_reasoning|provider_reasoning|gedanke)\b[^>]*>",
            source,
            re.IGNORECASE,
        )
        if private_open:
            tag_name = private_open.group(1)
            private_close = re.search(rf"<\s*/\s*{re.escape(tag_name)}\s*>", source[private_open.end():], re.IGNORECASE)
            if private_close:
                close_end = private_open.end() + private_close.end()
                source = source[:private_open.start()] + source[close_end:]
            else:
                source = source[:private_open.start()]

        prose_reasoning = re.match(
            r"^\s*(?:#{1,6}\s*)?(?:Thinking|Reasoning|Thought)\s+Process\s*: ?",
            source,
            re.IGNORECASE,
        )
        if prose_reasoning:
            final_marker = re.search(
                r"(?:^|\n)\s*(?:#{1,6}\s*)?(?:Final\s+(?:Answer|Response)|Finale\s+Antwort)\s*:\s*",
                source,
                re.IGNORECASE,
            )
            if not final_marker:
                return ""
            source = source[final_marker.end():]

        answer_open = re.search(r"<\s*(antwort|answer|response)\b[^>]*>", source, re.IGNORECASE)
        if answer_open:
            tag_name = answer_open.group(1)
            answer_close = re.search(rf"<\s*/\s*{re.escape(tag_name)}\s*>", source[answer_open.end():], re.IGNORECASE)
            if answer_close:
                source = source[answer_open.end():answer_open.end() + answer_close.start()]
            else:
                source = source[answer_open.end():]

        source = re.sub(
            r"<\s*/?\s*(?:think|thinking|thought|reasoning|model_reasoning|provider_reasoning|gedanke|antwort|answer|response)\b[^>]*>",
            "",
            source,
            flags=re.IGNORECASE,
        )
        source = self._strip_leaked_metadata(source)
        visible, _ = sanitize_visible_response(source)
        return visible
