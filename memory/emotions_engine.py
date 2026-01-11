"""
CHAPiE - Emotions Engine
========================
Dynamisches Emotions-System basierend auf User-Interaktion.

Das System speichert:
- happiness: Gluecklichkeits-Level (0-100)
- trust: Vertrauens-Level (0-100)  
- energy: Energie-Level (0-100)

Die Werte aendern sich basierend auf der Sentiment-Analyse des User-Inputs.
"""

import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

from config.config import PROJECT_ROOT, settings


# Status-Datei Pfad
STATUS_FILE = PROJECT_ROOT / "data" / "status.json"


@dataclass
class EmotionalState:
    """Repraesentiert den emotionalen Zustand von CHAPiE."""
    happiness: int = 50
    trust: int = 50
    energy: int = 100
    curiosity: int = 50    # Neugier
    frustration: int = 0   # Frustration (niedrig ist gut)
    motivation: int = 80   # Motivation
    
    def clamp(self):
        """Begrenzt alle Werte auf 0-100."""
        self.happiness = max(0, min(100, self.happiness))
        self.trust = max(0, min(100, self.trust))
        self.energy = max(0, min(100, self.energy))
        self.curiosity = max(0, min(100, self.curiosity))
        self.frustration = max(0, min(100, self.frustration))
        self.motivation = max(0, min(100, self.motivation))
    
    def to_dict(self) -> dict:
        """Konvertiert zu Dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "EmotionalState":
        """Erstellt aus Dictionary."""
        return cls(
            happiness=data.get("happiness", 50),
            trust=data.get("trust", 50),
            energy=data.get("energy", 100),
            curiosity=data.get("curiosity", 50),
            frustration=data.get("frustration", 0),
            motivation=data.get("motivation", 80)
        )
    
    def get_mood_description(self) -> str:
        """Gibt eine textuelle Beschreibung der Stimmung zurueck."""
        if self.happiness >= 70:
            mood = "froehlich und enthusiastisch"
        elif self.happiness >= 50:
            mood = "ausgeglichen und freundlich"
        elif self.happiness >= 30:
            mood = "etwas nachdenklich"
        else:
            mood = "niedergeschlagen"
        
        if self.trust >= 70:
            trust_desc = "vertraut dir sehr"
        elif self.trust >= 50:
            trust_desc = "ist offen"
        elif self.trust >= 30:
            trust_desc = "ist etwas zurueckhaltend"
        else:
            trust_desc = "ist vorsichtig"
        
        if self.energy >= 70:
            energy_desc = "voller Energie"
        elif self.energy >= 50:
            energy_desc = "wach"
        elif self.energy >= 30:
            energy_desc = "etwas muede"
        else:
            energy_desc = "erschoepft"
        
        return f"CHAPiE ist {mood}, {trust_desc} und fuehlt sich {energy_desc}."


class EmotionsEngine:
    """
    Verwaltet den emotionalen Zustand von CHAPiE.
    
    Features:
    - Persistente Speicherung in status.json
    - Sentiment-basierte Updates
    - Mood-Beschreibungen fuer Prompts
    """
    
    def __init__(self):
        """Initialisiert die Emotions Engine."""
        self.state = self._load_state()
        print(f"Emotions Engine geladen: H={self.state.happiness} T={self.state.trust} E={self.state.energy}")
    
    def _load_state(self) -> EmotionalState:
        """Laedt den Status aus der Datei oder erstellt Defaults."""
        if STATUS_FILE.exists():
            try:
                with open(STATUS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return EmotionalState.from_dict(data)
            except Exception as e:
                print(f"Fehler beim Laden des Status: {e}")
        
        return EmotionalState()
    
    def _save_state(self):
        """Speichert den Status in die Datei."""
        STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(STATUS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.state.to_dict(), f, indent=2)
        except Exception as e:
            print(f"Fehler beim Speichern des Status: {e}")
    
    def update_from_sentiment(self, sentiment: str):
        """
        Aktualisiert den emotionalen Zustand basierend auf Sentiment.
        
        Args:
        Args:
            sentiment: "POSITIV", "NEGATIV", "NEUTRAL", "FRUSTRIERT", "NEUGIERIG"
        """
        sentiment = sentiment.upper().strip()
        
        # Basis-Analyse des Texts wurde schon gemacht, aber wir koennen
        # hier noch spezifische Logik einbauen.
        # HACK: Wir greifen nicht auf 'text' zu, also muessen wir uns auf sentiment verlassen oder main.py anpassen.
        # Die Methode signature in main.py ist update_from_sentiment(sentiment).
        # Wir koennen update_from_input(text) hinzufuegen, aber update_from_sentiment reicht vorerst.

        
        if sentiment == "POSITIV":
            self.state.happiness += 5
            self.state.trust += 2
            self.state.energy += 1
            self.state.motivation += 5
            self.state.frustration -= 5
        elif sentiment == "NEGATIV":
            self.state.happiness -= 8
            self.state.trust -= 3
            self.state.energy -= 2
            self.state.motivation -= 5
            self.state.frustration += 10
        elif sentiment == "FRUSTRIERT":
             self.state.frustration += 15
             self.state.happiness -= 5
        elif sentiment == "NEUGIERIG":
             self.state.curiosity += 10
             self.state.motivation += 2
        else:  # NEUTRAL
            # Leichte Regression zur Mitte
            if self.state.happiness < 50:
                self.state.happiness += 1
            elif self.state.happiness > 50:
                self.state.happiness -= 1
                
            self.state.frustration -= 2 # Frustration baut sich ab
        
        # Energie sinkt mit jeder Interaktion leicht
        self.state.energy -= 1
        
        self.state.clamp()
        self._save_state()
        
        if settings.debug:
            print(f"Emotions Update: {sentiment} -> H={self.state.happiness} T={self.state.trust} E={self.state.energy}")
    
    def restore_energy(self, amount: int = 30):
        """
        Stellt Energie wieder her (z.B. nach Traum-Phase).
        
        Args:
            amount: Menge der wiederherzustellenden Energie
        """
        self.state.energy += amount
        self.state.clamp()
        self._save_state()
    
    def get_prompt_injection(self) -> str:
        """
        Generiert den Emotions-Kontext fuer den System-Prompt.
        
        Returns:
            Formatierter String mit aktuellem Status
        """
        from config.prompts import EMOTION_STATUS_TEMPLATE
        
        return EMOTION_STATUS_TEMPLATE.format(
            happiness=self.state.happiness,
            trust=self.state.trust,
            energy=self.state.energy,
            curiosity=self.state.curiosity,
            frustration=self.state.frustration,
            motivation=self.state.motivation
        )
    
    def get_state(self) -> EmotionalState:
        """Gibt den aktuellen Zustand zurueck."""
        return self.state
    
    def reset(self):
        """Setzt den emotionalen Zustand zurueck."""
        self.state = EmotionalState()
        self._save_state()
        print("Emotionaler Zustand zurueckgesetzt")


def analyze_sentiment_simple(text: str) -> str:
    """
    Einfache regelbasierte Sentiment-Analyse.
    
    Fuer komplexere Analyse kann ein LLM verwendet werden.
    
    Args:
        text: Der zu analysierende Text
    
    Returns:
        "POSITIV", "NEGATIV" oder "NEUTRAL"
    """
    text_lower = text.lower()
    
    # Positive Woerter
    positive_words = [
        "danke", "super", "toll", "klasse", "prima", "perfekt", "wunderbar",
        "ausgezeichnet", "fantastisch", "liebe", "lieb", "gut", "richtig",
        "hilft", "hilfreich", "freue", "freut", "mag", "gerne", "cool",
        "genial", "stark", "nice", "top", "hammer", "geil", "brav"
    ]
    
    # Negative Woerter
    negative_words = [
        "schlecht", "falsch", "dumm", "bloed", "idiot", "nervig", "nervt",
        "hasse", "hass", "aerger", "wut", "scheisse", "mist", "kacke",
        "langweilig", "nutzlos", "falsch", "fehler", "nein", "nicht",
        "stop", "halt", "weg", "verschwinde", "still", "ruhe"
    ]
    
    # Neugier Woerter
    curious_words = ["warum", "wieso", "weshalb", "wie", "erklaer", "erzaehl", "interessant", "spannend"]
    
    # Frust Woerter
    frust_words = ["nervt", "mist", "scheisse", "klappt nicht", "fehler", "kaputt", "bloed"]

    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)
    curious_count = sum(1 for word in curious_words if word in text_lower)
    frust_count = sum(1 for word in frust_words if word in text_lower)

    if frust_count > 0:
        return "FRUSTRIERT"
    elif curious_count > 0 and "?" in text:
        return "NEUGIERIG"
    elif positive_count > negative_count:
        return "POSITIV"
    elif negative_count > positive_count:
        return "NEGATIV"
    else:
        return "NEUTRAL"


# === Test ===
if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    console.print("[bold]Emotions Engine Test[/bold]\n")
    
    engine = EmotionsEngine()
    
    # Zeige aktuellen Status
    table = Table(title="Emotionaler Zustand")
    table.add_column("Metrik", style="cyan")
    table.add_column("Wert", style="green")
    
    table.add_row("Happiness", str(engine.state.happiness))
    table.add_row("Trust", str(engine.state.trust))
    table.add_row("Energy", str(engine.state.energy))
    console.print(table)
    
    console.print(f"\n{engine.state.get_mood_description()}")
    
    # Test Sentiment-Analyse
    console.print("\n[cyan]Sentiment-Analyse Test:[/cyan]")
    test_messages = [
        "Danke, das war super hilfreich!",
        "Das ist falsch du Idiot",
        "Kannst du mir helfen?",
    ]
    
    for msg in test_messages:
        sentiment = analyze_sentiment_simple(msg)
        console.print(f"   '{msg[:30]}...' -> {sentiment}")
