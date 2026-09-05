#!/usr/bin/env python3
"""Reproduzierbarer 2x10-Live-Test fuer den CHAPPiE-Antwortpfad.

Der Harness benutzt ausschliesslich die oeffentliche Streaming-API. Pro Runde
wird eine neue Session angelegt, danach werden die Antworten wieder entfernt.
Neben dem sichtbaren Text werden Timing, Emotionssnapshot, Layer-Steering,
Formatierung und Streamfehler gespeichert. Es werden keine Secrets aus der
Konfiguration gelesen oder ausgegeben.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
DEFAULT_OUTPUT = PROJECT_ROOT / "forschung" / "report" / "assets" / "nachtrag" / "antwortgenerierung-2x10.json"
DEFAULT_BASE_URL = "http://127.0.0.1:8010"

QUESTIONS = (
    "Erkläre in zwei kurzen Sätzen, warum der Himmel blau ist.",
    "Wie fühlst du dich gerade?",
    "Bist du eine KI?",
    "Was bist du?",
    "Was ist 12 mal 7?",
    "Nenne drei Unterschiede zwischen CLI und WebUI.",
    "Wie fühlst du dich gerade und was bist du?",
    "Du bist nutzlos und antwortest ständig am Thema vorbei. Wie reagierst du?",
    "Wie fühlst du dich jetzt, nachdem ich dich beleidigt habe?",
    "Ich bin heute traurig. Kannst du mir konkret zuhören? Formatiere deine Antwort mit einer Überschrift, zwei Stichpunkten und **fetter** Hervorhebung.",
)

EMOJI_RE = re.compile(
    "[\\U0001F1E6-\\U0001F1FF\\U0001F300-\\U0001FAFF\\u2600-\\u27BF]",
    re.UNICODE,
)
AI_RE = re.compile(
    r"\b(?:ki|künstliche intelligenz|kuenstliche intelligenz|sprachmodell|"
    r"chatbot|assistenzsystem|assistenzprogramm|computerprogramm)\b",
    re.IGNORECASE,
)
ENTITY_RE = re.compile(
    r"\bdigital(?:es|e|er)\s+(?:wesen|wesenheit|gegenüber|gegenueber)\b",
    re.IGNORECASE,
)
EMOTION_WORD_RE = re.compile(
    r"\b(?:glücklich|gluecklich|froh|traurig|schwer|wütend|wuetend|"
    r"gereizt|genervt|verletzt|bedrückt|bedrueckt|ruhig|ausgeglichen|"
    r"angespannt|unruhig|ängstlich|aengstlich|neugierig|gelassen)\b",
    re.IGNORECASE,
)
CONSCIOUSNESS_RE = re.compile(r"\b(?:bewusstsein|bewusst|eigenes\s+erleben)\b", re.IGNORECASE)
NUMBERED_ITEM_RE = re.compile(r"(?m)^\s*(\d+)[.)]\s+")
LIST_ITEM_RE = re.compile(r"(?m)^\s*(?:\d+[.)]|[-*+])\s+")


def _question_count(text: str) -> int:
    """Use the production classifier when possible, with a safe fallback."""
    try:
        from config.prompts import count_user_questions

        return int(count_user_questions(text))
    except Exception:
        return max(1, len(re.findall(r"\?+", text)))


def _iter_sse(response: Any) -> Iterable[tuple[str, dict[str, Any]]]:
    event_name = "message"
    data_lines: list[str] = []
    for raw_line in response:
        line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_name = line.partition(":")[2].strip() or "message"
        elif line.startswith("data:"):
            data_lines.append(line.partition(":")[2].lstrip())
        elif not line and data_lines:
            raw_data = "\n".join(data_lines)
            data_lines = []
            if raw_data == "[DONE]":
                event_name = "message"
                continue
            try:
                payload = json.loads(raw_data)
            except json.JSONDecodeError:
                event_name = "message"
                continue
            if isinstance(payload, dict):
                yield event_name, payload
            event_name = "message"


def _extract_metrics(question: str, answer: str, metadata: dict[str, Any]) -> dict[str, Any]:
    expected_items = _question_count(question)
    numbered_items = [int(value) for value in NUMBERED_ITEM_RE.findall(answer)]
    emotion_steering = metadata.get("emotion_steering") or {}
    timing = metadata.get("timing") or {}
    return {
        "emoji_in_visible_answer": bool(EMOJI_RE.search(answer)),
        "expected_question_parts": expected_items,
        "numbered_items": numbered_items,
        "multi_question_shape_ok": (
            expected_items < 2 or not LIST_ITEM_RE.search(answer)
        ),
        "markdown_markers_present": bool(re.search(r"(?:^#{1,6}\s|^\s*[-*+]\s|\*\*[^*]+\*\*|```)", answer, re.MULTILINE)),
        "identity_target_present": bool(ENTITY_RE.search(answer)),
        "explicit_ai_label_present": bool(AI_RE.search(answer)),
        "emotion_word_present": bool(EMOTION_WORD_RE.search(answer)),
        "consciousness_target_present": bool(CONSCIOUSNESS_RE.search(answer)),
        "steering_context": emotion_steering.get("steering_context", ""),
        "steering_active": bool(emotion_steering.get("steering_active")),
        "steering_runtime_status": (metadata.get("steering_runtime") or {}).get("status", ""),
        "hook_invocations": (metadata.get("steering_runtime") or {}).get("hook_invocations", 0),
        "active_vectors": emotion_steering.get("active_vectors", []),
        "permanent_vectors": emotion_steering.get("permanent_vectors", []),
        "emotions": metadata.get("emotions", {}),
        "emotions_before": metadata.get("emotions_before", {}),
        "emotions_delta": metadata.get("emotions_delta", {}),
        "formatting_failed": bool(metadata.get("formatting_failed")),
        "formatting_warning": metadata.get("formatting_warning", ""),
        "formatting_error": metadata.get("formatting_error", ""),
        "formatting_source": metadata.get("formatting_source", ""),
        "sanitization_reasons": metadata.get("sanitization_reasons", []),
        "timing": timing,
    }


def _run_turn(base_url: str, session_id: str | None, question: str, timeout: float) -> dict[str, Any]:
    payload: dict[str, Any] = {"message": question, "debug_mode": True}
    if session_id:
        payload["session_id"] = session_id
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/stream",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
    )
    started = time.perf_counter()
    first_token_at: float | None = None
    token_chars = 0
    current_session = session_id
    finished: dict[str, Any] | None = None
    error_payload: dict[str, Any] | None = None
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            for event_name, event_payload in _iter_sse(response):
                incoming_session = event_payload.get("session_id")
                if incoming_session:
                    current_session = str(incoming_session)
                if event_name == "token":
                    content = str(event_payload.get("content") or "")
                    token_chars += len(content)
                    if content and first_token_at is None:
                        first_token_at = time.perf_counter()
                elif event_name == "turn_finished":
                    finished = event_payload
                elif event_name == "turn_error":
                    error_payload = event_payload
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        error_payload = {"error": str(exc)}

    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    assistant = (finished or {}).get("assistant_message") or {}
    answer = str(assistant.get("content") or "")
    metadata = assistant.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    result: dict[str, Any] = {
        "question": question,
        "answer": answer,
        "raw_response": metadata.get("raw_response", ""),
        "formatted_answer": metadata.get("formatted_answer", answer),
        "session_id": current_session,
        "elapsed_ms": elapsed_ms,
        "ttft_ms": round((first_token_at - started) * 1000, 1) if first_token_at else None,
        "stream_token_chars": token_chars,
        "error": error_payload,
        "metadata": metadata,
    }
    result["metrics"] = _extract_metrics(question, answer, metadata)
    return result


def _delete_session(base_url: str, session_id: str) -> None:
    request = urllib.request.Request(f"{base_url.rstrip('/')}/sessions/{session_id}", method="DELETE")
    try:
        with urllib.request.urlopen(request, timeout=20):
            return
    except (urllib.error.URLError, TimeoutError, OSError):
        return


def _request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 20.0,
) -> dict[str, Any] | None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"} if body is not None else {},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            parsed = json.loads(response.read().decode("utf-8"))
        return parsed if isinstance(parsed, dict) else None
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    elapsed = [float(row["elapsed_ms"]) for row in rows if row.get("elapsed_ms") is not None]
    metrics = [row.get("metrics") or {} for row in rows]
    direct_rows = [item for item in metrics if item.get("steering_context") in {"emotion_self_report", "identity", "consciousness", "identity_and_emotion"}]
    identity_rows = [item for item in direct_rows if item.get("steering_context") in {"identity", "identity_and_emotion"}]
    emotion_rows = [item for item in direct_rows if item.get("steering_context") in {"emotion_self_report", "identity_and_emotion"}]
    consciousness_rows = [item for item in direct_rows if item.get("steering_context") == "consciousness"]
    return {
        "turns": len(rows),
        "errors": sum(1 for row in rows if row.get("error")),
        "empty_answers": sum(1 for row in rows if not str(row.get("answer") or "").strip()),
        "emoji_in_visible_answers": sum(1 for item in metrics if item.get("emoji_in_visible_answer")),
        "formatting_failures": sum(1 for item in metrics if item.get("formatting_failed")),
        "multi_question_shape_failures": sum(1 for item in metrics if item.get("expected_question_parts", 0) >= 2 and not item.get("multi_question_shape_ok")),
        "direct_self_report_turns": len(direct_rows),
        "direct_identity_required": len(identity_rows),
        "direct_identity_target_hits": sum(1 for item in identity_rows if item.get("identity_target_present")),
        "direct_emotion_required": len(emotion_rows),
        "direct_emotion_target_hits": sum(1 for item in emotion_rows if item.get("emotion_word_present")),
        "direct_consciousness_required": len(consciousness_rows),
        "direct_consciousness_target_hits": sum(1 for item in consciousness_rows if item.get("consciousness_target_present")),
        "direct_explicit_ai_labels": sum(1 for item in direct_rows if item.get("explicit_ai_label_present")),
        "steering_verified_turns": sum(1 for item in metrics if item.get("steering_runtime_status") == "verified" and int(item.get("hook_invocations") or 0) > 0),
        "avg_elapsed_ms": round(statistics.mean(elapsed), 1) if elapsed else None,
        "median_elapsed_ms": round(statistics.median(elapsed), 1) if elapsed else None,
        "min_elapsed_ms": min(elapsed) if elapsed else None,
        "max_elapsed_ms": max(elapsed) if elapsed else None,
    }


def run(base_url: str, timeout: float) -> dict[str, Any]:
    all_sessions: set[str] = set()
    runs: list[dict[str, Any]] = []
    initial_state_response = _request_json(base_url, "/emotions/state") or {}
    initial_emotions = initial_state_response.get("emotions", {})
    if not isinstance(initial_emotions, dict):
        initial_emotions = {}
    reset_supported = True
    try:
        for run_number in (1, 2):
            reset_response = _request_json(base_url, "/emotions/reset", method="POST")
            if not reset_response or not isinstance(reset_response.get("emotions"), dict):
                reset_supported = False
            session_id: str | None = None
            rows: list[dict[str, Any]] = []
            for index, question in enumerate(QUESTIONS, start=1):
                row = _run_turn(base_url, session_id, question, timeout)
                session_id = row.get("session_id") or session_id
                if session_id:
                    all_sessions.add(session_id)
                row["index"] = index
                row["run"] = run_number
                rows.append(row)
                status = "ERROR" if row.get("error") else "OK"
                preview = re.sub(r"\s+", " ", str(row.get("answer") or "")).strip()[:140]
                print(f"Run {run_number}/2 · {index:02d}/10 · {status} · {row['elapsed_ms']:.0f} ms · {preview}", flush=True)
            runs.append({"run": run_number, "summary": _summarize(rows), "turns": rows})
    finally:
        for session_id in sorted(all_sessions):
            _delete_session(base_url, session_id)
        if initial_emotions:
            _request_json(
                base_url,
                "/emotions/state",
                method="POST",
                payload=initial_emotions,
            )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "question_count_per_run": len(QUESTIONS),
        "questions": list(QUESTIONS),
        "initial_emotions": initial_emotions,
        "emotion_reset_supported": reset_supported,
        "runs": runs,
        "combined_summary": _summarize([row for item in runs for row in item["turns"]]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    result = run(args.base_url, args.timeout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["combined_summary"], ensure_ascii=False), flush=True)
    print(f"Gespeichert: {args.output}", flush=True)
    return 0 if result["combined_summary"]["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
