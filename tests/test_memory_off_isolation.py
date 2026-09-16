"""Real event persistence through sync, streaming, cancellation and failure."""
import json
import sys
import tempfile
import threading
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.session_settings import SessionRuntimeSettings
from memory.event_store import EventStore
from web_infrastructure.persistence import TurnPersistence
from web_infrastructure.turn_context import build_turn_context
from web_infrastructure.turn_pipeline import TurnPipeline

class Runtime:
    research_mode = False
    def __init__(self, root):
        self._turn_lock = threading.Lock()
        self._active_turn = None
        self.scheduled = 0
        self.mode = "normal"
        self.persistence = TurnPersistence(event_store=EventStore(root / "events.sqlite"),
            promotion=SimpleNamespace(schedule=self.schedule), timestamp_callback=lambda: None)
    def schedule(self):
        self.scheduled += 1
    def _chat_provider(self):
        return "vllm"
    def _chat_model(self):
        return "test/model"
    def _get_emotions_snapshot(self):
        return {"frustration": 20}
    def _begin_turn(self, turn, streaming):
        self._active_turn = turn
        self._turn_timings = {}
    def _process_two_step(self, user_input, history, **kwargs):
        assert not history, "Memory OFF leaked history"
        assert len(self.persistence.store.events(self._active_turn.session_id)) == 1
        if self.mode == "error":
            raise RuntimeError("provider unavailable")
        return {"response_text": "Ich habe gestern eine Reise gemacht.", "emotions": {"frustration": 40}, "emotions_delta": {"frustration": {"applied_delta": 20}}, "raw_response": "raw model output"}
    def _process_two_step_stream(self, user_input, history, *args, **kwargs):
        assert not history
        yield {"event": "status", "content": "running"}
        yield {"event": "token", "content": "Teilantwort"}
        yield {"event": "finished", "result": {"response_text": "Teilantwort fertig"}}

def turn(session, live=True):
    return build_turn_context("Ich heiße Ada.", [{"role": "user", "content": "secret history"}],
        session_id=session, runtime_settings=SessionRuntimeSettings.from_mapping({"memory_enabled": False, "live_enabled": live}))

def main():
    with tempfile.TemporaryDirectory() as directory:
        runtime = Runtime(Path(directory))
        pipeline = TurnPipeline(runtime)
        result = pipeline.process(turn("sync"))
        assert result["timing"]["persistence_ms"] >= 0
        rows = runtime.persistence.store.events("sync")
        assert len(rows) == 2 and all(row["memory_enabled"] == 0 for row in rows)
        assert rows[1]["retrieval_eligible"] == 0
        assert rows[1]["raw_content"] == "raw model output"
        assert json.loads(rows[1]["emotion_delta_json"])["frustration"]["applied_delta"] == 20
        assert json.loads(rows[1]["emotion_after_json"])["frustration"] == 40
        events = list(pipeline.process_stream(turn("stream", live=False)))
        assert [event["event"] for event in events] == ["finished"]
        assert len(runtime.persistence.store.events("stream")) == 2
        stream = pipeline.process_stream(turn("cancel"))
        next(stream)
        next(stream)
        stream.close()
        rows = runtime.persistence.store.events("cancel")
        assert rows[1]["content"] == "Teilantwort"
        assert "incomplete_stream" in json.loads(rows[1]["quality_flags_json"])
        runtime.mode = "error"
        try:
            pipeline.process(turn("error"))
        except RuntimeError:
            pass
        else:
            raise AssertionError("Provider failure disappeared")
        assert len(runtime.persistence.store.events("error")) == 2
        assert runtime._active_turn is None and runtime._turn_timings is None
        assert runtime.scheduled == 4
    print("Memory OFF: durable sync/stream/error/cancellation and hidden live output passed")
if __name__ == "__main__":
    main()
