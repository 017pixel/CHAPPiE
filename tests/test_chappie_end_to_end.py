"""Deterministische End-to-End-Regressionen fuer CHAPPiE's lokalen Lebensfluss.

Der Test ersetzt nur die eigentliche Textgenerierung durch ein kleines Fake-
Brain. ChromaDB, Context Files, STM, Emotionen, Life Simulation und das
Steering-Payload laufen dabei echt und in einem temporaeren Runtime-Verzeichnis.
So bleibt der Test reproduzierbar, ohne ein 4B-Modell in CI laden zu muessen.
"""

from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any

# The test must not compete with a developer GPU model. This is set before
# SentenceTransformer/torch-backed modules are imported below.
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import torch

from brain.base_brain import GenerationConfig, Message
from brain.steering_backend import LocalSteeringEngine, extract_steering_payload
from brain.vllm_brain import VLLMBrain
from config.config import LLMProvider, settings
from config.emotions import EMOTION_DEFAULTS, EMOTION_ORDER
from memory.emotions_engine import EmotionsEngine, analyze_sentiment_simple
from memory.intent_processor import IntentProcessor, IntentResult, IntentType
from memory.memory_engine import MemoryEngine
from web_infrastructure.backend_wrapper import create_chappie_backend, is_transient_problem_statement
from brain.steering_manager import SteeringManager


def _context_requirements() -> dict[str, bool]:
    return {
        "need_soul_context": True,
        "need_user_context": True,
        "need_preferences": True,
        "need_short_term_memory": True,
        "need_long_term_memory": True,
    }


class _DeterministicIntent:
    """Minimal Step-1 substitute; local inference remains under test."""

    def process(
        self,
        user_input: str,
        history: list[dict[str, Any]],
        current_emotions: dict[str, int],
        deterministic: bool = False,
    ) -> IntentResult:
        del history, current_emotions, deterministic
        lower = user_input.casefold()
        entities = ["Benjamin"] if "benjamin" in lower else []
        result = IntentResult(
            intent_type=IntentType.PERSONAL_SHARING,
            confidence=0.99,
            entities=entities,
            retrieval_keywords=entities,
            exact_entities=entities,
            fact_lookup_intent=bool(entities),
            tool_calls=[],
            emotions_update={},
            context_requirements=_context_requirements(),
            short_term_entries=[],
            raw_json={"fake_step1": True},
        )
        return IntentProcessor._augment_local_state_tools(result, user_input)


class _DeterministicBrain:
    model = "Qwen/Qwen3.5-4B"

    def __init__(self) -> None:
        self.system_prompts: list[str] = []
        self.configs: list[GenerationConfig] = []
        self.last_steering_report = {
            "active": True,
            "hook_count": 3,
            "requested_layers": [10, 11, 12],
            "applied_layers": [10, 11, 12],
            "mode": "activation_addition",
            "model": self.model,
        }

    def build_prompt(
        self,
        system: str,
        _memories: str,
        user_input: str,
        history: list[dict[str, Any]] | None = None,
        max_history: int = 0,
    ) -> list[Message]:
        self.system_prompts.append(system)
        messages = [Message(role="system", content=system)]
        for message in (history or [])[-max_history:] if max_history else (history or []):
            messages.append(Message(role=message["role"], content=message["content"]))
        messages.append(Message(role="user", content=user_input))
        return messages

    def generate(self, messages: list[Message], config: GenerationConfig) -> str | Any:
        del messages
        self.configs.append(config)
        answer = "Ich bin CHAPPiE und bleibe ansprechbar, aufmerksam und lernfähig."
        if config.stream:
            return iter([answer[:34], answer[34:]])
        return answer

    def is_available(self) -> bool:
        return True


