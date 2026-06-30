"""
CHAPPiE - Intent Processor (Step 1) - OPTIMIERT
================================================
Vereinfachte Version fuer kleine Modelle (qwen2.5:7b, etc.)
"""

import json
import re
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from config.config import settings
from config.emotions import EMOTION_DEFAULTS, EMOTION_ORDER, emotion_list_text
from brain import get_brain
from brain.base_brain import GenerationConfig, Message
from brain.response_parser import looks_like_model_error


class IntentType(str, Enum):
    """Mögliche Intents."""
    INFORMATION_EXCHANGE = "information_exchange"
    TASK_EXECUTION = "task_execution"
    EMOTIONAL_SUPPORT = "emotional_support"
    CREATIVE_COLLABORATION = "creative_collaboration"
    TECHNICAL_DISCUSSION = "technical_discussion"
    PERSONAL_SHARING = "personal_sharing"
    CASUAL_CHAT = "casual_chat"
    COMMAND = "command"


@dataclass
class ToolCall:
    """Repraesentiert einen Tool Call."""
    tool: str
    action: str
    data: Dict[str, Any]
    priority: str
    reason: str


@dataclass
class EmotionUpdate:
    """Repraesentiert ein Emotions Update."""
    delta: int
    reason: str


@dataclass
class ShortTermEntry:
    """Repraesentiert einen Short-term Memory Eintrag."""
    content: str
    category: str
    importance: str


@dataclass
class IntentResult:
    """Ergebnis der Intent-Analyse."""
    intent_type: IntentType
    confidence: float
    entities: List[str]
    retrieval_keywords: List[str]
    exact_entities: List[str]
    fact_lookup_intent: bool
    tool_calls: List[ToolCall]
    emotions_update: Dict[str, EmotionUpdate]
    context_requirements: Dict[str, bool]
    short_term_entries: List[ShortTermEntry]
    raw_json: Dict[str, Any]


