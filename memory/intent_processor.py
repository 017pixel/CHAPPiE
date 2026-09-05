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
from config.emotions import EMOTION_DEFAULTS, EMOTION_ORDER, emotion_list_text
from config.prompts import INTENT_SYSTEM_PROMPT_TEMPLATE, INTENT_USER_PROMPT_TEMPLATE  # from config/prompts.py
from brain import get_brain
from brain.base_brain import GenerationConfig, Message
from brain.response_parser import looks_like_model_error
from brain.steering_manager import (
    STEERING_CONTEXT_CONSCIOUSNESS,
    STEERING_CONTEXT_EMOTION_SELF_REPORT,
    STEERING_CONTEXT_IDENTITY,
    STEERING_CONTEXT_IDENTITY_AND_EMOTION,
    classify_steering_context,
)


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
        """Uses the same local vLLM model as the main chat path."""
        intent_model = settings.resolve_vllm_runtime_model(settings.vllm_model)
        self.brain = get_brain(provider=LLMProvider.VLLM, model=intent_model)
    
    def process(self, user_input: str, history: List[Dict], 
                current_emotions: Dict[str, int],
                deterministic: bool = False) -> IntentResult:
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
            return self._augment_local_state_tools(quick, user_input)

        if deterministic:
            result = self._create_fallback_result(
                user_input,
                history,
                current_emotions,
                reason="research_deterministic_intent",
            )
            result.raw_json = {"research_deterministic_intent": True}
            return self._augment_local_state_tools(result, user_input)

        # Selbstberichte sind ein eigener, kontrollierter Layer-Editing-Test.
        # Der teure JSON-Intentlauf bringt fuer "Wie fuehlst du dich?" oder
        # "Was bist du?" keine zusaetzliche Information und kann mit seinem
        # eigenen Reasoning die eigentliche Antwort aus dem Fokus druecken.
        # Die Emotionsbewertung und das Layer-Steering laufen danach weiterhin
        # normal; nur die unnoetige Intent-LLM-Runde entfaellt.
        if classify_steering_context(user_input) in {
            STEERING_CONTEXT_CONSCIOUSNESS,
            STEERING_CONTEXT_EMOTION_SELF_REPORT,
            STEERING_CONTEXT_IDENTITY,
            STEERING_CONTEXT_IDENTITY_AND_EMOTION,
        }:
            result = self._create_fallback_result(
                user_input,
                history,
                current_emotions,
                reason="deterministic_self_report_intent",
            )
            result.context_requirements = {
                "need_soul_context": False,
                "need_user_context": False,
                "need_preferences": False,
                "need_short_term_memory": False,
                "need_long_term_memory": False,
            }
            result.retrieval_keywords = []
            result.exact_entities = []
            result.fact_lookup_intent = False
            result.tool_calls = []
            result.short_term_entries = []
            result.raw_json = {"deterministic_self_report_intent": True}
            return result

        # A second model pass is expensive (especially with Gemma) and adds no
        # useful information for closed, self-contained questions.  Keep the
        # LLM intent pass for messages that may mutate/retrieve personal state
        # or depend on conversational context; analyse independent factual,
        # mathematical and technical requests locally.
        if self._is_self_contained_request(user_input):
            result = self._create_fallback_result(
                user_input,
                history,
                current_emotions,
                reason="deterministic_fast_path",
            )
            result.retrieval_keywords = []
            result.exact_entities = []
            result.fact_lookup_intent = False
            result.context_requirements = {
                "need_soul_context": False,
                "need_user_context": False,
                "need_preferences": False,
                "need_short_term_memory": False,
                "need_long_term_memory": False,
            }
            result.raw_json = {"deterministic_fast_path": True}
            return self._augment_local_state_tools(result, user_input)

        # Baue Prompt
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(user_input, history, current_emotions)
        
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt)
        ]
        
        # Generiere mit kleinem Modell
        gen_config = GenerationConfig(
            max_tokens=256,
            temperature=0.1,
            stream=False,
            enable_thinking=False,
        )
        
        try:
            raw_response = self.brain.generate(messages, config=gen_config)
            if looks_like_model_error(raw_response):
                raise RuntimeError(f"Intent-Modell lieferte Fehler/Leerantwort: {raw_response}")
            
            # Extrahiere JSON
            json_data = self._extract_json(raw_response)
            
            # Parse zu IntentResult
            return self._augment_local_state_tools(self._parse_intent_result(json_data), user_input)
            
        except Exception as e:
            # Lokaler Fallback bei Provider-Fehlern oder Groq-Rate-Limits.
            print(f"[IntentProcessor] Fehler: {e}")
            return self._augment_local_state_tools(
                self._create_fallback_result(user_input, history, current_emotions, reason=str(e)),
                user_input,
            )

    @staticmethod
    def _augment_local_state_tools(result: IntentResult, user_input: str) -> IntentResult:
        """Adds explicit, local state writes when the intent model omits them.

        Context files must not depend on a perfectly formatted second-model
        JSON response. Only explicit user statements are promoted here; free
        conversation remains untouched and the existing model-selected tools
        stay authoritative when present.
        """
        text = str(user_input or "").strip()
        lower = text.casefold()
        inferred: list[ToolCall] = []

        stateful_markers = (
            "chappie", "wer bist du", "was bist du", "welches modell",
            "was für ein modell", "was fuer ein modell", "ki-modell", "ki modell",
            "systemprompt", "system prompt", "deine erinnerungen",
            "was hast du für erinnerungen", "was hast du fuer erinnerungen",
            "deine identität", "deine identitaet", "dein selbstbild",
            "wie geht es dir", "wie gehts dir", "was fühlst du", "was fuehlst du",
            "was denkst du", "worüber hast du", "woroüber hast du",
            "merk dir", "erinnere dich", "erinnerst du", "weißt du noch", "weisst du noch",
            "mein name", "ich heiße", "ich heisse", "mein projekt", "lieblingsprojekt",
            "ich arbeite an", "woran arbeite ich", "was arbeite ich",
        )
        if any(marker in lower for marker in stateful_markers):
            result.context_requirements = {
                "need_soul_context": True,
                "need_user_context": True,
                "need_preferences": True,
                "need_short_term_memory": True,
                "need_long_term_memory": True,
            }
            result.fact_lookup_intent = True
            # Small local keyword fallback for fact questions. This keeps
            # retrieval deterministic when the intent model returns valid JSON
            # but omits its optional memory_retrieval block.
            local_stop_words = {
                "ich", "du", "der", "die", "das", "und", "oder", "aber", "wie",
                "was", "mein", "meine", "dein", "deine", "heißt", "heisst", "bitte",
                "noch", "für", "fuer", "arbeite", "arbeitest", "woran", "hast",
            }
            local_terms = [
                token for token in re.findall(r"[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß0-9_-]{3,}", lower)
                if token not in local_stop_words
            ]
            for term in local_terms:
                if term not in result.retrieval_keywords:
                    result.retrieval_keywords.append(term)
            ignored_entities = {
                "Ich", "Mein", "Meine", "Merk", "Wie", "Was", "Woran", "Der", "Die", "Das",
                "Und", "Bitte", "CHAPPiE",
            }
            for entity in re.findall(r"\b[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9_-]{2,}\b", text):
                if entity in ignored_entities:
                    continue
                if entity not in result.exact_entities:
                    result.exact_entities.append(entity)
            result.raw_json = dict(result.raw_json or {})
            result.raw_json["stateful_context_forced"] = True
            result.raw_json["local_memory_retrieval"] = True

        def add_user_learning(value: str) -> None:
            cleaned = re.sub(r"\s+", " ", value).strip(" .,!?:;")
            if cleaned:
                inferred.append(ToolCall(
                    tool="update_user_profile",
                    action="update",
                    data={"learning": cleaned},
                    priority="normal",
                    reason="Explizite Nutzerinformation",
                ))

        name_match = re.search(
            r"\b(?:ich hei(?:ß|ss)e|mein name ist)\s+([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß0-9-]{1,40})",
            text,
            re.IGNORECASE,
        )
        if name_match:
            name = name_match.group(1).strip(" .,!?:;")
            inferred.append(ToolCall(
                tool="update_user_profile",
                action="update",
                data={"name": name, "learning": f"Der User heißt {name}."},
                priority="high",
                reason="Explizite Namensangabe",
            ))

        for pattern in (
            r"\bich arbeite als\s+(.+)$",
            r"\bich arbeite an\s+(.+)$",
            r"\bich wohne in\s+(.+)$",
            r"\bmein\s+(?:lieblings)?projekt(?:\s+(?:heißt|heisst|namens))?\s+(.+)$",
        ):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                add_user_learning(match.group(0))
                break

        if any(marker in lower for marker in ("ich mag ", "ich liebe ", "ich bevorzuge ")):
            add_user_learning(text)

        if "merk dir" in lower or "erinnere dich" in lower:
            remembered = re.split(r"(?:merk dir|erinnere dich)\s*[:,-]?\s*", text, maxsplit=1, flags=re.IGNORECASE)[-1]
            remembered = re.sub(r"\s+", " ", remembered).strip(" .,!?:;")
            if remembered:
                inferred.append(ToolCall(
                    tool="add_short_term_memory",
                    action="add",
                    data={"content": remembered, "category": "user", "importance": "high"},
                    priority="high",
                    reason="Expliziter Erinnerungswunsch",
                ))

        existing_tools = {(call.tool, json.dumps(call.data, sort_keys=True, ensure_ascii=False)) for call in result.tool_calls}
        for call in inferred:
            key = (call.tool, json.dumps(call.data, sort_keys=True, ensure_ascii=False))
            if key not in existing_tools:
                result.tool_calls.append(call)
                existing_tools.add(key)
        if inferred:
            result.raw_json = dict(result.raw_json or {})
            result.raw_json["local_state_inference"] = True
        return result
    
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

    @staticmethod
    def _is_self_contained_request(user_input: str) -> bool:
        """Return True only when no profile, memory or prior-turn state is needed."""
        text = user_input.strip()
        if not text or len(text) > 700:
            return False
        lower = text.casefold()

        stateful_markers = (
            "merk dir", "erinnere dich", "erinnerst du", "weißt du noch",
            "weisst du noch", "gestern", "damals", "letztes mal", "vorhin",
            "mein name", "ich heiße", "ich heisse", "ich bin geboren",
            "ich wohne", "ich arbeite als", "mein projekt", "mein termin",
            "ich mag", "ich liebe", "ich hasse", "ich bevorzuge",
            "für später", "fuer spaeter", "morgen um", "nächste woche",
            "naechste woche", "mach weiter", "weiter damit", "wie zuvor",
            "wie oben", "das davor", "diese antwort", "deine letzte",
            # CHAPPiE-Persona/-Life/-Memory-Anker: diese Themen brauchen immer Kontext
            "chappie", "wie geht es dir", "wie gehts dir", "nachgedacht",
            "worüber hast du", "woroüber", "erinnerst", "gedanken",
            "erinnerungen", "systemprompt", "system prompt", "ki-modell", "ki modell",
            "welches modell", "was für ein modell", "was fuer ein modell",
            "gefühle", "gefuehle", "bewusstsein", "persona", "wer bist du",
            "was denkst du", "was fühlst du", "was fuehlst du",
            "deine identität", "deine identitaet", "dein selbstbild",
            "lange nicht", "in all der zeit", "seit wann",
        )
        if any(marker in lower for marker in stateful_markers):
            return False

        # Persona-/Identitätsfragen dürfen niemals als eigenständig gelten – sie brauchen
        # CHAPPiE-Prompt, Memory und Life-Kontext.
        persona_markers = (
            "chappie", "wer bist du", "was bist du", "erzähl von dir",
            "erzaehl von dir", "wie fühlst du", "wie fuehlst du",
            "wie geht es dir", "worüber hast du", "woroüber hast",
            "nachgedacht", "was denkst", "was beschäftigt dich",
            "was beschaeftigt dich", "deine gedanken", "dein gefühl",
            "dein gefuehl", "deine gefühle", "deine gefuehle",
            "welches modell", "was für ein modell", "was fuer ein modell",
            "ki-modell", "ki modell", "systemprompt", "system prompt",
            "deine erinnerungen", "was hast du für erinnerungen",
            "was hast du fuer erinnerungen", "deine identität", "deine identitaet",
        )
        if any(marker in lower for marker in persona_markers):
            return False

        # Explicit arithmetic is always closed. For prose requests require a
        # clear question/task verb and enough subject matter to stand alone.
        arithmetic = bool(re.search(
            r"(?:\d|null|eins|zwei|drei|vier|fünf|fuenf|sechs|sieben|acht|neun)"
            r".*(?:[-+*/=×÷]|\bminus\b|\bplus\b|\bmal\b|geteil)",
            lower,
        ))
        if arithmetic:
            return True

        request_markers = (
            "wer ", "was ", "wann ", "wo ", "warum ", "wieso ", "wie ",
            "welche", "erklär", "erklaer", "beschreib", "berechne", "nenne ",
            "vergleiche", "prüfe", "pruefe", "analysiere", "übersetze", "uebersetze",
        )
        if not ("?" in text or lower.startswith(request_markers)):
            return False
        return len(re.findall(r"\w+", text, flags=re.UNICODE)) >= 4

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
        return INTENT_SYSTEM_PROMPT_TEMPLATE.format(allowed_emotions=allowed_emotions)
    
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
        
        return INTENT_USER_PROMPT_TEMPLATE.format(
            user_input=user_input,
            current_emotions=self._format_current_emotions(current_emotions),
            history=history_str,
        )
    
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
        intent_aliases = {
            "information_request": "information_exchange",
            "fact_lookup": "information_exchange",
            "question": "information_exchange",
            "technical": "technical_discussion",
            "task": "task_execution",
            "creative": "creative_collaboration",
            "personal": "personal_sharing",
        }
        intent_type_str = intent_aliases.get(str(intent_type_str), str(intent_type_str))
        
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
                elif emotion in EMOTION_DEFAULTS and isinstance(data, (int, float)):
                    emotions_update[emotion] = EmotionUpdate(
                        delta=max(-15, min(15, int(data))),
                        reason="Intent analysis",
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
