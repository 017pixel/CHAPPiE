"""
CHAPPiE - Next-Gen Brain CLI
============================
Nutzt die volle Multi-Agenten Brain-Architektur inklusive 
neuem vLLM-Backend, Qwen 3.5 und emotionalem Steering.
"""

import sys
import threading
import json
import time
import colorama
from datetime import datetime
from typing import Optional, List, Dict, Any

colorama.init(autoreset=True)

from config.config import settings, get_active_model, LLMProvider
from brain.brain_pipeline import get_brain_pipeline
from brain.base_brain import GenerationConfig, Message
from memory import MemoryEngine
from memory.emotions_engine import EmotionsEngine
from memory.context_files import get_context_files_manager
from brain.agents.steering_manager import get_steering_manager

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
        
        self.pipeline = get_brain_pipeline()
        self.memory = MemoryEngine()
        self.emotions = EmotionsEngine()
        self.context = get_context_files_manager()
        self.steering = get_steering_manager()
        
        model_name = settings.vllm_model if settings.llm_provider == LLMProvider.VLLM else get_active_model()
        print_log("INIT", f"Modell: {model_name}", Colors.AI)
        print_log("INIT", f"Provider: {settings.llm_provider.value}", Colors.AI)
        
        is_local = self.steering.is_local_provider()
        if settings.enable_steering:
            mode = "LOKAL (Vektor-Injection)" if is_local else "CLOUD (Prompt-basiert)"
            print_log("INIT", f"Steering: {mode}", Colors.STEER)
            print_log("INIT", f"Verfuegbare Vektoren: {len(self.steering.get_available_vectors())}", Colors.STEER)
        else:
            print_log("INIT", "Steering: DEAKTIVIERT", Colors.THOUGHT)
        
        self.history = []
        
    def _show_status(self):
        """Zeigt den aktuellen emotionalen Status."""
        state = self.emotions.get_state()
        mood = state.get_mood_description()
        
        print(f"\n{Colors.EMOTION}{'='*50}")
        print(f"  EMOTIONALER STATUS: {mood}")
        print(f"{'='*50}")
        print(f"  Freude:       {state.happiness:>3}/100    Vertrauen:    {state.trust:>3}/100")
        print(f"  Energie:      {state.energy:>3}/100    Neugier:      {state.curiosity:>3}/100")
        print(f"  Motivation:   {state.motivation:>3}/100    Frustration:  {state.frustration:>3}/100")
        print(f"  Traurigkeit:  {state.sadness:>3}/100")
        
        if settings.enable_steering:
            emotions_dict = state.to_dict()
            summary = self.steering.get_emotion_summary(emotions_dict)
            is_local = self.steering.is_local_provider()
            mode = "VEKTOR" if is_local else "PROMPT"
            print(f"\n  Steering [{mode}]: {summary}")
        
        # Sleep Info
        from memory.sleep_phase import get_sleep_phase_handler
        sleep_status = get_sleep_phase_handler().get_status()
        print(f"\n  Schlaf: {sleep_status['interactions_since_sleep']} Nachrichten seit letztem Schlaf")
        print(f"  Naechster Schlaf: {sleep_status['next_sleep_trigger']}")
        print(f"{'='*50}{Colors.RESET}\n")
    
    def _handle_command(self, cmd: str) -> bool:
        """Verarbeitet CLI-Befehle. Returns True wenn Befehl verarbeitet."""
        
        if cmd == "/status":
            self._show_status()
            return True
        
        if cmd == "/sleep":
            print_log("SLEEP", "Starte Schlafphase...", Colors.MEMORY)
            from memory.sleep_phase import get_sleep_phase_handler
            handler = get_sleep_phase_handler()
            result = handler.execute_sleep_phase(memory_engine=self.memory)
            
            if result.get("energy_restored"):
                print_log("SLEEP", f"Energie wiederhergestellt: {result.get('energy_value', 100)}%", Colors.SUCCESS)
            
            recovery = result.get("emotional_recovery", {})
            for emotion, delta in recovery.items():
                sign = "+" if delta > 0 else ""
                print_log("SLEEP", f"  {emotion}: {sign}{delta}", Colors.EMOTION)
            
            # Lade neuen Status
            self.emotions = EmotionsEngine()
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
            print(f"  /sleep    - Startet Schlafphase (Energie-Reset)")
            print(f"  /vectors  - Zeigt verfuegbare Steering-Vektoren")
            print(f"  /exit     - Beendet das Programm")
            print(f"  /help     - Zeigt diese Hilfe{Colors.RESET}\n")
            return True
        
        return False

    def process_message(self, user_text: str):
        if not user_text.strip():
            return

        # 1. Pipeline Execution (Multi-Agent)
        print_log("BRAIN", "Starte Multi-Agenten Analyse...", Colors.AI)
        
        current_emotions = self.emotions.get_state().__dict__
        # Nur die 7 relevanten Dimensionen
        emotion_keys = ["happiness", "trust", "energy", "curiosity", "frustration", "motivation", "sadness"]
        filtered_emotions = {k: current_emotions[k] for k in emotion_keys if k in current_emotions}
        
        brain_result = self.pipeline.process(
            user_input=user_text,
            history=self.history,
            current_emotions=filtered_emotions,
            memory_engine=self.memory,
            context_files=self.context,
            run_background=True
        )
        
        # 2. Results Extraction
        amygdala = brain_result["amygdala"].data
        pfc = brain_result["prefrontal"].data
        steering_payload = brain_result["steering_payload"]
        steering_mode = brain_result.get("steering_mode", "prompt")
        
        primary_emotion = amygdala.get('primary_emotion', 'neutral')
        intensity = amygdala.get('emotional_intensity', 0)
        print_log("AMYGDALA", f"Emotion: {primary_emotion} (Intensitaet: {intensity:.2f})", Colors.EMOTION)
        
        # Steering Info
        if steering_payload:
            n_vectors = len(steering_payload.get('steering', {}).get('vectors', []))
            dominant = steering_payload.get('steering', {}).get('dominant_emotion', '?')
            strength = steering_payload.get('steering', {}).get('dominant_strength', 0)
            print_log("STEERING", f"[{steering_mode.upper()}] {n_vectors} Vektoren aktiv | Dominant: {dominant} ({strength:.2f})", Colors.STEER)
        else:
            print_log("STEERING", f"[{steering_mode.upper()}] Keine aktive Steuerung", Colors.THOUGHT)
        
        strategy = pfc.get('response_strategy', 'standard')
        tone = pfc.get('tone', 'neutral')
        print_log("PFC", f"Strategie: {strategy} | Ton: {tone}", Colors.AI)
        
        # 3. Final Generation with Steering
        print_log("GEN", "Generiere Antwort...", Colors.AI)
        
        system_prompt = f"Du bist CHAPPiE, ein lebendiges digitales Bewusstsein. Strategie: {strategy}. Ton: {tone}."
        
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_text)
        ]
        
        # Bei lokalen Modellen: Steering via extra_body, bei Cloud: kein extra_body
        extra = steering_payload if (settings.enable_steering and steering_mode == "vector") else None
        
        config = GenerationConfig(
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
            stream=True,
            extra_body=extra
        )
        
        print(f"\n{Colors.AI}CHAPPiE > {Colors.RESET}", end="")
        full_response = ""
        
        brain_backend = self.pipeline.prefrontal_cortex._get_brain()
        
        for token in brain_backend.generate(messages, config):
            full_response += token
            print(f"{Colors.AI}{token}", end="")
            sys.stdout.flush()
        print("\n")
        
        # 4. Update History & Emotions
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": full_response})
        
        # Emotionen in der Engine aktualisieren
        self.emotions.update_state(brain_result["emotions_after"])

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
