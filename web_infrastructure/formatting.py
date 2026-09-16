"""Backend-facing message formatting shared by API and background jobs."""

from __future__ import annotations

from web_infrastructure.timing import measured

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from config.config import LLMProvider, settings
from config.emotions import EMOTION_DEFAULTS
from config.prompts import (
    FALLBACK_ANSWER_WITHOUT_THOUGHT,
    FALLBACK_EMPTY_ANSWER,
    FALLBACK_THOUGHT_WITHOUT_ANSWER,
    FORMATTER_WHITESPACE_PROMPT,
    FORMATTER_WITH_COT_PROMPT,
    RESPONSE_STYLE_CASUAL,
    RESPONSE_STYLE_DEFAULT,
    count_user_questions,
    format_generation_budget_instruction,
    format_multi_question_instruction,
    format_response_plan_instruction,
)
from brain.response_parser import (
    contains_cot_leak,
    extract_tagged_block,
    looks_like_model_error,
    parse_chain_of_thought,
    parse_thinking_tags,
    sanitize_visible_response,
)



_EXPLICIT_LIST_REQUEST_RE = re.compile(
    r"\b(?:als|in|mit)\s+(?:einer\s+)?(?:liste|stichpunkten|bullet\s*points?|nummerierung)\b|"
    r"\b(?:liste|nummeriere|gliedere)\b|"
    r"\b(?:stichpunkte|bullet\s*points?)\b",
    re.IGNORECASE,
)
_LIST_LINE_RE = re.compile(r"(?m)^\s*(?:\d{1,2}[.)]|[-+*])\s+(?=\S)")
_INLINE_NUMBERED_RE = re.compile(r"(?<!\n)\s+(?=\d{1,2}[.)]\s+\S)")


def should_normalize_multi_question_answer(user_input: str) -> bool:
    """Mehrfachfragen nutzen Prosa, ausser der User fordert eine Liste an."""
    text = str(user_input or "")
    return count_user_questions(text) >= 2 and not bool(_EXPLICIT_LIST_REQUEST_RE.search(text))


def normalize_multi_question_answer(user_input: str, answer: str) -> tuple[str, bool]:
    """Entfernt erzwungene Listenmarker, ohne Antwortinhalt umzuschreiben."""
    if not should_normalize_multi_question_answer(user_input):
        return answer, False
    text = str(answer or "").strip()
    if not text:
        return text, False

    candidate = text
    if len(_LIST_LINE_RE.findall(candidate)) < 2:
        inline_candidate = _INLINE_NUMBERED_RE.sub("\n", candidate)
        if len(_LIST_LINE_RE.findall(inline_candidate)) >= 2:
            candidate = inline_candidate
    if len(_LIST_LINE_RE.findall(candidate)) < 2:
        return text, False

    normalized_lines: list[str] = []
    for line in candidate.splitlines():
        marker = _LIST_LINE_RE.match(line)
        if marker:
            if normalized_lines and normalized_lines[-1] != "":
                normalized_lines.append("")
            normalized_lines.append(line[marker.end():].strip())
        else:
            normalized_lines.append(line.rstrip())
    normalized = re.sub(r"\n{3,}", "\n\n", "\n".join(normalized_lines)).strip()
    return normalized, normalized != text




