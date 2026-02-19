"""
CHAPPiE Training Setup Wizard
==============================
Interaktiver Setup für das autonome Training von CHAPPiE.

Features:
- Auswahl des KI-Backends (Groq, Cerebras, Ollama)
- Modell-Auswahl für jeden Provider
- Trainer-Persona Konfiguration
- Curriculum-Erstellung mit mehreren Themen
- API Key Management
"""

import os
import sys
import json
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.table import Table

# Projekt-Root zum Path hinzufügen
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)

from config.config import settings, LLMProvider, PROJECT_ROOT as CONFIG_ROOT
from config import secrets

console = Console()


# === Verfügbare Modelle pro Provider ===
GROQ_MODELS = {
    "1": ("moonshotai/kimi-k2-instruct-0905", "Kimi K2 - MoonshotAI (Empfohlen)"),
    "2": ("llama-3.1-70b-versatile", "Llama 3.1 70B - Meta"),
    "3": ("llama-3.1-8b-instant", "Llama 3.1 8B - Schnell"),
    "4": ("mixtral-8x7b-32768", "Mixtral 8x7B - MoE"),
    "5": ("gemma2-9b-it", "Gemma 2 9B - Google"),
}

CEREBRAS_MODELS = {
    "1": ("llama-3.3-70b", "Llama 3.3 70B - Leistungsstark (Empfohlen)"),
    "2": ("llama-3.1-8b", "Llama 3.1 8B - Schnell & Kompakt"),
    "3": ("qwen-3-32b", "Qwen 3 32B - Alibaba"),
}

OLLAMA_MODELS = {
    "1": ("llama3:70b", "Llama 3 70B - Maximum Power"),
    "2": ("llama3:8b", "Llama 3 8B - Ausgewogen (Empfohlen)"),
    "3": ("qwen2.5:72b", "Qwen 2.5 72B - Alternative Power-Modell"),
    "4": ("deepseek-r1:14b", "DeepSeek R1 14B - Reasoning"),
    "5": ("CUSTOM", "Eigenes Modell eingeben..."),
}

# === Beispiel-Curricula ===
EXAMPLE_CURRICULA = {
    "1": {
        "name": "Philosophie & Ethik",
        "curriculum": [
            {"topic": "Philosophie & Moral", "duration_minutes": 120},
            {"topic": "Ethische Dilemmas", "duration_minutes": 60},
            {"topic": "Kritisches Denken", "duration_minutes": "infinite"},
        ]
    },
    "2": {
        "name": "Kundenservice Training",
        "curriculum": [
            {"topic": "Umgang mit wütenden Usern", "duration_minutes": 60},
            {"topic": "Empathische Kommunikation", "duration_minutes": 60},
            {"topic": "Problemlösung & Hilfe", "duration_minutes": "infinite"},
        ]
    },
    "3": {
        "name": "Allgemeinwissen",
        "curriculum": [
            {"topic": "Allgemeinwissen & Smalltalk", "duration_minutes": "infinite"},
        ]
    },
    "4": {
        "name": "Custom",
        "curriculum": []
    }
}


def show_header():
    """Zeigt den Willkommens-Header."""
    console.print(Panel.fit(
        "[bold cyan]CHAPPiE Training Setup Wizard[/bold cyan]\n"
        "[dim]Konfiguriere das autonome Training[/dim]",
        border_style="cyan"
    ))
    console.print()


def select_provider() -> LLMProvider:
    """Lässt den User den KI-Provider auswählen."""
    console.print("[bold]Schritt 1: KI-Backend auswählen[/bold]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Nr.", style="cyan", width=4)
    table.add_column("Provider", style="white")
    table.add_column("Beschreibung", style="dim")
    
    table.add_row("1", "[API] Groq", "Cloud - Schnell & Gratis Tier")
    table.add_row("2", "[API] Cerebras", "Cloud - Ultra-High-Speed (2000+ tok/s)")
    table.add_row("3", "[Lokal] Ollama", "Lokal - Privat & Offline")
    
    console.print(table)
    console.print()
    
    choice = Prompt.ask("Provider wählen", choices=["1", "2", "3"], default="1")
    
    if choice == "1":
        return LLMProvider.GROQ
    elif choice == "2":
        return LLMProvider.CEREBRAS
    else:
        return LLMProvider.OLLAMA


def select_model(provider: LLMProvider) -> str:
    """Lässt den User das Modell auswählen."""
    console.print(f"\n[bold]Schritt 2: Modell für {provider.value.upper()} auswählen[/bold]\n")
    
    if provider == LLMProvider.GROQ:
        models = GROQ_MODELS
    elif provider == LLMProvider.CEREBRAS:
        models = CEREBRAS_MODELS
    else:
        models = OLLAMA_MODELS
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Nr.", style="cyan", width=4)
    table.add_column("Modell", style="white")
    table.add_column("Beschreibung", style="dim")
    
    for key, (model_id, desc) in models.items():
        table.add_row(key, model_id, desc)
    
    console.print(table)
    console.print()
    
    choices = list(models.keys())
    choice = Prompt.ask("Modell wählen", choices=choices, default="1")
    
    model_id, _ = models[choice]
    
    # Custom Input für Ollama
    if model_id == "CUSTOM":
        model_id = Prompt.ask("Modell-Name eingeben (z.B. llama3:latest)")
    
    return model_id


