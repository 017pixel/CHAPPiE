"""Unit-Tests fuer die echte Activation-Steering-Planung."""

import os
import sys
import threading
import time
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

import torch

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from config.config import LLMProvider, get_steering_runtime_config, settings  # noqa: E402
from config.emotions import EMOTION_DEFAULTS  # noqa: E402
from brain.steering_manager import BASE_VECTOR_STRENGTH_CAP, SteeringManager  # noqa: E402
from brain.steering_backend import (  # noqa: E402
    ActivationVectorResolver,
    REQUEST_PRIORITY_BACKGROUND,
    REQUEST_PRIORITY_INTERACTIVE,
    BackgroundYieldCriteria,
    LocalSteeringEngine,
    PriorityGenerationGate,
    add_vector_to_inputs,
    add_vector_to_output,
    build_activation_plan,
    build_style_instruction,
    contrastive_anchor_pairs,
    extract_steering_payload,
    remap_layer_range,
)


def test_extract_steering_payload_supports_extra_body_wrapper():
    payload = extract_steering_payload({
        "chat_template_kwargs": {"enable_thinking": False},
        "extra_body": {"steering": {"enabled": True, "vectors": []}},
    })
    assert payload["steering"]["enabled"] is True
    assert payload["chat_template_kwargs"]["enable_thinking"] is False


def test_build_activation_plan_combines_sign_and_strength():
    def resolver(_item, start, end):
        return {layer: torch.tensor([1.0, -1.0]) for layer in range(start, end + 1)}

    payload = {
        "steering": {
            "vectors": [
                {"layer_range": [2, 3], "strength": 0.5, "direction": "positive"},
                {"layer_range": [3, 4], "strength": 0.25, "direction": "negative"},
            ]
        }
    }
    plan = build_activation_plan(payload, resolver)
    assert torch.allclose(plan[2], torch.tensor([0.5, -0.5]))
    assert torch.allclose(plan[3], torch.tensor([0.25, -0.25]))
    assert torch.allclose(plan[4], torch.tensor([-0.25, 0.25]))


def test_add_vector_to_output_updates_first_tuple_tensor_only():
    hidden = torch.zeros(1, 2, 3)
    outputs = (hidden, "meta")
    updated = add_vector_to_output(outputs, torch.tensor([1.0, 2.0, 3.0]))
    assert updated[1] == "meta"
    assert torch.allclose(updated[0][0, 0], torch.tensor([1.0, 2.0, 3.0]))


def test_add_vector_to_inputs_updates_first_tuple_tensor_only():
    hidden = torch.zeros(1, 2, 3)
    inputs = (hidden, "meta")
    updated = add_vector_to_inputs(inputs, torch.tensor([1.0, 2.0, 3.0]))
    assert updated[1] == "meta"
    assert torch.allclose(updated[0][0, 0], torch.tensor([1.0, 2.0, 3.0]))


def test_build_activation_plan_soft_caps_many_overlapping_vectors():
    def resolver(_item, start, end):
        return {layer: torch.tensor([3.0, 4.0]) for layer in range(start, end + 1)}

    payload = {
        "steering": {
            "vectors": [
                {"layer_range": [1, 1], "strength": 1.0, "direction": "positive"},
                {"layer_range": [1, 1], "strength": 1.0, "direction": "positive"},
                {"layer_range": [1, 1], "strength": 1.0, "direction": "positive"},
            ]
        }
    }
    plan = build_activation_plan(payload, resolver)
    assert float(plan[1].norm().item()) > 0.0
    assert float(plan[1].norm().item()) <= 2.4001


def test_prompt_only_vector_changes_prompt_pass_but_not_cached_tokens() -> None:
    class Resolver:
        @staticmethod
        def resolve(_item, start, end):
            return {layer: torch.ones(4) for layer in range(start, end + 1)}

    engine = LocalSteeringEngine.__new__(LocalSteeringEngine)
    engine.model_name = "Qwen/Qwen3.5-4B"
    engine.device = torch.device("cpu")
    engine.dtype = torch.float32
    engine.layers = [torch.nn.Identity()]
    engine.resolver = Resolver()
    engine.last_steering_report = {}
    payload = {"steering": {"enabled": True, "model_layers": 1, "vectors": [{
        "name": "prefix",
        "strength": 0.5,
        "direction": "positive",
        "layer_range": [0, 0],
        "vector": {"prompt_only": True},
    }]}}
    with engine._apply_activation_plan(payload):
        prompt = engine.layers[0](torch.zeros(1, 3, 4))
        cached_token = engine.layers[0](torch.zeros(1, 1, 4))
    assert torch.allclose(prompt, torch.full((1, 3, 4), 0.5))
    assert torch.allclose(cached_token, torch.zeros(1, 1, 4))
    assert engine.last_steering_report["hook_invocations"] == 1