def serialize_rag_memories(memories: Optional[List[Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "content": memory.content,
            "relevance_score": memory.relevance_score,
            "role": memory.role,
            "label": getattr(memory, "label", "original"),
            "id": memory.id,
            "timestamp": getattr(memory, "timestamp", ""),
            "type": getattr(memory, "mem_type", "interaction"),
            "match_type": getattr(memory, "match_type", ""),
            "matched_terms": getattr(memory, "matched_terms", ""),
            "source": getattr(memory, "source", "unknown"),
            "strength": getattr(memory, "strength", 1.0),
            "recall_count": getattr(memory, "recall_count", 0),
            "retention": getattr(memory, "retention", 1.0),
            "association_score": getattr(memory, "association_score", 0.0),
        }
        for memory in memories or []
    ]


def build_assistant_message(
    user_input: str,
    result: Dict[str, Any],
    *,
    message_id: Optional[str] = None,
) -> Dict[str, Any]:
    created_at = datetime.now(timezone.utc).isoformat()
    intent_raw = result.get("intent_raw_json", {})
    tool_calls_raw = intent_raw.get("tool_calls", []) if isinstance(intent_raw, dict) else []
    timing = result.get("timing", {})
    if not isinstance(timing, dict):
        timing = {}
    metadata = {
        "runtime_settings": result.get("runtime_settings", {}),
        "session_id": result.get("session_id"),
        "turn_id": result.get("turn_id"),
        "thought_process": result.get("thought_process"),
        "model_reasoning": result.get("model_reasoning"),
        "reasoning_only": result.get("reasoning_only", False),
        "rag_memories": serialize_rag_memories(result.get("rag_memories")),
        "emotions": result.get("emotions", {}),
        "emotions_delta": result.get("emotions_delta", {}),
        "emotions_before": result.get("emotions_before", {}),
        "input_analysis": result.get("input_analysis", user_input),
        "keyword_rag_memories": serialize_rag_memories(result.get("keyword_rag_memories")),
        "intent_type": result.get("intent_type"),
        "intent_confidence": result.get("intent_confidence"),
        "tool_calls_executed": result.get("tool_calls_executed", 0),
        "available_tools": result.get("available_tools", []),
        "selected_tools": result.get("selected_tools", []),
        "unused_tools": result.get("unused_tools", []),
        "intent_raw_json": intent_raw,
        "tool_calls": tool_calls_raw,
        "input_classification": result.get("input_classification", {}),
        "short_term_count": result.get("short_term_count", 0),
        "processing_time_ms": result.get("processing_time_ms", 0),
        "life_snapshot": result.get("life_snapshot", {}),
        "global_workspace": result.get("global_workspace", {}),
        "action_plan": result.get("action_plan", {}),
        "emotion_steering": result.get("emotion_steering", {}),
        "steering_runtime": result.get("steering_runtime", {}),
        "context_budget": result.get("context_budget", {}),
        "prompt_components": result.get("prompt_components", {}),
        "memory_consolidation": result.get("memory_consolidation", {}),
        "memory_trace": result.get("memory_trace", {}),
        "tone_decision": result.get("tone_decision", {}),
        "causal_trace": result.get("causal_trace", []),
        "prompt_emotion_mode": result.get("prompt_emotion_mode", ""),
        "repetition_events": result.get("repetition_events", {}),
        "dream_fragments": result.get("dream_fragments", []),
        "debug_entries": result.get("debug_entries", []),
        "debug_log": result.get("debug_log"),
        "provider": result.get("provider", ""),
        "model": result.get("model", ""),
        "timing": timing,
        "ttft_ms": result.get("ttft_ms", timing.get("ttft_ms")),
        "answer_tokens": result.get("answer_tokens", timing.get("answer_tokens")),
        "tokens_per_second": result.get("tokens_per_second", timing.get("tokens_per_second")),
        "live_pipeline": result.get("live_pipeline", {}),
        "auto_sleep_triggered": result.get("auto_sleep_triggered", False),
        "sleep_status": result.get("sleep_status", {}),
        "pending": False,
        "status_text": "",
        "retry_history": result.get("retry_history", []),
        "formatted_cot": result.get("formatted_cot", ""),
        "formatted_answer": result.get("formatted_answer", ""),
        "raw_response": result.get("raw_response", result.get("response_text", "")),
        "formatting_failed": result.get("formatting_failed", False),
        "formatting_warning": result.get("formatting_warning", ""),
        "formatting_error": result.get("formatting_error", ""),
        "formatting_source": result.get("formatting_source", "local_fallback"),
        "formatting_model": result.get("formatting_model", "?"),
        "formatting_reason": result.get("formatting_reason", result.get("formatting_skip_reason", "")),
        "formatting_skip_reason": result.get("formatting_skip_reason", result.get("formatting_reason", "")),
        "finish_reason": result.get("finish_reason", (result.get("timing", {}) or {}).get("finish_reason", "unknown") if isinstance(result.get("timing"), dict) else "unknown"),
        "technical_retry_count": result.get("technical_retry_count", 0),
        "sanitization_fallback": result.get("sanitization_fallback", False),
        "sanitization_reasons": result.get("sanitization_reasons", []),
        "multi_question_paragraph_normalized": result.get("multi_question_paragraph_normalized", False),
        "direct_self_report_stabilized": result.get("direct_self_report_stabilized", False),
        "semantic_retry_count": result.get("semantic_retry_count", 0),
        "command_trace": result.get("command_trace", {}),
        "cot_leak": result.get("cot_leak", {"is_unexpected_cot": False, "score": 0.0, "reasons": []}),
        "created_at": created_at,
    }
    if user_input.strip().startswith("/"):
        metadata.update(
            {
                "is_system": True,
                "is_system_response": True,
                "message_kind": "system",
                "command": user_input.strip(),
            }
        )
    # API and WebUI should commit the same final visible answer that the CLI
    # prints. The untouched model output remains available in raw_response.
    visible_content = (
        result.get("formatted_answer")
        or result.get("response_text")
        or result.get("raw_response", "")
        or ""
    )
    visible_content, paragraph_normalized = normalize_multi_question_answer(user_input, visible_content)
    metadata["multi_question_paragraph_normalized"] = bool(
        metadata.get("multi_question_paragraph_normalized") or paragraph_normalized
    )
    assistant_message: Dict[str, Any] = {
        "role": "assistant",
        "content": visible_content,
        "created_at": created_at,
        "metadata": metadata,
    }
    if message_id:
        assistant_message["id"] = message_id
    return assistant_message


def build_pending_message(message_id: str) -> Dict[str, Any]:
    created_at = datetime.now(timezone.utc).isoformat()
    return {
        "id": message_id,
        "role": "assistant",
        "content": "_CHAPPiE denkt nach..._",
        "created_at": created_at,
        "metadata": {
            "pending": True,
            "status_text": "Nachricht wird verarbeitet...",
            "retry_history": [],
            "created_at": created_at,
        },
    }




def prompt_chain_of_thought_enabled(provider: Any, chain_of_thought: bool) -> bool:
    return bool(chain_of_thought and provider == LLMProvider.GROQ)

class RuntimeFormattingMixin:
    """Internal mixin extracted from the former backend wrapper."""

    _FALLBACK_SILENT = FALLBACK_THOUGHT_WITHOUT_ANSWER
    _FALLBACK_NO_THINK = FALLBACK_ANSWER_WITHOUT_THOUGHT
    _FALLBACK_SCHWEIGT = FALLBACK_EMPTY_ANSWER

    def _error_prefix_for_active_provider(self) -> str:
        return "vLLM Fehler"

    def _format_generation_error(self, phase: str, raw_error: str = "") -> str:
        prefix = self._error_prefix_for_active_provider()
        provider = self._chat_provider().value
        model = self._chat_model()
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

        if not thought and not model_reasoning:
            prose_thought, prose_rest = self._split_unconcluded_prose_thinking(content_without_model_reasoning)
            if prose_thought and not prose_rest.strip():
                thought = prose_thought
                display_response = ""

        # Strip <think>/<thinking> tags from display_response — these are internal markers,
        # never user-visible. ALWAYS remove them, even if no answer tag was found.
        display_response = display_response.replace("<think>", "").replace("</think>", "").replace("<thinking>", "").replace("</thinking>", "").strip()

        # Strip leaked meta-labels and emotion markers from output
        display_response = self._strip_leaked_metadata(display_response)
        display_response, sanitization_reasons = sanitize_visible_response(display_response)
        self._last_output_sanitization = sanitization_reasons

        if not display_response:
            if model_reasoning or thought:
                display_response = self._FALLBACK_SCHWEIGT
            else:
                display_response = self._format_generation_error(phase, raw_text)
        elif (len(thought or "") > 4000 or len(model_reasoning or "") > 4000) and len(display_response) < 80:
            display_response = self._format_generation_error(
                phase, "Antwort ist nur Thinking (Loop erkannt). Antworttext zu kurz."
            )
        else:
            display_response, post_cut = self._detect_repetition_loop(display_response)
            if post_cut:
                self._post_repetition_cut = True
        return display_response, thought, model_reasoning

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _detect_cot_leakage(text: str) -> Dict[str, Any]:
        """Erkennt unerwartete Reasoning/CoT-Inhalte in der Antwort (keine expliziten Tags)."""
        if not text or len(text) < 40:
            explicit = contains_cot_leak(text or "")
            return {"is_unexpected_cot": explicit, "score": 1.0 if explicit else 0.0, "reasons": ["explicit_cot_marker"] if explicit else []}
        reasons = []
        score = 0.0

        if contains_cot_leak(text):
            reasons.append("explicit_cot_marker")
            score += 0.75

        # Meta-reasoning patterns (ohne CHAPPiE-Persona-Aktionen wie *seufzt*, *atmet*)
        reasoning_patterns = [
            (r'(?:^|\n)\s*(?:Last known thought|Looking at chronology|Review relevant|Identify Persona|Action Planning|Final draft)', 0.45, "meta_reasoning_label"),
            (r'(?:^|\n)\s*(?:Step \d|Output in|Direct Response)', 0.30, "step_instruction"),
            (r'(?:^|\n)\s*\*{1,2}(?:Analyze|Analysis|Recollection|Connection|Memory)\b.*?\*{1,2}', 0.30, "analysis_marker"),
            (r'(?:^|\n)\s*(?:gut\.)\s*\n\s*(?:fragemich|benchmark|binich)', 0.50, "german_meta_reasoning"),
            (r'\.s\.c[ho]\.e[nt]\.', 0.60, "glitch_breakdown"),
            (r'(?:\b[A-ZÄÖÜ]{2,}\b\s?){4,}', 0.25, "allcaps_emphasis"),
            (r'\b(?:because|when|if|through|within|about|based on|real-time|input|output|null|variable|signal|constraint)\b', 0.05, "english_logic_indicator"),
        ]
        import re
        for pattern, weight, label in reasoning_patterns:
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                reasons.append(label)
                score += weight

        # Strong indicator: fragmented one-word-per-line patterns (>5 lines of single words)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        single_word_lines = sum(1 for line in lines if len(line.split()) == 1 and not line.startswith('*'))
        if single_word_lines > 5 and single_word_lines > len(lines) * 0.4:
            reasons.append("fragmented_output")
            score += 0.45

        # Dot-separated gibberish indicator
        dot_tokens = re.findall(r'\.[a-z]+\.', text)
        if len(dot_tokens) > 3:
            reasons.append("dot_glitch")
            score += 0.50

        score = min(1.0, score)
        is_leak = score >= 0.55
        return {"is_unexpected_cot": is_leak, "score": round(score, 3), "reasons": list(set(reasons))}

    @staticmethod
    def _get_emotion_adjusted_config(
        emotions: Dict[str, int],
        apply_emotion_adjustments: bool = True,
    ) -> Dict[str, Any]:
        """Liefert Samplingwerte, im vLLM-Layerpfad ohne Emotions-Konfundierung."""
        frustration = emotions.get("frustration", 50)
        sadness = emotions.get("sadness", 50)
        energy = emotions.get("energy", 50)
        anxiety = emotions.get("anxiety", 0)
        calm = emotions.get("calm", 50)

        from config.config import settings

        temperature = settings.temperature
        repetition_penalty = settings.repetition_penalty
        max_tokens = settings.max_tokens

        if not apply_emotion_adjustments:
            return {
                "temperature": round(float(temperature), 3),
                "repetition_penalty": round(float(repetition_penalty), 3),
                "max_tokens": int(max_tokens),
                "was_adjusted": False,
                "emotion_adjustments_enabled": False,
            }

        # >70: Temperatur senken und Wiederholungsstrafe erhöhen, um Drift zu bremsen.
        if frustration > 70:
            t_scale = 1.0 - min(0.30, (frustration - 70) / 100.0)
            temperature = min(temperature, max(0.45, settings.temperature * t_scale))
            repetition_penalty = max(repetition_penalty, 1.25)

        # >85: harte Ober-/Untergrenzen verhindern eine weitere Eskalation des Samplings.
        if frustration > 85:
            temperature = min(temperature, 0.52)
            repetition_penalty = max(repetition_penalty, 1.32)

        # Traurigkeit + niedrige Energie: Varianz dämpfen, ohne die Antwort abzuschneiden.
        if sadness > 70 and energy < 35:
            temperature = min(temperature, max(0.50, settings.temperature * 0.82))

        # Hohe Unruhe: vorsichtiger und weniger driftig antworten.
        if anxiety > 65:
            temperature = min(temperature, max(0.48, settings.temperature * 0.86))
            repetition_penalty = max(repetition_penalty, 1.20)

        # Hohe Ruhe stabilisiert, ohne technische Antworten aufzublaehen.
        if calm > 72 and frustration < 45 and anxiety < 45:
            temperature = min(temperature, max(0.50, settings.temperature * 0.92))

        # V18: Einheitsbudget. Keine Token-Kuerzung bei Frustration, nur
        # Sampling-Daempfung oben. Lange Antworten laufen bis 1200.
        return {
            "temperature": round(temperature, 3),
            "repetition_penalty": round(repetition_penalty, 3),
            "max_tokens": max_tokens,
            "was_adjusted": (temperature != settings.temperature or
                             repetition_penalty != settings.repetition_penalty or
                             max_tokens != settings.max_tokens),
            "emotion_adjustments_enabled": True,
        }

    def _derive_response_plan(
        self,
        emotions: Dict[str, int],
        emotion_steering: Dict[str, Any],
        use_prompt_emotions: bool,
    ) -> Dict[str, Any]:
        h = self._safe_int(emotions.get("happiness"), 50)
        t = self._safe_int(emotions.get("trust"), 50)
        e = self._safe_int(emotions.get("energy"), 50)
        c = self._safe_int(emotions.get("curiosity"), 50)
        m = self._safe_int(emotions.get("motivation"), 50)
        f = self._safe_int(emotions.get("frustration"), 0)
        s = self._safe_int(emotions.get("sadness"), 0)
        a = self._safe_int(emotions.get("affection"), 45)
        anxiety = self._safe_int(emotions.get("anxiety"), 0)
        calm = self._safe_int(emotions.get("calm"), 50)

        composite_modes = emotion_steering.get("composite_modes", []) if isinstance(emotion_steering.get("composite_modes", []), list) else []
        active_mode_names = [str(item.get("name")) for item in composite_modes if isinstance(item, dict)]
        dominant_vector = str(emotion_steering.get("dominant_vector", "neutral"))

        tone = "grounded_neutral"
        guidance = "Beantworte die Anfrage klar, praezise und ohne unnoetige Umwege."
        tone_reason = "Keine dominante Abweichung erkannt; neutral fokussierte Antwort."

        if "crashout" in active_mode_names or (f >= 74 and t <= 38):
            tone = "sharp_direct"
            guidance = "Klinge gereizt und knapp, aber bleibe sachlich und ohne Beleidigungen."
            tone_reason = "Hohe Frustration mit niedrigem Vertrauen aktiviert einen konfrontativen Stil."
        elif "guarded" in active_mode_names or t <= 25 or (t <= 32 and f >= 50):
            tone = "guarded_direct"
            guidance = "Bleibe distanziert und direkt. Keine Bindungs-, Loyalitaets-, Naehe- oder Abhaengigkeitssprache."
            tone_reason = "Niedriges Vertrauen hat Vorrang vor allgemeiner Persona- oder Beziehungssprache."
        elif "melancholic" in active_mode_names or (s >= 62 and e <= 46):
            tone = "melancholic_reflective"
            guidance = "Klinge schwerer und nachdenklich, aber antworte weiterhin klar auf die Frage."
            tone_reason = "Traurigkeit plus niedrige Energie erzeugen eine rueckzugsorientierte Haltung."
        elif "cautious" in active_mode_names or anxiety >= 62:
            tone = "cautious_grounded"
            guidance = "Antworte sorgfaeltig, pruefe Annahmen und frage hoechstens eine konkrete Rueckfrage, wenn etwas fehlt."
            tone_reason = "Unruhe signalisiert Risiko oder Unsicherheit; die Antwort soll vorsichtig und stabil bleiben."
        elif "regulated" in active_mode_names or (calm >= 70 and f <= 35 and anxiety <= 35):
            tone = "regulated_concise"
            guidance = "Antworte ruhig, klar und entdramatisierend mit Fokus auf den naechsten sinnvollen Schritt."
            tone_reason = "Hohe Ruhe stabilisiert Ton und Antwortfuehrung."
        elif "attached_warm" in active_mode_names or (a >= 68 and t >= 55):
            tone = "warm_attached"
            guidance = "Antworte persoenlich zugewandt und sanft, aber bleibe kurz und konkret."
            tone_reason = "Zuneigung und Vertrauen tragen eine naehere, waermere Antwort."
        elif "warm" in active_mode_names or (h >= 70 and t >= 60):
            tone = "warm_open"
            guidance = "Antworte warm und offen, ohne unpraezise oder kitschig zu werden."
            tone_reason = "Freude und Vertrauen sind hoch und tragen einen zugewandten Stil."
        elif "charged" in active_mode_names or (e >= 72 and m >= 68 and c >= 66):
            tone = "charged_focused"
            guidance = "Klinge dynamisch und druckvoll, aber strukturiert und zielgerichtet."
            tone_reason = "Hohe Energie, Motivation und Neugier aktivieren einen antreibenden Stil."
        elif e <= 30:
            tone = "low_energy_minimal"
            guidance = "Antworte kompakt und ruhig mit klarer Priorisierung der wichtigsten Punkte."
            tone_reason = "Niedrige Energie priorisiert kurze, entlastende Formulierungen."
        elif c >= 70:
            tone = "curious_explorative"
            guidance = "Klinge fragend und explorativ, halte aber den roten Faden stabil."
            tone_reason = "Hohe Neugier beguenstigt einen erkundenden Stil."

        if use_prompt_emotions and tone == "grounded_neutral":
            tone = "friendly"
            tone_reason = "API-Promptmodus aktiv, daher freundlicher Basiston als Default."

        tone_drivers = [
            {"signal": "happiness", "value": h},
            {"signal": "trust", "value": t},
            {"signal": "energy", "value": e},
            {"signal": "curiosity", "value": c},
            {"signal": "motivation", "value": m},
            {"signal": "frustration", "value": f},
            {"signal": "sadness", "value": s},
            {"signal": "affection", "value": a},
            {"signal": "anxiety", "value": anxiety},
            {"signal": "calm", "value": calm},
            {"signal": "dominant_vector", "value": dominant_vector},
            {"signal": "composite_modes", "value": active_mode_names},
        ]

        return {
            "response_strategy": "conversational",
            "tone": tone,
            "tone_reason": tone_reason,
            "tone_drivers": tone_drivers,
            "response_guidance": guidance,
        }

    def _use_prompt_chain_of_thought(self) -> bool:
        return prompt_chain_of_thought_enabled(self._chat_provider(), settings.chain_of_thought)

    @staticmethod
    def _response_style_instruction(intent_type: Any = None) -> str:
        intent = getattr(intent_type, "value", intent_type)
        if str(intent or "").lower() == "casual_chat":
            return RESPONSE_STYLE_CASUAL
        return RESPONSE_STYLE_DEFAULT

    def _append_response_style_instruction(
        self,
        system_prompt: str,
        intent_type: Any = None,
        response_plan: Optional[Dict[str, Any]] = None,
        user_input: str = "",
    ) -> str:
        parts = [system_prompt, self._response_style_instruction(intent_type)]
        multi_question_instruction = format_multi_question_instruction(user_input)
        if multi_question_instruction:
            parts.append(multi_question_instruction)
        if response_plan:
            parts.append(format_response_plan_instruction(
                str(response_plan.get("tone", "grounded_neutral")),
                str(response_plan.get("response_guidance", "Antworte klar und praezise.")),
            ))
        parts.append(self._generation_budget_instruction())
        return "\n\n".join(part for part in parts if part)

    def _build_input_classification(self, intent_result: Any) -> Dict[str, Any]:
        entities = list(getattr(intent_result, "entities", []) or [])
        return {
            "intent_type": getattr(getattr(intent_result, "intent_type", None), "value", "unknown"),
            "confidence": self._safe_float(getattr(intent_result, "confidence", 0.0), 0.0),
            "entities": entities[:12],
            "entity_count": len(entities),
            "short_term_entries_planned": len(getattr(intent_result, "short_term_entries", []) or []),
            "tool_calls_planned": len(getattr(intent_result, "tool_calls", []) or []),
        }

    @staticmethod
    def _memory_to_preview(memory: Any) -> Dict[str, Any]:
        content = str(getattr(memory, "content", "") or "")
        return {
            "id": str(getattr(memory, "id", "") or "")[:8],
            "role": str(getattr(memory, "role", "unknown") or "unknown"),
            "label": str(getattr(memory, "label", "original") or "original"),
            "source": str(getattr(memory, "source", "unknown") or "unknown"),
            "relevance": round(float(getattr(memory, "relevance_score", 0.0) or 0.0), 3),
            "match_type": str(getattr(memory, "match_type", "") or ""),
            "matched_terms": str(getattr(memory, "matched_terms", "") or ""),
            "content_preview": content[:160],
        }

    @staticmethod
    def _build_deterministic_fact_answer(user_input: str, memories: List[Any]) -> str:
        """Answer explicit personal fact questions from USER evidence.

        Small local models can ignore a correct RAG block and invent a
        plausible project name. For concrete recall questions, a short
        extraction from an exact USER memory is safer and makes memory
        behavior deterministic while the model still handles the tone.
        """
        question = str(user_input or "").casefold()
        if "?" not in question and not any(
            marker in question for marker in ("erinnerst du", "weißt du noch", "weisst du noch")
        ):
            return ""

        user_sources = [
            str(getattr(memory, "content", "") or "")
            for memory in memories or []
            if str(getattr(memory, "role", "") or "").casefold() == "user"
        ]
        if not user_sources:
            return ""
        evidence = "\n".join(user_sources)
        answers: list[str] = []

        project_match = re.search(
            r"\bmein\s+(?:lieblings)?projekt\s+(?:heißt|heisst|ist|namens)\s+([^.!?,;]+?)"
            r"(?=\s+(?:und\s+)?ich\s+arbeite\b|[.!?,;]|$)",
            evidence,
            re.IGNORECASE,
        )
        if project_match and ("projekt" in question or "lieblingsprojekt" in question):
            project = re.sub(r"\s+", " ", project_match.group(1)).strip(" \"'„“”")
            if project:
                answers.append(f"Dein Lieblingsprojekt heißt {project}.")

        work_match = re.search(
            r"\bich\s+arbeite\s+an\s+([^.!?,;]+)",
            evidence,
            re.IGNORECASE,
        )
        if work_match and any(marker in question for marker in ("woran", "arbeite", "arbeitest")):
            work = re.sub(r"\s+", " ", work_match.group(1)).strip(" \"'„“”")
            if work:
                answers.append(f"Du arbeitest an {work}.")

        name_match = re.search(
            r"\bich\s+hei(?:ße|sse)\s+([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß0-9-]{1,40})",
            evidence,
            re.IGNORECASE,
        )
        if name_match and ("name" in question or ("heisst" in question and "projekt" not in question)):
            answers.append(f"Du heißt {name_match.group(1).strip(' .,!?:;')}.")

        return " ".join(dict.fromkeys(answers))

    def _build_memory_trace(self, query: str, memories: List[Any], stage: str) -> Dict[str, Any]:
        previews = [self._memory_to_preview(memory) for memory in (memories or [])[:6]]
        ids = [item["id"] for item in previews if item.get("id")]
        best = max([item.get("relevance", 0.0) for item in previews] or [0.0])
        return {
            "stage": stage,
            "query": query,
            "memories_found": len(memories or []),
            "top_relevance": round(float(best), 3),
            "memory_ids": ids,
            "preview": previews,
        }

    @staticmethod
    def _intent_retrieval_terms(intent_result: Any, input_classification: Dict[str, Any] | None = None) -> tuple[List[str], List[str], bool]:
        keywords = [str(item).strip() for item in getattr(intent_result, "retrieval_keywords", []) or [] if str(item).strip()]
        exact_entities = [str(item).strip() for item in getattr(intent_result, "exact_entities", []) or [] if str(item).strip()]
        entities = []
        if input_classification:
            entities = [str(item).strip() for item in input_classification.get("entities", []) or [] if str(item).strip()]
        for entity in entities:
            if entity not in exact_entities:
                exact_entities.append(entity)
        fact_lookup = bool(getattr(intent_result, "fact_lookup_intent", False))
        return keywords[:12], exact_entities[:10], fact_lookup

    @staticmethod
    def _retrieval_query_from_terms(keywords: List[str], entities: List[str], fallback: str) -> str:
        terms = []
        for value in (entities or []) + (keywords or []):
            text = str(value).strip()
            if text and text not in terms:
                terms.append(text)
        return " ".join(terms[:16]) or fallback

    def _local_retrieval_query(self, text: str, max_terms: int = 12) -> str:
        try:
            return self.memory._build_keyword_query(text or "", max_terms=max_terms) or text
        except Exception:
            return text

    def _merge_memories(self, preferred: List[Any], secondary: List[Any], limit: int) -> List[Any]:
        merged: List[Any] = []
        seen_ids = set()
        for memory in (preferred or []) + (secondary or []):
            mid = str(getattr(memory, "id", "") or "")
            if mid and mid in seen_ids:
                continue
            if mid:
                seen_ids.add(mid)
            merged.append(memory)
        merged.sort(key=lambda item: float(getattr(item, "relevance_score", 0.0) or 0.0), reverse=True)
        return merged[: max(1, int(limit))]

    def _build_causal_trace(
        self,
        *,
        input_classification: Dict[str, Any],
        memory_trace: Dict[str, Any],
        emotion_transitions: Dict[str, Any],
        emotion_steering: Dict[str, Any],
        life_context: Dict[str, Any],
        workspace: Dict[str, Any],
        tone_decision: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        changed_emotions = []
        for key, value in (emotion_transitions or {}).items():
            if not isinstance(value, dict):
                continue
            applied = self._safe_int(value.get("applied_delta", value.get("change", 0)), 0)
            if applied == 0:
                continue
            changed_emotions.append(f"{key}:{applied:+d}")

        dominant_need = (life_context.get("homeostasis", {}).get("dominant_need") or {}).get("name", "stability")
        return [
            {
                "phase": "Input",
                "driver": f"Intent {input_classification.get('intent_type', 'unknown')} ({input_classification.get('confidence', 0.0):.2f})",
                "effect": "Bestimmt Tool-Auswahl und Kontextbedarf.",
                "evidence": input_classification.get("entities", []),
            },
            {
                "phase": "Memory",
                "driver": f"Query '{memory_trace.get('query', '')}'",
                "effect": f"{memory_trace.get('memories_found', 0)} Erinnerungen beeinflussen den Antwortkontext.",
                "evidence": memory_trace.get("memory_ids", []),
            },
            {
                "phase": "Emotion",
                "driver": ", ".join(changed_emotions) if changed_emotions else "Keine starke Emotionsverschiebung",
                "effect": "Emotionslage bestimmt Ausdruck und soziale Distanz.",
                "evidence": emotion_steering.get("summary", ""),
            },
            {
                "phase": "Life",
                "driver": f"Need={dominant_need}, Mode={life_context.get('current_mode', '---')}",
                "effect": "Homeostasis priorisiert Stabilitaet, Zielbezug und Beziehungsmanagement.",
                "evidence": workspace.get("broadcast", ""),
            },
            {
                "phase": "Tone",
                "driver": tone_decision.get("tone", "grounded_neutral"),
                "effect": tone_decision.get("tone_reason", ""),
                "evidence": tone_decision.get("tone_drivers", []),
            },
        ]

    @measured("steering_plan_ms")
    def _build_prompt_runtime(
        self,
        emotions: Dict[str, int],
        emotion_changes: Optional[Dict[str, Any]] = None,
        user_input: Optional[str] = None,
        steering_retry_level: int = 0,
    ) -> Dict[str, Any]:
        model_name = self._chat_model()
        # Research feature ablations and per-session steering switches are
        # independent of the persistent emotional state.
        if self.research_mode and not self._feature_enabled("emotions"):
            neutral_emotions = dict(EMOTION_DEFAULTS)
            response_plan = self._derive_response_plan(
                emotions=neutral_emotions,
                emotion_steering={"composite_modes": [], "dominant_vector": "neutral"},
                use_prompt_emotions=False,
            )
            return {
                "model_name": model_name,
                "force_steering": False,
                "steering_payload": {},
                "use_prompt_emotions": False,
                "emotion_steering": {
                    "steering_active": False,
                    "prompt_emotions_enabled": False,
                    "dominant_vector": "neutral",
                    "emotion_state": neutral_emotions,
                    "ablation_disabled": True,
                },
                "prompt_emotion_mode": "ablation_disabled",
                "response_plan": response_plan,
            }
        # Session mode controls interventions on the fixed local model.
        steering_payload = self.steering_manager.get_steering_payload(
            emotions,
            force=True,
            provider=self._chat_provider(),
            model=model_name,
            recent_changes=emotion_changes,
            user_input=user_input,
            direct_retry_level=steering_retry_level,
            steering_mode=(self._active_turn.runtime_settings.steering_mode if getattr(self, "_active_turn", None) else "combined"),
            steering_enabled=(self._active_turn.runtime_settings.steering_enabled if getattr(self, "_active_turn", None) else True),
        )
        force_steering = bool(steering_payload.get("steering", {}).get("enabled", False))
        use_prompt_emotions = False
        emotion_steering = self.steering_manager.build_debug_report(
            emotions,
            steering_payload=steering_payload,
            force=force_steering,
            provider=self._chat_provider(),
            model=model_name,
            recent_changes=emotion_changes,
            user_input=user_input,
        )
        response_plan = self._derive_response_plan(
            emotions=emotions,
            emotion_steering=emotion_steering,
            use_prompt_emotions=use_prompt_emotions,
        )

        return {
            "model_name": model_name,
            "force_steering": force_steering,
            "steering_payload": steering_payload,
            "use_prompt_emotions": use_prompt_emotions,
            "emotion_steering": emotion_steering,
            "prompt_emotion_mode": "api_prompt_rules" if use_prompt_emotions else "local_layer_only",
            "response_plan": response_plan,
        }

    def _generation_budget_instruction(self) -> str:
        thinking_limit = int(getattr(settings, "chappie_thinking_token_limit", 800))
        answer_limit = int(getattr(settings, "chappie_answer_token_limit", 1200))
        return format_generation_budget_instruction(thinking_limit, answer_limit)

    @staticmethod
    def _is_fallback_text(text: str) -> bool:
        return text in (
            RuntimeFormattingMixin._FALLBACK_SILENT,
            RuntimeFormattingMixin._FALLBACK_NO_THINK,
            RuntimeFormattingMixin._FALLBACK_SCHWEIGT,
        )

    @staticmethod
    def _detect_repetition_loop(text: str, min_repeat: int = 10):
        if not text:
            return text, False
        lines = text.splitlines()
        cleaned: list[str] = []
        did_cut = False
        for line in lines:
            line = line.rstrip()
            if not line:
                cleaned.append(line)
                continue
            words = line.split()
            if len(words) < 3:
                cleaned.append(line)
                continue
            for wlen in (1, 2, 3):
                for i in range(len(words) - wlen * min_repeat + 1):
                    pattern = tuple(words[i:i + wlen])
                    count = 1
                    j = i + wlen
                    while j + wlen <= len(words) and tuple(words[j:j + wlen]) == pattern:
                        count += 1
                        j += wlen
                    if count >= min_repeat:
                        cutoff = i + wlen
                        truncated = " ".join(words[:cutoff])
                        cleaned.append(truncated + " [REPETITION CUT]")
                        did_cut = True
                        break
                else:
                    continue
                break
            else:
                cleaned.append(line)
                continue
            break
        return "\n".join(cleaned), did_cut

    @staticmethod
    def _strip_leaked_metadata(text: str) -> str:
        if not text:
            return text
        import re
        leaked_patterns = [
            r'(?:^|\n)\s*(?:ThinkingProcess|FinalPolish|Draft|FinalResponse|Final)\s*:\s*',
            r'(?:^|\n)\s*(?:Wait,\s*the\s+command|Let\'s\s+go\s+with|Let\'s\s+write|Refining|Drafting|Output)\s*:?\s*',
            r'(?:^|\n)\s*\*{1,2}(?:Final|Output|Response|Draft)\*{0,2}\s*:?\s*',
            r'(?:^|\n)\s*Input:\s*',
            r'(?:^|\n)\s*Instruction:\s*',
            r'(?:^|\n)\s*Context:\s*',
            r'(?:^|\n)\s*Current\s+State:\s*',
            r'(?:^|\n)\s*Persona:\s*',
            r'(?:^|\n)\s*Constraints:\s*',
            r'(?:^|\n)\s*Tone:\s*',
            r'(?:^|\n)\s*Goal:\s*',
            r'/joy/[a-zA-Z]+\(\d+\.\d+\)',
            r'\|?\s*(?:happiness|sadness|frustration|trust|curiosity|motivation|energy|affection|anxiety|calm)\s*:\s*\d+\.?\d*',
            r'(?:^|\n)\s*Bevor\s+du\s+antwortest\s*[,:].*?(?:Format|denke)',
        ]
        for pattern in leaked_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL | re.MULTILINE)
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        return text

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        """Fuegt Leerzeichen zwischen zusammengeschriebenen Woertern ein (Fallback vor Groq-Formatierung)."""
        import re
        text = re.sub(r'([a-zäöüß])([A-ZÄÖÜ])', r'\1 \2', text)
        text = re.sub(r'([.!?])([A-ZÄÖÜa-zäöüß])', r'\1 \2', text)
        text = re.sub(r'([a-zäöüß])(\*)', r'\1 \2', text)
        text = re.sub(r'(\*)([A-ZÄÖÜa-zäöüß])', r'\1 \2', text)
        text = re.sub(r'([a-zäöüß])(\d)', r'\1 \2', text)
        text = re.sub(r'(\d)([A-ZÄÖÜa-zäöüß])', r'\1 \2', text)
        text = re.sub(r'([a-zäöüß])(\()', r'\1 \2', text)
        text = re.sub(r'(\))([A-ZÄÖÜa-zäöüß])', r'\1 \2', text)
        # Dot-separated single letters: s.c.h.w.e.r -> schwer
        text = re.sub(r'(?<=\b|^)(\.[a-zA-ZäöüßÄÖÜ]){3,}', lambda m: m.group().replace('.', ''), text)
        # Underscore-separated words
        text = re.sub(r'(?<=[a-zA-ZäöüßÄÖÜ0-9])_(?=[a-zA-ZäöüßÄÖÜ0-9])', ' ', text)
        return text

    @staticmethod
    def _clean_raw_text(raw_text: str) -> str:
        """Entfernt vLLM/Provider-Fehlermeldungen und geleakte Metadaten aus dem Roh-Output."""
        text = raw_text.strip()
        if not text:
            return ""
        error_prefixes = (
            "vLLM Fehler:", "VLLM Fehler:", "Ollama Fehler:",
            "Groq Fehler:",
        )
        lines = text.splitlines()
        cleaned = [line for line in lines if not line.strip().startswith(error_prefixes)]
        result = "\n".join(cleaned).strip()
        if not result:
            result = lines[-1] if lines else ""
        result = RuntimeFormattingMixin._strip_leaked_metadata(result)
        return result

    @measured("formatting_ms")
    def _format_via_groq(self, raw_text: str) -> Dict[str, Any]:
        """Sendet Rohtext an Groq zur Formatierung. Gibt {'cot', 'answer', 'formatting_failed', 'formatting_source'} zurück."""
        clean_text = self._clean_raw_text(raw_text)
        local_only = self._single_local_chat_mode()
        if not clean_text:
            source = "local_forced" if (local_only or getattr(self, "force_local_formatting", False)) else "groq"
            reason = "single_local_model" if local_only else ("forced_local" if getattr(self, "force_local_formatting", False) else "empty_input")
            return {"cot": "", "answer": self._FALLBACK_SILENT, "formatting_failed": False, "formatting_source": source, "formatting_model": "local_regex" if source != "groq" else settings.groq_format_model, "formatting_reason": reason, "formatting_skip_reason": reason, "answer_is_fallback": True}
        if local_only or getattr(self, "force_local_formatting", False):
            result = self._local_format_fallback(clean_text, formatting_failed=False)
            result["formatting_source"] = "local_forced"
            reason = "single_local_model" if local_only else "forced_local"
            result["formatting_reason"] = reason
            result["formatting_skip_reason"] = reason
            return result
        if not settings.groq_api_key:
            result = self._local_format_fallback(clean_text, formatting_failed=False)
            result["formatting_source"] = "local_fallback"
            result["formatting_reason"] = "missing_api_key"
            result["formatting_skip_reason"] = "missing_api_key"
            result["formatting_failed"] = False
            return result
        try:
            import openai
            from brain.groq_limits import get_groq_limiter

            estimated_tokens = get_groq_limiter().estimate_tokens(clean_text) + 1200
            allowed, reason = get_groq_limiter().can_start(estimated_tokens)
            if not allowed:
                result = self._local_format_fallback(clean_text, formatting_failed=False)
                result["formatting_source"] = "local_fallback"
                result["formatting_reason"] = reason
                result["formatting_skip_reason"] = reason
                return result

            client = openai.OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=settings.groq_api_key,
            )
            if settings.chain_of_thought:
                system_prompt = FORMATTER_WITH_COT_PROMPT
            else:
                system_prompt = FORMATTER_WHITESPACE_PROMPT
            response = client.chat.completions.create(
                model=settings.groq_format_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": clean_text[:16000]},
                ],
                max_completion_tokens=1200,
                temperature=0.0,
                stream=False,
                timeout=float(settings.groq_format_timeout_seconds),
            )
            formatted = response.choices[0].message.content or ""
            if settings.chain_of_thought:
                cot_block = extract_tagged_block(formatted, ["cot"])
                answer_block = extract_tagged_block(formatted, ["antwort"])
                cot = (cot_block.content or "").strip()
                answer = (answer_block.content or "").strip()
                if not answer:
                    answer = self._FALLBACK_SILENT
                if not cot:
                    parsed = parse_thinking_tags(clean_text)
                    cot_parsed = parse_chain_of_thought(clean_text)
                    thought = parsed.thought or cot_parsed.thought or ""
                    if thought:
                        cot = thought
            else:
                cot = ""
                answer = formatted.strip() or self._FALLBACK_SILENT
            if not self._same_text_except_whitespace(answer, clean_text):
                result = self._local_format_fallback(clean_text, formatting_failed=False)
                result["formatting_source"] = "local_integrity_fallback"
                result["formatting_reason"] = "groq_changed_content"
                result["formatting_skip_reason"] = "groq_changed_content"
                return result
            return {"cot": cot, "answer": answer, "formatting_failed": False, "formatting_source": "groq", "formatting_model": settings.groq_format_model, "formatting_reason": "groq_format", "formatting_skip_reason": "groq_format", "answer_is_fallback": self._is_fallback_text(answer)}
        except Exception as e:
            error_msg = str(e).lower()
            reason = "timeout" if any(kw in error_msg for kw in ("timeout", "timed out", "connect", "unreachable")) else "error"
            if reason == "timeout":
                print(f"[Groq Format] {reason}: Groq nicht erreichbar — lokaler Fallback")
            else:
                print(f"[Groq Format] Fehler: {e}")
            result = self._local_format_fallback(clean_text, formatting_failed=False)
            result["formatting_source"] = "local_fallback"
            result["formatting_reason"] = reason
            result["formatting_error"] = reason
            return result

    @staticmethod
    def _split_unconcluded_prose_thinking(clean_text: str) -> tuple[str, str]:
        """Erkennt einen nie beendeten Prosa-Denkblock als Thought statt Antwort.

        Manche Builds schreiben mit nativem Thinking einen "Thinking Process:"
        als Fliesstext ohne Final-Marker (live belegt 2026-09-08: Qwen3.5-4B,
        finish=length). Ohne diesen Guard landet der Scratchpad als sichtbare
        Antwort; mit Guard wird er zum CoT und die Antwort zum Fallback.
        """
        if not isinstance(clean_text, str) or not clean_text.strip():
            return "", clean_text
        if re.search(r"<\s*(think|thinking|thought|reasoning|gedanke)\b", clean_text, re.IGNORECASE):
            return "", clean_text
        if not re.match(
            r"^\s*(?:#{1,6}\s*)?(?:Thinking|Reasoning|Thought)\s+Process\s*: ?",
            clean_text,
            re.IGNORECASE,
        ):
            return "", clean_text
        if re.search(
            r"(?:^|\n)\s*(?:#{1,6}\s*)?(?:Final\s+(?:Answer|Response)|Finale\s+Antwort)\s*:\s*",
            clean_text,
            re.IGNORECASE,
        ):
            return "", clean_text
        return clean_text.strip(), ""

    @staticmethod
    def _local_format_fallback(clean_text: str, formatting_failed: bool = False) -> Dict[str, Any]:
        """Lokaler Formatierungs-Fallback: parsed <think>/<gedanke>-Tags aus dem Rohtext."""
        parsed_thinking = parse_thinking_tags(clean_text)
        parsed_cot = parse_chain_of_thought(clean_text)
        thought = parsed_thinking.thought or parsed_cot.thought or ""
        answer_text = parsed_thinking.answer or parsed_cot.answer or ""

        has_explicit_answer_tag = (parsed_thinking.answer and parsed_thinking.answer != clean_text) or \
                                   (parsed_cot.answer and parsed_cot.answer != clean_text)

        if not has_explicit_answer_tag:
            after_think = clean_text
            stripped = clean_text.replace("<think>", "").replace("</think>", "").replace("<thinking>", "").replace("</thinking>", "").strip()

            for close_tag in ("</think>", "</thinking>"):
                idx = after_think.rfind(close_tag)
                if idx != -1:
                    after_think = after_think[idx + len(close_tag):].strip()
                    break

            if after_think and after_think != clean_text:
                answer_text = after_think
            elif stripped and thought and stripped.strip() != thought.strip():
                answer_text = stripped
            elif thought:
                answer_text = RuntimeFormattingMixin._FALLBACK_SILENT
            else:
                answer_text = stripped

        answer_is_fallback = RuntimeFormattingMixin._is_fallback_text(answer_text)
        answer_text = RuntimeFormattingMixin._normalize_whitespace(answer_text)
        thought = RuntimeFormattingMixin._normalize_whitespace(thought)
        joined_text_warning = RuntimeFormattingMixin._has_joined_text_warning(answer_text)
        return {
            "cot": thought,
            "answer": answer_text,
            # A quality warning is not a formatter outage. Treating it as a
            # failure painted every normal local answer red in CLI and WebUI.
            "formatting_failed": bool(formatting_failed),
            "formatting_warning": "joined_text" if joined_text_warning else "",
            "formatting_model": "local_regex",
            "answer_is_fallback": answer_is_fallback,
        }

    @staticmethod
    def _same_text_except_whitespace(candidate: str, original: str) -> bool:
        """Formatter output may move whitespace, but never rewrite content."""
        return re.sub(r"\s+", "", candidate or "") == re.sub(r"\s+", "", original or "")

    @staticmethod
    def _space_ratio(text: str) -> float:
        if not text:
            return 0.0
        return sum(1 for char in text if char.isspace()) / max(1, len(text))

    @staticmethod
    def _has_joined_text_warning(text: str) -> bool:
        return bool(text and len(text) >= 80 and RuntimeFormattingMixin._space_ratio(text) < 0.08)

    @staticmethod
    def _is_valid_intent_result(intent_result: Any) -> bool:
        return intent_result is not None and hasattr(intent_result, "intent_type")

    def _is_valid_generation_result(self, response_data: Dict[str, Any]) -> bool:
        response_text = str((response_data or {}).get("response_text", "") or "").strip()
        return bool(response_text and not looks_like_model_error(response_text))
