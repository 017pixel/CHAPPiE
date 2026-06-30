"""Parser fuer test_fragen.md → strukturierte Kategorien + Fragen."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class QuestionItem:
    text: str
    pre_commands: List[str] = field(default_factory=list)
    post_commands: List[str] = field(default_factory=list)
    setup_prompts: List[str] = field(default_factory=list)
    notes: str = ""
    question_number: int = 0


@dataclass
class Category:
    id: int
    name: str
    description: str = ""
    questions: List[QuestionItem] = field(default_factory=list)


def _parse_text_block(block: str) -> List[QuestionItem]:
    items: List[QuestionItem] = []
    pending_commands: List[str] = []
    pending_setup: List[str] = []
    current_commands: List[str] = []
    current_setup: List[str] = []
    current_question: str = ""

    def finish_current() -> None:
        nonlocal current_question, current_commands, current_setup
        if not current_question:
            return
        items.append(QuestionItem(
            text=current_question,
            pre_commands=list(current_commands),
            post_commands=[],
            setup_prompts=list(current_setup),
        ))
        current_question = ""
        current_commands = []
        current_setup = []

    for line in block.strip().split("\n"):
        stripped = line.strip()
        if not stripped:
            continue

        setup_match = re.match(r"^@setup\s+(.+)", stripped)
        if setup_match:
            if current_question:
                finish_current()
            pending_setup.append(setup_match.group(1).strip())
            continue

        if stripped.startswith("/"):
            cmd = stripped
            if current_question:
                finish_current()
                pending_commands.append(cmd)
            else:
                pending_commands.append(cmd)
            continue

        match = re.match(r"^\d+\.\s+(.*)", stripped)
        if match:
            finish_current()
            current_commands = list(pending_commands)
            current_setup = list(pending_setup)
            pending_commands = []
            pending_setup = []
            current_question = match.group(1).strip()
        elif current_question:
            current_question += " " + stripped

    finish_current()

    if items:
        if pending_commands:
            items[-1].post_commands.extend(pending_commands)
        if pending_setup:
            items[-1].notes = (items[-1].notes + "\n" if items[-1].notes else "") + "Nicht ausgefuehrte Setup-Zeilen: " + " | ".join(pending_setup)

    for i, item in enumerate(items):
        item.question_number = i + 1

    return items


def parse_test_fragen(filepath: str) -> List[Category]:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    categories: List[Category] = []

    sections = re.split(r"^## Kategorie (\d+):", content, flags=re.MULTILINE)

    name_pattern = re.compile(r"^(.*?)(?:\n|$)")

    for i in range(1, len(sections), 2):
        cat_id = int(sections[i].strip())
        body = sections[i + 1] if i + 1 < len(sections) else ""

        name_match = name_pattern.match(body.strip())
        name = name_match.group(1).strip() if name_match else f"Kategorie {cat_id}"
        body_after_name = body[name_match.end():] if name_match else body

        description = ""
        desc_match = re.match(r"^(.*?)(?=\n```)", body_after_name, re.DOTALL)
        if desc_match:
            description = desc_match.group(1).strip()

        text_blocks = re.findall(r"```text\n(.*?)```", body, re.DOTALL)
        questions: List[QuestionItem] = []
        for block in text_blocks:
            questions.extend(_parse_text_block(block))

        if not questions:
            questions = _parse_text_block(body)

        if questions:
            for idx, q in enumerate(questions):
                q.question_number = idx + 1

        categories.append(Category(id=cat_id, name=name, description=description, questions=questions))

    categories.sort(key=lambda c: c.id)
    return categories