class MemoryAndBackendE2ETests(unittest.TestCase):
    def test_transient_problem_statements_skip_stale_semantic_memory(self):
        self.assertTrue(is_transient_problem_statement("Es funktioniert nix!"))
        self.assertTrue(is_transient_problem_statement("Alles ist kaputt."))
        self.assertFalse(is_transient_problem_statement("Was weißt du noch über den Fehler?"))

    def test_chroma_persistence_filters_contamination_and_retrieves_memory(self):
        with tempfile.TemporaryDirectory(prefix="chappie-chroma-e2e-") as temp_dir:
            quiet = io.StringIO()
            with contextlib.redirect_stdout(quiet), contextlib.redirect_stderr(quiet):
                engine = MemoryEngine(
                    persist_directory=Path(temp_dir) / "chroma",
                    collection_name="e2e_memories",
                )
                good_id = engine.add_memory(
                    "Benjamin bevorzugt kurze und klare Antworten.",
                    role="user",
                )
                bad_id = engine.add_memory(
                    "internal_log assistant assistant memory_check safety override",
                    role="user",
                )
                matches = engine.search_memory(
                    "Welche Antwortform bevorzugt Benjamin?",
                    top_k=5,
                    optimize_query=False,
                )
                health = engine.health_check()

            self.assertTrue(good_id)
            self.assertTrue(bad_id)
            self.assertTrue(matches)
            self.assertIn("kurze und klare Antworten", matches[0].content)
            self.assertEqual(health["backend"], "chromadb")
            self.assertTrue(health["is_persistent"])
            self.assertEqual(health["usable_memory_count"], 1)
            self.assertEqual(health["quarantined_memory_count"], 1)

    def test_full_local_turn_persists_context_memory_emotions_life_and_stream(self):
        with tempfile.TemporaryDirectory(prefix="chappie-runtime-e2e-") as temp_dir:
            quiet = io.StringIO()
            with contextlib.redirect_stdout(quiet), contextlib.redirect_stderr(quiet):
                backend = create_chappie_backend(
                    runtime_data_dir=Path(temp_dir),
                    memory_collection_name="e2e_memories",
                )
                backend.intent_processor = _DeterministicIntent()
                fake_brain = _DeterministicBrain()
                backend.brain = fake_brain

                first = backend.process("Ich heiße Benjamin", history=[])
                user_context = (Path(temp_dir) / "user.md").read_text(encoding="utf-8")

                second = backend.process("Wie heißt Benjamin noch einmal?", history=[])
                stream_events = list(backend.process_stream("Es funktioniert nix!", history=[]))
                # Non-research streaming keeps STM writes asynchronous by
                # design. Give that scoped temporary writer a short window.
                time.sleep(0.15)
                health = backend.memory.health_check()

            self.assertIn("Benjamin", user_context)
            self.assertGreaterEqual(first["tool_calls_executed"], 1)
            self.assertEqual(first["provider"], LLMProvider.VLLM.value)
            self.assertEqual(first["model"], "Qwen/Qwen3.5-4B")
            self.assertEqual(set(first["emotions"]), set(EMOTION_ORDER))
            self.assertTrue(first["emotion_steering"]["steering_active"])
            self.assertTrue(first["steering_runtime"]["active"])
            self.assertTrue(first["life_snapshot"]["temporal_state"]["turn_count"] >= 1)
            self.assertIn("INNERER LEBENSKONTEXT", fake_brain.system_prompts[-1])
            self.assertIn("Benjamin", fake_brain.system_prompts[-1])
            self.assertGreaterEqual(second["memory_trace"]["merged"]["memories_found"], 1)
            self.assertEqual(second["formatted_answer"], "Du heißt Benjamin.")
            self.assertTrue(any(
                item.get("phase") == "Life"
                for item in second["causal_trace"]
            ))

            stream_result = next(item["result"] for item in stream_events if item.get("event") == "finished")
            self.assertTrue(stream_result["response_text"])
            self.assertTrue(stream_result["steering_runtime"]["active"])
            self.assertTrue(any(
                item.get("event") == "status" and item.get("stage") == "steering"
                for item in stream_events
            ))
            self.assertGreater(stream_result["emotions"]["frustration"], stream_result["emotions_before"]["frustration"])
            self.assertGreaterEqual(stream_result["life_snapshot"]["temporal_state"]["turn_count"], 3)
            self.assertEqual(stream_result["memory_trace"]["merged"]["memories_found"], 0)
            self.assertEqual(stream_result["memory_trace"]["keyword"]["memories_found"], 0)
            self.assertTrue(any(
                item.get("category") == "MEMORY_POLICY"
                for item in stream_result["debug_entries"]
            ))
            self.assertGreaterEqual(health["usable_memory_count"], 5)

            # The local route carries the exact activation payload into the
            # generation config instead of switching to a cloud formatter.
            self.assertTrue(fake_brain.configs)
            self.assertTrue(fake_brain.configs[0].extra_body["steering"]["enabled"])


