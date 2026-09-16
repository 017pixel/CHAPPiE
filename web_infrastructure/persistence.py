"""Persistence boundary shared by synchronous and streamed turn finalization."""

from __future__ import annotations

import threading
from web_infrastructure.timing import measured
from datetime import datetime, timezone
from typing import Any, Dict, List

from config.emotions import EMOTION_DEFAULTS, EMOTION_ORDER
from brain.response_parser import (
    is_safe_retrieval_text,
)





class TurnPersistence:
    """Archive first; embedding and migration run in the durable worker."""

    def __init__(self, *, event_store, promotion, timestamp_callback):
        self.store = event_store
        self.promotion = promotion
        self._timestamp_callback = timestamp_callback

    def archive_input(self, turn, metadata):
        self.store.append(
            session_id=turn.session_id or "local", turn_id=turn.turn_id,
            role="user", content=turn.user_input, metadata=metadata,
        )

    def archive_result(self, turn, result, metadata):
        self.store.append(
            session_id=turn.session_id or "local", turn_id=turn.turn_id,
            role="assistant", content=result.get("response_text", ""),
            raw_content=result.get("raw_response"), metadata=metadata,
        )
        self._timestamp_callback()


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

    @measured("memory_retrieval_ms")
    def _search_memory(self, *args, **kwargs) -> List[Any]:
        if not self._feature_enabled("memory"):
            return []
        memories = self.memory.search_memory(*args, **kwargs)
        return [memory for memory in memories if is_safe_retrieval_text(getattr(memory, "content", ""))]

    @measured("memory_retrieval_ms")
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

