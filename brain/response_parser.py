"""
CHAPiE - Response Parser
========================
Verarbeitet LLM-Antworten und extrahiert strukturierte Inhalte.

Hauptfunktion: Innerer Monolog (Chain of Thought)
- Trennt <gedanke> vom <antwort> Teil
- Zeigt Gedanken nur im Debug-Modus
- User sieht nur die eigentliche Antwort
"""

import re
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class ParsedResponse:
    """Repraesentiert eine geparste LLM-Antwort."""
    thought: Optional[str]  # Innerer Monolog (kann None sein)
    answer: str             # Die eigentliche Antwort
    raw: str                # Originale, ungeparste Antwort


@dataclass
class TaggedBlockExtraction:
    """Extrahierter Tag-Block plus Resttext."""
    content: Optional[str]
    remaining: str
    raw: str


def parse_chain_of_thought(response: str) -> ParsedResponse:
    """
    Extrahiert Gedanken und Antwort aus einer strukturierten LLM-Antwort.
    
    Erwartet Format:
    <gedanke>
    Interner Denkprozess...
    </gedanke>
    
    <antwort>
    Eigentliche Antwort an den User...
    </antwort>
    
    Falls das Format nicht gefunden wird, wird die gesamte Antwort
    als 'answer' zurueckgegeben.
    
    Args:
        response: Die rohe LLM-Antwort
    
    Returns:
        ParsedResponse mit thought, answer und raw
    """
    # Regex fuer Gedanken-Tag
    thought_pattern = r'<gedanke>(.*?)</gedanke>'
    thought_match = re.search(thought_pattern, response, re.DOTALL | re.IGNORECASE)
    
    # Regex fuer Antwort-Tag
    answer_pattern = r'<antwort>(.*?)</antwort>'
    answer_match = re.search(answer_pattern, response, re.DOTALL | re.IGNORECASE)
    
    thought = None
    answer = response  # Default: Gesamte Antwort
    
    if thought_match:
        thought = thought_match.group(1).strip()
        # Wenn wir einen Gedanken gefunden haben, aber kein Antwort-Tag,
        # dann entfernen wir den Gedanken aus der 'answer', damit er nicht doppelt angezeigt wird.
        if not answer_match:
            answer = response.replace(thought_match.group(0), "").strip()
    
    if answer_match:
        answer = answer_match.group(1).strip()
    
    return ParsedResponse(
        thought=thought,
        answer=answer,
        raw=response
    )


def extract_answer_only(response: str) -> str:
    """
    Extrahiert nur den Antwort-Teil aus einer LLM-Antwort.
    
    Shortcut fuer parse_chain_of_thought().answer
    
    Args:
        response: Die rohe LLM-Antwort
    
    Returns:
        Nur der Antwort-Teil (oder gesamte Antwort wenn kein Tag gefunden)
    """
    return parse_chain_of_thought(response).answer


def looks_like_model_error(response: str) -> bool:
    """Erkennt typische Backend-Fehlerstrings oder leere Modellantworten."""
    if not isinstance(response, str) or not response.strip():
        return True
    stripped = strip_role_prefixes(response).strip()
    lowered = stripped.lower()
    error_markers = (
        "ollama fehler",
        "groq fehler",
        "vllm fehler",
        "steering-server fehler",
        "stream lieferte keinen text",
        "stream lieferte nur reasoning_content",
        "completions.create() got an unexpected key",
        "leere modellantwort",
        "api lieferte keine choices",
        "verbindungsfehler",
        "connection error",
    )
    if any(marker in lowered for marker in error_markers):
        return True
    if not re.search(r"[A-Za-zÄÖÜäöüß0-9]", stripped):
        return True
    return False


def strip_role_prefixes(text: str) -> str:
    """Entfernt einfache Chat-Rollenpraefixe vor Fehler-/Qualitaetschecks."""
    if not isinstance(text, str):
        return ""
    stripped = text.strip()
    role_prefix_re = re.compile(r"^(?:CHAPP?i?E|Assistant|Assistent|Bot|AI|KI|User)\s*:\s*", re.IGNORECASE)
    previous = None
    while stripped and stripped != previous:
        previous = stripped
        stripped = role_prefix_re.sub("", stripped, count=1).strip()
    return stripped


