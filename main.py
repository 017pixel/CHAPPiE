"""
CHAPiE - Main Application (CLI / Debug Mode)
============================================
Der Haupt-Loop der CHAPiE KI im Advanced Debug Mode.
Zeigt detaillierte Hintergrundinformationen zu jedem Schritt an.
"""

import sys
import time
import threading
import json
import colorama
from datetime import datetime
from typing import Optional, List

# Init Colorama for cross-platform ANSI colors
colorama.init(autoreset=True)

from config.config import settings, get_active_model
from config.prompts import SYSTEM_PROMPT, get_system_prompt_with_emotions
from memory import MemoryEngine
from memory.emotions_engine import EmotionsEngine, analyze_sentiment_simple
from brain import get_brain, Message

# --- COLORS ---
class Colors:
    DEBUG = colorama.Fore.CYAN
    MEMORY = colorama.Fore.MAGENTA
    EMOTION = colorama.Fore.YELLOW
    THOUGHT = colorama.Fore.LIGHTBLACK_EX
    AI = colorama.Fore.BLUE
    USER = colorama.Fore.GREEN
    ERROR = colorama.Fore.RED
    RESET = colorama.Style.RESET_ALL
    BOLD = colorama.Style.BRIGHT
    GREEN = colorama.Fore.GREEN
    SUCCESS = colorama.Fore.GREEN

def print_section(title: str, color=Colors.RESET):
    print(f"\n{color}{Colors.BOLD}=== {title} ==={Colors.RESET}")

def print_log(category: str, msg: str, color=Colors.DEBUG):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{color}[{timestamp}] [{category}] {msg}{Colors.RESET}")

