import streamlit as st
import os
from typing import Dict, Any, List

# CHAPiE imports
from config.config import settings, get_active_model, PROJECT_ROOT
from config.prompts import get_system_prompt_with_emotions
from memory.memory_engine import MemoryEngine
from memory.emotions_engine import EmotionsEngine, analyze_sentiment_simple
from memory.chat_manager import ChatManager
from brain import get_brain
from brain.base_brain import GenerationConfig
from brain.response_parser import parse_chain_of_thought
from brain.deep_think import DeepThinkEngine

@st.cache_resource
def init_chappie():
    """Initialisiert das Backend (Memory, Emotions, Brain, ChatManager)."""
    class CHAPPiEBackend:
        def __init__(self):
            # Module init
            self.memory = MemoryEngine()
            self.emotions = EmotionsEngine()
            self.brain = get_brain()
            # Chat Manager init
            data_dir = os.path.join(PROJECT_ROOT, "data")
            self.chat_manager = ChatManager(data_dir)
            # Deep Think Engine
            self.deep_think_engine = DeepThinkEngine(
                memory_engine=self.memory,
                emotions_engine=self.emotions,
                brain=self.brain
            )

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
        
        def process(self, user_input: str, history: List[Dict]) -> Dict[str, Any]:
            # ===== BRAIN MONITOR: Emotionen VORHER =====
            emotions_before = self._get_emotions_snapshot()
            
            # 1. LLM-basierte Emotions-Analyse (intelligent, kontextbewusst)
            # Fallback auf Regex-Analyse für Performance (kein Model-Swap)
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

            # 3. Prompt Building
            state = self.emotions.get_state()
            system_prompt = get_system_prompt_with_emotions(
                **state.__dict__,
                use_chain_of_thought=settings.chain_of_thought
            )

            # Baue Nachrichten-Verlauf beachte Context
            messages = self.brain.build_prompt(system_prompt, memories_for_prompt, user_input, history)

            # 4. Generierung
            gen_config = GenerationConfig(
                max_tokens=settings.max_tokens,
                temperature=settings.temperature,
                stream=False,
            )
            raw_response = self.brain.generate(messages, config=gen_config)

            # 5. Parsing (CoT)
            if settings.chain_of_thought:
                parsed = parse_chain_of_thought(raw_response)
                display_response = parsed.answer
                thought = parsed.thought or ""
            else:
                display_response = raw_response
                thought = ""
            
            # 6. Kurzzeitgedaechtnis speichern
            self.memory.add_memory(user_input, role="user")
            self.memory.add_memory(display_response, role="assistant")

            return {
                "response_text": display_response,
                "emotions": emotions_after,
                "emotions_before": emotions_before,  # BRAIN MONITOR
                "emotions_delta": emotions_delta,    # BRAIN MONITOR
                "thought_process": thought,
                "rag_memories": memories,
                "input_analysis": user_input,        # BRAIN MONITOR
            }

    return CHAPPiEBackend()