def contains_cot_leak(text: str) -> bool:
    """Erkennt sichtbare Reasoning-/Draft-Artefakte in finalen Antworten."""
    if not isinstance(text, str) or not text.strip():
        return False
    patterns = (
        r"<\s*/?\s*(think|thinking|thought|reasoning|model_reasoning|gedanke)\b",
        r"\bDraft\s*idea\b",
        r"\bDraftidea\b",
        r"\bImportant\s*:\s*Keep\b",
        r"\bReasoning\s*:\s*",
        r"\bAnalysis\s*:\s*",
        # Some local generations remove spaces while exposing their hidden
        # scratchpad.  Treat both spaced and fused variants as leakage.
        r"\b(?:thinking|analysis|reasoning)[\s._-]*(?:process|therequest|the_request)\b",
        r"\b(?:analy[sz]e|analyse)[\s._-]*(?:the[\s._-]*)?request\b",
        r"\buser[\s._-]*(?:input|message)\b",
        r"\bbased[\s._-]*on[\s._-]*the[\s._-]*system[\s._-]*prompt\b",
        r"\bcurrent[\s._-]*(?:vital[\s._-]*)?(?:signs|state|emotions?)\b",
        r"\b(?:drafting|response)[\s._-]*(?:the[\s._-]*)?(?:process|plan)\b",
        r"(?:^|\n)\s*(?:#{1,6}\s*)?(?:Thinking|Reasoning|Thought)\s+Process\s*:?",
        r"(?:^|\n)\s*\d+[.)]\s*\*{0,2}(?:Analyze|Analyse|Reason|Plan)\b",
        r"\bFinal\s*Response\s*:\s*",
        r"\bHmm,\s*der\s+User\b",
        r"(?:^|\n)\s*(?:```)?\s*thought\s*(?:\n|:)",
        r"(?:^|\n)\s*(?:CALL\s+FUNCTION\s*:\s*None\s*)?Thought[\s._-]*process\b",
    )
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


INSTRUCTION_LEAK_PATTERNS = (
    r"<\s*/?\s*function(?:_call)?\b[^>]*>",
    r"\b(?:call|function|funktionsaufruf)\s*:\s*(?:update_soul|update_user|update_preferences)\b",
    r"[\"'](?:name|function|action)[\"']\s*:\s*[\"'](?:update_soul|update_user|update_preferences|add_short_term_memory)[\"']",
    r"\b(?:update_soul|update_user|update_preferences|add_short_term_memory)\s*\(",
    r"\bsoul\s*\.\s*md\b",
    r"\{\%\s*(?:if|else|endif|for|endfor)\b",
    r"\{\{[^{}]{1,200}\}\}",
    r"<\|(?:channel|start|end|message|constrain)[^>]*\|>",
    r"\b(?:system prompt|prompt structure|internal functions?|tool plan|expected next step)\b",
    r"\b(?:internal thought process|internal reasoning|system state seems)\b",
    r"\b(?:expected output|strict formatting rules|final response generation)\b",
    r"\b(?:My Score Update|Mean Confidence Resultant Factor)\b",
    r"\bbrandoffset\s*=",
    r"\boutbound\\?_thought\\?_stream\b",
    r"\bThink\s+End\b",
    r"\bFUNCTION_CALL(?:_ACTIVATE)?\b",
    r"\bANWEISUNG\s+F[ÜU]R\s+DIE\s+(?:AUTOR)?GENERATION\b",
    r"<\s*/?\s*(?:html|body|table)\b[^>]*>",
)


def contains_instruction_leak(text: str) -> bool:
    """Detect orchestration, tool-call and template fragments in visible text."""
    if not isinstance(text, str) or not text.strip():
        return False
    return any(re.search(pattern, text, re.IGNORECASE | re.DOTALL) for pattern in INSTRUCTION_LEAK_PATTERNS)


def is_safe_retrieval_text(text: str) -> bool:
    """Return whether a persisted memory is safe to place back into a prompt."""
    return bool(isinstance(text, str) and text.strip()) and not (
        contains_instruction_leak(text)
        or contains_cot_leak(text)
        or _contains_memory_header(text)
        or _contains_dialogue_role_line(text)
    )