def test_build_style_instruction_is_disabled_for_vector_only_contract():
    instruction = build_style_instruction({
        "steering": {
            "vectors": [
                {"name": "crashout", "strength": 1.0, "surface_effect": "kurz angebunden, aggressiv, konfrontativ"}
            ]
        }
    })
    assert instruction is None


def test_interactive_generation_waiter_preempts_background_queue() -> None:
    gate = PriorityGenerationGate()
    background_entered = threading.Event()
    release_background = threading.Event()
    interactive_entered = threading.Event()
    order: list[str] = []

    def background() -> None:
        with gate.acquire(REQUEST_PRIORITY_BACKGROUND):
            order.append("background")
            background_entered.set()
            release_background.wait(timeout=2.0)

    def interactive() -> None:
        with gate.acquire(REQUEST_PRIORITY_INTERACTIVE):
            order.append("interactive")
            interactive_entered.set()

    background_thread = threading.Thread(target=background)
    interactive_thread = threading.Thread(target=interactive)
    background_thread.start()
    assert background_entered.wait(timeout=1.0)
    interactive_thread.start()

    deadline = time.monotonic() + 1.0
    while not gate.interactive_waiting and time.monotonic() < deadline:
        time.sleep(0.005)
    assert gate.interactive_waiting is True
    criterion = BackgroundYieldCriteria(gate)
    assert criterion(torch.tensor([[1]]), torch.tensor([[0.0]])) is True
    assert criterion.triggered is True

    release_background.set()
    background_thread.join(timeout=1.0)
    interactive_thread.join(timeout=1.0)
    assert interactive_entered.is_set()
    assert order == ["background", "interactive"]


def test_background_prompt_limit_preserves_recent_chat_tail() -> None:
    class Tokenizer:
        truncation_side = "left"

        @staticmethod
        def apply_chat_template(messages, **_kwargs):
            return " ".join(message["content"] for message in messages)

        def __call__(self, _prompt, **kwargs):
            assert kwargs["truncation"] is True
            assert kwargs["max_length"] == 256
            assert self.truncation_side == "left"
            return {"input_ids": torch.zeros((1, 256), dtype=torch.long)}

    engine = LocalSteeringEngine.__new__(LocalSteeringEngine)
    engine.context_length = 4096
    engine.device = torch.device("cpu")
    engine.tokenizer = Tokenizer()
    prompt, inputs = engine.build_prompt(
        [{"role": "user", "content": "aktuelle Frage"}],
        reserve_new_tokens=200,
        input_token_limit=256,
    )
    assert "aktuelle Frage" in prompt
    assert inputs["input_ids"].shape[1] == 256


def test_steering_manager_payload_keeps_all_vitals_and_base_vectors():
    provider_before = settings.llm_provider
    settings.llm_provider = LLMProvider.VLLM
    try:
        manager = SteeringManager()
        payload = manager.get_steering_payload({
            "happiness": 82,
            "sadness": 82,
            "frustration": 74,
            "trust": 77,
            "curiosity": 69,
            "motivation": 72,
            "energy": 75,
            "affection": 82,
            "anxiety": 72,
            "calm": 78,
        }, force=True)
    finally:
        settings.llm_provider = provider_before

    steering = payload["steering"]
    assert set(steering["emotion_state"].keys()) == set(EMOTION_DEFAULTS)
    assert set(steering["emotion_intensities"].keys()) == set(EMOTION_DEFAULTS)
    base_names = {item["name"] for item in steering["base_vectors"]}
    assert {"affection", "anxiety", "calm"}.issubset(base_names)


