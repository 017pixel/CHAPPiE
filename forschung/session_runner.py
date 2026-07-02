"""Core Test-Loop: steuert CHAPPiE Backend, fuehrt Fragen aus, loggt Ergebnisse."""
from __future__ import annotations

import json
import os
import queue
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from config.emotions import EMOTION_DEFAULTS
from forschung.session_logger import SessionLogger, evaluate_response_quality
from forschung.test_fragen_parser import Category, QuestionItem, parse_test_fragen

DEFAULT_BASE_EMOTIONS = dict(EMOTION_DEFAULTS)


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
        from config.config import apply_model_defaults_if_unset, is_gemma4_model, settings, PROJECT_ROOT

        os.chdir(str(PROJECT_ROOT))

        enable_thinking = self.config.get("enable_thinking")
        if enable_thinking is not None:
            settings.update_from_ui(chain_of_thought=bool(enable_thinking))

        model_name = str(self.config.get("model") or "").strip()
        if model_name:
            is_gemma_26b = is_gemma4_model(model_name) and ("26b" in model_name.lower() or "a4b" in model_name.lower())
            context_length = 4096 if is_gemma_26b else 8192
            settings.update_from_ui(
                llm_provider="vllm",
                vllm_model=model_name,
                steering_model=model_name,
                steering_quantize=is_gemma_26b,
                steering_context_length=context_length,
                use_model_defaults=True,
            )
            apply_model_defaults_if_unset(model_name, settings)

        if self.backend is None:
            try:
                self.backend = create_chappie_backend()
            except Exception as exc:
                raise RuntimeError(f"Backend-Initialisierung fehlgeschlagen: {exc}") from exc

        if self.config.get("formatting_mode", "local") == "local":
            setattr(self.backend, "force_local_formatting", True)
        if model_name:
            self.backend.apply_runtime_settings(force=True)

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
                    history = []
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

                    setup_results = []
                    setup_error = None
                    setup_failed = False
                    for setup_prompt in item.setup_prompts:
                        try:
                            self._emit_progress("status", {"text": "Setup-Kontext laeuft..."})
                            setup_result = self._ask_question(setup_prompt, history)
                            setup_answer = setup_result.get("formatted_answer") or setup_result.get("response_text", "")
                            setup_quality = evaluate_response_quality(
                                setup_result,
                                question_text=setup_prompt,
                                category_name=cat.name,
                                enable_thinking=self.config.get("enable_thinking"),
                            )
                            setup_results.append({
                                "prompt": setup_prompt,
                                "response_text": setup_result.get("response_text", ""),
                                "formatted_answer": setup_result.get("formatted_answer", ""),
                                "formatting_source": setup_result.get("formatting_source", "local_fallback"),
                                "formatting_failed": setup_result.get("formatting_failed", False),
                                "quality": setup_quality,
                            })
                            if setup_quality.get("quality_failed"):
                                setup_failed = True
                                setup_error = "Setup-Qualitaetscheck fehlgeschlagen"
                                break
                            history.append({"role": "user", "content": setup_prompt})
                            history.append({"role": "assistant", "content": setup_answer})
                        except Exception as exc:
                            setup_failed = True
                            setup_error = str(exc) if str(exc) else type(exc).__name__
                            setup_results.append({"prompt": setup_prompt, "_error": setup_error})
                            break

                    emotions_before = self._get_emotions()
                    result = None
                    error = None
                    t_start = time.time()

                    try:
                        if setup_error:
                            setup_failed = True
                        else:
                            self._emit_progress("question", {
                                "iteration": iteration, "iterations": iterations,
                                "category": cat.name, "category_id": cat.id,
                                "question": item.text, "question_number": item.question_number,
                                "question_index": question_index,
                                "status": "generating",
                            })

                            result = self._ask_question(item.text, history)
                            result_quality = evaluate_response_quality(
                                result,
                                question_text=item.text,
                                category_name=cat.name,
                                enable_thinking=self.config.get("enable_thinking"),
                            )
                            result["quality"] = result_quality
                            if not result_quality.get("quality_failed"):
                                history.append({"role": "user", "content": item.text})
                                display = result.get("formatted_answer") or result.get("response_text", "")
                                history.append({"role": "assistant", "content": display})

                        if result and result.get("auto_sleep_triggered"):
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
                        setup_prompts=list(item.setup_prompts),
                        setup_results=setup_results,
                        emotions_before=emotions_before,
                        emotions_after=emotions_after,
                        result=result,
                        duration_ms=duration_ms,
                        error=error,
                        setup_failed=setup_failed,
                    )

                    self._emit_progress("done_question", {
                        "iteration": iteration, "iterations": iterations,
                        "category": cat.name, "category_id": cat.id,
                        "question": item.text, "question_number": item.question_number,
                        "question_index": question_index,
                        "status": "error" if error or setup_failed else "ok",
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
        last_error = None
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
                    last_error = event.get("error") or "Backend-Fehler"
                    break
                elif ev == "finished":
                    result = event["result"]
                    break
        finally:
            abort.set()
            t.join(timeout=5)

        if result is None:
            raise RuntimeError(last_error or "Keine Antwort vom Backend erhalten (Timeout oder Fehler)")

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
