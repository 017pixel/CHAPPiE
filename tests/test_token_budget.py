"""Regression tests for exact model-tokenizer context accounting."""

from pathlib import Path
import sys
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from brain.base_brain import Message
from brain.token_counter import ModelTokenCounter
from config.config import settings
from web_infrastructure.backend_wrapper import create_chappie_backend, measure_prompt_components


GERMAN_TEXT = "Übermäßig große Äpfel überraschen zwölf fröhliche Fußgänger in Köln."


def test_qwen_uses_real_chat_template_tokens():
    counter = ModelTokenCounter("Qwen/Qwen3.5-4B")
    messages = [Message(role="system", content="Du bist CHAPPiE."), Message(role="user", content=GERMAN_TEXT)]
    expected = counter.tokenizer.apply_chat_template(
        [{"role": item.role, "content": item.content} for item in messages],
        tokenize=True,
        add_generation_prompt=True,
    )["input_ids"]
    assert counter.count_messages(messages) == len(expected)
    assert counter.count_messages(messages) > 10


def test_gemma_uses_its_own_chat_template():
    qwen = ModelTokenCounter("Qwen/Qwen3.5-4B")
    gemma = ModelTokenCounter("google/gemma-4-E4B-it")
    messages = [Message(role="user", content=GERMAN_TEXT * 8)]
    assert gemma.count_messages(messages) > 20
    assert qwen.count_messages(messages) != gemma.count_messages(messages)


def test_gpt_oss_uses_harmony_renderer():
    counter = ModelTokenCounter("openai/gpt-oss-120b")
    messages = [Message(role="system", content="Antworte knapp."), Message(role="user", content=GERMAN_TEXT)]
    assert counter.kind == "harmony"
    assert counter.count_messages(messages) > counter.count_text(GERMAN_TEXT)


def test_prompt_component_sum_plus_overhead_matches_exact_chat_total():
    counter = ModelTokenCounter("Qwen/Qwen3.5-4B")
    components = {
        "system": "Du bist CHAPPiE.",
        "persona": "Persona-Kontext.",
        "semantic_memory": "Semantische Erinnerung.",
        "keyword_memory": "ORBIT-741 ist der kontrollierte Code.",
        "short_term_memory": "Aktueller Kontext.",
        "life": "",
        "user": GERMAN_TEXT,
        "generation_budget": "Maximal 450 Antworttoken.",
        "response_style": "Antworte klar.",
        "response_plan": "Ton: neutral.",
    }
    system_text = "\n\n".join(value for key, value in components.items() if key not in {"user", "life"} and value)
    history = [{"role": "assistant", "content": "Vorherige kurze Antwort."}]
    before = [
        Message(role="system", content=system_text),
        Message(role="assistant", content=history[0]["content"]),
        Message(role="user", content=components["user"]),
    ]
    after = [before[0], before[-1]]

    metrics = measure_prompt_components(counter, components, history, before, after)

    assert metrics["component_sum_tokens"] + metrics["chat_template_and_join_overhead_tokens"] == metrics["chat_template_total_tokens_before_budget"]
    assert metrics["chat_template_total_tokens_after_budget"] == counter.count_messages(after)
    assert metrics["components"]["life"] == 0
    assert metrics["components"]["keyword_memory"] > 0


def test_real_tokenizer_can_locate_boundary_just_below_7000_tokens():
    counter = ModelTokenCounter("Qwen/Qwen3.5-4B")
    low, high = 1, 2000
    while low < high:
        mid = (low + high + 1) // 2
        messages = [Message(role="system", content="System."), Message(role="user", content=(GERMAN_TEXT + " ") * mid)]
        if counter.count_messages(messages) <= 7000:
            low = mid
        else:
            high = mid - 1
    below = [Message(role="system", content="System."), Message(role="user", content=(GERMAN_TEXT + " ") * low)]
    above = [Message(role="system", content="System."), Message(role="user", content=(GERMAN_TEXT + " ") * (low + 1))]
    assert counter.count_messages(below) <= 7000
    assert counter.count_messages(above) > 7000
    assert counter.count_messages(below) > 6900


def test_oversize_context_reports_every_trim_operation():
    original_limit = settings.context_token_limit
    try:
        settings.context_token_limit = 256
        with tempfile.TemporaryDirectory(prefix="chappie-context-budget-") as temp_dir:
            backend = create_chappie_backend(
                runtime_data_dir=Path(temp_dir),
                research_mode=True,
                feature_flags={
                    "persona": False,
                    "memory": False,
                    "emotions": False,
                    "life": False,
                },
            )
            messages = [
                Message(role="system", content=("Systemkontext mit vielen Details. " * 220)),
                Message(role="user", content=("Frühere lange Frage. " * 80)),
                Message(role="assistant", content=("Frühere lange Antwort. " * 80)),
                Message(role="user", content=("Aktuelle lange Forschungsfrage. " * 220)),
            ]

            trimmed, budget = backend._enforce_context_budget(messages)

        assert budget["original_tokens"] > budget["token_limit"]
        assert budget["was_trimmed"] is True
        assert budget["removed_messages"] == 2
        assert budget["system_was_truncated"] is True
        assert budget["user_was_truncated"] is True
        assert budget["trimmed_tokens"] <= budget["token_limit"]
        assert budget["context_budget_failed"] is False
        assert len(trimmed) == 2
        assert "wegen Tokenbudget gekuerzt" in trimmed[0].content
        assert "wegen Tokenbudget gekuerzt" in trimmed[-1].content
    finally:
        settings.context_token_limit = original_limit


if __name__ == "__main__":
    test_qwen_uses_real_chat_template_tokens()
    test_gemma_uses_its_own_chat_template()
    test_gpt_oss_uses_harmony_renderer()
    test_prompt_component_sum_plus_overhead_matches_exact_chat_total()
    test_real_tokenizer_can_locate_boundary_just_below_7000_tokens()
    test_oversize_context_reports_every_trim_operation()
    print("OK: model tokenizer context budget")