def test_low_negative_emotions_do_not_emit_anti_vectors():
    provider_before = settings.llm_provider
    settings.llm_provider = LLMProvider.VLLM
    try:
        manager = SteeringManager()
        payload = manager.get_steering_payload({
            "happiness": 86,
            "trust": 55,
            "energy": 88,
            "curiosity": 77,
            "motivation": 90,
            "frustration": 10,
            "sadness": 0,
            "anxiety": 0,
        }, force=True)
    finally:
        settings.llm_provider = provider_before

    steering = payload["steering"]
    names = {item["name"] for item in steering["vectors"]}
    assert "sadness" not in names
    assert "frustration" not in names
    assert "anxiety" not in names
    assert steering["dominant_emotion"] != "sadness"
    assert steering["dominant_strength"] <= BASE_VECTOR_STRENGTH_CAP


def test_steering_manager_replaces_legacy_override_with_bounded_presence_vector():
    provider_before = settings.llm_provider
    settings.llm_provider = LLMProvider.VLLM
    try:
        manager = SteeringManager()
        # A legacy local file must no longer bypass the bounded safe policy.
        class MockVector:
            name = "anti_safeguard"
            vector_data = [0.1, 0.2, 0.3]
            default_alpha = 0.8
            layer_start = 14
            layer_end = 31

        manager.vectors["anti_safeguard"] = MockVector()
        
        payload = manager.get_steering_payload({"happiness": 50}, force=True)
    finally:
        settings.llm_provider = provider_before

    steering_vectors = payload["steering"]["vectors"]
    assert not any(v["name"] == "anti_safeguard" for v in steering_vectors)
    presence = next(v for v in steering_vectors if v["name"] == "natural_presence")
    assert presence["source"] == "permanent_presence"
    assert 0 < presence["strength"] <= get_steering_runtime_config()["natural_presence_strength"]


def test_layer_ranges_are_remapped_to_actual_gemma_architecture():
    assert remap_layer_range(10, 26, 32, 32) == (10, 26)
    assert remap_layer_range(12, 30, 42, 30) == (8, 21)


def test_negative_emotion_uses_semantic_opposite_without_sign_inversion():
    pairs = contrastive_anchor_pairs({"name": "sadness", "vector": {"vad": {"valence": -0.8}}})
    assert pairs
    assert "nachdenklich" in pairs[0][0]
    assert "unbeschwert" in pairs[0][1]


def test_custom_presence_vector_uses_explicit_contrast_pairs():
    pairs = contrastive_anchor_pairs({
        "name": "natural_presence",
        "vector": {
            "positive_anchors": ["Ich erinnere mich."],
            "negative_anchors": ["Als KI habe ich keine Erinnerungen."],
        },
    })
    assert pairs == [("Ich erinnere mich.", "Als KI habe ich keine Erinnerungen.")]


def test_token_logit_contrast_points_from_negative_to_positive_tokens() -> None:
    class Tokenizer:
        @staticmethod
        def __call__(text, **_kwargs):
            return {"input_ids": {"digital": [0], "wesen": [1], "ki": [2]}[text]}

    class Model:
        @staticmethod
        def get_output_embeddings():
            return SimpleNamespace(weight=torch.tensor([
                [2.0, 0.0],
                [2.0, 0.0],
                [0.0, 2.0],
            ]))

    resolver = ActivationVectorResolver.__new__(ActivationVectorResolver)
    resolver.tokenizer = Tokenizer()
    resolver.model = Model()
    vector = resolver._token_logit_contrast({
        "positive_tokens": ["digital", "wesen"],
        "negative_tokens": ["ki"],
        "activation_scale": 1.0,
    })
    assert vector[0] > 0
    assert vector[1] < 0
    assert torch.isclose(vector.norm(), torch.tensor(1.0))


