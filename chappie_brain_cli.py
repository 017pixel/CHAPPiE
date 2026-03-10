"""Interaktive CHAPPiE-CLI auf Basis des echten Web-/Runtime-Pfads."""

import sys
import colorama
from datetime import datetime
from typing import Dict, Any

colorama.init(autoreset=True)

from config.config import settings, LLMProvider
from memory.emotions_engine import EmotionsEngine
from web_infrastructure.backend_wrapper import create_chappie_backend

# --- COLORS ---
class Colors:
    DEBUG = colorama.Fore.CYAN
    MEMORY = colorama.Fore.MAGENTA
    EMOTION = colorama.Fore.YELLOW
    THOUGHT = colorama.Fore.LIGHTBLACK_EX
    AI = colorama.Fore.BLUE
    USER = colorama.Fore.GREEN
    STEER = colorama.Fore.RED
    SUCCESS = colorama.Fore.GREEN
    RESET = colorama.Style.RESET_ALL
    BOLD = colorama.Style.BRIGHT

def print_log(category: str, msg: str, color=Colors.DEBUG):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{color}[{timestamp}] [{category}] {msg}{Colors.RESET}")

class CHAPPiEBrainCLI:
    def __init__(self):
        print_log("INIT", "Initialisiere High-End Brain Architektur...", Colors.AI)

        self.backend = create_chappie_backend()
        self.memory = self.backend.memory
        self.emotions = self.backend.emotions
        self.context = self.backend.context_files
        self.steering = self.backend.steering_manager
        self.history = []
        self.last_result: Dict[str, Any] | None = None

        status = self.backend.get_status()
        model_name = status.get("model", "unbekannt")
        print_log("INIT", f"Modell: {model_name}", Colors.AI)
        print_log("INIT", f"Provider: {settings.llm_provider.value}", Colors.AI)
        
        is_local = self.steering.is_local_provider()
        if settings.enable_steering:
            mode = "LOKAL (Vektor-Injection)" if is_local else "CLOUD (Prompt-basiert)"
            print_log("INIT", f"Steering: {mode}", Colors.STEER)
            print_log("INIT", f"Verfuegbare Vektoren: {len(self.steering.get_available_vectors())}", Colors.STEER)
        else:
            print_log("INIT", "Steering: DEAKTIVIERT", Colors.THOUGHT)

    def _get_emotions_dict(self) -> Dict[str, int]:
        return self.emotions.get_state().to_dict()

    def _build_steering_report(self) -> Dict[str, Any]:
        status = self.backend.get_status()
        model_name = status.get("model", settings.vllm_model)
        force = self.steering.should_force_local_emotion_steering(settings.llm_provider, model_name)
        return self.steering.build_debug_report(self._get_emotions_dict(), force=force)

    @staticmethod
    def _format_vector_names(items: list[Dict[str, Any]], limit: int = 5) -> str:
        if not items:
            return "-"
        parts = []
        for item in items[:limit]:
            name = item.get("name", "?")
            strength = item.get("strength")
            if isinstance(strength, (int, float)):
                parts.append(f"{name}({strength:.2f})")
            else:
                parts.append(name)
        return ", ".join(parts)

    def _show_runtime(self):
        status = self.backend.get_status()
        steering_report = self._build_steering_report()
        print(f"\n{Colors.AI}{'='*58}")
        print("  RUNTIME / MODELLPFAD")
        print(f"{'='*58}")
        print(f"  Provider:           {settings.llm_provider.value}")
        print(f"  Aktives Modell:     {status.get('model', '---')}")
        print(f"  vLLM URL:           {settings.vllm_url}")
        print(f"  Two-Step:           {'AN' if settings.enable_two_step_processing else 'AUS'}")
        print(f"  Query Extraction:   {'AN' if settings.enable_query_extraction else 'AUS'}")
        print(f"  Steering:           {'AN' if settings.enable_steering else 'AUS'}")
        print(f"  Steering-Modus:     {steering_report.get('mode', '---')}")
        print(f"  Prompt-Emotionen:   {'AN' if steering_report.get('prompt_emotions_enabled') else 'AUS'}")
        print(f"  Intent-Modell:      {settings.intent_processor_model_vllm if settings.intent_provider == LLMProvider.VLLM else settings.intent_processor_model_ollama}")
        print(f"  Query-Modell:       {settings.query_extraction_vllm_model if settings.query_extraction_provider == LLMProvider.VLLM else settings.query_extraction_ollama_model}")
        print(f"  Steering-Modell:    {settings.steering_model}")
        print(f"  Debug immer an:     {'JA' if settings.cli_debug_always_on else 'NEIN'}")
        print(f"{'='*58}{Colors.RESET}\n")

    def _show_steering_report(self):
        report = self._build_steering_report()
        print(f"\n{Colors.STEER}{'='*58}")
        print("  STEERING REPORT")
        print(f"{'='*58}")
        print(f"  Modus:              {report.get('mode', '---')}")
        print(f"  Aktiv:              {'JA' if report.get('steering_active') else 'NEIN'}")
        print(f"  Dominant:           {report.get('dominant_vector', 'neutral')} ({report.get('dominant_strength', 0.0):.2f})")
        print(f"  Zusammenfassung:    {report.get('summary', '-')}")
        print(f"  Basisvektoren:      {self._format_vector_names(report.get('base_vectors', []))}")
        print(f"  Aktive Vektoren:    {self._format_vector_names(report.get('active_vectors', []))}")
        print(f"  Composite-Modes:    {self._format_vector_names(report.get('composite_modes', []))}")
        print(f"  Layer-Profil:       {self.steering.model_profile.get('num_layers', '?')} Layers | Range {self.steering.model_profile.get('emotion_range', ('?', '?'))}")
        print(f"{'='*58}{Colors.RESET}\n")

    def _show_last_result(self):
        if not self.last_result:
            print_log("LAST", "Noch keine Antwort vorhanden.", Colors.THOUGHT)
            return

        result = self.last_result
        steering = result.get("emotion_steering", {})
        print(f"\n{Colors.DEBUG}{'='*58}")
        print("  LETZTER TURN")
        print(f"{'='*58}")
        print(f"  Provider/Modell:    {result.get('provider', '---')} / {result.get('model', '---')}")
        print(f"  Intent:             {result.get('intent_type', '---')} ({result.get('intent_confidence', 0.0):.2f})")
        print(f"  Tools:              {len(result.get('selected_tools', []))} genutzt | {', '.join(result.get('selected_tools', [])[:5]) or '-'}")
        print(f"  RAG-Memories:       {len(result.get('rag_memories', []))}")
        print(f"  Processing Time:    {result.get('processing_time_ms', 0):.1f} ms")
        print(f"  Antwort-Laenge:     {len(result.get('response_text', ''))} Zeichen")
        print(f"  Prompt-Modus:       {result.get('prompt_emotion_mode', '---')}")
        print(f"  Steering dominant:  {steering.get('dominant_vector', 'neutral')} ({steering.get('dominant_strength', 0.0):.2f})")
        print(f"  Aktive Vektoren:    {self._format_vector_names(steering.get('active_vectors', []))}")
        print(f"  Workspace-Fokus:    {result.get('global_workspace', {}).get('dominant_focus', {}).get('label', '---')}")
        print(f"{'='*58}{Colors.RESET}\n")
        
    def _show_status(self):
        """Zeigt den aktuellen emotionalen Status."""
        state = self.emotions.get_state()
        status = self.backend.get_status()
        mood = state.get_mood_description()
        steering_report = self._build_steering_report()
        
        print(f"\n{Colors.EMOTION}{'='*50}")
        print(f"  EMOTIONALER STATUS: {mood}")
        print(f"{'='*50}")
        print(f"  Freude:       {state.happiness:>3}/100    Vertrauen:    {state.trust:>3}/100")
        print(f"  Energie:      {state.energy:>3}/100    Neugier:      {state.curiosity:>3}/100")
        print(f"  Motivation:   {state.motivation:>3}/100    Frustration:  {state.frustration:>3}/100")
        print(f"  Traurigkeit:  {state.sadness:>3}/100")
        
        if settings.enable_steering:
            is_local = self.steering.is_local_provider()
            mode = "VEKTOR" if is_local else "PROMPT"
            print(f"\n  Steering [{mode}]: {steering_report.get('summary', '-')}")
            print(f"  Dominant: {steering_report.get('dominant_vector', 'neutral')} ({steering_report.get('dominant_strength', 0.0):.2f})")
            print(f"  Prompt-Modus: {steering_report.get('mode', '---')}")
        
        # Sleep Info
        from memory.sleep_phase import get_sleep_phase_handler
        sleep_status = get_sleep_phase_handler().get_status()
        print(f"\n  Schlaf: {sleep_status['interactions_since_sleep']} Nachrichten seit letztem Schlaf")
        print(f"  Naechster Schlaf: {sleep_status['next_sleep_trigger']}")

        life_state = status.get("life_state", {})
        if life_state:
            goal = life_state.get("active_goal", {})
            dominant_need = (life_state.get("homeostasis", {}).get("dominant_need") or {}).get("name", "stability")
            world = life_state.get("world_model", {})
            development = life_state.get("development", {})
            planning = life_state.get("planning_state", {})
            print(f"\n  Life: {life_state.get('clock', {}).get('phase_label', 'unbekannt')} | {life_state.get('current_activity', '---')}")
            print(f"  Need-Fokus: {dominant_need} | Ziel: {goal.get('title', '---')} | Stage: {development.get('stage', '---')}")
            print(f"  Weltmodell: {world.get('predicted_user_need', '---')} | Next: {world.get('next_best_action', '---')[:55]}")
            print(f"  Planung: {planning.get('planning_horizon', '---')} | {planning.get('next_milestone', '---')[:55]}")
        print(f"  Runtime: {status.get('model', '---')} | Two-Step={'AN' if status.get('two_step_enabled') else 'AUS'}")
        print(f"{'='*50}{Colors.RESET}\n")

    def _handle_emotion_command(self, cmd: str) -> bool:
        parts = cmd.split()
        if len(parts) != 3:
            print_log("EMOTION", "Nutze: /emotion <name> <0-100>", Colors.EMOTION)
            return True

        _, emotion, value_text = parts
        try:
            value = int(value_text)
        except ValueError:
            print_log("EMOTION", f"Ungueltiger Wert: {value_text}", Colors.STEER)
            return True

        valid = {"happiness", "trust", "energy", "curiosity", "frustration", "motivation", "sadness"}
        if emotion not in valid:
            print_log("EMOTION", f"Unbekannte Emotion: {emotion}", Colors.STEER)
            return True

        self.emotions.set_emotion(emotion, value)
        print_log("EMOTION", f"{emotion} auf {max(0, min(100, value))} gesetzt.", Colors.EMOTION)
        self._show_steering_report()
        return True
    
    def _handle_command(self, cmd: str) -> bool:
        """Verarbeitet CLI-Befehle. Returns True wenn Befehl verarbeitet."""
        
        if cmd == "/status":
            self._show_status()
            return True

        if cmd == "/runtime":
            self._show_runtime()
            return True

        if cmd == "/steering":
            self._show_steering_report()
            return True

        if cmd == "/last":
            self._show_last_result()
            return True

        if cmd.startswith("/emotion "):
            return self._handle_emotion_command(cmd)

        if cmd == "/resetemotions":
            self.emotions.reset()
            self._show_status()
            return True
        
        if cmd == "/sleep":
            print_log("SLEEP", "Starte Schlafphase...", Colors.MEMORY)
            from memory.sleep_phase import get_sleep_phase_handler
            handler = get_sleep_phase_handler()
            result = handler.execute_sleep_phase(memory_engine=self.memory, context_files=self.context)
            
            if result.get("energy_restored"):
                print_log("SLEEP", f"Energie wiederhergestellt: {result.get('energy_value', 100)}%", Colors.SUCCESS)
            
            recovery = result.get("emotional_recovery", {})
            for emotion, delta in recovery.items():
                sign = "+" if delta > 0 else ""
                print_log("SLEEP", f"  {emotion}: {sign}{delta}", Colors.EMOTION)

            for fragment in result.get("dream_replay", [])[:3]:
                print_log("DREAM", fragment, Colors.MEMORY)
            replay = result.get("replay_state", {})
            if replay:
                print_log("REPLAY", replay.get("summary", "Replay abgeschlossen."), Colors.AI)
                print_log("REPLAY", f"Habit: {replay.get('habit_reinforcement', '---')} | Themes: {', '.join(replay.get('themes', [])[:3])}", Colors.AI)
            
            # Lade neuen Status
            self.backend.emotions = EmotionsEngine()
            self.emotions = self.backend.emotions
            self._show_status()
            return True
        
        if cmd == "/vectors":
            vectors = self.steering.get_available_vectors()
            print(f"\n{Colors.STEER}Verfuegbare Steering-Vektoren ({len(vectors)}):")
            for name in vectors:
                info = self.steering.get_vector_info(name)
                if info:
                    desc = info.get("description", "")
                    layers = f"L{info.get('layer_start', '?')}-{info.get('layer_end', '?')}"
                    alpha = info.get("default_alpha", 0.3)
                    print(f"  [{name}] {layers} alpha={alpha:.2f} - {desc}")
            print(f"{Colors.RESET}")
            return True
        
        if cmd == "/help":
            print(f"\n{Colors.AI}CHAPPiE Brain CLI Commands:")
            print(f"  /status   - Zeigt emotionalen Status & Steering")
            print(f"  /runtime  - Zeigt aktiven Runtime-/Modellpfad")
            print(f"  /steering - Zeigt detaillierten Steering-Report")
            print(f"  /last     - Zeigt Metriken des letzten Turns")
            print(f"  /emotion <name> <0-100> - Setzt eine Emotion direkt")
            print(f"  /resetemotions - Setzt den Emotionszustand zurueck")
            print(f"  /sleep    - Startet Schlafphase (Energie-Reset)")
            print(f"  /life     - Zeigt Life-Simulation Zustand")
            print(f"  /world    - Zeigt World-Model Vorhersage")
            print(f"  /habits   - Zeigt gelernte Gewohnheiten")
            print(f"  /stage    - Zeigt Entwicklungsphase")
            print(f"  /plan     - Zeigt Langzeit-Planungszustand")
            print(f"  /forecast - Zeigt Self-Forecasting")
            print(f"  /arc      - Zeigt sozialen Beziehungsbogen")
            print(f"  /timeline - Zeigt Growth-Timeline")
            print(f"  /vectors  - Zeigt verfuegbare Steering-Vektoren")
            print(f"  /exit     - Beendet das Programm")
            print(f"  /help     - Zeigt diese Hilfe{Colors.RESET}\n")
            return True

        if cmd == "/life":
            status = self.backend.get_status()
            life_state = status.get("life_state", {})
            goal = life_state.get("active_goal", {})
            world = life_state.get("world_model", {})
            development = life_state.get("development", {})
            attachment = life_state.get("attachment_model", {})
            planning = life_state.get("planning_state", {})
            social_arc = life_state.get("social_arc", {})
            print(f"\n{Colors.MEMORY}Life Simulation")
            print(f"  Phase: {life_state.get('clock', {}).get('phase_label', '---')}")
            print(f"  Aktivitaet: {life_state.get('current_activity', '---')}")
            print(f"  Modus: {life_state.get('current_mode', '---')}")
            print(f"  Ziel: {goal.get('title', '---')} ({goal.get('progress', 0):.0%})")
            print(f"  Stage: {development.get('stage', '---')} -> {development.get('next_stage', '---')}")
            print(f"  Attachment: {attachment.get('bond_type', '---')} ({attachment.get('attachment_security', 0):.2f})")
            print(f"  Planung: {planning.get('planning_horizon', '---')} | {planning.get('next_milestone', '---')}")
            print(f"  Social Arc: {social_arc.get('arc_name', '---')} | {social_arc.get('phase', '---')}")
            print(f"  World Model: {world.get('predicted_user_need', '---')}")
            print(f"  Next Action: {world.get('next_best_action', '---')}")
            for item in life_state.get("homeostasis", {}).get("active_needs", [])[:6]:
                print(f"  - {item['name']}: {item['value']} (Druck {item['pressure']})")
            print(f"{Colors.RESET}")
            return True

        if cmd == "/habits":
            status = self.backend.get_status()
            habits = sorted(status.get("life_state", {}).get("habits", {}).items(), key=lambda item: item[1].get("strength", 0), reverse=True)
            print(f"\n{Colors.MEMORY}Habit Engine")
            for name, meta in habits[:5]:
                print(f"  {meta.get('label', name)}: Stärke {meta.get('strength', 0):.2f} | Count {meta.get('count', 0)} | Trend {meta.get('trend', 'stable')}")
            print(f"{Colors.RESET}")
            return True

        if cmd == "/stage":
            status = self.backend.get_status()
            development = status.get("life_state", {}).get("development", {})
            print(f"\n{Colors.AI}Development Stage")
            print(f"  Stage: {development.get('stage', '---')}")
            print(f"  Next: {development.get('next_stage', '---')}")
            print(f"  Score: {development.get('development_score', 0):.2f}")
            print(f"  Progress: {development.get('progress_to_next', 0):.0%}{Colors.RESET}")
            return True

        if cmd == "/plan":
            status = self.backend.get_status()
            planning = status.get("life_state", {}).get("planning_state", {})
            print(f"\n{Colors.AI}Planning State")
            print(f"  Horizon: {planning.get('planning_horizon', '---')}")
            print(f"  Coordination: {planning.get('coordination_mode', '---')}")
            print(f"  Milestone: {planning.get('next_milestone', '---')}")
            print(f"  Confidence: {planning.get('plan_confidence', 0):.2f}{Colors.RESET}")
            return True

        if cmd == "/forecast":
            status = self.backend.get_status()
            forecast = status.get("life_state", {}).get("forecast_state", {})
            print(f"\n{Colors.AI}Self Forecast")
            print(f"  Risk: {forecast.get('risk_level', '---')}")
            print(f"  Next: {forecast.get('next_turn_outlook', '---')}")
            print(f"  Day: {forecast.get('daily_outlook', '---')}")
            print(f"  Trajectory: {forecast.get('stage_trajectory', '---')}{Colors.RESET}")
            return True

        if cmd == "/arc":
            status = self.backend.get_status()
            social_arc = status.get("life_state", {}).get("social_arc", {})
            print(f"\n{Colors.MEMORY}Social Arc")
            print(f"  Arc: {social_arc.get('arc_name', '---')}")
            print(f"  Phase: {social_arc.get('phase', '---')}")
            print(f"  Episode: {social_arc.get('current_episode', '---')}")
            print(f"  Score: {social_arc.get('arc_score', 0):.2f}{Colors.RESET}")
            return True

        if cmd == "/timeline":
            status = self.backend.get_status()
            summary = status.get("life_state", {}).get("timeline_summary", {})
            history = status.get("life_state", {}).get("timeline_history", [])
            print(f"\n{Colors.MEMORY}Growth Timeline")
            print(f"  Entries: {summary.get('entries', 0)}")
            print(f"  Summary: {summary.get('summary', '---')}")
            for item in history[-5:]:
                print(f"  - {item.get('phase_label', '---')} | {item.get('source', '---')} | {item.get('goal', '---')} | {item.get('stage', '---')}")
            print(f"{Colors.RESET}")
            return True

        if cmd == "/world":
            status = self.backend.get_status()
            world = status.get("life_state", {}).get("world_model", {})
            print(f"\n{Colors.AI}World Model")
            print(f"  Interaction: {world.get('interaction_mode', '---')}")
            print(f"  Predicted Need: {world.get('predicted_user_need', '---')}")
            print(f"  Next Best Action: {world.get('next_best_action', '---')}")
            print(f"  Trajectory: {world.get('expected_trajectory', '---')}")
            print(f"  Confidence: {world.get('confidence', 0):.2f}{Colors.RESET}")
            return True

        backend_response = self.backend.handle_command(cmd)
        if not backend_response.startswith("Unbekannter Command:"):
            print(f"\n{Colors.MEMORY}{backend_response}{Colors.RESET}\n")
            return True
        
        return False

    def process_message(self, user_text: str):
        if not user_text.strip():
            return

        print_log("BRAIN", "Starte echten Zwei-Schritte Runtime-Pfad...", Colors.AI)
        result = self.backend.process(user_text, self.history, debug_mode=True)
        self.last_result = result

        steering = result.get("emotion_steering", {})
        print_log("INTENT", f"Typ: {result.get('intent_type', '---')} | Confidence: {result.get('intent_confidence', 0.0):.2f}", Colors.EMOTION)
        print_log("TOOLS", f"Genutzt: {', '.join(result.get('selected_tools', [])[:5]) or 'keine'}", Colors.MEMORY)
        print_log("STEERING", f"[{result.get('prompt_emotion_mode', '---')}] Dominant: {steering.get('dominant_vector', 'neutral')} ({steering.get('dominant_strength', 0.0):.2f}) | Aktiv: {len(steering.get('active_vectors', []))}", Colors.STEER)
        print_log("WORKSPACE", f"Fokus: {result.get('global_workspace', {}).get('dominant_focus', {}).get('label', '---')}", Colors.MEMORY)
        print_log("RUNTIME", f"{result.get('provider', '---')} | {result.get('model', '---')} | {result.get('processing_time_ms', 0):.1f} ms", Colors.DEBUG)

        print(f"\n{Colors.AI}CHAPPiE > {Colors.RESET}{Colors.AI}{result.get('response_text', '')}{Colors.RESET}\n")

        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": result.get("response_text", "")})
        self._show_last_result()

    def run(self):
        is_local = self.steering.is_local_provider()
        steering_info = "VEKTOR-STEERING" if is_local else "PROMPT-STEERING"
        
        print(f"""
{Colors.AI}{Colors.BOLD}
  ██████╗ ██████╗  █████╗ ██╗███╗   ██╗
  ██╔══██╗██╔══██╗██╔══██╗██║████╗  ██║
  ██████╔╝██████╔╝███████║██║██╔██╗ ██║
  ██╔══██╗██╔══██╗██╔══██║██║██║╚██╗██║
  ██████╔╝██║  ██║██║  ██║██║██║ ╚████║
  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝
{Colors.AI}CHAPPiE Advanced Brain Interface v4.0
{Colors.STEER}Modus: {steering_info} | 7 Emotionale Dimensionen
{Colors.RESET}""")
        
        self._show_status()
        
        while True:
            try:
                user_input = input(f"\n{Colors.USER}Benjamin > {Colors.RESET}")
                
                if user_input.lower() in ["/exit", "/quit"]:
                    break
                
                if user_input.startswith("/"):
                    if self._handle_command(user_input.lower()):
                        continue
                
                self.process_message(user_input)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print_log("ERROR", str(e), Colors.STEER)
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    cli = CHAPPiEBrainCLI()
    cli.run()
