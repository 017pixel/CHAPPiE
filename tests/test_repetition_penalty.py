"""
Tests dass repetition_penalty korrekt via extra_body an vLLM uebergeben wird.
Keine externen Abhaengigkeiten noetig – alle Module werden gepatched.
"""
import os
import sys
from unittest.mock import MagicMock, patch

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

for mod in (
    "ollama", "chromadb", "chromadb.config", "requests", "openai",
    "brain.groq_brain",
    "brain.ollama_brain", "brain.brain_pipeline", "brain.steering_api_server",
    "brain.steering_backend", "brain.deep_think", "brain.global_workspace",
    "brain.action_response", "brain.response_parser", "brain.agents",
    "brain.groq_limits", "life", "memory", "memory.memory_engine",
    "memory.emotions_engine", "memory.sleep_phase", "memory.forgetting_curve",
    "memory.context_files", "memory.chat_manager", "memory.short_term_memory",
    "memory.short_term_memory_v2", "memory.personality_manager",
    "memory.function_registry", "memory.intent_processor", "memory.debug_logger",
):
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

from brain.base_brain import GenerationConfig  # noqa: E402
from brain.vllm_brain import VLLMBrain     # noqa: E402


class _FakeMessage:
    def __init__(self, content=None, reasoning_content=None):
        self.content = content
        self.reasoning_content = reasoning_content


class _FakeChoice:
    def __init__(self, message, finish_reason="stop"):
        self.message = message
        self.finish_reason = finish_reason


class _FakeResponse:
    def __init__(self, choices):
        self.choices = choices


class _CapturedCompletions:
    def __init__(self, response):
        self._response = response

    def create(self, **kwargs):
        self._last_kwargs = kwargs
        return self._response


class _FakeChat:
    def __init__(self, response):
        self.completions = _CapturedCompletions(response)


class _FakeOpenAIClient:
    def __init__(self, response):
        self.chat = _FakeChat(response)


class _FakeStreamGenerator:
    def __init__(self, response):
        self._response = response

    def __iter__(self):
        choices = getattr(self._response, "choices", None) or []
        if not choices:
            return iter([])
        msg = choices[0].message
        chunks = []
        content = getattr(msg, "content", None)
        if content:
            chunks.append(_FakeStreamChunk(content))
        reasoning = getattr(msg, "reasoning_content", None)
        if reasoning:
            chunks.append(_FakeStreamReasoningChunk(reasoning))
        return iter(chunks)


class _FakeStreamChunk:
    def __init__(self, content):
        self.choices = [_FakeStreamDelta(content=content)]


class _FakeStreamReasoningChunk:
    def __init__(self, reasoning):
        self.choices = [_FakeStreamDelta(reasoning_content=reasoning)]


class _FakeStreamDelta:
    def __init__(self, content=None, reasoning_content=None):
        self.delta = _FakeMessage(content=content, reasoning_content=reasoning_content)


class _FakeStreamCompletions:
    def __init__(self, response):
        self._response = response

    def create(self, **kwargs):
        self._last_kwargs = kwargs
        return _FakeStreamGenerator(self._response)


class _FakeStreamChat:
    def __init__(self, response):
        self.completions = _FakeStreamCompletions(response)


class _FakeStreamOpenAIClient:
    def __init__(self, response):
        self.chat = _FakeStreamChat(response)


def test_sync_generate_passes_repetition_penalty_in_extra_body():
    """Sync-Generierung: repetition_penalty muss via extra_body kommen."""
    config = GenerationConfig(stream=False, repetition_penalty=1.15)
    response = _FakeResponse([_FakeChoice(_FakeMessage(content="Test"), "stop")])
    with patch("brain.vllm_brain.OpenAI", return_value=_FakeOpenAIClient(response)):
        brain = VLLMBrain(model="Qwen/Qwen3.5-4B", url="http://localhost:8000/v1")
        capturer = brain.client.chat.completions

    brain._sync_generate([], config, {})
    extra = capturer._last_kwargs.get("extra_body", {})
    assert extra.get("repetition_penalty") == 1.15, (
        f"repetition_penalty=1.15 in extra_body erwartet, war {extra.get('repetition_penalty')}"
    )
    assert "repetition_penalty" not in capturer._last_kwargs, (
        "repetition_penalty darf NICHT als direktes Keyword in create() stehen"
    )
    print("  [OK] sync: repetition_penalty=1.15 korrekt in extra_body")


def test_stream_generate_passes_repetition_penalty_in_extra_body():
    """Stream-Generierung: repetition_penalty muss via extra_body kommen."""
    config = GenerationConfig(stream=True, repetition_penalty=1.2)
    response = _FakeResponse([_FakeChoice(_FakeMessage(content="Hallo"), "stop")])
    with patch("brain.vllm_brain.OpenAI", return_value=_FakeStreamOpenAIClient(response)):
        brain = VLLMBrain(model="Qwen/Qwen3.5-4B", url="http://localhost:8000/v1")
        capturer = brain.client.chat.completions

    list(brain._stream_generate([], config, {}))
    extra = capturer._last_kwargs.get("extra_body", {})
    assert extra.get("repetition_penalty") == 1.2, (
        f"repetition_penalty=1.2 in extra_body erwartet, war {extra.get('repetition_penalty')}"
    )
    assert "repetition_penalty" not in capturer._last_kwargs, (
        "repetition_penalty darf NICHT als direktes Keyword in create() stehen"
    )
    print("  [OK] stream: repetition_penalty=1.2 korrekt in extra_body")