# Local models sometimes continue a serialized RAG example instead of
# answering.  These are prompt-infrastructure lines, not part of CHAPPiE's
# response.  Keep the patterns line-scoped so ordinary prose containing words
# such as "user" or "assistant" remains untouched.
_MEMORY_HEADER_LINE = re.compile(
    r"^\s*(?:"
    r"[0-9a-f]{8,}\s*\|\s*score\b"
    r"|\[[^\]\n]*\bid\s+[0-9a-f]{8,}\b[^\]\n]*\bscore\b[^\]\n]*\]"
    r")\s*$",
    re.IGNORECASE,
)
_DIALOGUE_ROLE_LINE = re.compile(
    r"^\s*(?P<role>user|assistant|assistent|system|tool|developer)"
    r"(?:\s*:\s*(?P<content>.*))?\s*$",
    re.IGNORECASE,
)


def _contains_memory_header(text: str) -> bool:
    return any(_MEMORY_HEADER_LINE.match(line) for line in str(text or "").splitlines())


def _contains_dialogue_role_line(text: str) -> bool:
    role_lines = []
    for line in str(text or "").splitlines():
        match = _DIALOGUE_ROLE_LINE.match(line)
        if match:
            role_lines.append((match.group("role").casefold(), (match.group("content") or "").strip()))
    if any(not content for _role, content in role_lines):
        return True
    if len(role_lines) >= 2:
        return True
    # A canonical USER: prefix is common in persisted user memories. Other
    # inline role prefixes are still suspicious when they occur alone.
    return bool(role_lines and role_lines[0][0] != "user")


def _strip_serialized_dialogue(text: str) -> tuple[str, bool]:
    """Keep only the final assistant segment of an echoed chat transcript."""
    lines = str(text or "").splitlines()
    role_lines: list[tuple[int, str, str]] = []
    for index, line in enumerate(lines):
        match = _DIALOGUE_ROLE_LINE.match(line)
        if match:
            role_lines.append(
                (
                    index,
                    match.group("role").casefold(),
                    (match.group("content") or "").strip(),
                )
            )

    if not role_lines:
        return str(text or ""), False

    assistant_lines = [item for item in role_lines if item[1] == "assistant"]
    if not assistant_lines:
        # A user/system-only transcript would expose the prompt as the answer.
        return "", True

    assistant_index, _role, inline_content = assistant_lines[-1]
    next_role_index = next(
        (index for index, _role, _content in role_lines if index > assistant_index),
        len(lines),
    )
    selected_lines: list[str] = []
    if inline_content:
        selected_lines.append(inline_content)
    selected_lines.extend(lines[assistant_index + 1:next_role_index])
    return "\n".join(selected_lines).strip(), True