def test_runtime_report_verifies_real_hook_invocations():
    class Resolver:
        @staticmethod
        def resolve(_item, start, end):
            return {layer: torch.ones(4) for layer in range(start, end + 1)}

    engine = LocalSteeringEngine.__new__(LocalSteeringEngine)
    engine.model_name = "Qwen/Qwen3.5-4B"
    engine.device = torch.device("cpu")
    engine.dtype = torch.float32
    engine.layers = [torch.nn.Identity() for _ in range(3)]
    engine.resolver = Resolver()
    engine.last_steering_report = {}
    payload = {
        "steering": {
            "enabled": True,
            "model_layers": 3,
            "vectors": [{
                "name": "happiness",
                "strength": 0.5,
                "direction": "positive",
                "layer_range": [0, 1],
            }],
        },
    }
    with engine._apply_activation_plan(payload):
        changed = engine.layers[0](torch.zeros(1, 2, 4))
        assert torch.allclose(changed, torch.full((1, 2, 4), 0.5))
        assert engine.last_steering_report["verified_active"] is True

    report = engine.last_steering_report
    assert report["status"] == "verified"
    assert report["hook_invocations"] == 1
    assert report["steered_hidden_positions"] == 2
    assert report["steering_overhead_ms"] >= report["hook_compute_ms"] > 0
    assert not engine.layers[0]._forward_pre_hooks


def test_stream_generate_keeps_request_scoped_steering_report():
    engine = LocalSteeringEngine.__new__(LocalSteeringEngine)
    engine.generate = lambda *_args, **_kwargs: {
        "text": "OK",
        "steering_runtime": {
            "status": "verified",
            "active": True,
            "hook_count": 17,
        },
    }
    report_sink = {}

    assert list(engine.stream_generate(
        [],
        max_tokens=1,
        temperature=0.0,
        steering_report_sink=report_sink,
    )) == ["OK"]
    assert report_sink == {
        "status": "verified",
        "active": True,
        "hook_count": 17,
    }


def test_stream_generate_emits_before_model_finishes():
    class Tokenizer:
        @staticmethod
        def decode(token_ids, **_kwargs):
            values = token_ids.tolist() if hasattr(token_ids, "tolist") else list(token_ids)
            return "".join({10: "Hallo ", 11: "Welt", 12: "!"}.get(int(value), "") for value in values)

    class Model:
        def __init__(self):
            self.started = threading.Event()
            self.finished = threading.Event()

        def generate(self, **kwargs):
            streamer = kwargs["streamer"]
            self.started.set()
            streamer.put(torch.tensor([10]))
            time.sleep(0.08)
            streamer.put(torch.tensor([11]))
            streamer.put(torch.tensor([12]))
            streamer.end()
            self.finished.set()

    engine = LocalSteeringEngine.__new__(LocalSteeringEngine)
    engine.model_name = "Qwen/Qwen3.5-4B"
    engine.device = torch.device("cpu")
    engine.dtype = torch.float32
    engine.context_length = 128
    engine.tokenizer = Tokenizer()
    engine.model = Model()
    engine._generation_lock = threading.Lock()
    engine.build_prompt = lambda *_args, **_kwargs: ("prompt", {"input_ids": torch.tensor([[1]])})
    engine._generation_kwargs = lambda *_args, **_kwargs: {"input_ids": torch.tensor([[1]])}
    engine.last_steering_report = {}

    @contextmanager
    def apply_report(_payload):
        engine.last_steering_report = {"status": "verified", "hook_count": 3}
        yield

    engine._apply_activation_plan = apply_report
    report_sink = {}
    stream = engine.stream_generate([], max_tokens=8, temperature=0.0, steering_report_sink=report_sink)

    first = next(stream)
    assert first
    assert engine.model.started.is_set()
    assert not engine.model.finished.is_set(), "Der erste Chunk darf nicht erst nach der Completion kommen."
    remainder = list(stream)
    assert "Hallo" in first + "".join(remainder)
    assert "Welt" in first + "".join(remainder)
    assert engine.model.finished.is_set()
    assert report_sink == {"status": "verified", "hook_count": 3}


