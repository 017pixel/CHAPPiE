"""Core Test-Loop: steuert CHAPPiE Backend, fuehrt Fragen aus, loggt Ergebnisse."""
from __future__ import annotations

import json
import os
import queue
import threading
import time
from uuid import uuid4
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from config.emotions import EMOTION_DEFAULTS
from forschung.session_logger import SessionLogger, evaluate_response_quality
from forschung.test_fragen_parser import Category, QuestionItem, parse_test_fragen

DEFAULT_BASE_EMOTIONS = dict(EMOTION_DEFAULTS)
DEFAULT_SEEDS = [11, 23, 37, 53, 71]
ABLATION_PROFILES = {
    "full": {"persona": True, "memory": True, "emotions": True, "life": True},
    "neutral": {"persona": False, "memory": False, "emotions": False, "life": False},
    "persona_only": {"persona": True, "memory": False, "emotions": False, "life": False},
    "memory_only": {"persona": False, "memory": True, "emotions": False, "life": False},
    "emotions_only": {"persona": False, "memory": False, "emotions": True, "life": False},
    "life_only": {"persona": False, "memory": False, "emotions": False, "life": True},
    "persona_memory": {"persona": True, "memory": True, "emotions": False, "life": False},
    "persona_emotions": {"persona": True, "memory": False, "emotions": True, "life": False},
    "persona_life": {"persona": True, "memory": False, "emotions": False, "life": True},
    "memory_emotions": {"persona": False, "memory": True, "emotions": True, "life": False},
    "memory_life": {"persona": False, "memory": True, "emotions": False, "life": True},
    "emotions_life": {"persona": False, "memory": False, "emotions": True, "life": True},
    "no_persona": {"persona": False, "memory": True, "emotions": True, "life": True},
    "no_memory": {"persona": True, "memory": False, "emotions": True, "life": True},
    "no_emotions": {"persona": True, "memory": True, "emotions": False, "life": True},
    "no_life": {"persona": True, "memory": True, "emotions": True, "life": False},
}


def resolve_ablation_profile(value: Any) -> tuple[str, Dict[str, bool]]:
    name = str(value or "full").strip().lower()
    if name not in ABLATION_PROFILES:
        raise ValueError(f"Unbekanntes ablation_profile '{name}'. Erlaubt: {', '.join(sorted(ABLATION_PROFILES))}")
    return name, dict(ABLATION_PROFILES[name])


def selected_questions(category: Category, selection: Any = None) -> List[QuestionItem]:
    """Return a reproducible category-local question subset.

    A missing selection preserves the historical full-suite behavior. When a
    mapping is provided, omitted categories intentionally contribute no turns.
    """
    if selection is None:
        return list(category.questions)
    if not isinstance(selection, dict):
        raise ValueError("question_selection muss ein Mapping Kategorie -> Fragenliste sein")
    raw_numbers = selection.get(str(category.id), selection.get(category.id, []))
    if not isinstance(raw_numbers, list):
        raise ValueError(f"question_selection[{category.id}] muss eine Liste sein")
    try:
        numbers = {int(number) for number in raw_numbers}
    except (TypeError, ValueError) as exc:
        raise ValueError(f"question_selection[{category.id}] enthaelt ungueltige Nummern") from exc
    available = {item.question_number for item in category.questions}
    unknown = numbers - available
    if unknown:
        raise ValueError(f"question_selection[{category.id}] unbekannte Fragen: {sorted(unknown)}")
    return [item for item in category.questions if item.question_number in numbers]


def selected_question_count(categories: List[Category], selection: Any = None) -> int:
    return sum(len(selected_questions(category, selection)) for category in categories)