def sanitize_visible_response(text: str) -> tuple[str, list[str]]:
    """Remove private reasoning and orchestration fragments before emission.

    Returns the cleaned answer and stable reason labels for logging. The
    sanitizer is intentionally conservative: if a leaked block cannot be
    separated from a genuine answer, it withholds that block.
    """
    if not isinstance(text, str) or not text.strip():
        return "", []

    cleaned = text
    reasons: list[str] = []

    # Remove the compact metadata line emitted by the memory prompt builder
    # before looking for role boundaries.  The model has been observed to
    # answer with this line followed by a complete user/assistant transcript.
    memory_lines = []
    for line in cleaned.splitlines():
        if _MEMORY_HEADER_LINE.match(line):
            reasons.append("memory_header")
            continue
        memory_lines.append(line)
    cleaned = "\n".join(memory_lines)

    serialized_answer, had_roles = _strip_serialized_dialogue(cleaned)
    if had_roles:
        cleaned = serialized_answer
        reasons.append("role_fragment")
        if not cleaned:
            return "", sorted(set(reasons + ["unresolved_leak"]))

    # Some local chat templates emit a prose reasoning preamble instead of
    # structured reasoning tokens. Never stream that preamble. If a clearly
    # delimited final answer exists, keep only the final answer; otherwise
    # withhold the truncated reasoning-only completion.
    prose_reasoning = re.compile(
        r"^\s*(?:#{1,6}\s*)?(?:Thinking|Reasoning|Thought)\s+Process\s*:?",
        re.IGNORECASE,
    )
    if prose_reasoning.search(cleaned):
        final_marker = re.search(
            r"(?:^|\n)\s*(?:#{1,6}\s*)?(?:Final\s+(?:Answer|Response)|Finale\s+Antwort)\s*:\s*",
            cleaned,
            re.IGNORECASE,
        )
        if final_marker:
            cleaned = cleaned[final_marker.end():]
            reasons.append("private_reasoning")
        else:
            return "", ["private_reasoning", "unresolved_leak"]

    # Gemma can first produce a valid answer and then continue with an
    # unstructured internal evaluation. Cut at the earliest unambiguous
    # orchestration marker so the valid prefix survives while nothing after
    # the private boundary can reach SSE or persistence.
    private_boundary = re.compile(
        r"(?:\bbrandoffset\s*=|\bMy Score Update\b|\bMean Confidence Resultant Factor\b|"
        r"\binternal thought process\b|\binternal reasoning\b|\bsystem state seems\b|"
        r"\bexpected output\b|\bstrict formatting rules\b|\bfinal response generation\b|"
        r"\boutbound\\?_thought\\?_stream\b|\bThink\s+End\b)",
        re.IGNORECASE,
    )
    boundary_match = private_boundary.search(cleaned)
    if boundary_match:
        cleaned = cleaned[:boundary_match.start()].rstrip(" \t\r\n;:,-")
        reasons.append("private_reasoning_tail")

    thought_block = re.compile(
        r"<\s*(think|thinking|thought|reasoning|model_reasoning|provider_reasoning|gedanke)\b[^>]*>.*?<\s*/\s*\1\s*>",
        re.IGNORECASE | re.DOTALL,
    )
    if thought_block.search(cleaned):
        cleaned = thought_block.sub("", cleaned)
        reasons.append("private_reasoning")

    function_block = re.compile(
        r"<\s*function(?:_call)?\b[^>]*>.*?<\s*/\s*function(?:_call)?\s*>",
        re.IGNORECASE | re.DOTALL,
    )
    if function_block.search(cleaned):
        cleaned = function_block.sub("", cleaned)
        reasons.append("tool_call")

    kept_lines = []
    for line in cleaned.splitlines():
        if contains_instruction_leak(line) or contains_cot_leak(line):
            reasons.append("instruction_fragment")
            continue
        kept_lines.append(line)
    cleaned = "\n".join(kept_lines)

    # Compact JSON tool calls can span one block without XML wrappers.
    json_tool = re.compile(
        r"\{[^{}]{0,800}[\"'](?:name|function|action)[\"']\s*:\s*[\"'](?:update_soul|update_user|update_preferences|add_short_term_memory)[\"'][^{}]{0,800}\}",
        re.IGNORECASE | re.DOTALL,
    )
    if json_tool.search(cleaned):
        cleaned = json_tool.sub("", cleaned)
        reasons.append("json_tool_call")

    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    if not cleaned:
        return "", sorted(set(reasons + ["unresolved_leak"]))
    if contains_instruction_leak(cleaned) or contains_cot_leak(cleaned):
        return "", sorted(set(reasons + ["unresolved_leak"]))
    return cleaned, sorted(set(reasons))


def has_chain_of_thought_format(response: str) -> bool:
    """
    Prueft ob die Antwort das Chain-of-Thought Format enthaelt.
    
    Args:
        response: Die LLM-Antwort
    
    Returns:
        True wenn beide Tags (<gedanke> und <antwort>) gefunden wurden
    """
    has_thought = bool(re.search(r'<gedanke>', response, re.IGNORECASE))
    has_answer = bool(re.search(r'<antwort>', response, re.IGNORECASE))
    return has_thought and has_answer