# =============================================================================
# HAUPTKLASSE
# =============================================================================
class CHAPPiE:
    """Haupt-Klasse fuer den CHAPPiE KI-Agenten (CLI Mode)."""
    
    COMMANDS = {
        "/memory": "Zeigt Memory-Statistiken an",
        "/status": "Zeigt den aktuellen emotionalen Status",
        "/config": "Zeigt die aktuelle Konfiguration",
        "/sleep": "CHAPiE geht schlafen (konsolidiert Erinnerungen)",
        "/think": "Startet tiefen Reflektionsmodus (10 Schritte)",
        "/daily": "Zeigt Kurzzeitgedächtnis (Daily Info)",
        "/personality": "Zeigt aktuelle Persönlichkeit",
        "/consolidate": "Bereinigt abgelaufene Daily Infos",
        "/functions": "Listet verfügbare Funktionen auf",
        "/help": "Zeigt alle verfuegbaren Befehle",
        "/exit": "Beendet CHAPPiE",
        "/quit": "Alias fuer /exit",
    }
    
    def __init__(self):
        # Module initialisieren
        print_log("INIT", "Initialisiere Memory Engine...", Colors.MEMORY)
        self.memory = MemoryEngine()
        
        print_log("INIT", "Initialisiere Emotions Engine...", Colors.EMOTION)
        self.emotions = EmotionsEngine()
        
        print_log("INIT", f"Verbinde mit Brain ({get_active_model()})...", Colors.AI)
        self.brain = get_brain()
        
        self.current_thought: str = ""
        self.is_sleeping = False
        
        if not self.brain.is_available():
            print(f"\n{Colors.ERROR}FEHLER: LLM-Backend nicht verfuegbar!{Colors.RESET}")
            sys.exit(1)
            
        print_log("INIT", "System bereit.", Colors.SUCCESS if hasattr(Colors, 'SUCCESS') else Colors.GREEN)

    def _handle_command(self, command: str) -> bool:
        """Verarbeitet Slash-Commands."""
        cmd = command.lower().strip()
        
        if self.is_sleeping and cmd not in ["/exit", "/quit", "/sleep", "/help"]:
            print(f"{Colors.THOUGHT}CHAPiE schlaeft... zZz... (Nutze /sleep zum Aufwecken){Colors.RESET}")
            return True
        
        # Memory Stats
        if cmd == "/memory":
            count = self.memory.get_memory_count()
            recent = self.memory.get_recent_memories(5)
            print_section("MEMORY STATS", Colors.MEMORY)
            print(f"Gespeicherte Erinnerungen: {count}")
            if recent:
                print("Letzte 5 Eintraege:")
                for mem in recent:
                    print(f" - [{mem.role}] {mem.content[:80]}...")
            return True
        
        # Status
        if cmd == "/status":
            state = self.emotions.get_state()
            mood = state.get_mood_description()
            print_section("EMOTIONAL STATUS", Colors.EMOTION)
            print(f"Stimmung: {mood}")
            print(f"Freude:     {state.happiness:<3} | Vertrauen:  {state.trust:<3}")
            print(f"Energie:    {state.energy:<3} | Neugier:    {state.curiosity:<3}")
            print(f"Motivation: {state.motivation:<3} | Frust:      {state.frustration:<3}")
            return True
        
        # Config
        if cmd == "/config":
            print_section("CONFIGURATION", Colors.DEBUG)
            print(f"Provider:   {settings.llm_provider.value}")
            print(f"Modell:     {get_active_model()}")
            print(f"Temp:       {settings.temperature}")
            print(f"CoT:        {'An' if settings.chain_of_thought else 'Aus'}")
            return True
        
        # Sleep Mode
        if cmd == "/sleep":
            if self.is_sleeping:
                self.is_sleeping = False
                print(f"\n{Colors.AI}CHAPPiE ist aufgewacht!{Colors.RESET}")
            else:
                print_section("SLEEP MODE", Colors.MEMORY)
                print("Startet Konsolidierung (Traum-Phase)...")
                result = self.memory.consolidate_memories(self.brain)
                print(result)
                self.emotions.restore_energy(30)
                print_log("SLEEP", "Energie wiederhergestellt.", Colors.EMOTION)
                self.is_sleeping = True
            return True
        
        # Think Mode
        if cmd.startswith("/think"):
            parts = command.split(" ", 1)
            topic = parts[1] if len(parts) > 1 else ""
            print_section("DEEP THINK MODE", Colors.THOUGHT)
            print(f"Thema: {topic if topic else 'Allgemeine Reflektion'}")
            
            for step_result in self.memory.think_deep(self.brain, topic=topic, steps=10, delay=0.5):
                step = step_result["step"]
                total = step_result["total_steps"]
                thought = step_result["thought"]
                mem_count = step_result["memories_found"]
                
                print(f"\n[{step}/{total}] (Memories: {mem_count})")
                print(f"{Colors.THOUGHT}{thought}{Colors.RESET}")
                
                if step_result.get("error"):
                    print(f"{Colors.ERROR}Fehler: {thought}{Colors.RESET}")
                    break
            return True
        
        # === NEU: Memory Enhancement Commands ===
        if cmd == "/daily":
            from memory.short_term_memory import get_short_term_memory
            stm = get_short_term_memory()
            infos = stm.get_relevant_infos()
            print_section("KURZZEITGEDÄCHTNIS", Colors.MEMORY)
            print(f"Einträge: {len(infos)}")
            for timestamp, importance, category, content in infos:
                print(f"  [{importance}] [{category}] {content[:60]}...")
            return True
        
        if cmd == "/personality":
            from memory.personality_manager import get_personality_manager
            pm = get_personality_manager()
            print_section("PERSÖNLICHKEIT", Colors.MEMORY)
            print(pm.get_for_prompt())
            return True
        
        if cmd == "/consolidate":
            from memory.short_term_memory import get_short_term_memory
            stm = get_short_term_memory()
            count = stm.cleanup_expired()
            print_section("KONSOLIDIERUNG", Colors.MEMORY)
            print(f"Bereinigt: {count} abgelaufene Einträge")
            return True
        
        if cmd == "/functions":
            from memory.function_registry import get_function_registry
            func_registry = get_function_registry()
            funcs = func_registry.get_function_names()
            print_section("VERFÜGBARE FUNKTIONEN", Colors.MEMORY)
            for f in funcs:
                print(f"  🔧 {f}")
            return True
        
        # Help
        if cmd == "/help":
            print_section("COMMANDS", Colors.DEBUG)
            for k, v in self.COMMANDS.items():
                print(f"{k:<10} - {v}")
            return True
        
        # Exit
        if cmd in ["/exit", "/quit"]:
            print(f"\n{Colors.AI}Auf Wiedersehen!{Colors.RESET}")
            sys.exit(0)
        
        return False

    def process_user_input(self, user_text: str):
        """Hauptlogik fuer die Verarbeitung."""
        if not user_text.strip():
            return

        # 1. Commands check
        if user_text.startswith("/"):
            if self._handle_command(user_text):
                return

        if self.is_sleeping:
            print(f"{Colors.THOUGHT}CHAPiE schlaeft... (Nutze /sleep){Colors.RESET}")
            return

        # 2. Sentiment Analysis
        print_log("PROCESS", "Analysiere Sentiment...", Colors.EMOTION)
        sentiment = analyze_sentiment_simple(user_text)
        self.emotions.update_from_sentiment(sentiment)
        state = self.emotions.get_state()
        print(f"   > Sentiment: {sentiment} | Neue Stimmung: {state.get_mood_description()}")

        # 3. Memory Retrieval
        print_log("PROCESS", "Durchsuche Gedaechtnis...", Colors.MEMORY)
        memories = self.memory.search_memory(user_text)
        if memories:
            print(f"   > {len(memories)} relevante Erinnerungen gefunden:")
            for m in memories:
                print(f"     - [{int(m.relevance_score*100)}%] {m.content[:60]}...")
        else:
            print("   > Keine relevanten Erinnerungen.")
        
        memories_text = self.memory.format_memories_for_prompt(memories)

        # 4. Prompt Building
        system_prompt = get_system_prompt_with_emotions(
            **state.__dict__, 
            use_chain_of_thought=settings.chain_of_thought
        )
        
        # NEU: Persönlichkeits-Kontext hinzufügen
        from config.prompts import get_personality_context, get_function_calling_instruction
        if settings.enable_functions:
            system_prompt += f"\n\n{get_personality_context()}"
            system_prompt += f"\n\n{get_function_calling_instruction()}"
        
        messages = self.brain.build_prompt(system_prompt, memories_text, user_text)
 
       # 5. Generation
        print_section("GENERATION STREAM", Colors.AI)
        
        full_response = ""
        is_in_thought = False
        
        # Stream output
        for token in self.brain.generate(messages):
            full_response += token
            
            # Thought Parsing & Display
            if "<gedanke>" in token or "<gedanke>" in full_response[-20:]: # Check recent buffer for tag start
                is_in_thought = True
                
            if is_in_thought:
                # Wir sammeln Gedanken, um sie evtl. anders zu faerben
                # Hier einfach direkt in Thought-Farbe ausgeben
                sys.stdout.write(f"{Colors.THOUGHT}{token}{Colors.RESET}")
                if "</gedanke>" in token:
                    is_in_thought = False
            else:
                # Normale Antwort
                sys.stdout.write(f"{Colors.AI}{token}{Colors.RESET}")
            
            sys.stdout.flush()
        
        print("\n") # Newline after generation

        # 6. Post-Processing (Speichern & Function-Calling)
        import re
        from brain.response_parser import parse_chain_of_thought
        
        # NEU: Function Calls extrahieren
        function_calls = []
        func_pattern = r'<function_call>\s*(\{.*?\})\s*</function_call>'
        func_matches = re.findall(func_pattern, full_response, re.DOTALL)
        
        if func_matches:
            from memory.function_registry import get_function_registry
            func_registry = get_function_registry()
            
            print_log("FUNC", f"{len(func_matches)} Funktion(en) erkannt!", Colors.MEMORY)
            
            for func_match in func_matches:
                try:
                    func_data = json.loads(func_match)
                    func_name = func_data.get("name", "")
                    args = func_data.get("arguments", {})
                    
                    print_log("FUNC", f"> Führe {func_name} aus...", Colors.MEMORY)
                    
                    if func_registry.has_function(func_name):
                        result = func_registry.execute(func_name, args)
                        function_calls.append({"name": func_name, "arguments": args, "result": result})
                        print_log("FUNC", f"  ✓ {result[:60]}...", Colors.SUCCESS)
                    else:
                        print_log("FUNC", f"  ✗ Unbekannte Funktion: {func_name}", Colors.ERROR)
                except Exception as e:
                    print_log("FUNC", f"  ✗ Fehler: {e}", Colors.ERROR)
        
        # Parse final result
        parsed = parse_chain_of_thought(full_response)
        display_response = parsed.answer
        
        print_log("PROCESS", "Speichere Interaktion...", Colors.MEMORY)
        self.memory.add_memory(user_text, role="user")
        if display_response and display_response.strip():
            self.memory.add_memory(display_response, role="assistant")
        else:
            print_log("WARN", "Leere Antwort generiert, wird nicht gespeichert.", Colors.ERROR)
        
        # NEU: Function Calls anzeigen wenn welche ausgeführt wurden
        if function_calls:
            print_section("AUSGEFÜHRTE FUNKTIONEN", Colors.MEMORY)
            for func in function_calls:
                print(f"  🔧 {func['name']}")
                print(f"     Args: {func['arguments']}")
                print(f"     Result: {func['result'][:80]}...")

    def run(self):
        """Main Loop mit Standard Input."""
        print(f"""
{Colors.AI}{Colors.BOLD}
  ██████╗ ██╗  ██╗  █████╗  ██████╗ ██████╗ ██╗███████╗
 ██╔════╝ ██║  ██║ ██╔══██╗██╔══██╗██╔══██╗██║██╔════╝
 ██║      ███████║ ███████║██████╔╝██████╔╝██║█████╗  
 ██║      ██╔══██║ ██╔══██║██╔═══╝ ██╔═══╝ ██║██╔══╝  
 ╚██████╗ ██║  ██║ ██║  ██║██║     ██║     ██║███████╗
  ╚═════╝ ╚═╝  ╚═╝ ╚═╝  ╚═╝╚═╝     ╚═╝     ╚═╝╚══════╝
{Colors.RESET}
Advanced Debug CLI v2.0
Modell: {get_active_model()}
""")
        
        while True:
            try:
                # Standard Python Input (blockierend)
                user_input = input(f"\n{Colors.USER}Du > {Colors.RESET}")
                self.process_user_input(user_input)
                
            except KeyboardInterrupt:
                print(f"\n{Colors.ERROR}Abbruch durch User.{Colors.RESET}")
                sys.exit(0)
            except Exception as e:
                print(f"\n{Colors.ERROR}KRITISCHER FEHLER: {e}{Colors.RESET}")
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    try:
        app = CHAPPiE()
        app.run()
    except Exception as e:
        print(f"Start-Fehler: {e}")
