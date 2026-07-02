"""Modellfreie Regressionstests fuer die Gemma-4-Integration."""

import os
import sys
import types

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)


class _FakeTensor:
    def __init__(self, values):
        self._values = list(values)

    def numel(self):
        return len(self._values)

    def tolist(self):
        return list(self._values)

    def __getitem__(self, _index):
        return self


if "torch" not in sys.modules:
    fake_torch = types.ModuleType("torch")
    fake_torch.Tensor = _FakeTensor
    fake_torch.float16 = "float16"
    fake_torch.float32 = "float32"
    fake_torch.inference_mode = lambda: types.SimpleNamespace(__enter__=lambda self: None, __exit__=lambda self, exc_type, exc, tb: None)
    fake_torch.tensor = lambda values, *args, **kwargs: _FakeTensor(values)
    fake_torch.nn = types.SimpleNamespace(functional=types.SimpleNamespace(normalize=lambda value, dim=0: value))
    fake_torch.cuda = types.SimpleNamespace(is_available=lambda: False, empty_cache=lambda: None)
    fake_torch.device = lambda value: types.SimpleNamespace(type=value)
    sys.modules["torch"] = fake_torch

if "transformers" not in sys.modules:
    fake_transformers = types.ModuleType("transformers")
    fake_transformers.AutoConfig = object
    fake_transformers.AutoModelForCausalLM = object
    fake_transformers.AutoTokenizer = object
    fake_transformers.BitsAndBytesConfig = lambda *args, **kwargs: {"args": args, "kwargs": kwargs}
    fake_transformers.TextIteratorStreamer = object
    sys.modules["transformers"] = fake_transformers

import torch  # noqa: E402

from brain.agents.steering_manager import MODEL_LAYER_PROFILES, SteeringManager  # noqa: E402
from brain.steering_backend import LocalSteeringEngine, anchor_scale_for_model  # noqa: E402
from brain.vllm_brain import VLLMBrain  # noqa: E402
from config.config import get_model_generation_defaults, is_gemma4_model, is_qwen_model  # noqa: E402


class _GemmaTokenizer:
    def decode(self, token_ids, skip_special_tokens=False, clean_up_tokenization_spaces=True):  # noqa: ANN001
        if skip_special_tokens:
            return "Antwort"
        return "<|channel>thought\nIch pruefe das.\n<|channel|>\nAntwort<turn|>"

    def __call__(self, text, add_special_tokens=False, return_tensors="pt"):  # noqa: ANN001
        return {"input_ids": torch.tensor([[1, 2, 3]])}


class _DumpMessage:
    def model_dump(self):
        return {"thinking_content": "Gemma denkt"}


def test_gemma4_config_detection_and_generation_defaults():
    assert is_gemma4_model("google/gemma-4-26B-A4B-it") is True
    assert is_qwen_model("google/gemma-4-26B-A4B-it") is False
    assert get_model_generation_defaults("google/gemma-4-E4B-it") == {
        "temperature": 1.0,
        "top_p": 0.95,
        "top_k": 64,
    }


def test_gemma4_steering_profile_detection_uses_specific_profiles():
    manager = SteeringManager.__new__(SteeringManager)
    assert manager._detect_model_profile_for_name("google/gemma-4-26B-A4B-it") is MODEL_LAYER_PROFILES["gemma-4-26b-a4b"]
    assert manager._detect_model_profile_for_name("google/gemma-4-E4B-it") is MODEL_LAYER_PROFILES["gemma-4-e4b"]


def test_gemma4_anchor_scale_is_separate_from_qwen():
    assert anchor_scale_for_model("google/gemma-4-26B-A4B-it") > anchor_scale_for_model("Qwen/Qwen3.5-4B")


def test_gemma4_thinking_output_split_uses_channel_tokens():
    engine = LocalSteeringEngine.__new__(LocalSteeringEngine)
    engine.model_name = "google/gemma-4-26B-A4B-it"
    engine.tokenizer = _GemmaTokenizer()
    reasoning, answer = engine._split_thinking_output(torch.tensor([1, 2, 3]))
    assert reasoning == "Ich pruefe das."
    assert answer == "Antwort"


def test_vllm_reasoning_extraction_accepts_gemma_thinking_keys():
    brain = VLLMBrain.__new__(VLLMBrain)
    assert brain._extract_reasoning_content(_DumpMessage()) == "Gemma denkt"


if __name__ == "__main__":
    test_gemma4_config_detection_and_generation_defaults()
    test_gemma4_steering_profile_detection_uses_specific_profiles()
    test_gemma4_anchor_scale_is_separate_from_qwen()
    test_gemma4_thinking_output_split_uses_channel_tokens()
    test_vllm_reasoning_extraction_accepts_gemma_thinking_keys()
    print("OK: Gemma 4 integration")
