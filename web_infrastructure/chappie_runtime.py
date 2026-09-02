import os
import threading
from datetime import datetime
from pathlib import Path

from typing import Dict, Any, List, Optional, Generator

# CHAPiE imports
from config.config import settings, PROJECT_ROOT, LLMProvider
from config.prompts import LIFE_CONTEXT_TEMPLATE
from memory.memory_engine import MemoryEngine
from memory.emotions_engine import EmotionsEngine
from memory.chat_manager import ChatManager
from memory.short_term_memory import get_short_term_memory
from memory.personality_manager import PersonalityManager
from memory.function_registry import get_function_registry
from memory.context_files import get_context_files_manager
from memory.intent_processor import get_intent_processor, reset_intent_processor
from memory.debug_logger import get_debug_logger
from memory.sleep_phase import SleepPhaseHandler, get_sleep_phase_handler
from brain import get_brain
from brain.action_response import ActionResponseLayer
from brain.steering_manager import get_steering_manager
from brain.global_workspace import GlobalWorkspace
from brain.deep_think import DeepThinkEngine
from brain.token_counter import ModelTokenCounter
from life import get_life_simulation_service
from web_infrastructure.contracts import ResponseEnvelope, StatusCallback, StreamEvent, TurnContext
from web_infrastructure.formatting import (
    prompt_chain_of_thought_enabled as prompt_chain_of_thought_enabled,
    RuntimeFormattingMixin,
    build_assistant_message as format_assistant_message,
    build_pending_message as format_pending_message,
    serialize_rag_memories,
)
from web_infrastructure.generation import (
    GenerationGateway,
    RuntimeGenerationMixin,
    calculate_generation_timing as calculate_generation_timing,
    measure_prompt_components as measure_prompt_components,
    response_memory_top_k_for_intent as response_memory_top_k_for_intent,
)
from web_infrastructure.persistence import RuntimePersistenceMixin, TurnPersistence
from web_infrastructure.turn_context import (
    build_turn_context,
    context_allows_long_term_memory as context_allows_long_term_memory,
    is_isolated_request as is_isolated_request,
    is_self_contained_math_query as is_self_contained_math_query,
    is_transient_problem_statement as is_transient_problem_statement,
)
from web_infrastructure.turn_pipeline import RuntimeTurnPipelineMixin, TurnPipeline










CHAT_PROVIDER = LLMProvider.VLLM










