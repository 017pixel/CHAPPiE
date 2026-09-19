"""Pure helpers for preparing autonomous training chat history."""

from __future__ import annotations


def normalize_training_prompt_history(
    history: list[dict],
    current_input: str,
    max_history: int,
) -> tuple[str, list[dict]]:
    """Return one summary context plus valid user/assistant chat history."""
    system_summaries = [
        str(item.get("content", "")).strip()
        for item in history
        if item.get("role") == "system" and str(item.get("content", "")).strip()
    ]
    dialogue = [
        {"role": item.get("role"), "content": str(item.get("content", ""))}
        for item in history
        if item.get("role") in {"user", "assistant"} and str(item.get("content", "")).strip()
    ]
    if dialogue and dialogue[-1]["role"] == "user" and dialogue[-1]["content"] == str(current_input):
        dialogue.pop()
    history_limit = max(0, int(max_history))
    if history_limit:
        dialogue = dialogue[-history_limit:]
    latest_summary = system_summaries[-1] if system_summaries else ""
    return latest_summary, dialogue
