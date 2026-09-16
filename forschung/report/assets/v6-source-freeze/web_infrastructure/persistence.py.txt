"""Persistence boundary shared by synchronous and streamed turn finalization."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List

from config.emotions import EMOTION_DEFAULTS, EMOTION_ORDER
from brain.response_parser import (
    is_safe_retrieval_text,
    looks_like_model_error,
)





class TurnPersistence:
    def __init__(
        self,
        *,
        memory_getter: Callable[[], Any],
        short_term_memory_getter: Callable[[], Any],
        timestamp_callback: Callable[[], None],
    ) -> None:
        self._memory_getter = memory_getter
        self._short_term_memory_getter = short_term_memory_getter
        self._timestamp_callback = timestamp_callback

    def persist_exchange(
        self,
        user_input: str,
        response_text: str,
        *,
        background_short_term: bool = False,
        deterministic: bool = False,
        suppress_short_term_errors: bool = False,
    ) -> None:
        memory = self._memory_getter()
        memory.add_memory(user_input, role="user")
        if response_text.strip() and not looks_like_model_error(response_text):
            memory.add_memory(response_text, role="assistant")
        self._timestamp_callback()

        def persist_short_term() -> None:
            short_term_memory = self._short_term_memory_getter()
            short_term_memory.add_entry(
                content=f"User: {user_input}",
                category="chat",
                importance="normal",
            )
            short_term_memory.add_entry(
                content=f"CHAPPiE: {response_text[:200]}",
                category="chat",
                importance="normal",
            )

        def run_short_term() -> None:
            if not suppress_short_term_errors:
                persist_short_term()
                return
            try:
                persist_short_term()
            except Exception:
                pass

        if background_short_term and not deterministic:
            threading.Thread(target=run_short_term, daemon=True).start()
        else:
            run_short_term()


class RuntimePersistenceMixin:
    """Internal mixin extracted from the former backend wrapper."""

    def _turn_checkpoint(self) -> Any:
        if not self._feature_enabled("life"):
            return None
        return self.life_simulation.create_checkpoint()

    def _rollback_failed_turn(self, emotions_before: Dict[str, int], life_checkpoint: Any) -> None:
        for emotion in EMOTION_ORDER:
            try:
                self.emotions.set_emotion(emotion, emotions_before.get(emotion, EMOTION_DEFAULTS[emotion]))
            except Exception:
                pass
        if life_checkpoint is not None:
            try:
                self.life_simulation.restore_checkpoint(life_checkpoint)
            except Exception:
                pass

    def _search_memory(self, *args, **kwargs) -> List[Any]:
        if not self._feature_enabled("memory"):
            return []
        memories = self.memory.search_memory(*args, **kwargs)
        return [memory for memory in memories if is_safe_retrieval_text(getattr(memory, "content", ""))]

    def _search_memory_keywords(self, *args, **kwargs) -> List[Any]:
        if not self._feature_enabled("memory"):
            return []
        memories = self.memory.search_memory_keywords(*args, **kwargs)
        return [memory for memory in memories if is_safe_retrieval_text(getattr(memory, "content", ""))]

    def _collect_repetition_events(self) -> Dict[str, Any]:
        events: Dict[str, Any] = {}
        brain = getattr(self, "brain", None)
        if brain and hasattr(brain, "_repetition_events"):
            events.update(dict(brain._repetition_events))
        if getattr(self, "_post_repetition_cut", False):
            events["post_detect_cut"] = True
        self._post_repetition_cut = False
        if events:
            self.debug_logger.log_warning("REPETITION", "Wiederholungsschleifen erkannt", events)
        return events

    def _set_last_memory_timestamp(self):
        self.last_memory_timestamp = datetime.now(timezone.utc).isoformat()

    def _run_sleep_phase_job(self):
        print(f"\n{'=' * 50}")
        print("  SCHLAFPHASE GESTARTET - Energie & Emotionen regenerieren...")
        print(f"{'=' * 50}")
        try:
            result = self.sleep_handler.execute_sleep_phase(
                memory_engine=self.memory,
                context_files=self.context_files,
                short_term_memory=self.short_term_memory,
                emotions_engine=self.emotions,
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
            print("  SCHLAFPHASE ABGESCHLOSSEN")
            print(f"{'=' * 50}\n")

    def _schedule_sleep_phase_if_due(self) -> Dict[str, Any]:
        if self.research_mode:
            return {"triggered": False, "status": {"disabled": True, "reason": "isolated_research_run"}}
        self.sleep_handler.increment_interaction()
        status = self.sleep_handler.get_status()
        if not self.sleep_handler.should_run_sleep():
            return {"triggered": False, "status": status}

        if not self._sleep_job_lock.acquire(blocking=False):
            return {"triggered": False, "status": status, "already_running": True}

        worker = threading.Thread(target=self._run_sleep_phase_job, daemon=True, name="chappie-sleep-phase")
        worker.start()
        return {"triggered": True, "status": self.sleep_handler.get_status()}

