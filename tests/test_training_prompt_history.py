"""Training prompts must remain compatible with strict local chat templates."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from Chappies_Trainingspartner.training_loop import normalize_training_prompt_history


def test_system_summaries_are_folded_into_one_leading_context():
    history = [
        {"role": "system", "content": "alter Traum"},
        {"role": "user", "content": "alte Frage"},
        {"role": "assistant", "content": "alte Antwort"},
        {"role": "system", "content": "neuster Traum"},
        {"role": "user", "content": "aktuelle Frage"},
    ]

    summary, dialogue = normalize_training_prompt_history(history, "aktuelle Frage", max_history=20)

    assert summary == "neuster Traum"
    assert dialogue == [
        {"role": "user", "content": "alte Frage"},
        {"role": "assistant", "content": "alte Antwort"},
    ]
    assert all(item["role"] != "system" for item in dialogue)


def test_training_history_is_bounded_and_does_not_duplicate_current_input():
    history = [
        {"role": "user" if index % 2 == 0 else "assistant", "content": f"turn-{index}"}
        for index in range(30)
    ] + [{"role": "user", "content": "jetzt"}]

    _, dialogue = normalize_training_prompt_history(history, "jetzt", max_history=8)

    assert len(dialogue) == 8
    assert dialogue[-1]["content"] == "turn-29"
    assert all(item["content"] != "jetzt" for item in dialogue)


if __name__ == "__main__":
    test_system_summaries_are_folded_into_one_leading_context()
    test_training_history_is_bounded_and_does_not_duplicate_current_input()
    print("OK: training prompt history")