class CHAPPiERuntime(
    RuntimeFormattingMixin,
    RuntimeGenerationMixin,
    RuntimePersistenceMixin,
    RuntimeTurnPipelineMixin,
):
    """Public facade for CHAPPiE's active local turn runtime."""

    def __init__(
        self,
        *,
        runtime_data_dir: Optional[Path] = None,
        memory_collection_name: Optional[str] = None,
        research_mode: bool = False,
        feature_flags: Optional[Dict[str, bool]] = None,
    ):
        self.runtime_data_dir = Path(runtime_data_dir) if runtime_data_dir else None
        self.research_mode = bool(research_mode)
        self.feature_flags = {
            "persona": True,
            "memory": True,
            "emotions": True,
            "life": True,
            **dict(feature_flags or {}),
        }
        if self.runtime_data_dir:
            self.runtime_data_dir.mkdir(parents=True, exist_ok=True)
        # Module init
        self.memory = MemoryEngine(
            persist_directory=self.runtime_data_dir / "chroma" if self.runtime_data_dir else None,
            collection_name=memory_collection_name,
        )
        self.emotions = EmotionsEngine(
            status_file=self.runtime_data_dir / "status.json" if self.runtime_data_dir else None,
            # Emotion changes stay deterministic and local. The main
            # vLLM request then receives those values through activation
            # steering without an auxiliary sentiment-model route.
            force_simple=True,
        )
        self.brain = get_brain(provider=self._chat_provider(), model=self._chat_model())
        self._current_provider = self._chat_provider()
        self._brain_signature = self._build_brain_signature()

        # Chat Manager init
        data_dir = str(self.runtime_data_dir) if self.runtime_data_dir else os.path.join(PROJECT_ROOT, "data")
        self.chat_manager = ChatManager(data_dir)

        # Deep Think Engine
        self.deep_think_engine = DeepThinkEngine(
            memory_engine=self.memory,
            emotions_engine=self.emotions,
            brain=self.brain
        )

        # NEU: Context Files Manager (soul.md, user.md, CHAPPiEsPreferences.md)
        if self.runtime_data_dir:
            from memory.context_files import ContextFilesManager
            self.context_files = ContextFilesManager(base_dir=self.runtime_data_dir)
        else:
            self.context_files = get_context_files_manager()
        self.sleep_handler = (
            SleepPhaseHandler(state_path=self.runtime_data_dir / "sleep_state.json")
            if self.runtime_data_dir
            else get_sleep_phase_handler()
        )
        self._sleep_job_lock = threading.Lock()

        # Short-Term Memory (JSON-basiert mit Timestamps)
        if self.runtime_data_dir:
            from memory.short_term_memory import ShortTermMemory
            self.short_term_memory = ShortTermMemory(
                memory_engine=self.memory,
                storage_path=self.runtime_data_dir / "short_term_memory.json",
            )
        else:
            self.short_term_memory = get_short_term_memory(memory_engine=self.memory)
        
        # Migration von abgelaufenen Eintraegen beim Start
        try:
            migrated = self.short_term_memory.migrate_expired_entries()
            if migrated > 0:
                print(f"[CHAPPiE] {migrated} Eintraege ins Langzeitgedaechtnis migriert")
        except Exception as e:
            print(f"[CHAPPiE] Migration fehlgeschlagen: {e}")

        # NEU: Intent Processor (Step 1)
        self.intent_processor = get_intent_processor()
        self._intent_signature = self._build_intent_signature()

        # NEU: Debug Logger
        self.debug_logger = get_debug_logger()
        # CLI Debug ist immer an
        if settings.cli_debug_always_on:
            self.debug_logger.enable()

        # Personality Manager
        self.personality_manager = PersonalityManager(
            personality_path=self.runtime_data_dir / "personality.md" if self.runtime_data_dir else None,
        )

        # Function Registry
        self.function_registry = get_function_registry()
        if self.runtime_data_dir:
            from life.service import LifeSimulationService
            self.life_simulation = LifeSimulationService(
                state_path=self.runtime_data_dir / "life_state.json",
                personality_manager=self.personality_manager,
            )
        else:
            self.life_simulation = get_life_simulation_service()
        self.global_workspace = GlobalWorkspace()
        self.action_response = ActionResponseLayer()
        self.steering_manager = get_steering_manager()
        self.last_memory_timestamp: Optional[str] = None
        self._token_counter: Optional[ModelTokenCounter] = None
        self._token_counter_model: Optional[str] = None
        self.generation = GenerationGateway(lambda: self.brain)
        self.persistence = TurnPersistence(
            memory_getter=lambda: self.memory,
            short_term_memory_getter=lambda: self.short_term_memory,
            timestamp_callback=self._set_last_memory_timestamp,
        )
        self.turn_pipeline = TurnPipeline(self)
    def _feature_enabled(self, name: str) -> bool:
        return bool(self.feature_flags.get(name, True))

    @staticmethod
    def _chat_provider() -> LLMProvider:
        """The web chat has one inference route: local vLLM."""
        return CHAT_PROVIDER

    @staticmethod
    def _chat_model() -> str:
        """Return the single local model used by every chat inference step."""
        return settings.resolve_vllm_runtime_model(settings.vllm_model)

    @staticmethod
    def _single_local_chat_mode() -> bool:
        return True

    @staticmethod
    def _neutral_life_snapshot() -> Dict[str, Any]:
        return {
            "disabled": True,
            "current_mode": "neutral",
            "homeostasis": {"emotion_adjustments": {}, "active_needs": [], "dominant_need": {}},
            "recent_events": [],
            "dream_fragments": [],
        }

    def _prepare_life_turn(self, *args, **kwargs) -> Dict[str, Any]:
        if not self._feature_enabled("life"):
            return self._neutral_life_snapshot()
        return self.life_simulation.prepare_turn(*args, **kwargs)

    def _finalize_life_turn(self, *args, **kwargs) -> Dict[str, Any]:
        if not self._feature_enabled("life"):
            return self._neutral_life_snapshot()
        return self.life_simulation.finalize_turn(*args, **kwargs)

    def get_emotions_snapshot(self) -> Dict[str, int]:
        """Return the current emotion values through the public runtime API."""
        return self._get_emotions_snapshot()

    def _build_life_prompt_context(
        self,
        life_context: Dict[str, Any] | None,
        global_workspace: Dict[str, Any] | None,
    ) -> str:
        """Serialize the live inner-state contract for the local model.

        Life simulation and workspace used to affect only metadata,
        action planning and steering. The model therefore received no
        usable signal that CHAPPiE had a current phase, needs, goals or
        attention focus. Keep the block compact and instruct the model
        to express it naturally instead of exposing implementation keys.
        """
        if not life_context and not global_workspace:
            return ""
        try:
            state = self.action_response.build_prompt_suffix(
                {},
                life_context or {},
                global_workspace or {},
            )
        except Exception:
            state = ""
        if not state:
            return ""
        return LIFE_CONTEXT_TEMPLATE.format(state=state)











    @staticmethod
    def serialize_rag_memories(memories: List[Any] | None) -> List[Dict[str, Any]]:
        return serialize_rag_memories(memories)

    @staticmethod
    def _serialize_rag_memories(memories: List[Any] | None) -> List[Dict[str, Any]]:
        """Compatibility alias for callers using the historical private helper."""
        return serialize_rag_memories(memories)

    def build_assistant_message(
        self,
        user_input: str,
        result: Dict[str, Any],
        message_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return format_assistant_message(user_input, result, message_id=message_id)

    def _build_assistant_message(
        self,
        user_input: str,
        result: Dict[str, Any],
        message_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compatibility alias for the former private router dependency."""
        return self.build_assistant_message(user_input, result, message_id=message_id)

    @staticmethod
    def build_pending_message(message_id: str) -> Dict[str, Any]:
        return format_pending_message(message_id)

    def _build_pending_message(self, message_id: str) -> Dict[str, Any]:
        """Compatibility alias for the former private router dependency."""
        return self.build_pending_message(message_id)


    def _provider_runtime_signature(self, provider: LLMProvider, model: str):
        if provider == LLMProvider.OLLAMA:
            return (provider.value, model, settings.ollama_host)
        if provider == LLMProvider.VLLM:
            return (provider.value, model, settings.vllm_url)
        if provider == LLMProvider.GROQ:
            return (provider.value, model, settings.groq_api_key)
        return (provider.value, model)

    def _build_brain_signature(self):
        return self._provider_runtime_signature(self._chat_provider(), self._chat_model())

    def _build_intent_signature(self):
        return (
            "single_local_chat",
            *self._provider_runtime_signature(self._chat_provider(), self._chat_model()),
        )

    def apply_runtime_settings(self, force: bool = False):
        changed = False
        brain_signature = self._build_brain_signature()
        if force or brain_signature != self._brain_signature:
            old_label = self._brain_signature[:2] if self._brain_signature else None
            new_label = brain_signature[:2]
            print(f"Runtime-Reload Hauptmodell: {old_label} -> {new_label}")
            self.brain = get_brain(provider=self._chat_provider(), model=self._chat_model())
            self._brain_signature = brain_signature
            self._current_provider = self._chat_provider()
            self.deep_think_engine = DeepThinkEngine(
                memory_engine=self.memory,
                emotions_engine=self.emotions,
                brain=self.brain
            )
            self.steering_manager.refresh_runtime_profile(self._chat_model())
            changed = True

        intent_signature = self._build_intent_signature()
        if force or changed or intent_signature != self._intent_signature:
            old_label = self._intent_signature[:3] if self._intent_signature else None
            new_label = intent_signature[:3]
            print(f"Runtime-Reload Intent: {old_label} -> {new_label}")
            reset_intent_processor()
            self.intent_processor = get_intent_processor()
            self._intent_signature = intent_signature
            changed = True
        return changed

    def reinit_brain_if_needed(self):
        """Abwaertskompatibler Alias fuer Runtime-Reload."""
        return self.apply_runtime_settings()























    GROQ_FORMAT_MODEL = "openai/gpt-oss-120b"














    def get_status(self) -> Dict[str, Any]:
        try:
            brain_ok = self.brain.is_available()
        except Exception:
            brain_ok = False

        life_snapshot = self.life_simulation.get_snapshot()
        emotions = self._get_emotions_snapshot()
        steering_payload = self.steering_manager.get_steering_payload(
            emotions,
            force=True,
            provider=CHAT_PROVIDER,
            model=self._chat_model(),
        )

        return {
            "brain_available": brain_ok,
            "model": self._chat_model(),
            "provider": self._chat_provider().value,
            "routing": "single_local_vllm",
            "emotion_steering_forced": True,
            "emotion_steering_active": bool(steering_payload.get("steering")),
            "steering_transport": "activation_addition",
            "emotions": emotions,
            "daily_info_count": self.short_term_memory.get_count(),
            "two_step_enabled": True,
            "life_snapshot": life_snapshot,
            "life_state": life_snapshot,
        }

    def get_emotion_layer_config(self, current_emotions: Optional[Dict[str, int]] = None) -> List[Dict[str, Any]]:
        snapshot = current_emotions or self._get_emotions_snapshot()
        return self.steering_manager.get_emotion_layer_config(snapshot)

    def update_emotion_layer_config(self, emotion_name: str, layer_start: int, layer_end: int, default_alpha: float) -> Optional[Dict[str, Any]]:
        return self.steering_manager.update_vector_config(
            emotion_name,
            layer_start=layer_start,
            layer_end=layer_end,
            default_alpha=default_alpha,
        )





    def process(
        self,
        user_input: str,
        history: List[Dict],
        debug_mode: bool = False,
        status_callback: Optional[StatusCallback] = None,
        temporal_context: Optional[Dict[str, Any]] = None,
    ) -> ResponseEnvelope:
        """Run a turn through the shared pipeline and return the final envelope."""
        turn = build_turn_context(
            user_input,
            history,
            debug_mode=debug_mode,
            status_callback=status_callback,
            temporal_context=temporal_context,
        )
        return self.turn_pipeline.process(turn)

    def _begin_turn(self, turn: TurnContext, *, streaming: bool) -> None:
        """Apply the setup shared by synchronous and streamed turns."""
        if turn.debug_mode:
            self.debug_logger.enable()
        elif not settings.cli_debug_always_on:
            self.debug_logger.disable()

        if self.debug_logger.enabled:
            self.debug_logger.clear()
            self.debug_logger.log_info(
                "TURN",
                "Neuer Streaming-Turn gestartet" if streaming else "Neuer Turn gestartet",
                {
                    "provider": self._chat_provider().value,
                    "model": self._chat_model(),
                    "history_messages": len(turn.history),
                },
            )

        self.apply_runtime_settings()
        self._processing_start_time = datetime.now()
















    def _shrink_message_in_context(self, messages: list, index: int, token_limit: int) -> tuple[list, bool]:
        content = self._msg_content(messages[index])
        if not content or self._estimate_total_tokens(messages) <= token_limit:
            return messages, False

        marker = "\n[... wegen Tokenbudget gekuerzt ...]\n"
        low, high = 0, len(content)
        best = marker.strip()
        while low <= high:
            keep = (low + high) // 2
            head = (keep + 1) // 2
            tail = keep // 2
            candidate_content = content[:head].rstrip() + marker
            if tail:
                candidate_content += content[-tail:].lstrip()
            candidate = list(messages)
            candidate[index] = self._copy_msg_with_content(messages[index], candidate_content)
            if self._estimate_total_tokens(candidate) <= token_limit:
                best = candidate_content
                low = keep + 1
            else:
                high = keep - 1

        result = list(messages)
        result[index] = self._copy_msg_with_content(messages[index], best)
        return result, best != content

















    def process_stream(
        self,
        user_input: str,
        history: List[Dict],
        debug_mode: bool = False,
        status_callback: Optional[StatusCallback] = None,
        temporal_context: Optional[Dict[str, Any]] = None,
    ) -> Generator[StreamEvent, None, None]:
        """Run a turn through the shared pipeline and stream its events."""
        turn = build_turn_context(
            user_input,
            history,
            debug_mode=debug_mode,
            status_callback=status_callback,
            temporal_context=temporal_context,
        )
        yield from self.turn_pipeline.process_stream(turn)


    # === Command Handler ===

    def handle_command(self, command: str) -> str:
        """Verarbeitet Slash-Commands."""
        cmd = command.lower().strip()

        if cmd == "/daily" or cmd == "/shortterm":
            entries = self.short_term_memory.get_active_entries()
            if not entries:
                return "Keine Eintraege im Kurzzeitgedaechtnis."
            lines = ["**Kurzzeitgedaechtnis (24h):**\\n"]
            for entry in entries[:20]:
                from datetime import datetime 
                created = datetime.fromisoformat(entry.created_at)
                time_str = created.strftime("%d.%m %H:%M")
                lines.append(f"- [{time_str}] [{entry.importance}] [{entry.category}] {entry.content}")
            return "\\n".join(lines)

        elif cmd == "/personality":
            return self.personality_manager.get_for_prompt()
        
        elif cmd == "/soul":
            return self.context_files.get_soul_context()
        
        elif cmd == "/user":
            return self.context_files.get_user_context()
        
        elif cmd == "/prefs" or cmd == "/preferences":
            return self.context_files.get_preferences_context()

        elif cmd == "/consolidate":
            migrated = self.short_term_memory.migrate_expired_entries()
            return f"Bereinigung abgeschlossen: {migrated} Eintraege migriert."

        elif cmd == "/reflect":
            insights = self.personality_manager.get_recent_reflections(limit=3)
            return "Deine letzten Selbst-Reflexionen:\\n" + "\\n".join(insights) if insights else "Noch keine Reflexionen dokumentiert."

        elif cmd == "/functions":
            funcs = self.function_registry.get_function_names()
            return "Verfuegbare Funktionen:\\n" + "\\n".join(f"- {f}" for f in funcs)
        
        elif cmd == "/life":
            snapshot = self.life_simulation.get_snapshot()
            need_lines = [f"- {item['name']}: {item['value']}" for item in snapshot.get("homeostasis", {}).get("active_needs", [])[:6]]
            goal = snapshot.get("active_goal", {})
            world = snapshot.get("world_model", {})
            development = snapshot.get("development", {})
            attachment = snapshot.get("attachment_model", {})
            planning = snapshot.get("planning_state", {})
            social_arc = snapshot.get("social_arc", {})
            temporal = snapshot.get("temporal_state", {})
            episode = snapshot.get("episode_state", {})
            gap = temporal.get("minutes_since_last_interaction")
            gap_text = "erste Interaktion" if gap is None else f"{gap:.1f} Minuten seit letzter User-Nachricht"
            return (
                f"**Life Simulation**\n\n"
                f"Phase: {snapshot.get('clock', {}).get('phase_label', 'unbekannt')}\n"
                f"Zeitgefuehl: {gap_text} | Rhythmus: {temporal.get('interaction_rhythm', 'new')} | Pause: {temporal.get('silence_bucket', 'first_contact')}\n"
                f"Episode: {episode.get('topic', 'conversation')} ({episode.get('turn_count', 0)} Turns, {episode.get('elapsed_minutes', 0):.1f} min)\n"
                f"Aktivitaet: {snapshot.get('current_activity', '---')}\n"
                f"Modus: {snapshot.get('current_mode', '---')}\n"
                f"Fokusziel: {goal.get('title', '---')} ({goal.get('progress', 0):.0%})\n"
                f"Entwicklungsphase: {development.get('stage', '---')} -> {development.get('next_stage', '---')}\n"
                f"Bindung: {attachment.get('bond_type', '---')} ({attachment.get('attachment_security', 0):.2f})\n"
                f"Planung: {planning.get('planning_horizon', '---')} | {planning.get('next_milestone', '---')}\n"
                f"Social Arc: {social_arc.get('arc_name', '---')}\n"
                f"World Model: {world.get('predicted_user_need', '---')}\n"
                f"Next Best Action: {world.get('next_best_action', '---')}\n\n"
                + "\n".join(need_lines)
            )

        elif cmd == "/needs":
            snapshot = self.life_simulation.get_snapshot()
            return "\n".join(
                f"- {item['name']}: {item['value']} (Druck {item['pressure']})"
                for item in snapshot.get("homeostasis", {}).get("active_needs", [])
            )

        elif cmd == "/goals":
            snapshot = self.life_simulation.get_snapshot()
            goal_competition = snapshot.get("goal_competition", {})
            lines = ["Goal Competition:"]
            for goal in goal_competition.get("competition_table", [])[:5]:
                lines.append(f"- {goal.get('title', '---')}: Score {goal.get('score', 0):.2f} | Progress {goal.get('progress', 0):.0%}")
            return "\n".join(lines)

        elif cmd == "/habits":
            snapshot = self.life_simulation.get_snapshot()
            habits = sorted(snapshot.get("habits", {}).items(), key=lambda item: item[1].get("strength", 0), reverse=True)
            lines = ["Habit Engine:"]
            for name, meta in habits[:5]:
                lines.append(f"- {meta.get('label', name)}: Staerke {meta.get('strength', 0):.2f} | Count {meta.get('count', 0)} | Trend {meta.get('trend', 'stable')}")
            return "\n".join(lines)

        elif cmd == "/stage":
            snapshot = self.life_simulation.get_snapshot()
            development = snapshot.get("development", {})
            lines = [
                f"Stage: {development.get('stage', '---')}",
                f"Next Stage: {development.get('next_stage', '---')}",
                f"Development Score: {development.get('development_score', 0):.2f}",
                f"Progress To Next: {development.get('progress_to_next', 0):.0%}",
            ]
            for item in development.get("milestones", [])[:4]:
                lines.append(f"- {item}")
            return "\n".join(lines)

        elif cmd == "/plan":
            snapshot = self.life_simulation.get_snapshot()
            planning = snapshot.get("planning_state", {})
            lines = [
                f"Planning Horizon: {planning.get('planning_horizon', '---')}",
                f"Coordination Mode: {planning.get('coordination_mode', '---')}",
                f"Milestone: {planning.get('next_milestone', '---')}",
                f"Confidence: {planning.get('plan_confidence', 0):.2f}",
            ]
            for item in planning.get("immediate_steps", [])[:3]:
                lines.append(f"- {item}")
            for item in planning.get("bottlenecks", [])[:3]:
                lines.append(f"! {item}")
            return "\n".join(lines)

        elif cmd == "/forecast":
            snapshot = self.life_simulation.get_snapshot()
            forecast = snapshot.get("forecast_state", {})
            lines = [
                f"Risk Level: {forecast.get('risk_level', '---')}",
                f"Next Turn: {forecast.get('next_turn_outlook', '---')}",
                f"Daily Outlook: {forecast.get('daily_outlook', '---')}",
                f"Stage Trajectory: {forecast.get('stage_trajectory', '---')}",
            ]
            for item in forecast.get("protective_factors", [])[:4]:
                lines.append(f"- {item}")
            return "\n".join(lines)

        elif cmd == "/arc":
            snapshot = self.life_simulation.get_snapshot()
            social_arc = snapshot.get("social_arc", {})
            lines = [
                f"Arc Name: {social_arc.get('arc_name', '---')}",
                f"Phase: {social_arc.get('phase', '---')}",
                f"Arc Score: {social_arc.get('arc_score', 0):.2f}",
                f"Episode: {social_arc.get('current_episode', '---')}",
                f"Guidance: {social_arc.get('guidance', '---')}",
            ]
            for item in social_arc.get("recent_episode_titles", [])[:4]:
                lines.append(f"- {item}")
            return "\n".join(lines)

        elif cmd == "/timeline":
            snapshot = self.life_simulation.get_snapshot()
            summary = snapshot.get("timeline_summary", {})
            history = snapshot.get("timeline_history", [])
            lines = [
                f"Entries: {summary.get('entries', 0)}",
                f"Summary: {summary.get('summary', '---')}",
            ]
            for item in history[-5:]:
                lines.append(
                    f"- {item.get('phase_label', '---')} | {item.get('source', '---')} | Pause={item.get('silence_bucket', '---')} | Episode={item.get('episode_topic', '---')} | Goal={item.get('goal', '---')} | Stage={item.get('stage', '---')}"
                )
            return "\n".join(lines)

        elif cmd == "/world":
            snapshot = self.life_simulation.get_snapshot()
            world = snapshot.get("world_model", {})
            risks = world.get("risk_factors", [])
            opportunities = world.get("opportunities", [])
            attachment = snapshot.get("attachment_model", {})
            lines = [
                f"Interaction Mode: {world.get('interaction_mode', '---')}",
                f"Predicted User Need: {world.get('predicted_user_need', '---')}",
                f"Next Best Action: {world.get('next_best_action', '---')}",
                f"Trajectory: {world.get('expected_trajectory', '---')}",
                f"Confidence: {world.get('confidence', 0):.2f}",
                f"Attachment Guidance: {attachment.get('guidance', '---')}",
            ]
            if risks:
                lines.append("Risks: " + " | ".join(risks))
            if opportunities:
                lines.append("Opportunities: " + " | ".join(opportunities))
            return "\n".join(lines)

        elif cmd == "/debug":
            # Toggle Debug Mode
            if self.debug_logger.enabled:
                self.debug_logger.disable()
                return "Debug Mode: AUS"
            else:
                self.debug_logger.enable()
                return "Debug Mode: AN\\n\\n" + self.debug_logger.get_formatted_log()
        
        elif cmd == "/step1":
            # Zeige letzten Step 1 JSON
            debug_entries = self.debug_logger.get_entries_by_category("STEP1_JSON")
            if debug_entries:
                last_entry = debug_entries[-1]
                json_preview = last_entry.details.get("json_preview", "Keine Daten")
                return f"**Letzter Step 1 JSON:**\\n\\n```json\\n{json_preview}\\n```"
            return "Noch kein Step 1 JSON vorhanden."
        
        elif cmd == "/twostep":
            return "Zwei-Schritte System: immer aktiv (ein lokaler vLLM-Pfad mit Emotion-Steering)."

        return f"Unbekannter Command: {command}"


CHAPPiEBackend = CHAPPiERuntime


def create_chappie_backend(
    *,
    runtime_data_dir: Optional[Path] = None,
    memory_collection_name: Optional[str] = None,
    research_mode: bool = False,
    feature_flags: Optional[Dict[str, bool]] = None,
) -> CHAPPiERuntime:
    """Create the active runtime while preserving the historical factory API."""
    return CHAPPiERuntime(
        runtime_data_dir=runtime_data_dir,
        memory_collection_name=memory_collection_name,
        research_mode=research_mode,
        feature_flags=feature_flags,
    )


def init_chappie() -> CHAPPiERuntime:
    """Initialize the backend without a UI-specific cache."""
    return create_chappie_backend()
