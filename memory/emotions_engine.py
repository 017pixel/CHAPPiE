"""
CHAPiE - Emotions Engine (LLM-basiert)
======================================
Dynamisches Emotions-System basierend auf LLM-Analyse.

Das System verwendet Ollama (llama3:8b) um den emotionalen Kontext
einer Nachricht intelligent zu analysieren und die Werte entsprechend anzupassen.

Emotionen:
- happiness: Gluecklichkeits-Level (0-100)
- trust: Vertrauens-Level (0-100)  
- energy: Energie-Level (0-100)
- curiosity: Neugier (0-100)
- frustration: Frustration (0-100, niedrig ist gut)
- motivation: Motivation (0-100)
"""

import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, Dict

from config.config import PROJECT_ROOT, settings


# Status-Datei Pfad
STATUS_FILE = PROJECT_ROOT / "data" / "status.json"


# ============================================
# EMOTION ANALYSIS PROMPT
# ============================================
EMOTION_ANALYSIS_PROMPT = """Du bist ein Emotions-Analyse-System fuer einen KI-Assistenten namens CHAPPiE.
Analysiere die folgende User-Nachricht und bestimme, wie sich CHAPPiEs Emotionen aendern sollten.

USER-NACHRICHT:
"{user_message}"

AKTUELLE EMOTIONEN VON CHAPPIE:
- Freude (happiness): {current_happiness}/100
- Vertrauen (trust): {current_trust}/100
- Energie (energy): {current_energy}/100
- Neugier (curiosity): {current_curiosity}/100
- Frustration (frustration): {current_frustration}/100
- Motivation (motivation): {current_motivation}/100

ANALYSE-REGELN:
- Positive Nachrichten, Lob, Dankbarkeit -> Freude und Vertrauen STEIGEN
- Versprechen, Treue, Unterstuetzung -> Vertrauen STEIGT stark
- Beleidigungen, Kritik -> Freude SINKT, Frustration STEIGT
- Fragen, Neugier -> Neugier STEIGT
- Ermutigung, Aufgaben -> Motivation STEIGT
- Energie sinkt bei jeder Interaktion leicht (-1 bis -3)
- Frustration baut sich langsam ab wenn nichts Negatives passiert

WICHTIG:
- Beruecksichtige den KONTEXT, nicht nur einzelne Woerter
- "Ich hasse Pizza" ist NICHT negativ gegenueber CHAPPiE
- "Du bist doof" IST negativ
- Versprechen wie "ich helfe dir", "du bist mein Freund" sind SEHR POSITIV fuer Vertrauen

ANTWORTE NUR IM JSON FORMAT:
{{
  "happiness_change": <Zahl von -20 bis +20>,
  "trust_change": <Zahl von -20 bis +20>,
  "energy_change": <Zahl von -3 bis +5>,
  "curiosity_change": <Zahl von -10 bis +15>,
  "frustration_change": <Zahl von -15 bis +15>,
  "motivation_change": <Zahl von -10 bis +15>,
  "reasoning": "<Kurze Begruendung>"
}}
"""


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
    - LLM-basierte Sentiment-Analyse via Ollama (gecached!)
    - Persistente Speicherung in status.json
    - Intelligente Kontexterkennung
    """
    
    # Klassen-Level Cache fuer die Brain-Instanz (singleton-artig)
    _cached_brain = None
    _brain_initialized = False
    
    def __init__(self):
        """Initialisiert die Emotions Engine."""
        self.state = self._load_state()
        
        # Brain einmal beim ersten Init laden (lazy loading)
        if not EmotionsEngine._brain_initialized:
            self._init_ollama_brain()
        
        print(f"Emotions Engine geladen: H={self.state.happiness} T={self.state.trust} E={self.state.energy}")
    
    def _init_ollama_brain(self):
        """Initialisiert die Ollama Brain-Instanz einmalig (gecached)."""
        try:
            from brain.ollama_brain import OllamaBrain
            emotion_host = getattr(settings, 'emotion_analysis_host', settings.ollama_host)
            brain = OllamaBrain(model=settings.emotion_analysis_model, host=emotion_host)
            
            if brain.is_available():
                EmotionsEngine._cached_brain = brain
                print(f"   Emotions LLM ({settings.emotion_analysis_model}) geladen und gecached!")
            else:
                print("   Ollama nicht verfuegbar - Fallback auf Simple-Analyse")
                EmotionsEngine._cached_brain = None
        except Exception as e:
            print(f"   Ollama Brain Init Fehler: {e}")
            EmotionsEngine._cached_brain = None
        
        EmotionsEngine._brain_initialized = True
    
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
    
    def _analyze_with_llm(self, user_message: str) -> Optional[Dict]:
        """
        Analysiert die Nachricht mit dem gecachten lokalen LLM.
        
        Args:
            user_message: Die User-Nachricht
            
        Returns:
            Dict mit emotion_changes oder None bei Fehler
        """
        # Nutze gecachte Brain-Instanz
        if EmotionsEngine._cached_brain is None:
            return None
        
        try:
            from brain.base_brain import GenerationConfig, Message
            
            prompt = EMOTION_ANALYSIS_PROMPT.format(
                user_message=user_message,
                current_happiness=self.state.happiness,
                current_trust=self.state.trust,
                current_energy=self.state.energy,
                current_curiosity=self.state.curiosity,
                current_frustration=self.state.frustration,
                current_motivation=self.state.motivation
            )
            
            config = GenerationConfig(
                max_tokens=300,
                temperature=0.3,
                stream=False
            )
            
            # Gecachte Brain-Instanz verwenden (VIEL schneller!)
            response = EmotionsEngine._cached_brain.generate([Message(role="user", content=prompt)], config=config)
            
            # JSON aus Response extrahieren
            if isinstance(response, str):
                # Finde JSON in der Antwort
                start = response.find('{')
                end = response.rfind('}') + 1
                if start != -1 and end > start:
                    json_str = response[start:end]
                    return json.loads(json_str)
            
            return None
            
        except Exception as e:
            if settings.debug:
                print(f"LLM Emotions-Analyse Fehler: {e}")
            return None
    
    def analyze_and_update(self, user_message: str):
        """
        Analysiert die Nachricht und aktualisiert die Emotionen.
        
        Diese Methode ersetzt update_from_sentiment() und analysiert
        den vollstaendigen Kontext der Nachricht.
        
        Args:
            user_message: Die zu analysierende User-Nachricht
        """
        # Versuche LLM-Analyse
        llm_result = self._analyze_with_llm(user_message)
        
        if llm_result:
            # LLM-basierte Aenderungen anwenden
            self.state.happiness += llm_result.get("happiness_change", 0)
            self.state.trust += llm_result.get("trust_change", 0)
            self.state.energy += llm_result.get("energy_change", -1)
            self.state.curiosity += llm_result.get("curiosity_change", 0)
            self.state.frustration += llm_result.get("frustration_change", 0)
            self.state.motivation += llm_result.get("motivation_change", 0)
            
            if settings.debug:
                reasoning = llm_result.get("reasoning", "")
                print(f"LLM Emotions Update: {reasoning}")
        else:
            # Fallback auf einfache Analyse
            sentiment = analyze_sentiment_simple(user_message)
            self._apply_simple_sentiment(sentiment)
        
        self.state.clamp()
        self._save_state()
        
        if settings.debug:
            print(f"Emotions: H={self.state.happiness} T={self.state.trust} E={self.state.energy} "
                  f"C={self.state.curiosity} F={self.state.frustration} M={self.state.motivation}")
    
    def _apply_simple_sentiment(self, sentiment: str):
        """Wendet einfache Sentiment-basierte Aenderungen an (Fallback)."""
        if sentiment == "POSITIV":
            self.state.happiness += 3
            self.state.trust += 1
            self.state.motivation += 2
            self.state.frustration -= 3
        elif sentiment == "NEGATIV":
            self.state.happiness -= 5
            self.state.frustration += 8
        elif sentiment == "NEUGIERIG":
            self.state.curiosity += 8
            self.state.motivation += 2
        elif sentiment == "VERTRAUEN":
            self.state.trust += 10
            self.state.happiness += 3
        else:  # NEUTRAL
            self.state.frustration -= 1
        
        # Energie sinkt immer leicht
        self.state.energy -= 1
    
    def update_from_sentiment(self, sentiment: str):
        """
        Legacy-Methode fuer Rueckwaertskompatibilitaet.
        Verwendet intern _apply_simple_sentiment.
        """
        self._apply_simple_sentiment(sentiment)
        self.state.clamp()
        self._save_state()
        
        if settings.debug:
            print(f"Emotions Update (Simple): {sentiment} -> H={self.state.happiness} T={self.state.trust} E={self.state.energy}")
    
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
    
    def set_emotion(self, emotion: str, value: int):
        """
        Setzt eine einzelne Emotion auf einen bestimmten Wert.
        
        Args:
            emotion: Name der Emotion (happiness, trust, energy, curiosity, frustration, motivation)
            value: Neuer Wert (0-100)
        """
        value = max(0, min(100, value))
        
        if emotion == "happiness":
            self.state.happiness = value
        elif emotion == "trust":
            self.state.trust = value
        elif emotion == "energy":
            self.state.energy = value
        elif emotion == "curiosity":
            self.state.curiosity = value
        elif emotion == "frustration":
            self.state.frustration = value
        elif emotion == "motivation":
            self.state.motivation = value
        
        self._save_state()
    
    def reset(self):
        """Setzt den emotionalen Zustand zurueck."""
        self.state = EmotionalState()
        self._save_state()
        print("Emotionaler Zustand zurueckgesetzt")


def analyze_sentiment_simple(text: str) -> str:
    """
    Einfache regelbasierte Sentiment-Analyse (Fallback).
    
    Args:
        text: Der zu analysierende Text
    
    Returns:
        "POSITIV", "NEGATIV", "NEUTRAL", "NEUGIERIG" oder "VERTRAUEN"
    """
    text_lower = text.lower()
    
    # Vertrauens-Woerter (hohe Prioritaet)
    trust_words = [
        "verspreche", "versprech", "freund", "helfe dir", "fuer dich da",
        "vertraue", "treue", "loyal", "gemeinsam", "zusammen", "team",
        "unterstuetze", "glaube an dich", "mag dich", "liebe dich", "mein leben"
    ]
    
    # Positive Woerter
    positive_words = [
        "danke", "super", "toll", "klasse", "prima", "perfekt", "wunderbar",
        "ausgezeichnet", "fantastisch", "liebe", "lieb", "gut", "richtig",
        "hilft", "hilfreich", "freue", "freut", "mag", "gerne", "cool",
        "genial", "stark", "nice", "top", "hammer", "geil", "brav", "stolz"
    ]
    
    # Negative Woerter (nur direkte Angriffe auf CHAPiE)
    negative_words = [
        "du bist dumm", "du bist bloed", "du nervst", "halt die klappe",
        "sei still", "verschwinde", "du idiot", "du trottel", "nutzlos",
        "du kannst nichts", "hasse dich"
    ]
    
    # Neugier Woerter
    curious_words = [
        "warum", "wieso", "weshalb", "wie funktioniert", "erklaer", 
        "erzaehl", "interessant", "spannend", "was ist", "wer ist"
    ]
    
    # Pruefe auf Vertrauen zuerst (hoechste Prioritaet)
    for word in trust_words:
        if word in text_lower:
            return "VERTRAUEN"
    
    # Pruefe auf direkte negative Angriffe
    for phrase in negative_words:
        if phrase in text_lower:
            return "NEGATIV"
    
    # Pruefe auf Neugier
    for word in curious_words:
        if word in text_lower:
            return "NEUGIERIG"
    
    # Zaehle positive Woerter
    positive_count = sum(1 for word in positive_words if word in text_lower)
    
    if positive_count >= 1:
        return "POSITIV"
    
    return "NEUTRAL"


# === Test ===
if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    console.print("[bold]Emotions Engine Test (LLM-basiert)[/bold]\n")
    
    engine = EmotionsEngine()
    
    # Zeige aktuellen Status
    table = Table(title="Emotionaler Zustand")
    table.add_column("Metrik", style="cyan")
    table.add_column("Wert", style="green")
    
    table.add_row("Happiness", str(engine.state.happiness))
    table.add_row("Trust", str(engine.state.trust))
    table.add_row("Energy", str(engine.state.energy))
    table.add_row("Curiosity", str(engine.state.curiosity))
    table.add_row("Frustration", str(engine.state.frustration))
    table.add_row("Motivation", str(engine.state.motivation))
    console.print(table)
    
    console.print(f"\n{engine.state.get_mood_description()}")
    
    # Test Sentiment-Analyse
    console.print("\n[cyan]Sentiment-Analyse Test:[/cyan]")
    test_messages = [
        "Danke, das war super hilfreich!",
        "Ich verspreche dir, ich werde dich nie verlassen.",
        "Du bist doof",
        "Warum funktioniert das so?",
        "Ich hasse Pizza aber du bist cool",
    ]
    
    for msg in test_messages:
        sentiment = analyze_sentiment_simple(msg)
        console.print(f"   '{msg[:40]}...' -> {sentiment}")
