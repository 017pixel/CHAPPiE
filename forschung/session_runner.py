"""Core Test-Loop: steuert CHAPPiE Backend, fuehrt Fragen aus, loggt Ergebnisse."""
from __future__ import annotations

import json
import os
import queue
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from forschung.session_logger import SessionLogger
from forschung.test_fragen_parser import Category, QuestionItem, parse_test_fragen

DEFAULT_BASE_EMOTIONS = {
    "happiness": 50, "trust": 60, "energy": 70,
    "curiosity": 50, "motivation": 60, "frustration": 5, "sadness": 5,
}


class SessionRunner:
    def __init__(
        self,
        config: Dict[str, Any],
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.config = config
        self.progress_callback = progress_callback
        self.backend = None
        self.logger: Optional[SessionLogger] = None
        self.abort = threading.Event()
        self._pending_clear = False

    def run(self) -> str:
        from web_infrastructure.backend_wrapper import create_chappie_backend
        from config.config import settings, PROJECT_ROOT

        os.chdir(str(PROJECT_ROOT))

        if self.backend is None:
            try:
                self.backend = create_chappie_backend()
            except Exception as exc:
                raise RuntimeError(f"Backend-Initialisierung fehlgeschlagen: {exc}") from exc

        self.logger = SessionLogger(self.config)
        history: List[Dict[str, str]] = []

        categories: List[Category] = self.config.get("_categories", [])
        iterations: int = self.config.get("iterations", 1)
        delay: float = self.config.get("delay", 2.0)
        reset_per_category: bool = self.config.get("reset_per_category", True)

        question_index = 0
        self._pending_clear = False

        for iteration in range(1, iterations + 1):

            for cat in categories:
                if self.abort.is_set():
                    break

                if reset_per_category:
                    self._reset_emotions()
                    history = history[-6:] if history else []
                    self._pending_clear = False
                    self.backend.debug_logger.clear()

                self._emit_progress("category", {
                    "iteration": iteration, "iterations": iterations,
                    "category": cat.name, "category_id": cat.id,
                    "question_index": question_index,
                })

                for item in cat.questions:
                    if self.abort.is_set():
                        break

                    question_index += 1

                    for cmd in item.pre_commands:
                        self._exec_command(cmd)

                    emotions_before = self._get_emotions()
                    result = None
                    error = None
                    t_start = time.time()

                    try:
                        self._emit_progress("question", {
                            "iteration": iteration, "iterations": iterations,
                            "category": cat.name, "category_id": cat.id,
                            "question": item.text, "question_number": item.question_number,
                            "question_index": question_index,
                            "status": "generating",
                        })

                        result = self._ask_question(item.text, history)
                        history.append({"role": "user", "content": item.text})
                        display = result.get("formatted_answer") or result.get("response_text", "")
                        history.append({"role": "assistant", "content": display})

                        if result.get("auto_sleep_triggered"):
                            self._emit_progress("status", {"text": "Schlafphase laeuft..."})
                            time.sleep(3)

                    except Exception as exc:
                        error = str(exc) if str(exc) else type(exc).__name__

                    t_end = time.time()
                    duration_ms = (t_end - t_start) * 1000
                    emotions_after = self._get_emotions()

                    for cmd in item.post_commands:
                        self._exec_command(cmd)

                    if self._pending_clear:
                        history = []
                        self._pending_clear = False

                    self.logger.log_question(
                        iteration=iteration,
                        category_name=cat.name,
                        category_id=cat.id,
                        question_number=item.question_number,
                        question_text=item.text,
                        commands_before=list(item.pre_commands),
                        commands_after=list(item.post_commands),
                        emotions_before=emotions_before,
                        emotions_after=emotions_after,
                        result=result,
                        duration_ms=duration_ms,
                        error=error,
                    )

                    self._emit_progress("done_question", {
                        "iteration": iteration, "iterations": iterations,
                        "category": cat.name, "category_id": cat.id,
                        "question": item.text, "question_number": item.question_number,
                        "question_index": question_index,
                        "status": "error" if error else "ok",
                        "duration_ms": round(duration_ms),
                    })

                    if delay > 0:
                        time.sleep(delay)

        return self.logger.finalize()

    def _ask_question(self, text: str, history: List[Dict[str, str]]) -> Dict[str, Any]:
        eq: queue.Queue = queue.Queue()
        abort = threading.Event()

        def worker():
            try:
                gen = self.backend.process_stream(text, history, debug_mode=True)
                for event in gen:
                    if abort.is_set():
                        try:
                            gen.close()
                        except Exception:
                            pass
                        break
                    eq.put(event)
                eq.put(None)
            except Exception as exc:
                eq.put({"event": "error", "error": str(exc)})
                eq.put(None)

        t = threading.Thread(target=worker, daemon=True)
        t.start()

        result = None
        timeout_seconds = 300
        deadline = time.time() + timeout_seconds

        try:
            while True:
                remaining = deadline - time.time()
                if remaining <= 0:
                    abort.set()
                    break

                try:
                    event = eq.get(timeout=min(remaining, 0.5))
                except queue.Empty:
                    if self.abort.is_set():
                        abort.set()
                        break
                    continue

                if event is None:
                    break

                ev = event.get("event", "")
                if ev == "error":
                    break
                elif ev == "finished":
                    result = event["result"]
                    break
        finally:
            abort.set()
            t.join(timeout=5)

        if result is None:
            raise RuntimeError("Keine Antwort vom Backend erhalten (Timeout oder Fehler)")

        return result

    def _exec_command(self, cmd: str) -> None:
        if not self.backend:
            return
        try:
            stripped = cmd.strip()
            if stripped.startswith("/emotion "):
                parts = stripped.split()
                if len(parts) >= 3:
                    emotion = parts[1].lower()
                    val = parts[2]
                    if val.startswith("+") or val.startswith("-"):
                        delta = int(val)
                        current = self.backend.emotions.get_state().to_dict().get(emotion, 0)
                        new_val = max(0, min(100, current + delta))
                        self.backend.emotions.set_emotion(emotion, new_val)
                    else:
                        self.backend.emotions.set_emotion(emotion, int(val))
            elif stripped == "/clear":
                self._pending_clear = True
            elif stripped == "/resetemotions":
                self._reset_emotions()
            else:
                self.backend.handle_command(stripped)
        except Exception as exc:
            print(f"[harness] Command '{cmd}' fehlgeschlagen: {exc}", flush=True)

    def _reset_emotions(self) -> None:
        if not self.backend:
            return
        try:
            self.backend.emotions.reset()
        except Exception:
            pass
        for emo, val in DEFAULT_BASE_EMOTIONS.items():
            try:
                self.backend.emotions.set_emotion(emo, val)
            except Exception:
                pass

    def _get_emotions(self) -> Dict[str, int]:
        if not self.backend:
            return {}
        try:
            state = self.backend.emotions.get_state()
            return state.to_dict()
        except Exception:
            return {}

    def _emit_progress(self, event_type: str, data: Dict[str, Any]) -> None:
        if self.progress_callback:
            try:
                self.progress_callback({"event": event_type, **data})
            except Exception:
                pass

    def abort_session(self) -> None:
        self.abort.set()


def load_categories(filepath: str = None) -> List[Category]:
    if filepath is None:
        from pathlib import Path
        filepath = str(Path(__file__).resolve().parent / "test_fragen.md")
    return parse_test_fragen(filepath)


def load_config(filepath: str) -> Dict[str, Any]:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config: Dict[str, Any], filepath: str) -> None:
    clean = {k: v for k, v in config.items() if not k.startswith("_")}
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(clean, f, indent=2, ensure_ascii=False, default=str)