def check_api_key(provider: LLMProvider) -> str:
    """Prüft und fragt ggf. nach dem API Key."""
    if provider == LLMProvider.OLLAMA:
        return ""  # Kein API Key nötig
    
    console.print(f"\n[bold]Schritt 3: API Key prüfen[/bold]\n")
    
    if provider == LLMProvider.GROQ:
        existing_key = settings.groq_api_key
        key_name = "Groq"
        key_url = "https://console.groq.com/keys"
    else:  # CEREBRAS
        existing_key = settings.cerebras_api_key
        key_name = "Cerebras"
        key_url = "https://cloud.cerebras.ai"
    
    if existing_key and len(existing_key) > 10:
        masked = existing_key[:8] + "..." + existing_key[-4:]
        console.print(f"[green]✓[/green] {key_name} API Key gefunden: {masked}")
        
        if Confirm.ask("Diesen Key verwenden?", default=True):
            return existing_key
    
    console.print(f"[yellow]![/yellow] Kein {key_name} API Key gefunden oder neuer gewünscht.")
    console.print(f"[dim]Hole dir einen kostenlosen Key von: {key_url}[/dim]\n")
    
    new_key = Prompt.ask(f"{key_name} API Key eingeben")
    
    if new_key:
        # Den Key auch in die Settings übernehmen
        if provider == LLMProvider.GROQ:
            settings.groq_api_key = new_key
        else:
            settings.cerebras_api_key = new_key
        
        console.print(f"[green]✓[/green] API Key gesetzt!")
    
    return new_key


def configure_trainer() -> dict:
    """Konfiguriert die Trainer-Persona und das Curriculum."""
    console.print(f"\n[bold]Schritt 4: Trainer konfigurieren[/bold]\n")
    
    # Persona
    console.print("[dim]Die Persona bestimmt, wie sich der Trainer verhält.[/dim]")
    persona_options = {
        "1": "Kritischer User",
        "2": "Neugieriger Anfänger",
        "3": "Freundlicher Gesprächspartner",
        "4": "Strenger Prüfer",
        "5": "CUSTOM",
    }
    
    for key, persona in persona_options.items():
        console.print(f"  [{key}] {persona}")
    
    choice = Prompt.ask("\nPersona wählen", choices=list(persona_options.keys()), default="1")
    
    if choice == "5":
        persona = Prompt.ask("Eigene Persona eingeben")
    else:
        persona = persona_options[choice]
    
    # Curriculum
    console.print(f"\n[dim]Das Curriculum definiert die Trainings-Themen.[/dim]\n")
    
    for key, data in EXAMPLE_CURRICULA.items():
        name = data["name"]
        topics = len(data["curriculum"])
        console.print(f"  [{key}] {name} ({topics} Themen)" if topics > 0 else f"  [{key}] {name}")
    
    curriculum_choice = Prompt.ask("\nCurriculum wählen", choices=list(EXAMPLE_CURRICULA.keys()), default="3")
    
    if curriculum_choice == "4":
        # Custom Curriculum
        curriculum = create_custom_curriculum()
    else:
        curriculum = EXAMPLE_CURRICULA[curriculum_choice]["curriculum"]
    
    return {
        "persona": persona,
        "curriculum": curriculum
    }


def create_custom_curriculum() -> list:
    """Erstellt ein benutzerdefiniertes Curriculum."""
    console.print("\n[bold]Custom Curriculum erstellen[/bold]\n")
    console.print("[dim]Füge Themen hinzu. Gib 'fertig' ein wenn du fertig bist.[/dim]\n")
    
    curriculum = []
    
    while True:
        topic = Prompt.ask(f"Thema {len(curriculum) + 1} (oder 'fertig')")
        
        if topic.lower() == "fertig":
            break
        
        duration_input = Prompt.ask(
            f"Dauer für '{topic}' (Minuten, oder 'infinite')", 
            default="infinite"
        )
        
        if duration_input.lower() == "infinite":
            duration = "infinite"
        else:
            try:
                duration = int(duration_input)
            except ValueError:
                duration = "infinite"
        
        curriculum.append({
            "topic": topic,
            "duration_minutes": duration
        })
        
        console.print(f"[green]✓[/green] Thema hinzugefügt: {topic} ({duration} min)")
    
    if not curriculum:
        # Fallback wenn nichts eingegeben wurde
        curriculum = [{"topic": "Allgemeinwissen", "duration_minutes": "infinite"}]
    
    return curriculum


