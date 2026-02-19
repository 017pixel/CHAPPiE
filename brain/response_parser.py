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
        r'<thinking>(.*?)</thinking>',
        r'<thought>(.*?)</thought>',
        r'<reasoning>(.*?)</reasoning>',
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
