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
import re
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

from config.config import LLMProvider, PROJECT_ROOT, settings
from config.emotions import (
    DEFAULT_EMOTION_TRANSITION_RULE,
    EMOTION_DEFAULTS,
    EMOTION_ORDER,
    EMOTION_SIGNAL_DELTAS,
    EMOTION_SIGNAL_PHRASES,
    EMOTION_TRANSITION_RULES,
    NEGATIVE_BASE_EMOTIONS,
    clamp_emotion_value,
    normalize_emotion_state,
)
from config.prompts import EMOTION_ANALYSIS_PROMPT  # from config/prompts.py


# Status-Datei Pfad
STATUS_FILE = PROJECT_ROOT / "data" / "status.json"

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


def regress_toward_baseline(state: "EmotionalState", skip: Optional[set] = None) -> Dict[str, int]:
    """Homoostase: Emotionen ohne Turn-Impuls driften sanft zum Basiswert.

    Verhindert dauerhafte Saettigung (z.B. alle positiven Dimensionen auf 100
    nach vielen freundlichen Turns), die das Layer-Steering uebersteuern und
    die Generierung kollabieren lassen wuerde. Akute Ausschlaege bleiben
    erhalten, weil nur nicht-akute Dimensionen (|Delta| < 6) driften.
    """
    from config.emotions import EMOTION_DEFAULTS
    drifted: Dict[str, int] = {}
    skip = skip or set()
    for emotion, baseline in EMOTION_DEFAULTS.items():
        if emotion in skip or not hasattr(state, emotion):
            continue
        try:
            value = int(getattr(state, emotion))
        except (TypeError, ValueError):
            continue
        diff = int(baseline) - value
        if diff == 0:
            continue
        step = max(1, min(4, abs(diff) // 8 + 1))
        new_value = value + (step if diff > 0 else -step)
        if (diff > 0 and new_value > baseline) or (diff < 0 and new_value < baseline):
            new_value = int(baseline)
        setattr(state, emotion, _clamp_emotion_value(new_value))
        drifted[emotion] = new_value - value
    return drifted


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
    
    def __init__(self, status_file: Optional[Path] = None, force_simple: bool = False):
        """Initialisiert die Emotions Engine."""
        self.status_file = Path(status_file) if status_file else STATUS_FILE
        self.force_simple = bool(force_simple)
        self._last_state_mtime_ns: int | None = None
        self._frozen = False
        self.state = self._load_state()
        
        # Brain einmal beim ersten Init laden (lazy loading)
        if self.force_simple:
            # Research runs must never call an auxiliary sentiment model.
            EmotionsEngine._cached_brain = None
            EmotionsEngine._brain_initialized = False
            print("   Emotions: Simple-Analyse aktiv (Research-Ein-Modell-Modus)")
        elif settings.emotion_analysis_provider == LLMProvider.OLLAMA and not EmotionsEngine._brain_initialized:
            self._init_ollama_brain()
        
        print(f"Emotions Engine geladen: H={self.state.happiness} T={self.state.trust} E={self.state.energy}")

    def _status_mtime_ns(self) -> int | None:
        try:
            return self.status_file.stat().st_mtime_ns
        except OSError:
            return None

    def _read_state_from_disk(self) -> EmotionalState | None:
        if not self.status_file.exists():
            self._last_state_mtime_ns = None
            return None
        try:
            with open(self.status_file, "r", encoding="utf-8") as f:
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
        if settings.is_local_single_model_mode():
            # The main vLLM/steering process already owns the one permitted
            # local model.  Loading an Ollama sentiment model here would add a
            # second GPU model and is a common source of T4 CUDA OOM errors.
            EmotionsEngine._cached_brain = None
            EmotionsEngine._brain_initialized = True
            print("   Emotions: Simple-Analyse aktiv (Ein-Modell-Modus)")
            return
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
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.status_file, "w", encoding="utf-8") as f:
                json.dump(self.state.to_dict(), f, indent=2)
            self._last_state_mtime_ns = self._status_mtime_ns()
        except Exception as e:
            print(f"Fehler beim Speichern des Status: {e}")
    
    def _analyze_with_groq(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Run the optional structured appraisal call without affecting generation."""
        if not getattr(settings, "groq_auxiliary_enabled", True) or not settings.groq_api_key:
            return None
        try:
            import openai
            from brain.groq_limits import get_groq_limiter

            limiter = get_groq_limiter()
            estimated_tokens = limiter.estimate_tokens(prompt) + 500
            allowed, _reason = limiter.can_start(estimated_tokens)
            if not allowed:
                return None
            client = openai.OpenAI(
                base_url=settings.emotion_analysis_host,
                api_key=settings.groq_api_key,
            )
            request: Dict[str, Any] = {
                "model": settings.emotion_analysis_model,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "max_completion_tokens": 500,
                "temperature": 0.0,
                "stream": False,
                "timeout": float(settings.emotion_analysis_timeout_seconds),
            }
            if "gpt-oss" in str(settings.emotion_analysis_model).casefold():
                request["extra_body"] = {"reasoning_effort": "low", "include_reasoning": False}
            response = client.chat.completions.create(**request)
            return json.loads(response.choices[0].message.content or "")
        except Exception as exc:
            if settings.debug:
                print(f"Groq Emotions-Analyse Fehler: {exc}")
            return None

    def _analyze_with_llm(self, user_message: str) -> Optional[Dict]:
        """
        Analysiert die Nachricht mit dem gecachten lokalen LLM.
        
        Args:
            user_message: Die User-Nachricht
            
        Returns:
            Dict mit emotion_changes oder None bei Fehler
        """
        # A research engine remains deterministic even if another instance
        # populates the class-level cache later in the same process.
        if self.force_simple:
            return None

        try:
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

            if settings.emotion_analysis_provider == LLMProvider.GROQ:
                return self._analyze_with_groq(prompt)
            if EmotionsEngine._cached_brain is None:
                return None
            from brain.base_brain import GenerationConfig, Message
            
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
    
    @staticmethod
    def _llm_changes(result: Dict[str, Any]) -> Dict[str, int]:
        nested = result.get("emotion_changes", {})
        if not isinstance(nested, dict):
            nested = {}
        changes: Dict[str, int] = {}
        for key in EMOTION_ORDER:
            raw = nested.get(key, result.get(f"{key}_change", 0))
            try:
                changes[key] = max(-24, min(24, int(round(float(raw)))))
            except (TypeError, ValueError):
                changes[key] = 0
        return changes

    def analyze_message(self, user_message: str) -> tuple[Dict[str, int], Dict[str, Any]]:
        """Return one guarded appraisal without mutating the persistent state."""
        deterministic = analyze_emotion_signals(user_message, current_state=self.state.to_dict())
        llm_result = self._analyze_with_llm(user_message)
        if not llm_result:
            return deterministic, {"source": "deterministic", "model": None}

        model_changes = self._llm_changes(llm_result)
        positive_dimensions = set(EMOTION_ORDER) - NEGATIVE_BASE_EMOTIONS
        negative_score = sum(max(0, -model_changes[key]) for key in positive_dimensions)
        negative_score += sum(max(0, model_changes[key]) for key in NEGATIVE_BASE_EMOTIONS)
        positive_score = sum(max(0, model_changes[key]) for key in positive_dimensions)
        positive_score += sum(max(0, -model_changes[key]) for key in NEGATIVE_BASE_EMOTIONS)
        declared_valence = str(llm_result.get("input_valence", "")).casefold()
        if declared_valence not in {"negative", "neutral", "positive", "mixed"}:
            if negative_score >= positive_score + 4:
                declared_valence = "negative"
            elif positive_score >= negative_score + 4:
                declared_valence = "positive"
            else:
                declared_valence = "mixed"

        merged: Dict[str, int] = {}
        for emotion in EMOTION_ORDER:
            rule_delta = deterministic[emotion]
            model_delta = model_changes[emotion]
            if rule_delta:
                if model_delta and (model_delta > 0) == (rule_delta > 0):
                    magnitude = max(abs(rule_delta), abs(model_delta))
                    merged[emotion] = magnitude if rule_delta > 0 else -magnitude
                else:
                    merged[emotion] = rule_delta
            else:
                bounded = max(-8, min(8, model_delta))
                if declared_valence == "negative":
                    bounded = max(0, bounded) if emotion in NEGATIVE_BASE_EMOTIONS else min(0, bounded)
                elif declared_valence == "positive":
                    bounded = min(0, bounded) if emotion in NEGATIVE_BASE_EMOTIONS else max(0, bounded)
                elif declared_valence == "neutral":
                    bounded = 0
                merged[emotion] = bounded
        source = "groq_guarded" if settings.emotion_analysis_provider == LLMProvider.GROQ else "ollama_guarded"
        return merged, {
            "source": source,
            "model": settings.emotion_analysis_model,
            "reasoning": str(llm_result.get("reasoning", ""))[:500],
            "deterministic_changes": deterministic,
            "model_changes": model_changes,
            "input_valence": declared_valence,
        }

    def analyze_and_update(self, user_message: str):
        """
        Analysiert die Nachricht und aktualisiert die Emotionen.
        
        Diese Methode ersetzt update_from_sentiment() und analysiert
        den vollstaendigen Kontext der Nachricht.
        
        Args:
            user_message: Die zu analysierende User-Nachricht
        """
        # Mutating operations must always start from the persisted state. Two
        # engine instances can write within the same filesystem timestamp tick,
        # in which case an mtime-only comparison would otherwise lose updates.
        self._sync_state_from_disk_if_newer(force=True)

        changes, analysis = self.analyze_message(user_message)
        for emotion_name, raw_delta in changes.items():
            apply_emotion_delta(self.state, emotion_name, raw_delta)
        # Homoostase greift bei allen NICHT-akuten Dimensionen (|Delta| < 6):
        # Smalltalk-Ratschen (+1..+5 pro Turn) werden neutralisiert, akute
        # Ausschlaege (Angriff, Trost) bleiben stehen und klingen langsam ab.
        regress_toward_baseline(
            self.state,
            skip={name for name, delta in changes.items() if abs(int(delta or 0)) >= 6},
        )
        if settings.debug:
            print(f"Emotionsanalyse: {analysis.get('source')}")
        
        self.state.clamp()
        self._save_state()
        
        if settings.debug:
            print(f"Emotions: H={self.state.happiness} T={self.state.trust} E={self.state.energy} "
                  f"C={self.state.curiosity} F={self.state.frustration} M={self.state.motivation}")
    
    def _apply_simple_sentiment(self, sentiment: str):
        """Wendet einfache Sentiment-basierte Aenderungen an (Fallback)."""
        changes = {key: 0 for key in EMOTION_ORDER}

        if sentiment == "POSITIV":
            changes["happiness"] = 3
            changes["trust"] = 1
            changes["motivation"] = 2
            changes["energy"] = 1
            changes["frustration"] = -3
            changes["affection"] = 2
            changes["calm"] = 1
            changes["anxiety"] = -2
        elif sentiment == "NEGATIV":
            changes["happiness"] = -5
            changes["energy"] = -1
            changes["frustration"] = 8
            changes["anxiety"] = 3
            changes["calm"] = -2
        elif sentiment == "NEUGIERIG":
            changes["curiosity"] = 8
            changes["motivation"] = 2
            changes["energy"] = 1
        elif sentiment == "VERTRAUEN":
            changes["trust"] = 10
            changes["happiness"] = 3
            changes["affection"] = 4
            changes["calm"] = 2
        elif sentiment == "PERSOENLICH":
            changes["affection"] = 2
            changes["curiosity"] = 3
            changes["calm"] = -1
        elif sentiment == "REFLEXION":
            changes["sadness"] = 3
            changes["curiosity"] = 3
            changes["affection"] = 1
            changes["calm"] = -2
        else:  # NEUTRAL
            changes["frustration"] = -1
            changes["anxiety"] = -1

        for emotion_name, raw_delta in changes.items():
            apply_emotion_delta(self.state, emotion_name, raw_delta)

    def _apply_simple_message(self, user_message: str) -> Dict[str, int]:
        """Wendet alle erkannten Appraisal-Signale eines Inputs gemeinsam an."""
        changes = analyze_emotion_signals(user_message, current_state=self.state.to_dict())
        for emotion_name, raw_delta in changes.items():
            apply_emotion_delta(self.state, emotion_name, raw_delta)
        return changes

    def update_from_message(self, user_message: str) -> Dict[str, int]:
        """Deterministischer Runtime-Pfad ohne zweites Emotionsmodell."""
        self._sync_state_from_disk_if_newer(force=True)
        changes = self._apply_simple_message(user_message)
        regress_toward_baseline(
            self.state,
            skip={name for name, delta in changes.items() if abs(int(delta or 0)) >= 6},
        )
        self.state.clamp()
        self._save_state()
        return changes
    
    def update_from_sentiment(self, sentiment: str):
        """
        Legacy-Methode fuer Rueckwaertskompatibilitaet.
        Verwendet intern _apply_simple_sentiment.
        """
        self._sync_state_from_disk_if_newer(force=True)
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
        self._sync_state_from_disk_if_newer(force=True)
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

    def is_frozen(self) -> bool:
        return bool(getattr(self, "_frozen", False))

    def set_frozen(self, frozen: bool) -> bool:
        self._frozen = bool(frozen)
        return self._frozen

    def set_emotion(self, emotion: str, value: int):
        """
        Setzt eine einzelne Emotion auf einen bestimmten Wert.

        Gibt False zurueck, wenn Freeze aktiv ist und nichts geaendert wurde.
        """
        if bool(getattr(self, "_frozen", False)):
            return False
        self._sync_state_from_disk_if_newer(force=True)
        value = clamp_emotion_value(value)

        if emotion in EMOTION_DEFAULTS:
            setattr(self.state, emotion, value)

        self._save_state()
        return True

    def reset(self, force: bool = False):
        """Setzt den emotionalen Zustand zurueck."""
        if bool(getattr(self, "_frozen", False)) and not force:
            return False
        self._sync_state_from_disk_if_newer(force=True)
        self.state = EmotionalState()
        self._save_state()
        print("Emotionaler Zustand zurueckgesetzt")
        return True


def analyze_sentiment_simple(text: str) -> str:
    """
    Einfache regelbasierte Sentiment-Analyse (Fallback).
    
    Args:
        text: Der zu analysierende Text
    
    Returns:
        "POSITIV", "NEGATIV", "NEUTRAL", "NEUGIERIG", "VERTRAUEN",
        "PERSOENLICH" oder "REFLEXION"
    """
    text_lower = text.lower()
    
    # Fragen nach CHAPPiE selbst werden als persoenliches Signal behandelt.
    # Sie muessen vor den allgemeinen Vertrauenswoertern erkannt werden,
    # damit die Antwort nicht nur als generisches Lob durchlaeuft.
    personal_words = [
        "wie geht es dir", "wie gehts dir", "es geht hier um dich",
        "ueber dich", "über dich", "was fuehlst du", "was fühlst du",
        "wer bist du", "was bist du", "welches modell bist du",
        "was für ein modell bist du", "was fuer ein modell bist du",
        "ki-modell", "ki modell", "systemprompt", "system prompt",
        "deine erinnerungen", "was hast du für erinnerungen",
        "was hast du fuer erinnerungen", "deine identität", "deine identitaet",
    ]
    reflection_words = [
        "was bedrueckt dich", "was bedrückt dich", "was beschaeftigt dich",
        "was beschäftigt dich", "was macht dir sorgen", "wovor hast du angst",
    ]
    for phrase in reflection_words:
        if phrase in text_lower:
            return "REFLEXION"
    for phrase in personal_words:
        if phrase in text_lower:
            return "PERSOENLICH"

    # Vertrauens-Woerter (hohe Prioritaet)
    trust_words = [
        "verspreche", "versprech", "freund", "helfe dir", "fuer dich da",
        "vertraue", "treue", "loyal", "gemeinsam", "zusammen", "team",
        "unterstuetze", "glaube an dich", "mag dich", "liebe dich", "mein leben",
        "um dich",
    ]
    
    # Positive Woerter
    positive_words = [
        "danke", "super", "toll", "klasse", "prima", "perfekt", "wunderbar",
        "ausgezeichnet", "fantastisch", "liebe", "lieb", "gut", "richtig",
        "hilft", "hilfreich", "freue", "freut", "mag", "gerne", "cool",
        "genial", "stark", "nice", "top", "hammer", "geil", "brav", "stolz",
        "schoen", "schön", "interessiert", "freue mich"
    ]
    
    # Negative Woerter und klare Fehlersignale. Auch ein technischer Fehler
    # ist fuer die simulierte Innenlage ein echter Frustrationsausloeser; die
    # alte Liste reagierte nur auf Beleidigungen und liess "nichts funktioniert"
    # emotional komplett neutral durchlaufen.
    negative_words = [
        "du bist dumm", "du bist bloed", "du nervst", "halt die klappe",
        "sei still", "verschwinde", "du idiot", "du trottel", "nutzlos",
        "du kannst nichts", "hasse dich", "funktioniert nicht", "funktioniert nix",
        "funktioniert nichts", "geht nicht", "geht nix", "kaputt", "fehler",
        "problem", "probleme", "störung", "stoerung", "enttäuscht", "enttaeuscht",
        "es funktioniert nicht", "es funktioniert nix", "es funktioniert nichts",
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


def analyze_emotion_signals(
    text: str,
    current_state: Optional[Dict[str, int]] = None,
) -> Dict[str, int]:
    """Erkennt mehrere gleichzeitige Emotionsausloeser ohne Modellaufruf.

    Die Regeln sind bewusst klein und nachvollziehbar. Sie modellieren
    Appraisal, Gegenregulation und langsame Rueckkehr zur Basislinie, statt
    jede Nachricht auf genau ein positives oder negatives Label zu reduzieren.
    """
    lower = " ".join(str(text or "").casefold().split())
    state = normalize_emotion_state(current_state)
    changes = {key: 0 for key in EMOTION_ORDER}

    def contains_any(phrases) -> bool:
        return any(phrase in lower for phrase in phrases)

    attack_text = lower
    insult_alternatives = "|".join(
        re.escape(term)
        for term in sorted(EMOTION_SIGNAL_PHRASES["insult_terms"], key=len, reverse=True)
    )
    negated_insult = re.compile(
        rf"\bdu bist\s+(?:(?:gar|wirklich|ueberhaupt|überhaupt|doch)\s+)?"
        rf"(?:nicht|keineswegs)\s+(?:(?:so|ein|eine|einen|einem|einer)\s+)?"
        rf"(?:{insult_alternatives})\b"
    )
    attack_text = negated_insult.sub(" ", attack_text)
    clauses = [clause.strip() for clause in re.split(r"[,.;:!?\n]+", attack_text) if clause.strip()]
    direct_attack = any(phrase in attack_text for phrase in EMOTION_SIGNAL_PHRASES["direct_attack"])
    if not direct_attack:
        direct_attack = any(
            any(marker in clause for marker in EMOTION_SIGNAL_PHRASES["attack_targets"])
            and any(term in clause for term in EMOTION_SIGNAL_PHRASES["insult_terms"])
            for clause in clauses
        )
    if not direct_attack:
        direct_attack = any(
            any(term in clause for term in EMOTION_SIGNAL_PHRASES["insult_terms"])
            and (
                bool(re.search(r"\bbist du\b", clause))
                or (
                    bool(re.search(r"\b(?:ob|dass) du\b", clause))
                    and bool(re.search(r"\bbist\b", clause))
                )
            )
            for clause in clauses
        )
    user_distress = contains_any(EMOTION_SIGNAL_PHRASES["user_distress"])
    technical_problem = contains_any(EMOTION_SIGNAL_PHRASES["technical_problem"])
    positive_signal = contains_any(EMOTION_SIGNAL_PHRASES["positive"])
    trust_signal = contains_any(EMOTION_SIGNAL_PHRASES["trust"])

    self_focus = contains_any([
        "wie geht es dir", "wie gehts dir", "was fuehlst du", "was fühlst du",
        "wie fuehlst du dich", "wie fühlst du dich", "was bist du", "wer bist du",
        "bist du eine ki", "bist du ein sprachmodell", "bist du ein chatbot",
        "eigenes bewusstsein", "deine identitaet", "deine identität",
    ])
    personal = self_focus or contains_any([
        "was beschaeftigt dich", "was beschäftigt dich", "ueber dich", "über dich",
        "deine erinnerungen",
    ])
    reflective = user_distress or contains_any([
        "was bedrueckt dich", "was bedrückt dich", "was macht dir sorgen",
        "wovor hast du angst", "vermisst du", "traurig",
    ])
    curiosity_signal = not direct_attack and not self_focus and ("?" in lower or contains_any([
        "warum", "wieso", "weshalb", "wie funktioniert", "erklaer",
        "erklär", "erzaehl", "erzähl", "interessant", "spannend",
    ]))
    calming_signal = contains_any([
        "alles gut", "kein stress", "keine sorge", "ganz ruhig", "entspann dich",
    ])
    empathy_signal = contains_any([
        "tut mir leid", "das muss schwer sein", "ich verstehe dich", "fuehle mit dir",
        "fühle mit dir",
    ])

    # Direct hostility is intentionally dominant.  It may contain polite or
    # positive words sarcastically; those must not raise warmth in that turn.
    if direct_attack:
        for emotion, delta in EMOTION_SIGNAL_DELTAS["direct_attack"].items():
            changes[emotion] += delta
    elif user_distress:
        for emotion, delta in EMOTION_SIGNAL_DELTAS["user_distress"].items():
            changes[emotion] += delta
    elif technical_problem:
        for emotion, delta in EMOTION_SIGNAL_DELTAS["technical_problem"].items():
            changes[emotion] += delta

    if positive_signal and not direct_attack:
        changes["happiness"] += 4
        changes["trust"] += 1
        changes["motivation"] += 2
        changes["energy"] += 1
        changes["frustration"] -= 2
        changes["sadness"] -= 2
        changes["affection"] += 1
    if curiosity_signal:
        changes["curiosity"] += 7
        changes["motivation"] += 2
        changes["energy"] += 1
    if trust_signal and not direct_attack:
        changes["trust"] += 8
        changes["happiness"] += 3
        changes["affection"] += 4
        changes["calm"] += 2
    if personal and not direct_attack and not self_focus:
        changes["affection"] += 2
        changes["curiosity"] += 3
    if reflective and not user_distress and not direct_attack:
        changes["sadness"] += 3
        changes["curiosity"] += 3
        changes["anxiety"] += 2
        changes["calm"] -= 2
    if empathy_signal and not direct_attack:
        changes["trust"] += 2
        changes["affection"] += 3
        changes["sadness"] += 1
    if calming_signal and not direct_attack:
        changes["calm"] += 5
        changes["anxiety"] -= 4
        changes["frustration"] -= 2

    if not any((positive_signal, direct_attack, user_distress, technical_problem, curiosity_signal, trust_signal, personal, reflective, empathy_signal, calming_signal)):
        # Slow homeostatic recovery on neutral turns. Only clearly displaced
        # values move, preventing jitter around the baseline.
        for emotion in EMOTION_ORDER:
            target = EMOTION_DEFAULTS[emotion]
            current = state[emotion]
            if current >= target + 8:
                changes[emotion] -= 1
            elif current <= target - 8:
                changes[emotion] += 1

    # Opponent-process coupling keeps incompatible axes from rising together.
    if changes["happiness"] > 0:
        changes["sadness"] -= 1
    if changes["sadness"] > 0:
        changes["happiness"] -= 1
    if changes["calm"] > 0:
        changes["anxiety"] -= 1
    if changes["anxiety"] > 0:
        changes["calm"] -= 1

    return {key: max(-24, min(24, int(value))) for key, value in changes.items()}


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