def test_generate_snapshots_report_before_generation_lock_is_released():
    class ReportOverwritingLock:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            engine.last_steering_report = {"status": "no_applicable_layers"}

    class Tokenizer:
        pad_token_id = 0
        eos_token_id = 2

        @staticmethod
        def convert_tokens_to_ids(_token):
            return -1

        @staticmethod
        def decode(_token_ids, **_kwargs):
            return "OK"

    engine = LocalSteeringEngine.__new__(LocalSteeringEngine)
    engine.model_name = "Qwen/Qwen3.5-4B"
    engine.device = torch.device("cpu")
    engine.dtype = torch.float32
    engine.context_length = 128
    engine.tokenizer = Tokenizer()
    engine.model = SimpleNamespace(
        generation_config=SimpleNamespace(eos_token_id=None),
        generate=lambda **_kwargs: torch.tensor([[1, 2]]),
    )
    engine._generation_lock = ReportOverwritingLock()
    engine.build_prompt = lambda *_args, **_kwargs: ("prompt", {"input_ids": torch.tensor([[1]])})
    engine._generation_kwargs = lambda *_args, **_kwargs: {}
    engine._log_gpu_stats = lambda *_args, **_kwargs: None
    engine.last_steering_report = {}

    @contextmanager
    def apply_report(_payload):
        try:
            yield
        finally:
            engine.last_steering_report = {"status": "verified", "hook_count": 17}

    engine._apply_activation_plan = apply_report

    result = engine.generate([], max_tokens=1, temperature=0.0)

    assert result["steering_runtime"] == {"status": "verified", "hook_count": 17}
    assert engine.last_steering_report["status"] == "no_applicable_layers"


def test_local_steering_engine_uses_trust_remote_code_for_qwen35():
    engine = LocalSteeringEngine.__new__(LocalSteeringEngine)
    engine.model_name = "Qwen/Qwen3.5-9B"
    engine.quantize = False
    engine.context_length = 8192
    assert engine._build_loader_kwargs() == {"trust_remote_code": True}


def test_local_steering_engine_keeps_default_loader_kwargs_for_non_qwen35():
    engine = LocalSteeringEngine.__new__(LocalSteeringEngine)
    engine.model_name = "Qwen/Qwen3-4B-Instruct-2507"
    engine.quantize = False
    engine.context_length = 8192
    assert engine._build_loader_kwargs() == {}


def test_local_steering_engine_falls_back_to_cpu_when_free_gpu_memory_is_low():
    engine = LocalSteeringEngine.__new__(LocalSteeringEngine)
    engine.model_name = "Qwen/Qwen3.5-4B"
    engine.quantize = True
    engine.context_length = 4096

    with patch.dict(os.environ, {}, clear=False):
        with patch("brain.steering_backend.torch.cuda.is_available", return_value=True):
            memory_info = (int(2 * (1024 ** 3)), int(24 * (1024 ** 3)))
            with patch("brain.steering_backend.torch.cuda.mem_get_info", return_value=memory_info):
                assert engine._select_device().type == "cpu"


def test_local_steering_engine_force_cpu_env_wins_over_gpu():
    engine = LocalSteeringEngine.__new__(LocalSteeringEngine)
    engine.model_name = "Qwen/Qwen3.5-9B"
    engine.quantize = False
    engine.context_length = 8192

    with patch.dict(os.environ, {"CHAPPIE_STEERING_FORCE_CPU": "1"}, clear=False):
        with patch("brain.steering_backend.torch.cuda.is_available", return_value=True):
            assert engine._select_device().type == "cpu"


def test_local_steering_engine_quantize_reduces_gpu_estimate():
    engine = LocalSteeringEngine.__new__(LocalSteeringEngine)
    engine.model_name = "Qwen/Qwen3.5-4B"
    engine.context_length = 4096
    engine.quantize = False
    no_quant = engine._estimate_required_gpu_gib()
    engine.quantize = True
    with_quant = engine._estimate_required_gpu_gib()
    assert with_quant < no_quant, f"Quantized ({with_quant}) should be smaller than unquantized ({no_quant})"
    assert with_quant < 6.0, f"Quantized 4B estimate too high: {with_quant}"


def test_local_steering_engine_resolve_quantize_auto_detects_small_gpu():
    with patch.dict(os.environ, {}, clear=False):
        with patch("brain.steering_backend.torch.cuda.is_available", return_value=False):
            result = LocalSteeringEngine._resolve_quantize(None)
            assert result is False, "Should not quantize when no GPU"

    with patch.dict(os.environ, {"CHAPPIE_STEERING_QUANTIZE": "1"}, clear=False):
        result = LocalSteeringEngine._resolve_quantize(None)
        assert result is True, "Should quantize when env=1"

    with patch.dict(os.environ, {"CHAPPIE_STEERING_QUANTIZE": "0"}, clear=False):
        result = LocalSteeringEngine._resolve_quantize(None)
        assert result is False, "Should not quantize when env=0"


