"""JSON-Logging pro Session: config, summary, fragen-details."""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

LOG_ROOT = Path(__file__).resolve().parent / "session_logs"

_ERROR_PREFIXES = (
    "vLLM Fehler", "VLLM Fehler", "Ollama Fehler", "Groq Fehler",
)


def _looks_like_error(text: str) -> bool:
    if not text or not text.strip():
        return True
    return text.strip().startswith(_ERROR_PREFIXES)


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
    ) -> None:
        entry = {
            "session_id": self.session_id,
            "iteration": iteration,
            "category": category_name,
            "category_id": category_id,
            "question_number": question_number,
            "question_text": question_text,
            "commands_before": commands_before,
            "commands_after": commands_after,
            "timestamp": datetime.now().isoformat(),
            "duration_ms": round(duration_ms),
            "emotions_before": emotions_before,
            "emotions_after": emotions_after,
        }

        if error:
            entry["_error"] = error
            self.error_count += 1
            result = None

        if result:
            resp_text = result.get("response_text", "")
            resp_len = len(resp_text.strip()) if resp_text else 0
            is_fmt_fail = result.get("formatting_failed", False)
            is_gen_error = _looks_like_error(resp_text)
            is_short = 0 < resp_len < 20

            if is_fmt_fail:
                self.formatting_failures += 1
            if is_gen_error:
                self.generation_failures += 1
            if is_short:
                self.short_answers += 1
            self.total_response_chars += resp_len

            entry["response"] = {
                "response_text": resp_text,
                "formatted_cot": result.get("formatted_cot", ""),
                "formatted_answer": result.get("formatted_answer", ""),
                "formatting_source": result.get("formatting_source", "local_fallback"),
                "formatting_model": result.get("formatting_model", "?"),
                "formatting_failed": is_fmt_fail,
                "generation_failed": is_gen_error,
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

        filename = f"{question_number:03d}_cat{category_id}_{category_name[:20].replace(' ', '_')}_q{question_number}.json"
        filepath = self.session_dir / "questions" / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(entry, f, indent=2, ensure_ascii=False, default=str)

    def finalize(self) -> str:
        end_time = datetime.now()
        total_duration_ms = (end_time - self.start_time).total_seconds() * 1000

        question_count = len(self.question_logs)
        error_count = self.error_count
        completed_count = question_count - error_count

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
            "errors": error_count,
            "quality": {
                "formatting_failures": self.formatting_failures,
                "generation_failures": self.generation_failures,
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
