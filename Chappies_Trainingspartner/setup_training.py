import sys
import os
import json
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.config import settings

console = Console()

def main():
    console.clear()
    console.print(Panel.fit(
        "[bold magenta]CHAPPIES TRAINING SETUP[/bold magenta]\n"
        "[dim]Konfiguriere den autonomen 24/7 Modus[/dim]",
        border_style="magenta"
    ))

    # 1. Persona
    persona = Prompt.ask(
        "\n[yellow]Wie soll sich der Trainer verhalten? (Persona)[/yellow]",
        default="Ein kritischer User, der versucht Fehler zu finden"
    )

    # 2. Fokus
    focus_area = Prompt.ask(
        "\n[yellow]Worauf soll der Trainer besonders achten?[/yellow]",
        default="Logikfehler und Konsistenz im Gedächtnis"
    )

    # 3. Provider
    console.print("\n[yellow]Wähle das Modell für den Trainer und Chappie:[/yellow]")
    console.print("1. Groq API (Schnell, Cloud)")
    console.print("2. Lokal (Ollama / GPT-OSS / Kimmy K2)")
    
    choice = Prompt.ask("Auswahl", choices=["1", "2"], default="2")
    provider_selection = "groq" if choice == "1" else "local"

    model_name = None
    if provider_selection == "local":
        model_name = Prompt.ask("Modell-Name (leer lassen für Default)", default=settings.ollama_model)
    else:
        model_name = Prompt.ask("Groq Modell (leer lassen für Default)", default=settings.groq_model)

    # Config Dictionary
    config_data = {
        "persona": persona,
        "focus_area": focus_area,
        "provider": provider_selection,
        "model_name": model_name
    }

    # Speichern
    config_path = os.path.join(os.path.dirname(__file__), '..', 'training_config.json')
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)

    console.print(Panel(
        f"[bold green]Konfiguration gespeichert![/bold green]\n"
        f"Persona: {persona}\n"
        f"Modus: {provider_selection}\n\n"
        f"[dim]Der Daemon wird jetzt im Hintergrund gestartet...[/dim]",
        border_style="green"
    ))

if __name__ == "__main__":
    main()