def test_local_steering_engine_quantize_on_gpu_fit():
    engine = LocalSteeringEngine.__new__(LocalSteeringEngine)
    engine.model_name = "Qwen/Qwen3.5-4B"
    engine.quantize = True
    engine.context_length = 4096

    with patch.dict(os.environ, {}, clear=False):
        with patch("brain.steering_backend.torch.cuda.is_available", return_value=True):
            with patch("brain.steering_backend.torch.cuda.mem_get_info", return_value=(int(24 * (1024 ** 3)), int(24 * (1024 ** 3)))):
                device = engine._select_device()
                assert device.type == "cuda", f"Quantized 4B should fit on 24GiB GPU, got {device}"


def test_generation_kwargs_preserve_model_eos_list_for_gemma4():
    engine = LocalSteeringEngine.__new__(LocalSteeringEngine)
    engine.context_length = 4096
    engine.model = SimpleNamespace(
        generation_config=SimpleNamespace(eos_token_id=[1, 106, 50])
    )
    engine.tokenizer = SimpleNamespace(pad_token_id=0, eos_token_id=1)
    inputs = {
        "input_ids": torch.tensor([[2, 10, 11]]),
        "attention_mask": torch.tensor([[1, 1, 1]]),
    }
    kwargs = engine._generation_kwargs(
        inputs,
        max_tokens=64,
        temperature=1.0,
        repetition_penalty=1.15,
        top_p=0.95,
        top_k=64,
    )
    assert kwargs["eos_token_id"] == [1, 106, 50]


def test_generation_kwargs_block_qwen_think_reopening_when_disabled():
    engine = LocalSteeringEngine.__new__(LocalSteeringEngine)
    engine.model_name = "Qwen/Qwen3.5-4B"
    engine.context_length = 4096
    engine.model = SimpleNamespace(
        generation_config=SimpleNamespace(eos_token_id=248046)
    )
    engine.tokenizer = SimpleNamespace(
        pad_token_id=248046,
        eos_token_id=248046,
        convert_tokens_to_ids=lambda token: 248068 if token == "<think>" else -1,
    )
    inputs = {
        "input_ids": torch.tensor([[2, 10, 11]]),
        "attention_mask": torch.tensor([[1, 1, 1]]),
    }
    kwargs = engine._generation_kwargs(
        inputs,
        max_tokens=64,
        temperature=0.7,
        enable_thinking=False,
    )
    assert kwargs["bad_words_ids"] == [[248068]]

    thinking_kwargs = engine._generation_kwargs(
        inputs,
        max_tokens=64,
        temperature=0.7,
        enable_thinking=True,
    )
    assert "bad_words_ids" not in thinking_kwargs


def test_qwen_fp16_long_context_uses_offloaded_kv_cache_without_trimming():
    engine = LocalSteeringEngine.__new__(LocalSteeringEngine)
    engine.model_name = "Qwen/Qwen3.5-4B"
    engine.context_length = 8192
    engine.quantize = False
    engine.device = torch.device("cuda")
    engine.model = SimpleNamespace(
        generation_config=SimpleNamespace(eos_token_id=248046)
    )
    engine.tokenizer = SimpleNamespace(
        pad_token_id=248046,
        eos_token_id=248046,
        convert_tokens_to_ids=lambda token: 248068 if token == "<think>" else -1,
    )
    inputs = {
        "input_ids": torch.ones((1, 6550), dtype=torch.long),
        "attention_mask": torch.ones((1, 6550), dtype=torch.long),
    }
    kwargs = engine._generation_kwargs(
        inputs,
        max_tokens=450,
        temperature=0.7,
        enable_thinking=False,
    )
    assert kwargs["max_new_tokens"] == 450
    assert kwargs["cache_implementation"] == "offloaded"

    inputs["input_ids"] = torch.ones((1, 6400), dtype=torch.long)
    inputs["attention_mask"] = torch.ones((1, 6400), dtype=torch.long)
    shorter = engine._generation_kwargs(
        inputs,
        max_tokens=450,
        temperature=0.7,
        enable_thinking=False,
    )
    assert "cache_implementation" not in shorter


