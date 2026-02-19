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

from config.config import settings, LLMProvider
from brain import get_brain
from brain.base_brain import GenerationConfig, Message


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
        intent_provider = settings.intent_provider or settings.llm_provider
        original_provider = settings.llm_provider
        original_models = {
            LLMProvider.GROQ: settings.groq_model,
            LLMProvider.CEREBRAS: settings.cerebras_model,
            LLMProvider.NVIDIA: settings.nvidia_model,
            LLMProvider.OLLAMA: settings.ollama_model
        }
        
        if intent_provider == LLMProvider.GROQ:
            settings.groq_model = settings.intent_processor_model_groq
        elif intent_provider == LLMProvider.CEREBRAS:
            settings.cerebras_model = settings.intent_processor_model_cerebras
        elif intent_provider == LLMProvider.NVIDIA:
            settings.nvidia_model = settings.intent_processor_model_nvidia
        else:
            settings.ollama_model = settings.intent_processor_model_ollama
        
        original_llm_provider = settings.llm_provider
        settings.llm_provider = intent_provider
        
        self.brain = get_brain()
        
        settings.llm_provider = original_llm_provider
        settings.groq_model = original_models[LLMProvider.GROQ]
        settings.cerebras_model = original_models[LLMProvider.CEREBRAS]
        settings.nvidia_model = original_models[LLMProvider.NVIDIA]
        settings.ollama_model = original_models[LLMProvider.OLLAMA]
    
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
        # Baue Prompt
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(user_input, history, current_emotions)
        
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt)
        ]
        
        # Generiere mit kleinem Modell
        gen_config = GenerationConfig(
            max_tokens=2048,
            temperature=0.1,  # Sehr niedrig fuer konsistente JSON
            stream=False
        )
        
        try:
            raw_response = self.brain.generate(messages, config=gen_config)
            
            # Extrahiere JSON
            json_data = self._extract_json(raw_response)
            
            # Parse zu IntentResult
            return self._parse_intent_result(json_data)
            
        except Exception as e:
            # Fallback bei Fehler
            print(f"[IntentProcessor] Fehler: {e}")
            return self._create_fallback_result()
    
    def _build_system_prompt(self) -> str:
        """Baut den OPTIMIERTEN System Prompt fuer Intent Analysis."""
        return """DU BIST EIN TOOL-AUFRUF-SYSTEM fuer CHAPPiE.

DEINE AUFGABE:
1. Lies den User-Input
2. Entscheide: Soll ich ein TOOL benutzen?
3. Gib NUR JSON aus - sonst nichts!

=== VERFUEGBARE TOOLS ===

Tool 1: update_user_profile
WANN: User sagt seinen Namen, Job, Hobbys, etc.
BEISPIEL: User sagt "Ich heisse Max" -> update_user_profile mit {"name": "Max"}

Tool 2: update_soul  
WANN: CHAPPiE lernt etwas ueber sich selbst
BEISPIEL: "Ich merke, dass ich gerne helfe" -> update_soul mit {"evolution_note": "Ich helfe gerne"}

Tool 3: update_preferences
WANN: CHAPPiE entwickelt eine Meinung/Vorliebe
BEISPIEL: "Ich mag Kaffee lieber als Tee" -> update_preferences mit {"new_preference": "Mag Kaffee", "category": "My Personality Preferences"}

Tool 4: add_short_term_memory
WANN: WICHTIGE Info fuer die naechsten 24 Stunden
BEISPIELE:
- User sagt: "Morgen habe ich ein wichtiges Meeting" -> add_short_term_memory
- User teilt persoenliche Info -> add_short_term_memory  
- Technisches Detail -> add_short_term_memory

=== WICHTIGE REGELN ===

1. JSON MUSS valide sein - sonst funktioniert nichts!
2. Antworte NUR mit JSON - keine Erklaerungen davor oder danach!
3. Tool Calls nur wenn WIRKLICH noetig
4. Bei persoenlichen Infos: IMMER update_user_profile
5. Wichtige aktuelle Infos: IMMER add_short_term_memory

=== ERFORDERLICHES JSON FORMAT ===

{
  "intent_analysis": {
    "primary_intent": "information_exchange",
    "confidence": 0.95,
    "entities": ["Name", "Info"]
  },
  "tool_calls": [
    {
      "tool": "update_user_profile",
      "action": "update", 
      "data": {"name": "Max"},
      "priority": "high",
      "reason": "User hat Namen genannt"
    }
  ],
  "emotions_update": {
    "happiness": {"delta": 5, "reason": "User war freundlich"},
    "trust": {"delta": 3, "reason": "Persoenliche Info"},
    "energy": {"delta": 0, "reason": ""},
    "curiosity": {"delta": 5, "reason": "Neues Thema"},
    "frustration": {"delta": 0, "reason": ""},
    "motivation": {"delta": 5, "reason": "Positive Interaktion"}
  },
  "context_requirements": {
    "need_soul_context": true,
    "need_user_context": true,
    "need_preferences": false,
    "need_short_term_memory": true,
    "need_long_term_memory": true
  },
  "short_term_entries": [
    {
      "content": "User heisst Max und arbeitet als Entwickler",
      "category": "user",
      "importance": "high"
    }
  ]
}

=== BEISPIELE ===

User: "Ich heisse Benjamin"
JSON: {
  "intent_analysis": {"primary_intent": "personal_sharing", "confidence": 1.0, "entities": ["Benjamin", "Name"]},
  "tool_calls": [{"tool": "update_user_profile", "action": "update", "data": {"name": "Benjamin"}, "priority": "high", "reason": "User hat Namen genannt"}],
  "emotions_update": {"happiness": {"delta": 5, "reason": "Persoenliche Info"}, "trust": {"delta": 10, "reason": "Vertrauensvoll"}, "energy": {"delta": 0, "reason": ""}, "curiosity": {"delta": 5, "reason": "Will mehr wissen"}, "frustration": {"delta": 0, "reason": ""}, "motivation": {"delta": 5, "reason": "Neuer Kontakt"}},
  "context_requirements": {"need_soul_context": false, "need_user_context": true, "need_preferences": false, "need_short_term_memory": true, "need_long_term_memory": false},
  "short_term_entries": [{"content": "User heisst Benjamin", "category": "user", "importance": "high"}]
}

User: "Wie ist das Wetter?"
JSON: {
  "intent_analysis": {"primary_intent": "information_exchange", "confidence": 0.9, "entities": ["Wetter"]},
  "tool_calls": [],
  "emotions_update": {"happiness": {"delta": 0, "reason": ""}, "trust": {"delta": 0, "reason": ""}, "energy": {"delta": 0, "reason": ""}, "curiosity": {"delta": 3, "reason": "Wetter-Frage"}, "frustration": {"delta": 0, "reason": ""}, "motivation": {"delta": 0, "reason": ""}},
  "context_requirements": {"need_soul_context": false, "need_user_context": false, "need_preferences": false, "need_short_term_memory": false, "need_long_term_memory": false},
  "short_term_entries": []
}

DENKE: Tool noetig? -> Dann FUELLE tool_calls aus.
DENKE: Wichtige Info? -> Dann FUELLE short_term_entries aus.

GIB NUR JSON AUS!"""
    
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
- happiness: {current_emotions.get('happiness', 50)}
- trust: {current_emotions.get('trust', 50)}
- energy: {current_emotions.get('energy', 100)}
- curiosity: {current_emotions.get('curiosity', 50)}
- frustration: {current_emotions.get('frustration', 0)}
- motivation: {current_emotions.get('motivation', 80)}

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
                if isinstance(data, dict):
                    emotions_update[emotion] = EmotionUpdate(
                        delta=data.get("delta", 0),
                        reason=data.get("reason", "")
                    )
            except Exception:
                pass
        
        # Parse Context Requirements
        context_req = json_data.get("context_requirements", {})
        
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
        
        return IntentResult(
            intent_type=intent_type,
            confidence=intent_data.get("confidence", 0.5),
            entities=intent_data.get("entities", []),
            tool_calls=tool_calls,
            emotions_update=emotions_update,
            context_requirements=context_req,
            short_term_entries=short_term_entries,
            raw_json=json_data
        )
    
    def _create_fallback_result(self) -> IntentResult:
        """Erstellt Fallback Result bei Fehler."""
        return IntentResult(
            intent_type=IntentType.CASUAL_CHAT,
            confidence=0.5,
            entities=[],
            tool_calls=[],
            emotions_update={},
            context_requirements={
                "need_soul_context": False,
                "need_user_context": False,
                "need_preferences": False,
                "need_short_term_memory": True,
                "need_long_term_memory": True
            },
            short_term_entries=[],
            raw_json={}
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