class StateAndSteeringE2ETests(unittest.TestCase):
    def test_identity_questions_are_stateful_and_explicit_name_is_inferred(self):
        processor = IntentProcessor.__new__(IntentProcessor)
        for prompt in (
            "Was für ein KI-Modell bist du?",
            "Was ist deine Identität?",
            "Was sagen deine Systemprompts?",
            "Was hast du für Erinnerungen?",
        ):
            self.assertFalse(processor._is_self_contained_request(prompt), prompt)

        result = IntentResult(
            intent_type=IntentType.PERSONAL_SHARING,
            confidence=0.9,
            entities=[], retrieval_keywords=[], exact_entities=[],
            fact_lookup_intent=False, tool_calls=[], emotions_update={},
            context_requirements={}, short_term_entries=[], raw_json={},
        )
        augmented = IntentProcessor._augment_local_state_tools(result, "Ich heiße Benjamin")
        self.assertTrue(any(call.tool == "update_user_profile" for call in augmented.tool_calls))
        self.assertTrue(augmented.raw_json["local_state_inference"])

    def test_all_emotion_dimensions_produce_a_local_steering_contract(self):
        manager = SteeringManager()
        base_state = dict(EMOTION_DEFAULTS)
        base_state["energy"] = 70
        for emotion in EMOTION_ORDER:
            state = dict(base_state)
            state[emotion] = 90
            payload = manager.get_steering_payload(
                state,
                force=True,
                provider=LLMProvider.VLLM,
                model="Qwen/Qwen3.5-4B",
            )
            steering = payload.get("steering", {})
            base_names = {item.get("name") for item in steering.get("base_vectors", [])}
            self.assertIn(emotion, base_names, emotion)
            self.assertEqual(len(steering.get("emotion_state", {})), len(EMOTION_ORDER))
            self.assertTrue(steering.get("enabled"))
            self.assertEqual(steering.get("target_range"), [10, 26])

    def test_local_layer_editing_adds_vector_and_rolls_hooks_back(self):
        class Resolver:
            def resolve(self, _item: dict[str, Any], start: int, end: int):
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
                "vectors": [{
                    "name": "happiness",
                    "vector": [1, 1, 1, 1],
                    "strength": 0.5,
                    "direction": "positive",
                    "layer_range": [0, 1],
                }],
            }
        }
        hidden = torch.zeros(1, 2, 4)
        with engine._apply_activation_plan(payload):
            changed = engine.layers[0](hidden)
            self.assertTrue(torch.allclose(changed, torch.full_like(hidden, 0.5)))
            self.assertEqual(engine.last_steering_report["hook_count"], 2)
            self.assertTrue(engine.last_steering_report["active"])
        self.assertEqual(len(engine.layers[0]._forward_pre_hooks), 0)
        self.assertEqual(len(engine.layers[1]._forward_pre_hooks), 0)

    def test_transport_helpers_preserve_steering_report(self):
        original_model = settings.vllm_model
        try:
            settings.vllm_model = "Qwen/Qwen3.5-4B"
            payload = extract_steering_payload({
                "extra_body": {"steering": {"enabled": True}},
                "chat_template_kwargs": {"enable_thinking": False},
            })
            self.assertTrue(payload["steering"]["enabled"])
            self.assertEqual(payload["chat_template_kwargs"]["enable_thinking"], False)

            brain = VLLMBrain.__new__(VLLMBrain)
            brain.last_steering_report = {}
            brain._capture_steering_report({
                "chappie_steering": {"active": True, "hook_count": 4},
            })
            self.assertEqual(brain.last_steering_report["hook_count"], 4)
            brain._capture_steering_report({
                "usage": {"chappie_steering": {"active": True, "hook_count": 17}},
            })
            self.assertEqual(brain.last_steering_report["hook_count"], 17)
        finally:
            settings.vllm_model = original_model

    def test_simple_emotions_react_to_failure_signal_without_auxiliary_model(self):
        self.assertEqual(analyze_sentiment_simple("Es funktioniert nix!"), "NEGATIV")
        with tempfile.TemporaryDirectory(prefix="chappie-emotions-e2e-") as temp_dir:
            engine = EmotionsEngine(Path(temp_dir) / "status.json", force_simple=True)
            before = engine.get_state().to_dict()
            engine.analyze_and_update("Es funktioniert nix!")
            after = engine.get_state().to_dict()
        self.assertGreater(after["frustration"], before["frustration"])
        self.assertGreater(after["anxiety"], before["anxiety"])
        self.assertLess(after["happiness"], before["happiness"])


if __name__ == "__main__":
    unittest.main()