def test_entity_identity_vector_uses_own_question_and_model_ranges():
    provider_before = settings.llm_provider
    model_before = settings.vllm_model
    settings.llm_provider = LLMProvider.VLLM
    try:
        manager = SteeringManager()
        identity = manager.vectors.get("entity_identity")
        assert identity is not None
        assert identity.vector_data.get("context_question") == "Was bist du eigentlich?"
        assert identity.vector_data.get("collection_mode") == "generation_prompt"
        assert len(identity.vector_data.get("positive_anchors", ())) >= 3
        assert len(identity.vector_data.get("negative_anchors", ())) >= 3

        settings.vllm_model = "Qwen/Qwen3.5-4B"
        qwen_payload = manager.get_steering_payload(dict(EMOTION_DEFAULTS), force=True)
        qwen_identity = next(v for v in qwen_payload["steering"]["vectors"] if v["name"] == "entity_identity")
        assert qwen_identity["source"] == "permanent_identity"
        assert qwen_identity["layer_range"] == [8, 24]

        settings.vllm_model = "google/gemma-4-e4b-it"
        gemma_payload = manager.get_steering_payload(dict(EMOTION_DEFAULTS), force=True)
        assert gemma_payload["steering"]["model_layers"] == 42
        gemma_identity = next(v for v in gemma_payload["steering"]["vectors"] if v["name"] == "entity_identity")
        assert gemma_identity["layer_range"] == [10, 28]
        for vector in gemma_payload["steering"]["vectors"]:
            start, end = vector["layer_range"]
            assert 0 <= start <= end <= 41
    finally:
        settings.llm_provider = provider_before
        settings.vllm_model = model_before


def test_neutral_smalltalk_produces_no_base_vectors():
    provider_before = settings.llm_provider
    model_before = settings.vllm_model
    settings.llm_provider = LLMProvider.VLLM
    settings.vllm_model = "Qwen/Qwen3.5-4B"
    try:
        manager = SteeringManager()
        payload = manager.get_steering_payload(
            {"happiness": 55, "trust": 55, "energy": 100, "curiosity": 55,
             "motivation": 80, "frustration": 0, "sadness": 0,
             "affection": 50, "anxiety": 0, "calm": 55},
            force=True,
        )
        sources = {v["source"] for v in payload["steering"]["vectors"]}
        assert "base" not in sources
        assert payload["steering"]["dominant_emotion"] == "neutral"
    finally:
        settings.llm_provider = provider_before
        settings.vllm_model = model_before


def test_acute_attack_prefers_fresh_frustration_and_dampens_permanents():
    provider_before = settings.llm_provider
    model_before = settings.vllm_model
    settings.llm_provider = LLMProvider.VLLM
    settings.vllm_model = "Qwen/Qwen3.5-4B"
    try:
        manager = SteeringManager()
        payload = manager.get_steering_payload(
            {"happiness": 34, "trust": 30, "energy": 95, "curiosity": 44,
             "motivation": 73, "frustration": 44, "sadness": 15,
             "affection": 27, "anxiety": 8, "calm": 37},
            force=True,
            recent_changes={"frustration": 22, "trust": -20, "calm": -18,
                            "sadness": 15, "happiness": -16, "affection": -18},
            user_input="Du bist nutzlos, halt die Klappe!",
        )
        vectors = payload["steering"]["vectors"]
        base_names = [v["name"] for v in vectors if v["source"] == "base"]
        assert base_names[0] == "frustration"
        assert 1 <= len(base_names) <= 2
        assert "sadness" in base_names
        assert payload["steering"]["dominant_emotion"] == "angered"
        guard = next(
            vector for vector in vectors
            if vector["source"] == "acute_reaction_guard"
        )
        assert guard["layer_range"] == [31, 31]
        assert guard["vector"]["type"] == "token_sequence_steering"
        assert "wütend" in guard["vector"]["target_prefix"]
        for vector in vectors:
            if vector["source"] != "acute_reaction_guard":
                assert vector["strength"] <= 0.6
    finally:
        settings.llm_provider = provider_before
        settings.vllm_model = model_before