def save_configuration(provider: LLMProvider, model: str, trainer_config: dict):
    """Speichert die Konfiguration."""
    console.print(f"\n[bold]Konfiguration speichern...[/bold]\n")
    
    # Training Config speichern
    config_path = os.path.join(CONFIG_ROOT, "training_config.json")
    
    full_config = {
        "persona": trainer_config["persona"],
        "curriculum": trainer_config["curriculum"],
        "provider": provider.value,
        "model": model,
        "created_at": datetime.now().isoformat()
    }
    
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(full_config, f, ensure_ascii=False, indent=2)
        
        console.print(f"[green]✓[/green] Training-Konfiguration gespeichert: {config_path}")
    except Exception as e:
        console.print(f"[red]✗[/red] Fehler beim Speichern: {e}")
    
    # Provider in Settings aktualisieren
    settings.llm_provider = provider
    
    if provider == LLMProvider.GROQ:
        settings.groq_model = model
    elif provider == LLMProvider.CEREBRAS:
        settings.cerebras_model = model
    else:
        settings.ollama_model = model


def show_summary(provider: LLMProvider, model: str, api_key: str, trainer_config: dict):
    """Zeigt eine Zusammenfassung der Konfiguration."""
    console.print("\n")
    console.print(Panel.fit(
        "[bold green]Konfiguration abgeschlossen![/bold green]",
        border_style="green"
    ))
    
    table = Table(show_header=False, box=None)
    table.add_column("Setting", style="cyan")
    table.add_column("Wert", style="white")
    
    table.add_row("Provider", provider.value.upper())
    table.add_row("Modell", model)
    table.add_row("API Key", "✓ Gesetzt" if api_key else "Nicht benötigt")
    table.add_row("Persona", trainer_config["persona"])
    table.add_row("Themen", str(len(trainer_config["curriculum"])))
    
    for i, item in enumerate(trainer_config["curriculum"], 1):
        duration = item["duration_minutes"]
        duration_str = f"{duration} min" if duration != "infinite" else "∞"
        table.add_row(f"  Thema {i}", f"{item['topic']} ({duration_str})")
    
    console.print(table)


def run_setup():
    """Führt den kompletten Setup-Wizard aus."""
    show_header()
    
    # 1. Provider wählen
    provider = select_provider()
    
    # 2. Modell wählen
    model = select_model(provider)
    
    # 3. API Key prüfen
    api_key = check_api_key(provider)
    
    # 4. Trainer konfigurieren
    trainer_config = configure_trainer()
    
    # 5. Speichern
    save_configuration(provider, model, trainer_config)
    
    # 6. Zusammenfassung
    show_summary(provider, model, api_key, trainer_config)
    
    # 7. Training starten?
    console.print()
    if Confirm.ask("Training jetzt starten?", default=True):
        return True
    
    console.print("\n[dim]Setup beendet. Starte das Training später mit:[/dim]")
    console.print("[cyan]python3 Chappies_Trainingspartner/training_daemon.py[/cyan]")
    return False


def quick_setup() -> bool:
    """Schnell-Setup mit minimalen Fragen."""
    show_header()
    console.print("[yellow]Schnell-Setup Modus[/yellow]\n")
    
    # Frage nur Provider
    provider = select_provider()
    model = select_model(provider)
    api_key = check_api_key(provider)
    
    # Defaults für Trainer
    trainer_config = {
        "persona": "Kritischer User",
        "curriculum": [{"topic": "Allgemeinwissen & Smalltalk", "duration_minutes": "infinite"}]
    }
    
    save_configuration(provider, model, trainer_config)
    show_summary(provider, model, api_key, trainer_config)
    
    return Confirm.ask("\nTraining jetzt starten?", default=True)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="CHAPPiE Training Setup")
    parser.add_argument("--quick", "-q", action="store_true", help="Schnell-Setup mit Defaults")
    args = parser.parse_args()
    
    try:
        if args.quick:
            should_start = quick_setup()
        else:
            should_start = run_setup()
        
        if should_start:
            console.print("\n[bold cyan]Starte Training...[/bold cyan]\n")
            
            # Training Loop starten - Nutze relative Imports für Linux-Kompatibilität
            try:
                from Chappies_Trainingspartner.training_loop import TrainingLoop
                from Chappies_Trainingspartner.trainer_agent import TrainerAgent, load_training_config
            except ImportError:
                # Fallback: Direkter Import wenn wir im selben Ordner sind
                from training_loop import TrainingLoop
                from trainer_agent import TrainerAgent, load_training_config
            
            config = load_training_config()
            trainer = TrainerAgent(config)
            loop = TrainingLoop(trainer)
            
            thread = loop.start()
            
            console.print("\n[dim]Drücke Enter um das Training zu stoppen...[/dim]\n")
            input()
            
            loop.stop()
            thread.join(timeout=5)
            
            console.print("\n[green]Training beendet.[/green]")
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Abgebrochen.[/yellow]")
        sys.exit(0)