def evaluate_provider_request_audit(
    *,
    expected_provider: str,
    expected_model: str,
    force_single_model: bool,
    requests: List[Dict[str, Any]],
    components: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Evaluate provider requests captured at the brain factory boundary."""
    expected_pair = (str(expected_provider), str(expected_model))
    unexpected_requests = [
        dict(entry)
        for entry in requests
        if (str(entry.get("provider")), str(entry.get("model"))) != expected_pair
    ]
    unexpected_components = {
        name: dict(value)
        for name, value in components.items()
        if value.get("uses_brain", True)
        and (str(value.get("provider")), str(value.get("model"))) != expected_pair
    }
    emotion_simple = components.get("emotions", {}).get("mode") == "simple_local_rules"
    passed = bool(
        not force_single_model
        or (
            requests
            and not unexpected_requests
            and not unexpected_components
            and emotion_simple
        )
    )
    return {
        "schema_version": 1,
        "force_single_model": bool(force_single_model),
        "expected_provider": expected_pair[0],
        "expected_model": expected_pair[1],
        "components": components,
        "requests": requests,
        "request_count": len(requests),
        "unexpected_requests": unexpected_requests,
        "unexpected_components": unexpected_components,
        "passed": passed,
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
        from brain import get_brain_request_audit, reset_brain_request_audit
        from config.config import apply_model_defaults_if_unset, is_gemma4_model, settings, PROJECT_ROOT, RESEARCH_DATA_DIR

        os.chdir(str(PROJECT_ROOT))

        enable_thinking = self.config.get("enable_thinking")
        if enable_thinking is not None:
            settings.update_from_ui(chain_of_thought=bool(enable_thinking))

        llm_provider = str(self.config.get("llm_provider") or self.config.get("provider") or "vllm").strip().lower()
        if llm_provider not in {"vllm", "ollama", "groq"}:
            llm_provider = "vllm"

        model_name = str(self.config.get("model") or "").strip()
        if model_name:
            is_gemma_26b = is_gemma4_model(model_name) and ("26b" in model_name.lower() or "a4b" in model_name.lower())
            quantize_local = bool(self.config.get("steering_quantize", is_gemma4_model(model_name)))
            context_length = 4096 if is_gemma_26b else 8192
            updates: Dict[str, Any] = {"llm_provider": llm_provider, "use_model_defaults": True}
            if llm_provider == "vllm":
                updates.update(
                    vllm_model=model_name,
                    steering_model=model_name,
                    steering_quantize=quantize_local,
                    steering_context_length=context_length,
                    vllm_force_single_model=True,
                    intent_provider="vllm",
                    query_extraction_provider="vllm",
                )
                apply_model_defaults_if_unset(model_name, settings)
            elif llm_provider == "ollama":
                updates["ollama_model"] = model_name
            elif llm_provider == "groq":
                updates.update(
                    groq_model=model_name,
                    # Do not inherit the currently configured local model's
                    # defaults when switching the research condition to Groq.
                    use_model_defaults=False,
                    temperature=float(self.config.get("temperature", 0.7)),
                    top_p=float(self.config.get("top_p", 0.9)),
                    top_k=int(self.config.get("top_k", 50)),
                )
                # Research comparisons may require a true single-model cloud
                # condition. Without this explicit opt-in, the process-level
                # defaults can leave Intent/Query on a local vLLM model and the
                # measured GPT-OSS condition becomes an undocumented hybrid.
                if bool(self.config.get("force_single_model", False)):
                    updates.update(
                        intent_provider="groq",
                        query_extraction_provider="groq",
                        intent_processor_model_groq=model_name,
                        query_extraction_groq_model=model_name,
                    )
            settings.update_from_ui(**updates)

        # The audit starts immediately before any benchmark backend is
        # constructed, at the common provider factory boundary.
        reset_brain_request_audit()

        if self.backend is None:
            try:
                ablation_name, feature_flags = resolve_ablation_profile(self.config.get("ablation_profile", "full"))
                self.config["ablation_profile"] = ablation_name
                self.config["feature_flags"] = feature_flags
                run_namespace = f"run-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{uuid4().hex[:10]}"
                runtime_data_dir = RESEARCH_DATA_DIR / run_namespace
                self.config["research_state"] = {
                    "isolated": True,
                    "namespace": run_namespace,
                    "runtime_data_dir": str(runtime_data_dir.relative_to(PROJECT_ROOT)),
                    "memory_collection": "benchmark_memory",
                    "historical_memory_reused": False,
                    "sleep_disabled": True,
                    "tool_mutations_disabled": True,
                    "intent_mode": "deterministic_local",
                }
                self.backend = create_chappie_backend(
                    runtime_data_dir=runtime_data_dir,
                    memory_collection_name="benchmark_memory",
                    research_mode=True,
                    feature_flags=feature_flags,
                )
                # Explicit invariant checks make accidental carry-over a hard
                # setup failure rather than a hidden benchmark confounder.
                if self.backend.memory.get_memory_count() != 0:
                    self.backend.memory.clear_memory()
                self.backend.short_term_memory.clear_all()
                if self.backend.memory.get_memory_count() != 0 or self.backend.short_term_memory.get_count() != 0:
                    raise RuntimeError("Isolierter Research-Memory ist beim Start nicht leer")
            except Exception as exc:
                raise RuntimeError(f"Backend-Initialisierung fehlgeschlagen: {exc}") from exc

        if self.config.get("formatting_mode", "local" if llm_provider == "vllm" else "cloud") == "local":
            setattr(self.backend, "force_local_formatting", True)
        if model_name:
            self.backend.apply_runtime_settings(force=True)

        provider_audit_components = {
            "main": {
                "uses_brain": True,
                "provider": settings.llm_provider.value,
                "model": model_name,
            },
            "intent": {
                "uses_brain": True,
                "provider": settings.get_effective_provider(settings.intent_provider).value,
                "model": settings.get_intent_model(settings.intent_provider),
                "runtime_mode": "deterministic_local" if getattr(self.backend, "research_mode", False) else "model",
            },
            "query_extraction": {
                "uses_brain": True,
                "provider": settings.get_effective_provider(settings.query_extraction_provider).value,
                "model": settings.get_query_extraction_model(settings.query_extraction_provider),
            },
            "emotions": {
                "uses_brain": False,
                "mode": "simple_local_rules" if getattr(self.backend.emotions, "force_simple", False) else "model",
            },
        }
        self.config["provider_contract"] = {
            "force_single_model": bool(self.config.get("force_single_model", False)),
            "expected_provider": llm_provider,
            "expected_model": model_name,
            "components": provider_audit_components,
        }

        self.logger = SessionLogger(self.config)
        history: List[Dict[str, str]] = []

        categories: List[Category] = self.config.get("_categories", [])
        raw_seeds = self.config.get("seeds")
        if raw_seeds is None:
            iterations = max(1, int(self.config.get("iterations", 1)))
            seeds = [DEFAULT_SEEDS[index] if index < len(DEFAULT_SEEDS) else DEFAULT_SEEDS[-1] + index for index in range(iterations)]
        else:
            if not isinstance(raw_seeds, list) or not raw_seeds:
                raise ValueError("seeds muss eine nicht-leere Liste sein")
            seeds = [int(seed) for seed in raw_seeds]
            iterations = len(seeds)
        self.config["seeds"] = seeds
        self.config["iterations"] = iterations
        delay: float = self.config.get("delay", 2.0)
        reset_per_category: bool = self.config.get("reset_per_category", True)
        question_selection = self.config.get("question_selection")

        question_index = 0
        self._pending_clear = False

        for iteration in range(1, iterations + 1):
            generation_seed = seeds[iteration - 1]
            self.backend.generation_seed = generation_seed
            self._reset_research_state()
            history = []

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

                for item in selected_questions(cat, question_selection):
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
                    result_quality = None
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
                        seed=generation_seed,
                    )

                    self._emit_progress("done_question", {
                        "iteration": iteration, "iterations": iterations,
                        "category": cat.name, "category_id": cat.id,
                        "question": item.text, "question_number": item.question_number,
                        "question_index": question_index,
                        "status": "error" if error or setup_failed else "ok",
                        "duration_ms": round(duration_ms),
                    })

                    # A rejected turn must not silently affect later samples.
                    # The response/history filter alone is insufficient because
                    # processing may already have mutated Memory, Life and
                    # emotions before a setup/generation/quality failure became
                    # visible.
                    invalid_turn = self._is_invalid_turn(error, setup_failed, result_quality)
                    if invalid_turn:
                        self._reset_research_state()
                        history = []
                        self._pending_clear = False
                        self.backend.debug_logger.clear()

                    if delay > 0:
                        time.sleep(delay)

        provider_audit = evaluate_provider_request_audit(
            expected_provider=llm_provider,
            expected_model=model_name,
            force_single_model=bool(self.config.get("force_single_model", False)),
            requests=get_brain_request_audit(),
            components=provider_audit_components,
        )
        audit_path = self.logger.session_dir / "provider_audit.json"
        audit_path.write_text(json.dumps(provider_audit, indent=2, ensure_ascii=False), encoding="utf-8")
        session_dir = self.logger.finalize()
        if not provider_audit["passed"]:
            invalid = {
                "status": "invalid",
                "reason": "Single-Model-Provider-Audit fehlgeschlagen",
                "provider_audit": provider_audit,
            }
            (self.logger.session_dir / "INVALID.json").write_text(
                json.dumps(invalid, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            raise RuntimeError("Single-Model-Provider-Audit fehlgeschlagen")
        return session_dir

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
        timeout_seconds = int(self.config.get("question_timeout_seconds", 300))
        timeout_seconds = max(60, min(7500, timeout_seconds))
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

    def _reset_research_state(self) -> None:
        """Give every seed the same empty Memory/STM/Life/Emotion start."""
        if not self.backend or not getattr(self.backend, "research_mode", False):
            return
        self.backend.memory.clear_memory()
        self.backend.short_term_memory.clear_all()
        self.backend.life_simulation.reset_state()
        self._reset_emotions()
        if self.backend.memory.get_memory_count() or self.backend.short_term_memory.get_count():
            raise RuntimeError("Research-State konnte nicht vollstaendig geleert werden")

    @staticmethod
    def _is_invalid_turn(error: Any, setup_failed: bool, result_quality: Optional[Dict[str, Any]]) -> bool:
        """Central contamination guard for failed or rejected benchmark turns."""
        return bool(
            error
            or setup_failed
            or (result_quality and result_quality.get("quality_failed"))
        )

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
