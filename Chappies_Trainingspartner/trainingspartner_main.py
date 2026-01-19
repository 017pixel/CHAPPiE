"""
Chappies Trainingspartner - Main CLI
====================================
Hauptdatei fuer den Trainings-Modus.
Startet den CLI-Wizard und den Trainings-Loop.
"""

import sys
import os

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.layout import Layout
from rich import print as rprint

from Chappies_Trainingspartner.trainer_agent import TrainerAgent, TrainerConfig
from Chappies_Trainingspartner.training_loop import TrainingLoop
from config.config import settings, get_active_model

console = Console()

def print_header():
    console.clear()
    console.print(Panel.fit(
        "[bold magenta]CHAPPIES TRAININGSPARTNER[/bold magenta]\n"
        "[dim]Automatisierter Trainings-Modus[/dim]",
        border_style="magenta"
    ))

def main():
    print_header()
    
    # 1. Konfiguration abfragen
    console.print("[bold cyan]KONFIGURATION DES TRAINERS[/bold cyan]")
    
    persona = Prompt.ask(
        "\n[yellow]Wie soll sich der Trainer verhalten? (Persona)[/yellow]",
        default="Ein kritischer User, der versucht Fehler zu finden"
    )
    
    focus_area = Prompt.ask(
        "\n[yellow]Worauf soll der Trainer besonders achten?[/yellow]",
        default="Logikfehler und Konsistenz im Gedächtnis"
    )
    
    # Provider Auswahl
    rprint("\n[yellow]Wähle das Modell für den Trainer und Chappie:[/yellow]")
    rprint("1. Groq API (Schnell, Cloud)")
    rprint("2. Lokal (Ollama / GPT-OSS / Kimmy K2)")
    
    choice = Prompt.ask("Auswahl", choices=["1", "2"], default="1")
    
    provider_selection = "groq" if choice == "1" else "local"
    
    # Optional: Modell Name
    model_name = None
    if provider_selection == "local":
        model_name = Prompt.ask("Modell-Name (leer lassen für Default)", default=settings.ollama_model)
    
    # Globalen Settings für Chappie updaten (damit Chappie denselben Provider nutzt)
    # Mapping: local -> ollama
    settings_provider = "groq" if provider_selection == "groq" else "ollama"
    settings.update_from_ui(provider=settings_provider, model=model_name)
    
    # Zusammenfassung
    print_header()
    console.print(Panel(
        f"[bold]Persona:[/bold] {persona}\n"
        f"[bold]Fokus:[/bold] {focus_area}\n"
        f"[bold]Modus:[/bold] {provider_selection.upper()} (Trainer & Chappie)\n"
        f"[bold]Modell:[/bold] {get_active_model()}",
        title="Konfiguration",
        border_style="green"
    ))
    
    if not Confirm.ask("Möchten Sie das Training jetzt starten?"):
        console.print("[red]Abgebrochen.[/red]")
        return

    # 2. Initialisierung
    console.print("\n[dim]Initialisiere Agenten...[/dim]")
    
    config = TrainerConfig(
        persona=persona,
        focus_area=focus_area,
        provider=provider_selection,
        model_name=model_name
    )
    
    trainer = TrainerAgent(config)
    loop = TrainingLoop(trainer)
    
    # 3. Starten
    console.clear()
    console.print(Panel(
        "[bold green]TRAINING GESTARTET[/bold green]\n\n"
        "Der Loop läuft jetzt automatisch.\n"
        "[blink bold red]>>> DRÜCKE ENTER UM ZU UNTERBRECHEN <<<[/blink bold red]",
        border_style="green"
    ))
    
    # Thread starten
    loop.start()
    
    try:
        # Haupt-Thread wartet auf Enter
        input()
        
        # Stoppen
        console.print("\n[bold yellow]Stoppe Training... (bitte warten)[/bold yellow]")
        loop.stop()
        
    except KeyboardInterrupt:
        loop.stop()
        console.print("\n[bold red]Training hart abgebrochen.[/bold red]")
        
    console.print("[bold green]Training beendet. Alle Erinnerungen wurden gespeichert.[/bold green]")

if __name__ == "__main__":
    main()