def test_default_repetition_penalty_in_generation_config():
    """GenerationConfig default = 1.1."""
    config = GenerationConfig()
    assert config.repetition_penalty == 1.1, (
        f"Standard repetition_penalty=1.1 erwartet, war {config.repetition_penalty}"
    )
    print("  [OK] GenerationConfig default repetition_penalty=1.1")


def test_enable_thinking_is_true_for_qwen35():
    """Qwen3.5 Modelle bekommen enable_thinking=True."""
    response = _FakeResponse([_FakeChoice(_FakeMessage(content="ok"))])
    with patch("brain.vllm_brain.OpenAI", return_value=_FakeOpenAIClient(response)):
        brain = VLLMBrain(model="Qwen/Qwen3.5-4B", url="http://localhost:8000/v1")
    body = brain._prepare_extra_body({})
    ctk = body.get("chat_template_kwargs", {})
    assert ctk.get("enable_thinking") is True, (
        f"enable_thinking=True erwartet fuer Qwen3.5, war {ctk.get('enable_thinking')}"
    )
    print("  [OK] enable_thinking=True fuer Qwen/Qwen3.5-4B")


def test_extra_body_preserves_steering_when_adding_penalty():
    """Steering-Payload bleibt erhalten, wenn repetition_penalty dazu kommt."""
    config = GenerationConfig(stream=False, repetition_penalty=1.05)
    response = _FakeResponse([_FakeChoice(_FakeMessage(content="ok"))])
    with patch("brain.vllm_brain.OpenAI", return_value=_FakeOpenAIClient(response)):
        brain = VLLMBrain(model="Qwen/Qwen3.5-4B", url="http://localhost:8000/v1")
        capturer = brain.client.chat.completions

    steering = {"steering": {"enabled": True, "vectors": []}}
    brain._sync_generate([], config, steering)
    extra = capturer._last_kwargs.get("extra_body", {})
    assert extra.get("steering", {}).get("enabled") is True, "Steering payload muss erhalten bleiben"
    assert extra.get("repetition_penalty") == 1.05, "repetition_penalty muss hinzugefuegt worden sein"
    print("  [OK] extra_body merged: steering + repetition_penalty korrekt")


def test_loop_detector_catches_repeated_segment():
    """Ein 3x wiederholter Satz wird als Loop erkannt."""
    repeat = "DerUserwilldassCHAPiEetwasanderesmacht." * 3  # ~150 chars * 3
    text = "Start." + repeat + "Nochmehr." + repeat[0]  # letztes Stueck vom Repeat
    full = text + text[-170:]  # sorge dafuer dass letztes window im repeat auftaucht
    # Baue klaren Loop: 4x der gleiche Block
    block = "X" * 180
    test_text = "Einleitung." + block + block + block + block + "Abschlussversuch" + block
    assert len(test_text) > 800
    result = VLLMBrain._detect_reasoning_loop(test_text)
    assert result is True, f"Loop sollte erkannt werden (4x gleicher 180-char Block), war {result}"
    print("  [OK] Loop mit 4x Wiederholung korrekt erkannt")


def test_loop_detector_ignores_unique_text():
    """Text ohne Wiederholungen wird nicht als Loop markiert."""
    parts = [f"DiesistParagraph{i}mitganzvieleeinzigartigemInhalt." for i in range(20)]
    unique = "".join(parts)
    assert len(unique) > 600
    result = VLLMBrain._detect_reasoning_loop(unique)
    assert result is False, f"Einzigartiger Text sollte kein Loop sein, war {result}"
    print("  [OK] Einzigartiger Text wird nicht als Loop erkannt")


def test_loop_detector_needs_minimum_length():
    """Zu kurzer Text (< 360 Zeichen) wird nie als Loop erkannt."""
    short = "abc" * 60  # 180 chars, aber zu kurz fuer window*2
    result = VLLMBrain._detect_reasoning_loop(short)
    assert result is False, f"Kurzer Text ({len(short)} chars) sollte kein Loop sein"
    print("  [OK] Text unter window*2 wird ignoriert")


if __name__ == "__main__":
    tests = [
        test_default_repetition_penalty_in_generation_config,
        test_enable_thinking_is_true_for_qwen35,
        test_sync_generate_passes_repetition_penalty_in_extra_body,
        test_stream_generate_passes_repetition_penalty_in_extra_body,
        test_extra_body_preserves_steering_when_adding_penalty,
        test_loop_detector_catches_repeated_segment,
        test_loop_detector_ignores_unique_text,
        test_loop_detector_needs_minimum_length,
    ]
    results = []
    for test in tests:
        name = test.__name__
        print(f"\n--- {name} ---")
        try:
            test()
            results.append(True)
        except AssertionError as e:
            print(f"  [FAIL] {e}")
            results.append(False)
        except Exception as e:
            print(f"  [ERROR] {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    passed = sum(results)
    total = len(results)
    print(f"\n{'='*60}")
    print(f"Results: {passed}/{total} passed")
    print(f"{'='*60}")
    sys.exit(0 if passed == total else 1)
