import streamlit as st
import os
import re
from typing import Dict, Any, List

# CHAPiE imports
from config.config import settings, get_active_model, PROJECT_ROOT
from config.prompts import get_system_prompt_with_emotions, get_personality_context, get_function_calling_instruction
from memory.memory_engine import MemoryEngine
from memory.emotions_engine import EmotionsEngine, analyze_sentiment_simple
from memory.chat_manager import ChatManager
from memory.short_term_memory import ShortTermMemory
from memory.personality_manager import PersonalityManager
from memory.function_registry import get_function_registry
from brain import get_brain
from brain.base_brain import GenerationConfig, Message
from brain.response_parser import parse_chain_of_thought
from brain.deep_think import DeepThinkEngine


@st.cache_resource
def init_chappie():
    """Initialisiert das Backend (Memory, Emotions, Brain, ChatManager, Short-Term Memory, Personality, Functions)."""
    class CHAPPiEBackend:
        def __init__(self):
            # Module init
            self.memory = MemoryEngine()
            self.emotions = EmotionsEngine()
            self.brain = get_brain()
            self._current_provider = settings.llm_provider  # Track current provider

            # Chat Manager init
            data_dir = os.path.join(PROJECT_ROOT, "data")
            self.chat_manager = ChatManager(data_dir)

            # Deep Think Engine
            self.deep_think_engine = DeepThinkEngine(
                memory_engine=self.memory,
                emotions_engine=self.emotions,
                brain=self.brain
            )

            # NEU: Short-Term Memory (Daily Info)
            self.short_term_memory = ShortTermMemory(memory_engine=self.memory)
            
            # P2-FIX: Automatische Bereinigung abgelaufener Einträge beim Start
            try:
                cleaned = self.short_term_memory.cleanup_expired()
                if cleaned > 0:
                    print(f"   Short-Term Memory: {cleaned} abgelaufene Einträge bereinigt")
            except Exception as e:
                print(f"   WARNUNG: Short-Term Memory Bereinigung fehlgeschlagen: {e}")

            # NEU: Personality Manager
            self.personality_manager = PersonalityManager()

            # NEU: Function Registry
            self.function_registry = get_function_registry()
        
        def reinit_brain_if_needed(self):
            """Prüfe ob der Provider gewechselt wurde und initialisiere Brain neu."""
            if settings.llm_provider != self._current_provider:
                print(f"🔄 Provider wechsel erkannt: {self._current_provider} -> {settings.llm_provider}")
                self.brain = get_brain()  # Neu laden
                self._current_provider = settings.llm_provider
                # Deep Think Engine auch neu laden
                self.deep_think_engine = DeepThinkEngine(
                    memory_engine=self.memory,
                    emotions_engine=self.emotions,
                    brain=self.brain
                )
                return True
            return False

        def get_status(self) -> Dict[str, Any]:
            state = self.emotions.get_state()
            try:
                brain_ok = self.brain.is_available()
            except:
                brain_ok = False

            return {
                "brain_available": brain_ok,
                "model": get_active_model(),
                "emotions": {
                    "joy": state.happiness,
                    "trust": state.trust,
                    "energy": state.energy,
                    "curiosity": state.curiosity,
                },
                "daily_info_count": self.short_term_memory.get_count(),
            }

        def _get_emotions_snapshot(self) -> Dict[str, int]:
            """Erstellt einen Snapshot der aktuellen Emotionen."""
            state = self.emotions.get_state()
            return {
                "joy": state.happiness,
                "trust": state.trust,
                "energy": state.energy,
                "curiosity": state.curiosity,
                "frustration": state.frustration,
                "motivation": state.motivation
            }

        def _extract_function_calls(self, response: str) -> List[Dict]:
            """
            Extrahiert Funktionsaufrufe aus der Antwort.

            Args:
                response: Die LLM-Antwort

            Returns:
                Liste von Funktionsaufrufen
            """
            pattern = r'<function_call>\s*(\{.*?\})\s*</function_call>'
            matches = re.findall(pattern, response, re.DOTALL)

            function_calls = []
            for match in matches:
                try:
                    func_data = eval(match)
                    function_calls.append(func_data)
                except:
                    continue

            return function_calls

        def _execute_function_calls(self, function_calls: List[Dict]) -> str:
            """
            Führt alle Funktionsaufrufe aus und gibt die Ergebnisse zurück.

            Args:
                function_calls: Liste von Funktionsaufrufen

            Returns:
                Formatierte Ergebnisse
            """
            results = []
            for func_call in function_calls:
                func_name = func_call.get("name", "")
                args = func_call.get("arguments", {})

                if self.function_registry.has_function(func_name):
                    result = self.function_registry.execute(func_name, args)
                    results.append(f"Funktion {func_name}: {result}")
                else:
                    results.append(f"FEHLER: Unbekannte Funktion {func_name}")

            return "\n".join(results)

        def process(self, user_input: str, history: List[Dict]) -> Dict[str, Any]:
            # ===== BRAIN MONITOR: Emotionen VORHER =====
            emotions_before = self._get_emotions_snapshot()

            # 1. LLM-basierte Emotions-Analyse (intelligent, kontextbewusst)
            self.emotions.update_from_sentiment(analyze_sentiment_simple(user_input))

            # ===== BRAIN MONITOR: Emotionen NACHHER =====
            emotions_after = self._get_emotions_snapshot()

            # ===== BRAIN MONITOR: Delta berechnen =====
            emotions_delta = {}
            for key in emotions_before:
                delta = emotions_after[key] - emotions_before[key]
                if delta != 0:
                    emotions_delta[key] = {
                        "before": emotions_before[key],
                        "after": emotions_after[key],
                        "change": delta
                    }

            # 2. RAG Memory Search
            memories = self.memory.search_memory(user_input, top_k=settings.memory_top_k)
            memories_for_prompt = self.memory.format_memories_for_prompt(memories)

            # NEU: Daily Info Context
            daily_info_for_prompt = self.short_term_memory.get_formatted_for_prompt(query=user_input)

            # 3. Prompt Building mit Persönlichkeit und Functions
            state = self.emotions.get_state()
            system_prompt = get_system_prompt_with_emotions(
                **state.__dict__,
                use_chain_of_thought=settings.chain_of_thought
            )

            # NEU: Persönlichkeits-Kontext hinzufügen
            personality_context = get_personality_context()
            system_prompt += f"\n\n{personality_context}"

            # NEU: Function-Calling Instruction (wenn aktiviert)
            if settings.enable_functions:
                func_instruction = get_function_calling_instruction()
                system_prompt += f"\n\n{func_instruction}"

            # NEU: Daily Info zum Prompt hinzufügen
            if daily_info_for_prompt:
                system_prompt += f"\n\n{daily_info_for_prompt}"

            # Baue Nachrichten-Verlauf beachte Context
            messages = self.brain.build_prompt(system_prompt, memories_for_prompt, user_input, history)

            # 4. Generierung
            gen_config = GenerationConfig(
                max_tokens=settings.max_tokens,
                temperature=settings.temperature,
                stream=False,
            )
            raw_response = self.brain.generate(messages, config=gen_config)

            # 5. Function-Calling Check
            function_calls = self._extract_function_calls(raw_response)
            function_results = ""

            if function_calls:
                # Entferne function_call Tags für die Anzeige
                display_response = re.sub(r'<function_call>.*?</function_call>', '', raw_response, flags=re.DOTALL).strip()
                # Führe Funktionen aus
                function_results = self._execute_function_calls(function_calls)
                # Wenn Functions ausgeführt wurden, generiere nochmal ohne die Funktionsaufrufe
                if function_results:
                    messages.append(Message(role="user", content=f"Ergebnisse der Funktionsaufrufe:\n{function_results}\n\nBitte antworte jetzt auf die ursprüngliche Anfrage unter Berücksichtigung dieser Ergebnisse."))
                    raw_response = self.brain.generate(messages, config=gen_config)
            else:
                display_response = raw_response

            # 6. Parsing (CoT)
            if settings.chain_of_thought:
                parsed = parse_chain_of_thought(display_response)
                display_response = parsed.answer
                thought = parsed.thought or ""
            else:
                thought = ""

            # 7. Kurzzeitgedaechtnis speichern (ChromaDB)
            self.memory.add_memory(user_input, role="user")
            self.memory.add_memory(display_response, role="assistant")

            # NEU: Automatisch wichtige Infos in Daily Info speichern
            if self._should_store_in_daily_info(user_input):
                info = self._extract_daily_info(user_input)
                if info:
                    importance = "high" if self._is_important(user_input) else "normal"
                    self.short_term_memory.add_info(
                        content=info,
                        importance=importance,
                        category="user"
                    )

            return {
                "response_text": display_response,
                "emotions": emotions_after,
                "emotions_before": emotions_before,
                "emotions_delta": emotions_delta,
                "thought_process": thought,
                "rag_memories": memories,
                "input_analysis": user_input,
                "function_results": function_results,
                "daily_info_count": self.short_term_memory.get_count(),
            }

        def _should_store_in_daily_info(self, user_input: str) -> bool:
            """
            Prüft ob die User-Eingabe wichtige Infos enthält die im Daily Info gespeichert werden sollten.
            """
            important_keywords = [
                "ich heiße", "mein name", "ich mag", "ich hasse",
                "ich möchte", "ich brauche", "erinnere mich",
                "ich arbeite", "ich wohne", "ich studiere"
            ]

            user_lower = user_input.lower()
            return any(keyword in user_lower for keyword in important_keywords)

        def _extract_daily_info(self, user_input: str) -> str:
            """
            Extrahiert wichtige Infos aus der User-Eingabe.
            """
            # Einfache Extraktion - könnte mit LLM verbessert werden
            user_lower = user_input.lower()

            if "ich heiße" in user_lower or "mein name" in user_lower:
                return f"User hat sich vorgestellt: {user_input}"
            elif "ich mag" in user_lower:
                return f"User mag: {user_input}"
            elif "ich hasse" in user_lower:
                return f"User hasst/nicht mag: {user_input}"
            elif "ich wohne" in user_lower or "ich lebe" in user_lower:
                return f"Wohnort/Standort: {user_input}"
            elif "ich arbeite" in user_lower or "ich jobbe" in user_lower:
                return f"Arbeit/Beruf: {user_input}"
            else:
                return user_input[:100] if len(user_input) > 100 else user_input

        def _is_important(self, user_input: str) -> bool:
            """Prüft ob die Info besonders wichtig ist."""
            important_patterns = ["erinnere mich", "wichtig", "merke dir", "nicht vergessen"]
            user_lower = user_input.lower()
            return any(pattern in user_lower for pattern in important_patterns)

        # === NEU: Command Handler ===

        def handle_command(self, command: str) -> str:
            """Verarbeitet Slash-Commands."""
            cmd = command.lower().strip()

            if cmd == "/daily":
                infos = self.short_term_memory.get_relevant_infos()
                if not infos:
                    return "Keine Einträge im Kurzzeitgedächtnis."
                lines = ["**Kurzzeitgedächtnis:**\n"]
                for timestamp, importance, category, content in infos:
                    lines.append(f"- [{importance}] [{category}] {content}")
                return "\n".join(lines)

            elif cmd == "/personality":
                return self.personality_manager.get_for_prompt()

            elif cmd == "/consolidate":
                count = self.short_term_memory.cleanup_expired()
                return f"Bereinigung abgeschlossen: {count} abgelaufene Einträge entfernt."

            elif cmd == "/reflect":
                # CHAPI reflektiert über seine Persönlichkeit
                insights = self.personality_manager.get_recent_reflections(limit=3)
                return f"Deine letzten Selbst-Reflexionen:\n" + "\n".join(insights) if insights else "Noch keine Reflexionen dokumentiert."

            elif cmd == "/functions":
                funcs = self.function_registry.get_function_names()
                return "Verfügbare Funktionen:\n" + "\n".join(f"- {f}" for f in funcs)

            return f"Unbekannter Command: {command}"

    return CHAPPiEBackend()
