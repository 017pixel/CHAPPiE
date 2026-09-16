"""Offline regression tests for the modular runtime architecture."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_compatibility_module_keeps_pure_imports_lightweight() -> None:
    sys.modules.pop("web_infrastructure.backend_wrapper", None)
    sys.modules.pop("web_infrastructure.chappie_runtime", None)

    from web_infrastructure import backend_wrapper

    assert backend_wrapper.is_self_contained_math_query("Was ist 4 plus 5?")
    assert "web_infrastructure.chappie_runtime" not in sys.modules


def _install_optional_dependency_doubles() -> None:
    for name in (
        "chromadb",
        "chromadb.config",
        "ollama",
        "openai",
        "sentence_transformers",
    ):
        sys.modules.setdefault(name, MagicMock())


def test_old_and_new_runtime_imports_resolve_to_the_same_class() -> None:
    _install_optional_dependency_doubles()
    from web_infrastructure.backend_wrapper import CHAPPiEBackend as LegacyClass
    from web_infrastructure.backend_wrapper import CHAPPiERuntime as CompatibilityClass
    from web_infrastructure.chappie_runtime import CHAPPiEBackend, CHAPPiERuntime

    assert CHAPPiERuntime is CHAPPiEBackend
    assert CompatibilityClass is CHAPPiERuntime
    assert LegacyClass is CHAPPiERuntime


def test_factory_forwards_legacy_options_to_module_level_runtime() -> None:
    _install_optional_dependency_doubles()
    import web_infrastructure.chappie_runtime as runtime_module
    from web_infrastructure import backend_wrapper

    captured = {}
    original_runtime = runtime_module.CHAPPiERuntime

    class FakeRuntime:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    runtime_module.CHAPPiERuntime = FakeRuntime
    try:
        instance = backend_wrapper.create_chappie_backend(
            runtime_data_dir=Path("runtime-data"),
            memory_collection_name="contract",
            research_mode=True,
            feature_flags={"life": False},
        )
    finally:
        runtime_module.CHAPPiERuntime = original_runtime

    assert isinstance(instance, FakeRuntime)
    assert captured == {
        "runtime_data_dir": Path("runtime-data"),
        "memory_collection_name": "contract",
        "research_mode": True,
        "feature_flags": {"life": False},
    }


class _PipelineRuntime:
    def __init__(self) -> None:
        self.calls = []

    def _begin_turn(self, turn, *, streaming):
        self.calls.append(("begin", streaming, turn))

    def _process_two_step(self, user_input, history, status_callback=None, temporal_context=None):
        self.calls.append(("sync", user_input, history, status_callback, temporal_context))
        return {"response_text": "sync"}

    def _process_two_step_stream(self, user_input, history, status_callback=None, temporal_context=None):
        self.calls.append(("stream", user_input, history, status_callback, temporal_context))
        yield {"event": "token", "content": "stream"}
        yield {"event": "finished", "result": {"response_text": "stream"}}


def test_sync_and_stream_share_the_same_turn_context_entry() -> None:
    from web_infrastructure.turn_context import build_turn_context
    from web_infrastructure.turn_pipeline import TurnPipeline

    history = [{"role": "user", "content": "vorher"}]
    temporal = {"user_message_created_at": "2026-09-02T00:00:00+00:00"}
    def callback(event):
        del event

    sync_runtime = _PipelineRuntime()
    sync_turn = build_turn_context(
        "Hallo",
        history,
        debug_mode=True,
        status_callback=callback,
        temporal_context=temporal,
    )
    result = TurnPipeline(sync_runtime).process(sync_turn)

    stream_runtime = _PipelineRuntime()
    stream_turn = build_turn_context(
        "Hallo",
        history,
        debug_mode=True,
        status_callback=callback,
        temporal_context=temporal,
    )
    events = list(TurnPipeline(stream_runtime).process_stream(stream_turn))

    assert result["response_text"] == "sync"
    assert events[-1]["event"] == "finished"
    assert sync_runtime.calls[0][0:2] == ("begin", False)
    assert stream_runtime.calls[0][0:2] == ("begin", True)
    from dataclasses import replace
    assert sync_turn.turn_id != stream_turn.turn_id
    assert replace(sync_runtime.calls[0][2], turn_id="same") == replace(stream_runtime.calls[0][2], turn_id="same")
    assert history is not sync_turn.history
    assert temporal is not sync_turn.temporal_context


def test_generation_gateway_uses_the_current_brain() -> None:
    from web_infrastructure.generation import GenerationGateway

    first = MagicMock()
    second = MagicMock()
    current = {"brain": first}
    gateway = GenerationGateway(lambda: current["brain"])

    gateway.generate([], config={"stream": False})
    current["brain"] = second
    gateway.generate([], config={"stream": True})

    first.generate.assert_called_once()
    second.generate.assert_called_once()


def test_optional_prompt_metrics_do_not_abort_without_tokenizer() -> None:
    from brain.token_counter import TokenizerUnavailableError
    from web_infrastructure.generation import RuntimeGenerationMixin

    class Runtime(RuntimeGenerationMixin):
        brain = type("Brain", (), {"model": "missing/local-model"})()

        def _active_token_counter(self):
            raise TokenizerUnavailableError("nicht im Cache")

        def _chat_model(self):
            return self.brain.model

    metrics = Runtime()._measure_prompt_components(
        {"system": "System", "user": "Hallo"},
        [{"role": "user", "content": "Vorher"}],
        [],
        [],
    )

    assert metrics["token_count_source"] == "unavailable"
    assert metrics["tokenizer_model"] == "missing/local-model"
    assert metrics["history_messages"] == 1


def test_active_steering_import_does_not_load_historical_agents() -> None:
    historical_modules = {
        "brain.agents.amygdala",
        "brain.agents.hippocampus",
        "brain.agents.orchestrator",
        "brain.agents.prefrontal_cortex",
        "brain.agents.sensory_cortex",
    }
    for name in historical_modules:
        sys.modules.pop(name, None)

    import brain.steering_manager  # noqa: F401

    assert historical_modules.isdisjoint(sys.modules)


def test_brain_pipeline_compatibility_is_lazy() -> None:
    import brain.brain_pipeline as compatibility

    assert compatibility._legacy_module is None
    assert "brain.agents.sensory_cortex" not in sys.modules


def test_legacy_methods_are_absent_from_active_runtime_source() -> None:
    source = (ROOT / "web_infrastructure" / "chappie_runtime.py").read_text(encoding="utf-8")
    wrapper = (ROOT / "web_infrastructure" / "backend_wrapper.py").read_text(encoding="utf-8")

    for symbol in (
        "def _process_legacy(",
        "def _process_legacy_stream(",
        "def _extract_legacy_generation(",
        "def start_async_chat(",
        "def _run_chat_job(",
    ):
        assert symbol not in source
    assert "class CHAPPiEBackend" not in wrapper
    assert "def create_chappie_backend" in wrapper


if __name__ == "__main__":
    tests = [value for name, value in globals().copy().items() if name.startswith("test_") and callable(value)]
    for test in tests:
        test()
    print(f"OK: {len(tests)} modular runtime architecture tests")
