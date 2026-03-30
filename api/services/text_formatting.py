from __future__ import annotations

import re


def parse_emotional_text(text: str) -> str:
    if not text:
        return text
    text = re.sub(r"(?<!\.)(\.{3,})(?!\.)", r"<br/><br/><em>\1</em><br/><br/>", text)
    text = re.sub(r"(?<!\*)\*([^\*]+)\*(?!\*)", r"<br/><br/><em>*\1*</em><br/><br/>", text)
    text = re.sub(r'("{3,})', r"<br/><br/><em>\1</em><br/><br/>", text)
    return text.strip()