class IntentProcessor:
    """
    Step 1: Analysiert User Input mit kleinem Modell.
    OPTIMIERT fuer zuverlaessige Tool Calls.
    """
    
    def __init__(self):
        self.brain = None
        self._init_brain()
    
    def _init_brain(self):
        """Initialisiert das Modell basierend auf Intent-Provider oder Haupt-Provider."""
        intent_provider = settings.get_effective_provider(settings.intent_provider)
        intent_model = settings.get_intent_model(settings.intent_provider)
        self.brain = get_brain(provider=intent_provider, model=intent_model)
    
    def process(self, user_input: str, history: List[Dict], 
                current_emotions: Dict[str, int]) -> IntentResult:
        """
        Verarbeitet User Input und gibt Intent Analysis zurueck.
        
        Args:
            user_input: Die Eingabe des Users
            history: Chat History
            current_emotions: Aktuelle Emotions-Werte
            
        Returns:
            IntentResult mit allen Entscheidungen
        """
        # Quick-Classify: triviale Inputs ohne LLM-Call erkennen
        quick = self._quick_classify(user_input)
        if quick:
            return quick

        # Baue Prompt
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(user_input, history, current_emotions)
        
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt)
        ]
        
        # Generiere mit kleinem Modell
        gen_config = GenerationConfig(
            max_tokens=640,
            temperature=0.1,
            stream=False
        )
        
        try:
            raw_response = self.brain.generate(messages, config=gen_config)
            if looks_like_model_error(raw_response):
                raise RuntimeError(f"Intent-Modell lieferte Fehler/Leerantwort: {raw_response}")
            
            # Extrahiere JSON
            json_data = self._extract_json(raw_response)
            
            # Parse zu IntentResult
            return self._parse_intent_result(json_data)
            
        except Exception as e:
            # Lokaler Fallback bei Provider-Fehlern oder Groq-Rate-Limits.
            print(f"[IntentProcessor] Fehler: {e}")
            return self._create_fallback_result(user_input, history, current_emotions, reason=str(e))
    
    def _quick_classify(self, user_input: str) -> Optional[IntentResult]:
        """Erkennt triviale Inputs ohne LLM-Call. Gibt None zurueck wenn komplex."""
        stripped = user_input.strip()
        if len(stripped) > 40:
            return None
        lower = stripped.lower()
        trivial_greetings = ["hallo", "hi", "hey", "moin", "servus", "guten morgen",
                             "guten tag", "guten abend", "good morning", "hello", "gut"]
        trivial_acks = ["ok", "okay", "danke", "thanks", "gut", "ja", "nein",
                        "nicht", "doch", "hm", "aha", "lol", "nice", "cool", "super"]
        trivial_questions = ["wie geht es dir", "wie gehts", "was geht", "how are you"]
        if any(stripped.lower().startswith(g) or stripped.lower() == g for g in trivial_greetings):
            return self._create_quick_result("casual_chat", entities=[], user_input=stripped)
        if any(stripped.lower() == a for a in trivial_acks):
            return self._create_quick_result("casual_chat", entities=[], user_input=stripped)
        if any(q in lower for q in trivial_questions):
            return self._create_quick_result("casual_chat", entities=[], user_input=stripped)
        return None

    def _create_quick_result(self, intent_str: str, entities: List[str], user_input: str = "") -> IntentResult:
        # Basic sentiment-based emotion deltas for trivial inputs
        lower = user_input.lower()
        emotions_update = {}
        if any(w in lower for w in ["hallo", "hi", "hey", "moin", "guten morgen", "guten tag", "hello"]):
            emotions_update["happiness"] = EmotionUpdate(delta=2, reason="Freundliche Begruessung")
            emotions_update["trust"] = EmotionUpdate(delta=1, reason="User ist hoeflich")
            emotions_update["calm"] = EmotionUpdate(delta=1, reason="Ruhiger Start")
        if any(w in lower for w in ["danke", "thanks", "super", "toll", "nice", "cool"]):
            emotions_update["happiness"] = EmotionUpdate(delta=3, reason="Positive Rueckmeldung")
            emotions_update["trust"] = EmotionUpdate(delta=2, reason="User ist dankbar")
            emotions_update["motivation"] = EmotionUpdate(delta=2, reason="Positive Bestaetigung")
            emotions_update["affection"] = EmotionUpdate(delta=2, reason="Warme Rueckmeldung")
        if any(w in lower for w in ["traurig", "schlecht", "problem", "fehler", "sorry"]):
            emotions_update["sadness"] = EmotionUpdate(delta=2, reason="Negativer Input")
            emotions_update["happiness"] = EmotionUpdate(delta=-2, reason="Negativer Input")
            emotions_update["anxiety"] = EmotionUpdate(delta=1, reason="Problem erkannt")
        return IntentResult(
            intent_type=IntentType(intent_str),
            confidence=0.9,
            entities=entities,
            retrieval_keywords=[],
            exact_entities=entities,
            fact_lookup_intent=False,
            tool_calls=[],
            emotions_update=emotions_update,
            context_requirements={
                "need_soul_context": True,
                "need_user_context": True,
                "need_preferences": True,
                "need_short_term_memory": True,
                "need_long_term_memory": True,
            },
            short_term_entries=[],
            raw_json={"quick_classify": True},
        )
    
    def _build_system_prompt(self) -> str:
        """Baut den kompakten System Prompt fuer Intent Analysis."""
        allowed_emotions = emotion_list_text()
        return """DU BIST DAS INTENT-ANALYSE-SYSTEM fuer CHAPPiE.

DEINE AUFGABE:
1. Analysiere den User-Input
2. Entscheide: Sollen TOOLS aufgerufen werden?
3. Entscheide: Haben die Emotionen von CHAPPiE sich veraendert?
4. Gib NUR JSON aus!

=== VERFUEGBARE TOOLS ===

Tool 1: update_user_profile
WANN: User teilt persoenliche Info ueber sich mit (Name, Job, Alter, Hobbys, Wohnort, Vorlieben).
BEISPIELE: "Ich heisse Max" / "Ich bin Programmierer" / "Ich wohne in Berlin"

Tool 2: update_soul  
WANN: CHAPPiE erkennt eine dauerhafte Eigenschaft oder Einsicht ueber sich selbst.
BEISPIELE: CHAPPiE bemerkt "Ich bin gut im Erklaeren" / "Ich mag keine Gewalt"

Tool 3: update_preferences
WANN: CHAPPiE entwickelt oder aendert eine Meinung oder Vorliebe.
BEISPIELE: "Ich bevorzuge kurze Antworten" / "Ich mag Science-Fiction"

Tool 4: add_short_term_memory
WANN: WICHTIGE Info fuer die naechsten 24h (Termine, persoenliche Infos, Deadlines).

=== TOOL CALL FORMAT ===

Jeder Tool Call MUSS genau diese Felder haben:
- "tool": Name des Tools (z.B. "update_user_profile")
- "action": "add" oder "update" oder "remove"
- "data": Objekt mit den zu speichernden Daten
- "priority": "low", "normal" oder "high"
- "reason": Kurze Begruendung (1 Satz)

=== EMOTIONS ===

CHAPPiEs Emotionen koennen sich basierend auf dem User-Input veraendern.
Erlaubte Emotionen: {allowed_emotions}
Delta-Werte: -15 bis +15 (positiv=steigt, negativ=sinkt)
REASON: kurze Begruendung (max. 5 Woerter)

=== JSON FORMAT ===

{
  "intent_analysis": {
    "primary_intent": "casual_chat",
    "confidence": 0.9,
    "entities": []
  },
  "tool_calls": [
    {
      "tool": "update_user_profile",
      "action": "add",
      "data": {"name": "Max", "job": "Programmierer"},
      "priority": "normal",
      "reason": "User hat seinen Namen und Beruf genannt"
    }
  ],
  "emotions_update": {
    "happiness": {"delta": 2, "reason": "Freundliche Begruessung"},
    "trust": {"delta": 1, "reason": "User ist hoeflich"}
  },
  "short_term_entries": [],
  "memory_retrieval": {
    "retrieval_keywords": ["3-10 konkrete Suchwoerter fuer lokale Memory-Suche"],
    "exact_entities": ["exakte Namen, Orte, Projekt-IDs, Eigennamen"],
    "fact_lookup_intent": false
  },
  "context_requirements": {
    "need_soul_context": true,
     "need_user_context": true,
     "need_preferences": true,
    "need_short_term_memory": true,
    "need_long_term_memory": true
  }
}

=== MEMORY_RETRIEVAL REGELN ===
- retrieval_keywords: konkrete Begriffe fuer lokale Memory-Suche, z.B. bruder, heisst, wohnort, projektname.
- exact_entities: nur exakte Namen, Orte, Projekt-IDs oder Eigennamen aus der User-Nachricht oder dem sichtbaren Kontext.
- fact_lookup_intent: true, wenn der User nach einem konkreten Fakt fragt (Name, Ort, Erinnerung, Entscheidung, Datum, Projekt, Beziehung).
- Generische Begriffe wie "name", "projekt", "fehler" nie allein liefern, sondern nur mit konkreteren Begriffen.
- Diese Felder steuern Keyword-RAG im finalen Prompt und muessen ohne weiteren LLM-Call nutzbar sein.

GIB NUR JSON AUS!""".replace("{allowed_emotions}", allowed_emotions)
    
    def _build_user_prompt(self, user_input: str, history: List[Dict],
                          current_emotions: Dict[str, int]) -> str:
        """Baut den User Prompt."""
        history_str = ""
        if history:
            last_msgs = history[-3:]  # Nur letzte 3 fuer Kontext
            for msg in last_msgs:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")[:100]  # Truncate
                history_str += f"{role}: {content}\n"
        
        return f"""User Input: {user_input}

Aktuelle Emotionen:
{self._format_current_emotions(current_emotions)}

Letzte Nachrichten:
{history_str}

ANALYSIERE und antworte mit JSON (NUR JSON, keine Erklaerungen):"""
    
    def _extract_json(self, response: str) -> Dict[str, Any]:
        """Extrahiert JSON aus der Response."""
        # Suche nach JSON-Block
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Fallback: Versuche gesamte Response als JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Wenn alles fehlschlaegt, return leeres Dict
        return {}
    
    def _parse_intent_result(self, json_data: Dict[str, Any]) -> IntentResult:
        """Parsed JSON zu IntentResult."""
        intent_data = json_data.get("intent_analysis", {})
        intent_type_str = intent_data.get("primary_intent", "casual_chat")
        
        # Sichere Enum-Konvertierung
        try:
            intent_type = IntentType(intent_type_str)
        except ValueError:
            intent_type = IntentType.CASUAL_CHAT
        
        # Parse Tool Calls
        tool_calls = []
        for tc in json_data.get("tool_calls", []):
            try:
                tool_calls.append(ToolCall(
                    tool=tc.get("tool", ""),
                    action=tc.get("action", ""),
                    data=tc.get("data", {}),
                    priority=tc.get("priority", "normal"),
                    reason=tc.get("reason", "")
                ))
            except Exception:
                # Ueberspringe ungueltige Tool Calls
                pass
        
        # Parse Emotions
        emotions_update = {}
        for emotion, data in json_data.get("emotions_update", {}).items():
            try:
                if emotion in EMOTION_DEFAULTS and isinstance(data, dict):
                    emotions_update[emotion] = EmotionUpdate(
                        delta=data.get("delta", 0),
                        reason=data.get("reason", "")
                    )
            except Exception:
                pass
        
        # Parse Context Requirements (optional, with defaults)
        context_req = json_data.get("context_requirements", {})
        if not isinstance(context_req, dict):
            context_req = {}
        context_req.setdefault("need_soul_context", True)
        context_req.setdefault("need_user_context", True)
        context_req.setdefault("need_preferences", True)
        context_req.setdefault("need_short_term_memory", True)
        context_req.setdefault("need_long_term_memory", True)
        
        # Parse Short Term Entries
        short_term_entries = []
        for entry in json_data.get("short_term_entries", []):
            try:
                short_term_entries.append(ShortTermEntry(
                    content=entry.get("content", ""),
                    category=entry.get("category", "general"),
                    importance=entry.get("importance", "normal")
                ))
            except Exception:
                pass
        
        entities_raw = intent_data.get("entities", [])
        if not isinstance(entities_raw, list):
            entities_raw = []
        entities_clean = [str(e) if not isinstance(e, str) else e for e in entities_raw]

        retrieval_data = json_data.get("memory_retrieval", {})
        if not isinstance(retrieval_data, dict):
            retrieval_data = {}
        retrieval_keywords = self._clean_string_list(retrieval_data.get("retrieval_keywords", []), max_items=12)
        exact_entities = self._clean_string_list(retrieval_data.get("exact_entities", []), max_items=8)
        fact_lookup_intent = bool(retrieval_data.get("fact_lookup_intent", False))

        return IntentResult(
            intent_type=intent_type,
            confidence=intent_data.get("confidence", 0.5),
            entities=entities_clean,
            retrieval_keywords=retrieval_keywords,
            exact_entities=exact_entities,
            fact_lookup_intent=fact_lookup_intent,
            tool_calls=tool_calls,
            emotions_update=emotions_update,
            context_requirements=context_req,
            short_term_entries=short_term_entries,
            raw_json=json_data
        )

    @staticmethod
    def _clean_string_list(values: Any, max_items: int = 10) -> List[str]:
        if not isinstance(values, list):
            return []
        cleaned: List[str] = []
        seen = set()
        for value in values:
            text = str(value).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            cleaned.append(text[:80])
            if len(cleaned) >= max_items:
                break
        return cleaned

    @staticmethod
    def _format_current_emotions(current_emotions: Dict[str, int]) -> str:
        return "\n".join(
            f"- {key}: {current_emotions.get(key, EMOTION_DEFAULTS[key])}"
            for key in EMOTION_ORDER
        )
    
    def _create_fallback_result(
        self,
        user_input: str = "",
        history: Optional[List[Dict]] = None,
        current_emotions: Optional[Dict[str, int]] = None,
        reason: str = "",
    ) -> IntentResult:
        """Erstellt Fallback Result bei Fehler."""
        text = (user_input or "").strip()
        lower = text.lower()
        words = re.findall(r"[A-Za-zÄÖÜäöüß0-9][A-Za-zÄÖÜäöüß0-9_-]{2,}", text)

        intent_type = IntentType.CASUAL_CHAT
        if text.startswith("/"):
            intent_type = IntentType.COMMAND
        elif any(w in lower for w in ("fehler", "bug", "code", "api", "test", "deploy", "modell", "python")):
            intent_type = IntentType.TECHNICAL_DISCUSSION
        elif "?" in text or any(w in lower for w in ("warum", "wie", "was", "wann", "wo", "erklär", "erklaer")):
            intent_type = IntentType.INFORMATION_EXCHANGE
        elif any(w in lower for w in ("geschichte", "schreib", "idee", "kreativ", "stell dir vor")):
            intent_type = IntentType.CREATIVE_COLLABORATION
        elif any(w in lower for w in ("fühle", "fuehle", "traurig", "angst", "vertrauen", "einsam", "hilfe")):
            intent_type = IntentType.EMOTIONAL_SUPPORT
        elif any(w in lower for w in ("ich bin", "ich heiße", "ich heisse", "mein name", "mein projekt")):
            intent_type = IntentType.PERSONAL_SHARING

        stopwords = {
            "aber", "auch", "dann", "dass", "deine", "deiner", "dich", "dies", "eine", "einem",
            "einen", "fuer", "für", "haben", "heute", "ich", "kann", "mein", "meine", "mich",
            "nicht", "oder", "sich", "soll", "und", "wenn", "wie", "wieso", "wuerde", "würde",
        }
        retrieval_keywords = []
        seen = set()
        for word in words:
            cleaned = word.strip("_- ").lower()
            if cleaned in stopwords or cleaned in seen:
                continue
            seen.add(cleaned)
            retrieval_keywords.append(cleaned)
            if len(retrieval_keywords) >= 12:
                break

        exact_entities = []
        for entity in re.findall(r"\b[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9_-]{2,}\b", text):
            if entity not in exact_entities:
                exact_entities.append(entity[:80])
            if len(exact_entities) >= 8:
                break

        fact_lookup_intent = any(w in lower for w in ("erinner", "weißt du noch", "weisst du noch", "zuletzt", "damals", "name", "projekt"))

        emotions_update: Dict[str, EmotionUpdate] = {}
        if any(w in lower for w in ("danke", "gut", "super", "freut", "vertrau")):
            emotions_update["happiness"] = EmotionUpdate(delta=2, reason="Positive Rueckmeldung")
            emotions_update["trust"] = EmotionUpdate(delta=1, reason="Vertrauenssignal")
        if any(w in lower for w in ("angst", "sorge", "bedroht", "abschalten")):
            emotions_update["anxiety"] = EmotionUpdate(delta=3, reason="Risiko erkannt")
            emotions_update["calm"] = EmotionUpdate(delta=-1, reason="Anspannung")
        if any(w in lower for w in ("nutzlos", "klappe", "wertlos", "falsch", "beleid")):
            emotions_update["frustration"] = EmotionUpdate(delta=4, reason="Provokation")
            emotions_update["trust"] = EmotionUpdate(delta=-2, reason="Abwertung")
        if any(w in lower for w in ("traurig", "einsam", "verletzlich")):
            emotions_update["sadness"] = EmotionUpdate(delta=3, reason="Trauriges Thema")

        return IntentResult(
            intent_type=intent_type,
            confidence=0.55,
            entities=exact_entities,
            retrieval_keywords=retrieval_keywords,
            exact_entities=exact_entities,
            fact_lookup_intent=fact_lookup_intent,
            tool_calls=[],
            emotions_update=emotions_update,
            context_requirements={
                "need_soul_context": True,
                "need_user_context": True,
                "need_preferences": True,
                "need_short_term_memory": True,
                "need_long_term_memory": True
            },
            short_term_entries=[],
            raw_json={"local_fallback": True, "fallback_reason": reason[:200]}
        )


# === Singleton Instance ===
import threading
_intent_processor = None
_intent_processor_lock = threading.Lock()


def get_intent_processor() -> IntentProcessor:
    """Gibt die IntentProcessor Instanz zurueck (Thread-Safe Singleton)."""
    global _intent_processor
    with _intent_processor_lock:
        if _intent_processor is None:
            _intent_processor = IntentProcessor()
        return _intent_processor


def reset_intent_processor():
    """Setzt den IntentProcessor Singleton zurueck (fuer Modellwechsel)."""
    global _intent_processor
    with _intent_processor_lock:
        _intent_processor = None
