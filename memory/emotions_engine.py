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
- sadness: Traurigkeit (0-100)
- affection: Zuneigung (0-100)
- anxiety: Unruhe (0-100, niedrig ist gut)
- calm: Ruhe (0-100)
"""

import json
import math
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

from config.config import PROJECT_ROOT, settings
from config.emotions import EMOTION_DEFAULTS, EMOTION_ORDER, clamp_emotion_value, normalize_emotion_state
from config.prompts import EMOTION_ANALYSIS_PROMPT  # from config/prompts.py


# Status-Datei Pfad
STATUS_FILE = PROJECT_ROOT / "data" / "status.json"

DEFAULT_EMOTION_TRANSITION_RULE = {"scale": 0.55, "max_increase": 8, "max_decrease": 8}
EMOTION_TRANSITION_RULES = {
    "happiness": {"scale": 0.55, "max_increase": 8, "max_decrease": 8},
    "trust": {"scale": 0.55, "max_increase": 7, "max_decrease": 8},
    "energy": {"scale": 0.50, "max_increase": 6, "max_decrease": 7},
    "curiosity": {"scale": 0.55, "max_increase": 6, "max_decrease": 6},
    "frustration": {"scale": 0.50, "max_increase": 7, "max_decrease": 7},
    "motivation": {"scale": 0.55, "max_increase": 7, "max_decrease": 7},
    "sadness": {"scale": 0.50, "max_increase": 7, "max_decrease": 7},
    "affection": {"scale": 0.50, "max_increase": 6, "max_decrease": 7},
    "anxiety": {"scale": 0.45, "max_increase": 6, "max_decrease": 7},
    "calm": {"scale": 0.45, "max_increase": 6, "max_decrease": 6},
}


def _clamp_emotion_value(value: int) -> int:
    return clamp_emotion_value(value)


def calculate_emotion_transition(emotion: str, current_value: int, raw_delta: int | float) -> Dict[str, Any]:
    """Glaettet starke Emotionsspruenge pro Turn und liefert Debug-Metadaten."""
    rule = EMOTION_TRANSITION_RULES.get(emotion, DEFAULT_EMOTION_TRANSITION_RULE)

    try:
        raw_value = int(round(float(raw_delta)))
    except Exception:
        raw_value = 0

    if raw_value == 0:
        applied_delta = 0
        softened = False
        limit = 0
    elif abs(raw_value) <= 2:
        applied_delta = raw_value
        softened = False
        limit = abs(raw_value)
    else:
        limit = rule["max_increase"] if raw_value > 0 else rule["max_decrease"]
        scaled = max(1, int(math.ceil(abs(raw_value) * rule["scale"])))
        applied_delta = min(limit, scaled)
        if raw_value < 0:
            applied_delta *= -1
        softened = applied_delta != raw_value

    after = _clamp_emotion_value(current_value + applied_delta)
    clamped_delta = after - current_value

    return {
        "before": _clamp_emotion_value(current_value),
        "after": after,
        "raw_delta": raw_value,
        "applied_delta": clamped_delta,
        "change": clamped_delta,
        "softened": softened or clamped_delta != applied_delta,
        "limit": limit,
        "scale": rule["scale"],
    }


def apply_emotion_delta(state: "EmotionalState", emotion: str, raw_delta: int | float) -> Dict[str, Any]:
    """Wendet ein geglaettetes Delta auf einen EmotionalState an."""
    if not hasattr(state, emotion):
        return calculate_emotion_transition(emotion, 50, 0)

    before = getattr(state, emotion)
    transition = calculate_emotion_transition(emotion, before, raw_delta)
    setattr(state, emotion, transition["after"])
    return transition


@dataclass
class EmotionalState:
    """Repraesentiert den emotionalen Zustand von CHAPiE."""
    happiness: int = 50
    trust: int = 50
    energy: int = 100
    curiosity: int = 50    # Neugier
    frustration: int = 0   # Frustration (niedrig ist gut)
    motivation: int = 80   # Motivation
    sadness: int = 0       # Traurigkeit
    affection: int = 45    # Zuneigung
    anxiety: int = 0       # Unruhe (niedrig ist gut)
    calm: int = 50         # Ruhe

    def clamp(self):
        """Begrenzt alle Werte auf 0-100."""
        for key in EMOTION_ORDER:
            setattr(self, key, clamp_emotion_value(getattr(self, key), EMOTION_DEFAULTS[key]))
    
    def to_dict(self) -> dict:
        """Konvertiert zu Dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "EmotionalState":
        """Erstellt aus Dictionary."""
        return cls(**normalize_emotion_state(data))
    
    def get_mood_description(self) -> str:
        """Gibt eine textuelle Beschreibung der Stimmung zurueck."""
        if self.sadness >= 70:
            mood = "sehr traurig und bedrückt"
        elif self.sadness >= 40:
            mood = "etwas wehmütig"
        elif self.happiness >= 70:
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
        self._last_state_mtime_ns: int | None = None
        self.state = self._load_state()
        
        # Brain einmal beim ersten Init laden (lazy loading)
        if not EmotionsEngine._brain_initialized:
            self._init_ollama_brain()
        
        print(f"Emotions Engine geladen: H={self.state.happiness} T={self.state.trust} E={self.state.energy}")

    def _status_mtime_ns(self) -> int | None:
        try:
            return STATUS_FILE.stat().st_mtime_ns
        except OSError:
            return None

    def _read_state_from_disk(self) -> EmotionalState | None:
        if not STATUS_FILE.exists():
            self._last_state_mtime_ns = None
            return None
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._last_state_mtime_ns = self._status_mtime_ns()
            return EmotionalState.from_dict(data)
        except Exception as e:
            print(f"Fehler beim Laden des Status: {e}")
            return None

    def _sync_state_from_disk_if_newer(self, force: bool = False) -> EmotionalState:
        current_mtime_ns = self._status_mtime_ns()
        if current_mtime_ns is None:
            return self.state
        if force or self._last_state_mtime_ns is None or current_mtime_ns > self._last_state_mtime_ns:
            refreshed = self._read_state_from_disk()
            if refreshed is not None:
                self.state = refreshed
        return self.state
    
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
        loaded = self._read_state_from_disk()
        if loaded is not None:
            return loaded

        return EmotionalState()
    
    def _save_state(self):
        """Speichert den Status in die Datei."""
        STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(STATUS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.state.to_dict(), f, indent=2)
            self._last_state_mtime_ns = self._status_mtime_ns()
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
                current_motivation=self.state.motivation,
                current_sadness=self.state.sadness,
                current_affection=self.state.affection,
                current_anxiety=self.state.anxiety,
                current_calm=self.state.calm,
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
        self._sync_state_from_disk_if_newer()

        # Versuche LLM-Analyse
        llm_result = self._analyze_with_llm(user_message)
        
        if llm_result:
            # LLM-basierte Aenderungen anwenden
            llm_changes = {key: llm_result.get(f"{key}_change", 0) for key in EMOTION_ORDER}
            llm_changes["energy"] = llm_result.get("energy_change", -1)
            for emotion_name, raw_delta in llm_changes.items():
                apply_emotion_delta(self.state, emotion_name, raw_delta)
            
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
        changes = {
            **{key: 0 for key in EMOTION_ORDER},
            "energy": -1,
        }

        if sentiment == "POSITIV":
            changes["happiness"] = 3
            changes["trust"] = 1
            changes["motivation"] = 2
            changes["frustration"] = -3
            changes["affection"] = 2
            changes["calm"] = 1
            changes["anxiety"] = -2
        elif sentiment == "NEGATIV":
            changes["happiness"] = -5
            changes["frustration"] = 8
            changes["anxiety"] = 3
            changes["calm"] = -2
        elif sentiment == "NEUGIERIG":
            changes["curiosity"] = 8
            changes["motivation"] = 2
        elif sentiment == "VERTRAUEN":
            changes["trust"] = 10
            changes["happiness"] = 3
            changes["affection"] = 4
            changes["calm"] = 2
        else:  # NEUTRAL
            changes["frustration"] = -1
            changes["anxiety"] = -1

        for emotion_name, raw_delta in changes.items():
            apply_emotion_delta(self.state, emotion_name, raw_delta)
    
    def update_from_sentiment(self, sentiment: str):
        """
        Legacy-Methode fuer Rueckwaertskompatibilitaet.
        Verwendet intern _apply_simple_sentiment.
        """
        self._sync_state_from_disk_if_newer()
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
        self._sync_state_from_disk_if_newer()
        self.state.energy += amount
        self.state.clamp()
        self._save_state()
    
    def get_prompt_injection(self) -> str:
        """
        Generiert den Emotions-Kontext fuer den System-Prompt.
        
        Returns:
            Formatierter String mit aktuellem Status
        """
        self._sync_state_from_disk_if_newer()
        from config.prompts import EMOTION_STATUS_TEMPLATE  # from config/prompts.py
        
        return EMOTION_STATUS_TEMPLATE.format(
            **self.state.to_dict()
        )
    
    def get_state(self) -> EmotionalState:
        """Gibt den aktuellen Zustand zurueck."""
        self._sync_state_from_disk_if_newer()
        return self.state
    
    def set_emotion(self, emotion: str, value: int):
        """
        Setzt eine einzelne Emotion auf einen bestimmten Wert.
        
        Args:
            emotion: Name der Emotion (siehe config.emotions.EMOTION_ORDER)
            value: Neuer Wert (0-100)
        """
        self._sync_state_from_disk_if_newer()
        value = clamp_emotion_value(value)

        if emotion in EMOTION_DEFAULTS:
            setattr(self.state, emotion, value)
        
        self._save_state()
    
    def reset(self):
        """Setzt den emotionalen Zustand zurueck."""
        self._sync_state_from_disk_if_newer()
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
    table.add_row("Sadness", str(engine.state.sadness))
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
