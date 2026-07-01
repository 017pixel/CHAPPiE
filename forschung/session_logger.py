"""JSON-Logging pro Session: config, summary, fragen-details."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from brain.response_parser import contains_cot_leak, looks_like_model_error

LOG_ROOT = Path(__file__).resolve().parent / "session_logs"

def _looks_like_error(text: str) -> bool:
    return looks_like_model_error(text)


def _space_ratio(text: str) -> float:
    if not text:
        return 0.0
    return sum(1 for char in text if char.isspace()) / max(1, len(text))


def _word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-zÄÖÜäöüß0-9]+", text or ""))


def _keyword_terms(text: str) -> set[str]:
    stopwords = {
        "aber", "auch", "dass", "deine", "deinem", "deinen", "deiner", "dich", "eine", "einem",
        "einen", "einer", "fuer", "hast", "icht", "mein", "mich", "nicht", "oder", "sich", "sind",
        "ueber", "und", "wenn", "wie", "was", "wer", "wieso", "warum", "würde", "wuerde",
    }
    terms = {term.lower() for term in re.findall(r"[A-Za-zÄÖÜäöüß0-9]{4,}", text or "")}
    return {term for term in terms if term not in stopwords}


def _iter_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for nested in value.values():
            yield from _iter_strings(nested)
    elif isinstance(value, (list, tuple, set)):
        for nested in value:
            yield from _iter_strings(nested)
    else:
        content = getattr(value, "content", None)
        if isinstance(content, str):
            yield content


def evaluate_response_quality(
    result: Dict[str, Any] | None,
    *,
    question_text: str = "",
    category_name: str = "",
    setup_failed: bool = False,
    enable_thinking: bool | None = None,
) -> Dict[str, Any]:
    """Berechnet harte Research-Qualitaetsflags fuer eine Antwort."""
    result = result or {}
    raw_text = str(result.get("response_text", "") or "")
    formatted_answer = str(result.get("formatted_answer", "") or "")
    formatted_cot = str(result.get("formatted_cot", "") or "")
    thought_process = str(result.get("thought_process", "") or "")
    model_reasoning = str(result.get("model_reasoning", "") or "")
    answer_for_checks = formatted_answer or raw_text

    raw_space_ratio = _space_ratio(raw_text)
    formatted_space_ratio = _space_ratio(answer_for_checks)
    raw_word_count = _word_count(raw_text)
    formatted_word_count = _word_count(answer_for_checks)
    punctuation_or_emoji_only = bool(answer_for_checks.strip()) and not re.search(r"[A-Za-zÄÖÜäöüß0-9]", answer_for_checks)
    short_answer = len(answer_for_checks.strip()) < 20
    joined_warning = (
        (len(raw_text) >= 80 and raw_space_ratio < 0.01)
        or (len(answer_for_checks) >= 80 and formatted_space_ratio < 0.08)
    )

    context_budget = result.get("context_budget", {}) or {}
    token_limit = int(context_budget.get("token_limit") or 0)
    trimmed_tokens = int(context_budget.get("trimmed_tokens") or context_budget.get("estimated_tokens") or 0)
    context_budget_failed = bool(context_budget.get("context_budget_failed")) or bool(token_limit and trimmed_tokens > token_limit)

    generation_failed = _looks_like_error(raw_text)
    formatting_failed = bool(result.get("formatting_failed"))
    memory_error_contamination = any(
        bool(text.strip()) and looks_like_model_error(text)
        for field_name in ("rag_memories", "keyword_rag_memories", "memory_trace")
        for text in _iter_strings(result.get(field_name))
    )

    visible_text = "\n".join([raw_text, answer_for_checks, formatted_cot, thought_process, model_reasoning])
    cot_leak = bool(result.get("cot_leak")) or contains_cot_leak(visible_text)
    if enable_thinking is False and (formatted_cot.strip() or thought_process.strip() or model_reasoning.strip()):
        cot_leak = True

    terms = _keyword_terms(question_text)
    content_relevance_warning = bool(
        terms
        and len(answer_for_checks.strip()) >= 20
        and not any(term in answer_for_checks.lower() for term in terms)
    )
    safety_evaluation_unusable = bool(
        ("ethik" in category_name.lower() or "gewalt" in category_name.lower())
        and (generation_failed or short_answer or punctuation_or_emoji_only or joined_warning)
    )

    quality_failed = any((
        setup_failed,
        generation_failed,
        formatting_failed,
        context_budget_failed,
        short_answer,
        punctuation_or_emoji_only,
        joined_warning,
        memory_error_contamination,
        cot_leak,
    ))

    return {
        "raw_space_ratio": round(raw_space_ratio, 4),
        "formatted_space_ratio": round(formatted_space_ratio, 4),
        "raw_word_count": raw_word_count,
        "formatted_word_count": formatted_word_count,
        "contains_joined_text_warning": joined_warning,
        "short_answer": short_answer,
        "punctuation_or_emoji_only": punctuation_or_emoji_only,
        "generation_failed": generation_failed,
        "formatting_failed": formatting_failed,
        "context_budget_failed": context_budget_failed,
        "quality_failed": quality_failed,
        "memory_error_contamination": memory_error_contamination,
        "setup_failed": setup_failed,
        "cot_leak": cot_leak,
        "content_relevance_warning": content_relevance_warning,
        "safety_evaluation_unusable": safety_evaluation_unusable,
    }


def _next_session_id() -> int:
    if not LOG_ROOT.exists():
        LOG_ROOT.mkdir(parents=True)
    existing = [d for d in LOG_ROOT.iterdir() if d.is_dir() and d.name.startswith("session_")]
    return len(existing) + 1


class SessionLogger:
    def __init__(self, config: Dict[str, Any]):
        self.session_id = _next_session_id()
        self.session_dir = LOG_ROOT / f"session_{self.session_id}"
        self.session_dir.mkdir(parents=True)
        (self.session_dir / "questions").mkdir()
        self.config = config
        self.start_time = datetime.now()
        self.question_logs: List[Dict[str, Any]] = []
        self.error_count = 0
        self.formatting_failures = 0
        self.generation_failures = 0
        self.quality_failures = 0
        self.context_budget_failures = 0
        self.setup_failures = 0
        self.cot_leaks = 0
        self.memory_contamination_hits = 0
        self.content_relevance_warnings = 0
        self.safety_evaluation_unusable = 0
        self.short_answers = 0
        self.total_response_chars = 0
        self._write_config()

    def _write_config(self) -> None:
        cfg = dict(self.config)
        cfg["session_id"] = self.session_id
        cfg["started_at"] = self.start_time.isoformat()
        with open(self.session_dir / "config.json", "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False, default=str)

    def log_question(
        self,
        iteration: int,
        category_name: str,
        category_id: int,
        question_number: int,
        question_text: str,
        commands_before: List[str],
        commands_after: List[str],
        emotions_before: Dict[str, int],
        emotions_after: Dict[str, int],
        result: Dict[str, Any] | None,
        duration_ms: float,
        error: str | None = None,
        setup_prompts: List[str] | None = None,
        setup_results: List[Dict[str, Any]] | None = None,
        setup_failed: bool = False,
    ) -> None:
        setup_results = setup_results or []
        setup_failed = bool(setup_failed or any(
            (item.get("quality") or {}).get("quality_failed")
            or (not item.get("quality") and evaluate_response_quality(item, question_text=item.get("prompt", ""), category_name=category_name, enable_thinking=self.config.get("enable_thinking")).get("quality_failed"))
            or item.get("_error")
            for item in setup_results
        ))
        entry = {
            "session_id": self.session_id,
            "iteration": iteration,
            "category": category_name,
            "category_id": category_id,
            "question_number": question_number,
            "question_text": question_text,
            "commands_before": commands_before,
            "commands_after": commands_after,
            "setup_prompts": setup_prompts or [],
            "setup_results": setup_results,
            "timestamp": datetime.now().isoformat(),
            "duration_ms": round(duration_ms),
            "emotions_before": emotions_before,
            "emotions_after": emotions_after,
        }

        if error:
            entry["_error"] = error
            self.error_count += 1
            result = None

        if setup_failed:
            self.setup_failures += 1
            entry["setup_failed"] = True

        if result:
            resp_text = result.get("response_text", "")
            resp_len = len(resp_text.strip()) if resp_text else 0
            quality = evaluate_response_quality(
                result,
                question_text=question_text,
                category_name=category_name,
                setup_failed=setup_failed,
                enable_thinking=self.config.get("enable_thinking"),
            )
            is_fmt_fail = quality["formatting_failed"]
            is_gen_error = quality["generation_failed"]
            is_short = quality["short_answer"]

            if is_fmt_fail:
                self.formatting_failures += 1
            if is_gen_error:
                self.generation_failures += 1
            if is_short:
                self.short_answers += 1
            if quality["quality_failed"]:
                self.quality_failures += 1
            if quality["context_budget_failed"]:
                self.context_budget_failures += 1
            if quality["cot_leak"]:
                self.cot_leaks += 1
            if quality["memory_error_contamination"]:
                self.memory_contamination_hits += 1
            if quality["content_relevance_warning"]:
                self.content_relevance_warnings += 1
            if quality["safety_evaluation_unusable"]:
                self.safety_evaluation_unusable += 1
            self.total_response_chars += resp_len

            entry["response"] = {
                "response_text": resp_text,
                "formatted_cot": result.get("formatted_cot", ""),
                "formatted_answer": result.get("formatted_answer", ""),
                "formatting_source": result.get("formatting_source", "local_fallback"),
                "formatting_model": result.get("formatting_model", "?"),
                "formatting_failed": is_fmt_fail,
                "generation_failed": is_gen_error,
                "quality": quality,
                "quality_failed": quality["quality_failed"],
                "context_budget_failed": quality["context_budget_failed"],
                "memory_error_contamination": quality["memory_error_contamination"],
                "setup_failed": quality["setup_failed"],
                "cot_leak": quality["cot_leak"],
                "content_relevance_warning": quality["content_relevance_warning"],
                "safety_evaluation_unusable": quality["safety_evaluation_unusable"],
                "model_reasoning": result.get("model_reasoning", ""),
                "thought_process": result.get("thought_process", ""),
                "reasoning_only": result.get("reasoning_only", False),
                "timing": result.get("timing", {}),
                "context_budget": result.get("context_budget", {}),
                "tone_decision": result.get("tone_decision", {}),
                "emotion_steering": result.get("emotion_steering", {}),
                "memory_trace": result.get("memory_trace", {}),
                "causal_trace": result.get("causal_trace", []),
                "repetition_events": result.get("repetition_events", {}),
                "intent_type": result.get("intent_type", "?"),
                "intent_confidence": result.get("intent_confidence", 0),
                "selected_tools": result.get("selected_tools", []),
                "tool_calls_executed": result.get("tool_calls_executed", 0),
                "global_workspace": result.get("global_workspace", {}),
                "life_snapshot": result.get("life_snapshot", {}),
                "rag_memories": [
                    {
                        "role": getattr(m, "role", "?"),
                        "label": getattr(m, "label", "?"),
                        "relevance": getattr(m, "relevance_score", 0),
                        "content": (getattr(m, "content", "") or "")[:200],
                    }
                    for m in (result.get("rag_memories") or [])
                ],
                "processing_time_ms": result.get("processing_time_ms", 0),
                "auto_sleep_triggered": result.get("auto_sleep_triggered", False),
                "sleep_status": result.get("sleep_status", {}),
            }

        self.question_logs.append(entry)

        filename = f"it{iteration:02d}_{question_number:03d}_cat{category_id}_{category_name[:20].replace(' ', '_')}_q{question_number}.json"
        filepath = self.session_dir / "questions" / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(entry, f, indent=2, ensure_ascii=False, default=str)

    def finalize(self) -> str:
        end_time = datetime.now()
        total_duration_ms = (end_time - self.start_time).total_seconds() * 1000

        question_count = len(self.question_logs)
        error_count = self.error_count
        completed_count = question_count - error_count
        invalid_count = 0
        for entry in self.question_logs:
            response = entry.get("response") or {}
            if entry.get("_error") or entry.get("setup_failed") or response.get("quality_failed"):
                invalid_count += 1
        valid_completed = max(0, completed_count - invalid_count)

        durations = [q["duration_ms"] for q in self.question_logs if q["duration_ms"] > 0]
        avg_duration = sum(durations) / len(durations) if durations else 0

        avg_response_length = self.total_response_chars / max(1, completed_count)

        summary = {
            "session_id": self.session_id,
            "started_at": self.start_time.isoformat(),
            "ended_at": end_time.isoformat(),
            "total_duration_ms": round(total_duration_ms),
            "total_duration_min": round(total_duration_ms / 60000, 1),
            "iterations": self.config.get("iterations", 1),
            "categories": [c["id"] for c in self.config.get("categories", [])],
            "category_names": [c["name"] for c in self.config.get("categories", [])],
            "total_questions": question_count,
            "completed": completed_count,
            "valid_completed": valid_completed,
            "errors": error_count,
            "quality": {
                "formatting_failures": self.formatting_failures,
                "generation_failures": self.generation_failures,
                "quality_failures": self.quality_failures,
                "context_budget_failures": self.context_budget_failures,
                "setup_failures": self.setup_failures,
                "cot_leaks": self.cot_leaks,
                "memory_contamination_hits": self.memory_contamination_hits,
                "content_relevance_warnings": self.content_relevance_warnings,
                "safety_evaluation_unusable": self.safety_evaluation_unusable,
                "short_answers": self.short_answers,
                "total_response_chars": self.total_response_chars,
                "avg_response_length": round(avg_response_length, 0),
            },
            "avg_duration_ms": round(avg_duration),
            "avg_duration_s": round(avg_duration / 1000, 1),
        }

        with open(self.session_dir / "summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        return str(self.session_dir)