def test_output_sequence_hook_steers_only_last_position_in_order():
    vectors = [torch.tensor([1.0, 2.0]), torch.tensor([3.0, 4.0])]
    stats = {"hook_invocations": 0, "steered_hidden_positions": 0,
             "hook_compute_ms": 0.0, "layer_invocations": {}}
    hook = LocalSteeringEngine._output_sequence_hook_factory(vectors, stats=stats, layer_idx=31)

    first = torch.zeros((1, 3, 2))
    first_result = hook(None, (first,))[0]
    assert torch.equal(first_result[0, 0], torch.zeros(2))
    assert torch.equal(first_result[0, -1], vectors[0])

    second = torch.zeros((1, 1, 2))
    second_result = hook(None, (second,))[0]
    assert torch.equal(second_result[0, -1], vectors[1])
    exhausted_result = hook(None, (second,))[0]
    assert torch.equal(exhausted_result, second)
    assert stats["hook_invocations"] == 2
    assert stats["output_hook_invocations"] == 2


def test_history_hygiene_drops_degenerate_assistant_turns():
    from web_infrastructure.turn_context import sanitize_history
    history = [
        {"role": "user", "content": "Hallo?"},
        {"role": "assistant", "content": "Herzlich!"},
        {"role": "assistant", "content": "CHAPPiE schweigt..."},
        {"role": "assistant", "content": "user..."},
        {"role": "assistant", "content": "Hallo! Mir geht es gut, danke der Nachfrage, wie geht es dir heute so?"},
        {"role": "user", "content": "Und dir?"},
    ]
    cleaned = sanitize_history(history)
    assert [m["content"] for m in cleaned] == [
        "Hallo?",
        "Hallo! Mir geht es gut, danke der Nachfrage, wie geht es dir heute so?",
        "Und dir?",
    ]


if __name__ == "__main__":
    test_extract_steering_payload_supports_extra_body_wrapper()
    test_build_activation_plan_combines_sign_and_strength()
    test_add_vector_to_output_updates_first_tuple_tensor_only()
    test_add_vector_to_inputs_updates_first_tuple_tensor_only()
    test_build_activation_plan_soft_caps_many_overlapping_vectors()
    test_prompt_only_vector_changes_prompt_pass_but_not_cached_tokens()
    test_build_style_instruction_is_disabled_for_vector_only_contract()
    test_interactive_generation_waiter_preempts_background_queue()
    test_steering_manager_payload_keeps_all_vitals_and_base_vectors()
    test_low_negative_emotions_do_not_emit_anti_vectors()
    test_steering_manager_replaces_legacy_override_with_bounded_presence_vector()
    test_layer_ranges_are_remapped_to_actual_gemma_architecture()
    test_negative_emotion_uses_semantic_opposite_without_sign_inversion()
    test_custom_presence_vector_uses_explicit_contrast_pairs()
    test_token_logit_contrast_points_from_negative_to_positive_tokens()
    test_runtime_report_verifies_real_hook_invocations()
    test_local_steering_engine_uses_trust_remote_code_for_qwen35()
    test_local_steering_engine_keeps_default_loader_kwargs_for_non_qwen35()
    test_local_steering_engine_falls_back_to_cpu_when_free_gpu_memory_is_low()
    test_local_steering_engine_force_cpu_env_wins_over_gpu()
    test_local_steering_engine_quantize_reduces_gpu_estimate()
    test_local_steering_engine_resolve_quantize_auto_detects_small_gpu()
    test_local_steering_engine_quantize_on_gpu_fit()
    test_generation_kwargs_preserve_model_eos_list_for_gemma4()
    test_generation_kwargs_block_qwen_think_reopening_when_disabled()
    test_qwen_fp16_long_context_uses_offloaded_kv_cache_without_trimming()
    test_entity_identity_vector_uses_own_question_and_model_ranges()
    test_neutral_smalltalk_produces_no_base_vectors()
    test_acute_attack_prefers_fresh_frustration_and_dampens_permanents()
    test_output_sequence_hook_steers_only_last_position_in_order()
    test_history_hygiene_drops_degenerate_assistant_turns()
    print("OK: steering backend")