def format_thought_for_debug(thought: str, max_length: int = 200) -> str:
    """
    Formatiert den Gedanken fuer Debug-Ausgabe.
    
    Args:
        thought: Der interne Denkprozess
        max_length: Maximale Laenge (wird gekuerzt wenn laenger)
    
    Returns:
        Formatierter String fuer Debug-Ausgabe
    """
    if len(thought) > max_length:
        thought = thought[:max_length] + "..."
    
    # Entferne ueberfluessige Leerzeilen
    lines = [line.strip() for line in thought.split('\n') if line.strip()]
    return " | ".join(lines)


# === Alternative Tags (falls Modell andere verwendet) ===
def parse_thinking_tags(response: str) -> ParsedResponse:
    """
    Alternative Parser fuer andere Tag-Formate.
    Unterstuetzt: <thinking>, <thought>, <reasoning>
    
    Args:
        response: Die rohe LLM-Antwort
    
    Returns:
        ParsedResponse
    """
    # Versuche verschiedene Think-Tags
    think_patterns = [
        r'<think>(.*?)</think>',
        r'<thought>(.*?)</thought>',
        r'<reasoning>(.*?)</reasoning>',
        r'<thinking>(.*?)</thinking>',
        r'<gedanke>(.*?)</gedanke>',
    ]
    
    thought = None
    for pattern in think_patterns:
        match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
        if match:
            thought = match.group(1).strip()
            break
    
    # Versuche verschiedene Answer-Tags
    answer_patterns = [
        r'<answer>(.*?)</answer>',
        r'<response>(.*?)</response>',
        r'<antwort>(.*?)</antwort>',
    ]
    
    answer = response
    for pattern in answer_patterns:
        match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
        if match:
            answer = match.group(1).strip()
            break
    
    return ParsedResponse(thought=thought, answer=answer, raw=response)


def extract_tagged_block(response: str, tag_names: list[str]) -> TaggedBlockExtraction:
    """Extrahiert den ersten passenden XML-ähnlichen Block und liefert den Rest zurück."""
    if not isinstance(response, str):
        return TaggedBlockExtraction(content=None, remaining="", raw=str(response or ""))

    for tag_name in tag_names:
        pattern = rf'<{tag_name}>(.*?)</{tag_name}>'
        match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
        if match:
            content = match.group(1).strip()
            remaining = (response[:match.start()] + response[match.end():]).strip()
            return TaggedBlockExtraction(content=content, remaining=remaining, raw=response)

    return TaggedBlockExtraction(content=None, remaining=response.strip(), raw=response)


# === Test ===
if __name__ == "__main__":
    from rich.console import Console
    from rich.panel import Panel
    
    console = Console()
    console.print("[bold]Response Parser Test[/bold]\n")
    
    # Test-Antwort im Chain-of-Thought Format
    test_response = """<gedanke>
Der User fragt nach dem Wetter. Ich habe keine aktuellen Wetterdaten.
Ich sollte ehrlich sein und erklaeren, dass ich keinen Zugriff auf
aktuelle Wetterdaten habe.
</gedanke>

<antwort>
Ich habe leider keinen direkten Zugriff auf aktuelle Wetterdaten.
Fuer genaue Wetterinformationen empfehle ich dir, eine Wetter-App
oder eine Website wie wetter.de zu nutzen.
</antwort>"""
    
    result = parse_chain_of_thought(test_response)
    
    console.print("[cyan]1. Originale Antwort:[/cyan]")
    console.print(Panel(test_response[:200] + "...", title="Raw"))
    
    console.print("\n[cyan]2. Extrahierter Gedanke:[/cyan]")
    if result.thought:
        console.print(Panel(result.thought, title="<gedanke>"))
    
    console.print("\n[cyan]3. Extrahierte Antwort:[/cyan]")
    console.print(Panel(result.answer, title="<antwort>"))
    
    console.print("\n[cyan]4. Hat CoT Format:[/cyan]")
    console.print(f"   {has_chain_of_thought_format(test_response)}")
    
    # Test ohne Tags
    simple_response = "Das ist eine einfache Antwort ohne Tags."
    simple_result = parse_chain_of_thought(simple_response)
    
    console.print("\n[cyan]5. Test ohne Tags:[/cyan]")
    console.print(f"   Thought: {simple_result.thought}")
    console.print(f"   Answer: {simple_result.answer}")
    
    console.print("\n[green]Parser Test erfolgreich![/green]")
