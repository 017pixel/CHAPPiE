"""
CHAPiE - Main Application
==========================
Der Haupt-Loop der CHAPiE KI mit moderner Terminal UI.
"""

import sys
import time
import msvcrt
import re
import threading
from datetime import datetime
from typing import Optional, List

from rich.console import Console, Group, RenderableType
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich.align import Align
from rich.spinner import Spinner
from rich.style import Style
from rich.markup import escape

from config.config import settings, get_active_model
from config.prompts import SYSTEM_PROMPT, get_system_prompt_with_emotions
from memory import MemoryEngine
from memory.emotions_engine import EmotionsEngine, analyze_sentiment_simple
from brain import get_brain, Message


# === Konsole ===
console = Console()

# =============================================================================
# FARB-THEME (Pastellfarben)
# =============================================================================
class Theme:
    """Professionelles Pastellfarben-Theme."""
    # Hauptfarben (Pastell & Screenshot)
    PRIMARY = "#4A90E2"       # Blau (Screenshot Style)
    SECONDARY = "#B8A9C9"     # Lavendel
    ACCENT = "#50E3C2"        # Mint/Cyan (Screenshot Style)
    SUCCESS = "#A8D5BA"       # Mintgruen
    WARNING = "#F5D6A8"       # Sanftes Orange
    ERROR = "#E8A9A9"         # Sanftes Rot
    
    # Texte
    TEXT = "#E8E8E8"          # Helles Grau
    TEXT_DIM = "#8B8B8B"      # Gedimmtes Grau
    TEXT_MUTED = "#6B6B6B"    # Stark gedimmt
    
    # Hintergruende
    BG_PANEL = "#1E1E2E"      # Sehr dunkles Blau/Schwarz
    BG_HEADER = "#242435"     # Etwas heller
    
    # UI Elemente
    BORDER = "#4A90E2"        # Blau (Screenshot Style)
    BORDER_ACTIVE = "#50E3C2" # Aktiver Rand
    
    # Chat
    USER_NAME = "#A8D5BA"     # Gruen fuer User
    AI_NAME = "#4A90E2"       # Blau fuer CHAPPiE
    SYSTEM_MSG = "#B8A9C9"    # Lavendel fuer System


# =============================================================================
# MARKDOWN CONVERTER
# =============================================================================
def convert_markdown_to_rich(text: str) -> Text:
    """
    Konvertiert Markdown-Formatierung in Rich Text.
    Unterstuetzt: **bold**, *italic*, __underline__, `code`, ~~strike~~, -dash-, 'apostrophe'
    """
    result = Text()
    
    # Verarbeite zeilenweise
    lines = text.split('\n')
    
    for line_idx, line in enumerate(lines):
        # Bullet Points
        if line.strip().startswith('- '):
            result.append("  ", style=Theme.TEXT_DIM)
            result.append("* ", style=Theme.ACCENT)
            line = line.strip()[2:]
        elif line.strip().startswith('* '):
            result.append("  ", style=Theme.TEXT_DIM)
            result.append("* ", style=Theme.ACCENT)
            line = line.strip()[2:]
        # Nummerierte Listen
        elif re.match(r'^\d+\.\s', line.strip()):
            match = re.match(r'^(\d+\.)\s(.*)$', line.strip())
            if match:
                result.append("  ", style=Theme.TEXT_DIM)
                result.append(match.group(1) + " ", style=Theme.ACCENT)
                line = match.group(2)
        
        # Inline-Formatierung anwenden
        i = 0
        while i < len(line):
            # **bold**
            if line[i:i+2] == '**':
                end = line.find('**', i+2)
                if end != -1:
                    result.append(line[i+2:end], style="bold")
                    i = end + 2
                    continue
            # __underline__
            elif line[i:i+2] == '__':
                end = line.find('__', i+2)
                if end != -1:
                    result.append(line[i+2:end], style="underline")
                    i = end + 2
                    continue
            # *italic* oder _italic_
            elif line[i] == '*' and (i == 0 or line[i-1] != '*'):
                end = line.find('*', i+1)
                if end != -1 and (end+1 >= len(line) or line[end+1] != '*'):
                    result.append(line[i+1:end], style="italic")
                    i = end + 1
                    continue
            elif line[i] == '_' and (i == 0 or line[i-1] != '_'):
                end = line.find('_', i+1)
                if end != -1 and (end+1 >= len(line) or line[end+1] != '_'):
                    result.append(line[i+1:end], style="italic")
                    i = end + 1
                    continue
            # `code`
            elif line[i] == '`':
                end = line.find('`', i+1)
                if end != -1:
                    result.append(line[i+1:end], style=f"bold {Theme.WARNING}")
                    i = end + 1
                    continue
            # ~~strikethrough~~
            elif line[i:i+2] == '~~':
                end = line.find('~~', i+2)
                if end != -1:
                    result.append(line[i+2:end], style="strike")
                    i = end + 2
                    continue
            # "quoted" oder 'quoted'
            elif line[i] in ['"', "'", '‘', '’', '“', '”']:  # Verschiedene Anfuehrungszeichen
                quote_char = line[i]
                # Matche das gleiche Zeichen oder typografisches Gegenstueck
                end_chars = {'"': '"', "'": "'", '‘': '’', '’': '‘', '“': '”', '”': '“'}
                end_char = end_chars.get(quote_char, quote_char)
                end = line.find(end_char, i+1)
                if end != -1:
                    result.append(quote_char + line[i+1:end] + end_char, style="dim italic")
                    i = end + 1
                    continue
            # -- em dash --
            elif line[i:i+2] == '--':
                result.append('—', style=Theme.TEXT)  # Em Dash
                i += 2
                continue
            
            # Normales Zeichen
            result.append(line[i], style=Theme.TEXT)
            i += 1
        
        # Zeilenumbruch (ausser letzte Zeile)
        if line_idx < len(lines) - 1:
            result.append("\n")
    
    return result


# =============================================================================
# SCROLLABLE TEXT CONTAINER
# =============================================================================
class ScrollableHistory:
    """Verwaltet scrollbaren Chat-Verlauf."""
    
    def __init__(self, max_visible: int = 12):
        self.messages: List[dict] = []
        self.max_visible = max_visible
        self.scroll_offset = 0
        self._auto_scroll = True  # Auto-scroll nach unten bei neuen Nachrichten
    
    def add(self, role: str, content: str):
        """Fuegt Nachricht hinzu und scrollt automatisch nach unten."""
        self.messages.append({"role": role, "content": content})
        # Auto-scroll nach unten nur wenn bereits am Ende
        if self._auto_scroll:
            if len(self.messages) > self.max_visible:
                self.scroll_offset = len(self.messages) - self.max_visible
    
    def scroll_up(self, amount: int = 3):
        """Scrollt nach oben."""
        old_offset = self.scroll_offset
        self.scroll_offset = max(0, self.scroll_offset - amount)
        # Deaktiviere Auto-scroll wenn User manuell scrollt
        if self.scroll_offset != old_offset:
            self._auto_scroll = False
    
    def scroll_down(self, amount: int = 3):
        """Scrollt nach unten."""
        max_offset = max(0, len(self.messages) - self.max_visible)
        old_offset = self.scroll_offset
        self.scroll_offset = min(max_offset, self.scroll_offset + amount)
        # Reaktiviere Auto-scroll wenn am Ende
        if self.scroll_offset >= max_offset:
            self._auto_scroll = True
    
    def scroll_to_bottom(self):
        """Scrollt direkt ans Ende."""
        if len(self.messages) > self.max_visible:
            self.scroll_offset = len(self.messages) - self.max_visible
        else:
            self.scroll_offset = 0
        self._auto_scroll = True
    
    def scroll_to_top(self):
        """Scrollt direkt an den Anfang."""
        self.scroll_offset = 0
        self._auto_scroll = False
    
    def render(self) -> Text:
        """Rendert den sichtbaren Teil der History."""
        result = Text()
        
        # Berechne sichtbaren Bereich
        start_idx = self.scroll_offset
        end_idx = min(start_idx + self.max_visible, len(self.messages))
        
        # Scroll Indikator oben
        if start_idx > 0:
            result.append(f"[{start_idx} aeltere Nachrichten...]\n\n", style=Theme.TEXT_DIM)
        
        # Sichtbare Nachrichten
        for msg in self.messages[start_idx:end_idx]:
            role = msg['role']
            content = msg['content']
            
            if role == "system":
                result.append(content + "\n", style=f"bold {Theme.SYSTEM_MSG}")
            elif role == "user":
                result.append("\nDu: ", style=f"bold {Theme.USER_NAME}")
                result.append_text(convert_markdown_to_rich(content))
                result.append("\n")
            else:
                result.append("CHAPPiE: ", style=f"bold {Theme.AI_NAME}")
                result.append_text(convert_markdown_to_rich(content))
                result.append("\n")
        
        # Scroll Indikator unten
        remaining = len(self.messages) - end_idx
        if remaining > 0:
            result.append(f"\n[{remaining} weitere Nachrichten...]", style=Theme.TEXT_DIM)
        
        return result



class ThoughtHistory(ScrollableHistory):
    """Verwaltet scrollbaren Gedanken-Verlauf."""
    def render(self, visible_height: int = 10) -> Text:
        result = Text()
        start_idx = self.scroll_offset
        end_idx = min(start_idx + visible_height, len(self.messages))
        
        for msg in self.messages[start_idx:end_idx]:
            content = msg.get('content', '')
            result.append(f"• {content}\n", style=f"italic {Theme.TEXT_DIM}")
        
        return result


# =============================================================================
# HAUPTKLASSE
# =============================================================================
class CHAPPiE:
    """Haupt-Klasse fuer den CHAPPiE KI-Agenten."""
    
    COMMANDS = {
        "/memory": "Zeigt Memory-Statistiken an",
        "/status": "Zeigt den aktuellen emotionalen Status",
        "/clear": "Loescht den Chat-Verlauf",
        "/config": "Zeigt die aktuelle Konfiguration",
        "/sleep": "CHAPiE geht schlafen (konsolidiert Erinnerungen)",
        "/think": "Startet tiefen Reflektionsmodus (10 Schritte)",
        "/help": "Zeigt alle verfuegbaren Befehle",
        "/exit": "Beendet CHAPPiE",
        "/quit": "Alias fuer /exit",
    }
    
    # Commands die im Schlafmodus funktionieren
    SLEEP_MODE_COMMANDS = {"/exit", "/quit", "/sleep", "/help"}
    
    def __init__(self):
        # Module initialisieren
        self.memory = MemoryEngine()
        self.emotions = EmotionsEngine()
        self.brain = get_brain()
        
        self.chat_history = ScrollableHistory(max_visible=15)
        self.thought_history = ThoughtHistory(max_visible=10)
        
        self.debug_logs: List[str] = []
        self.current_thought: str = ""
        self.input_buffer: str = ""
        self.is_sleeping = False
        self.last_input_time: float = 0.0
        
        # UI State
        self.focus_mode = "chat"  # "chat" oder "thoughts"
        
        # Initialisiere Banner in der History
        self._add_banner_to_history()
        
        if not self.brain.is_available():
            console.print(f"\n[{Theme.ERROR}]FEHLER: LLM-Backend nicht verfuegbar![/{Theme.ERROR}]")
            sys.exit(1)

    def _add_banner_to_history(self):
        """Fuegt den ASCII Banner zur Chat History hinzu."""
        banner = f"[bold {Theme.PRIMARY}]CHAPPiE[/bold {Theme.PRIMARY}] v2.0 - KI-Agent mit episodischem Gedaechtnis"
        self.chat_history.add("system", banner)
        self.chat_history.add("assistant", "Hallo! Ich bin bereit. Was machen wir heute?")

    def log_debug(self, msg: str):
        """Fuegt eine Info zum Debug-Logger hinzu."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.debug_logs.append(f"[{Theme.TEXT_DIM}]{timestamp}[/{Theme.TEXT_DIM}] {msg}")
        if len(self.debug_logs) > 15:
            self.debug_logs.pop(0)

    def _make_layout(self) -> Layout:
        """Erzeugt das Rich-Layout."""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=10),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        layout["main"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=1)
        )
        layout["left"].split_column(
            Layout(name="chat_history")
        )
        return layout

    def _get_header(self) -> Panel:
        """Erzeugt den Header im Screenshot-Stil."""
        banner = f"""[bold {Theme.PRIMARY}]
 ██████╗ ██╗  ██╗  █████╗  ██████╗  ██████╗ ██╗ ███████╗
██╔════╝ ██║  ██║ ██╔══██╗ ██╔══██╗ ██╔══██╗██║ ██╔════╝
██║      ███████║ ███████║ ██████╔╝ ██████╔╝██║ █████╗  
██║      ██╔══██║ ██╔══██║ ██╔═══╝  ██╔═══╝ ██║ ██╔══╝  
╚██████╗ ██║  ██║ ██║  ██║ ██║      ██║     ██║ ███████╗
 ╚═════╝ ╚═╝  ╚═╝ ╚═╝  ╚═╝ ╚═╝      ╚═╝     ╚═╝ ╚══════╝[/bold {Theme.PRIMARY}]
 [bold {Theme.ACCENT}]Ein KI-Agent mit episodischem Gedaechtnis[/bold {Theme.ACCENT}]
        """
        
        if self.is_sleeping:
            mode = f"[bold {Theme.TEXT_DIM}]SCHLAFMODUS[/bold {Theme.TEXT_DIM}]"
        else:
            mode = f"[bold {Theme.PRIMARY}]TEXTMODUS[/bold {Theme.PRIMARY}]"
            
        model_info = f"[bold {Theme.PRIMARY}]Modell: {get_active_model()}[/bold {Theme.PRIMARY}]"
        
        return Panel(
            Align.left(banner),
            title=mode,
            title_align="center",
            subtitle=model_info,
            subtitle_align="center",
            style=Theme.PRIMARY,
            border_style=Theme.PRIMARY
        )

    def _get_footer(self) -> Panel:
        """Erzeugt den Footer (Input Zeile)."""
        cursor = "[blink]|[/blink]"
        if self.is_sleeping:
            content = f"[{Theme.TEXT_DIM}]CHAPiE schlaeft... Druecke eine Taste zum Aufwecken[/{Theme.TEXT_DIM}]"
        else:
            content = f"[bold {Theme.USER_NAME}]>[/bold {Theme.USER_NAME}] {escape(self.input_buffer)}{cursor}"
        
        # Scroll-Hinweis
        scroll_hint = f"[{Theme.TEXT_DIM}]Scroll: ↑↓ PgUp/PgDn Home/End | /help fuer Befehle[/{Theme.TEXT_DIM}]"
        
        return Panel(
            content, 
            title=scroll_hint,
            style=Theme.BORDER,
            border_style=Theme.BORDER
        )



    def _get_chat_view(self) -> Panel:
        """Zeigt den Chatverlauf (Links)."""
        history_text = self.chat_history.render()
        
        return Panel(
            history_text, 
            title=f"[{Theme.PRIMARY}]Chat History[/{Theme.PRIMARY}]",
            border_style=Theme.BORDER_ACTIVE if self.focus_mode == "chat" else Theme.BORDER,
            style=Theme.BG_PANEL
        )

    def _get_debug_panel(self) -> Panel:
        """Erzeugt das Debug/Status Panel (Rechts)."""
        state = self.emotions.get_state()
        
        # Emotional Status Table
        emo_table = Table.grid(expand=True, padding=(0, 1))
        emo_table.add_column(style=Theme.TEXT_DIM, width=12)
        emo_table.add_column(style=Theme.TEXT)
        
        def make_bar(value: int, color: str) -> str:
            filled = int(value / 10)
            empty = 10 - filled
            return f"[{color}]{'|' * filled}[/{color}][{Theme.TEXT_DIM}]{'|' * empty}[/{Theme.TEXT_DIM}] {value}"
        
        emo_table.add_row("Freude:", make_bar(state.happiness, Theme.SUCCESS))
        emo_table.add_row("Vertrauen:", make_bar(state.trust, Theme.PRIMARY))
        emo_table.add_row("Energie:", make_bar(state.energy, Theme.WARNING))
        emo_table.add_row("Neugier:", make_bar(state.curiosity, Theme.SECONDARY))
        emo_table.add_row("Motivation:", make_bar(state.motivation, Theme.ACCENT))
        
        # Logs
        log_content = "\n".join(self.debug_logs[-8:]) if self.debug_logs else f"[{Theme.TEXT_DIM}]Keine Logs[/{Theme.TEXT_DIM}]"
        
        # Thought History
        if self.current_thought:
             # Live updated current thought not added to history yet
             pass

        thought_text = self.thought_history.render(visible_height=8)
        if not thought_text:
            thought_text = Text("Keine Gedanken bisher...", style=Theme.TEXT_DIM)

        if self.current_thought:
            thought_text.append(f"\n[Aktuell]: {self.current_thought}", style=f"italic {Theme.WARNING}")

        style_thoughts = Theme.BORDER_ACTIVE if self.focus_mode == "thoughts" else Theme.BORDER

        full_content = Group(
            Panel(emo_table, title=f"[{Theme.SECONDARY}]Emotionen[/{Theme.SECONDARY}]", border_style=Theme.BORDER),
            Panel(thought_text, title=f"[{Theme.WARNING}]Gedanken Verlauf (TAB zum Wechseln)[/{Theme.WARNING}]", border_style=style_thoughts, height=12),
            Panel(log_content, title=f"[{Theme.TEXT_DIM}]System Logs[/{Theme.TEXT_DIM}]", border_style=Theme.BORDER)
        )
        
        return Panel(
            full_content, 
            title=f"[{Theme.PRIMARY}]Status[/{Theme.PRIMARY}]",
            border_style=Theme.BORDER
        )

    def _update_ui(self, layout: Layout):
        """Aktualisiert alle Layout-Komponenten."""
        layout["header"].update(self._get_header())
        layout["footer"].update(self._get_footer())
        

        
        layout["left"]["chat_history"].update(self._get_chat_view())
        layout["right"].update(self._get_debug_panel())

    def _handle_command(self, command: str) -> bool:
        """
        Verarbeitet Slash-Commands.
        Returns: True wenn Command verarbeitet wurde, False sonst.
        """
        cmd = command.lower().strip()
        
        # Check ob Command im Schlafmodus erlaubt ist
        if self.is_sleeping and cmd not in self.SLEEP_MODE_COMMANDS:
            self.chat_history.add("system", "CHAPiE schlaeft... Nur /sleep, /help, /exit sind verfuegbar.")
            return True
        

        
        # Memory Stats
        if cmd == "/memory":
            count = self.memory.get_memory_count()
            recent = self.memory.get_recent_memories(3)
            
            msg = f"Speicher-Statistik:\n"
            msg += f"- Gespeicherte Erinnerungen: {count}\n"
            if recent:
                msg += f"- Letzte Erinnerungen:\n"
                for mem in recent[:3]:
                    short = mem.content[:50] + "..." if len(mem.content) > 50 else mem.content
                    msg += f"  [{mem.role}] {short}\n"
            
            self.chat_history.add("system", msg)
            self.log_debug(f"Memory Stats abgerufen: {count} Eintraege")
            return True
        
        # Status
        if cmd == "/status":
            state = self.emotions.get_state()
            mood = state.get_mood_description()
            
            msg = f"Emotionaler Status von CHAPPiE:\n"
            msg += f"- Freude: {state.happiness}/100\n"
            msg += f"- Vertrauen: {state.trust}/100\n"
            msg += f"- Energie: {state.energy}/100\n"
            msg += f"- Neugier: {state.curiosity}/100\n"
            msg += f"- Motivation: {state.motivation}/100\n"
            msg += f"\n{mood}"
            
            self.chat_history.add("system", msg)
            self.log_debug("Status abgerufen")
            return True
        
        # Clear Chat
        if cmd == "/clear":
            self.chat_history = ScrollableHistory()
            self._add_banner_to_history()
            self.log_debug("Chat-Verlauf geloescht")
            return True
        
        # Config
        if cmd == "/config":
            msg = f"Aktuelle Konfiguration:\n"
            msg += f"- Provider: {settings.llm_provider.value}\n"
            msg += f"- Modell: {get_active_model()}\n"
            msg += f"- Temperatur: {settings.temperature}\n"
            msg += f"- Max Tokens: {settings.max_tokens}\n"
            msg += f"- Streaming: {'Ja' if settings.stream else 'Nein'}\n"
            msg += f"- Chain of Thought: {'Ja' if settings.chain_of_thought else 'Nein'}"
            
            self.chat_history.add("system", msg)
            self.log_debug("Konfiguration angezeigt")
            return True
        
        # Sleep Mode
        if cmd == "/sleep":
            if self.is_sleeping:
                # Aufwachen
                self.is_sleeping = False
                self.chat_history.add("system", "CHAPPiE ist aufgewacht!")
                self.log_debug("Aus Schlafmodus aufgewacht")
            else:
                # Konsolidierung starten
                self.chat_history.add("system", "CHAPPiE startet die Traum-Phase...")
                self.log_debug("Memory-Konsolidierung gestartet")
                result = self.memory.consolidate_memories(self.brain)
                self.chat_history.add("system", result)
                self.emotions.restore_energy(30)
                self.log_debug("Traum-Phase abgeschlossen")
            return True
        
        # Think Mode
        if cmd.startswith("/think"):
            # Extrahiere optionales Thema
            parts = command.split(" ", 1)
            topic = parts[1] if len(parts) > 1 else ""
            
            self.chat_history.add("system", f"CHAPPiE startet tiefen Reflektionsmodus...")
            self.log_debug(f"Think-Modus gestartet (Thema: {topic if topic else 'Allgemein'})")
            
            # Iteriere ueber alle Denkschritte
            for step_result in self.memory.think_deep(self.brain, topic=topic, steps=10, delay=1.0):
                step = step_result["step"]
                total = step_result["total_steps"]
                thought = step_result["thought"]
                mem_count = step_result["memories_found"]
                
                # Gedanken zum Thought-History hinzufuegen
                self.thought_history.add("system", f"[{step}/{total}] {thought}")
                self.current_thought = f"Schritt {step}/{total}: {thought[:50]}..."
                self.log_debug(f"Think Schritt {step}: {mem_count} Erinnerungen gefunden")
                
                # Bei Fehler abbrechen
                if step_result.get("error"):
                    self.chat_history.add("system", f"Fehler bei Schritt {step}: {thought}")
                    break
            
            self.current_thought = ""
            self.chat_history.add("system", f"Reflektionsmodus abgeschlossen. 10 Gedanken generiert und gespeichert.")
            self.log_debug("Think-Modus beendet")
            return True
        
        # Help
        if cmd == "/help":
            msg = "Verfuegbare Befehle:\n"
            for cmd_name, desc in self.COMMANDS.items():
                msg += f"- {cmd_name}: {desc}\n"
            
            self.chat_history.add("system", msg)
            return True
        
        # Exit
        if cmd in ["/exit", "/quit"]:
            self.chat_history.add("system", "Auf Wiedersehen!")
            time.sleep(0.5)
            sys.exit(0)
        
        # Unbekannter Command
        if cmd.startswith("/"):
            self.chat_history.add("system", f"Unbekannter Befehl: {cmd}\nNutze /help fuer eine Liste aller Befehle.")
            return True
        
        return False

    def process_user_input(self, user_text: str, skip_history: bool = False):
        """Generiert die Antwort."""
        
        # Commands zuerst pruefen
        if user_text.startswith("/"):
            if self._handle_command(user_text):
                return

        # Chat Logic
        if not skip_history:
            self.chat_history.add("user", user_text)
            
        self.log_debug(f"Input: {user_text[:40]}...")
        
        try:
            # Sentiment
            sentiment = analyze_sentiment_simple(user_text)
            self.emotions.update_from_sentiment(sentiment)
            
            # Memory
            memories = self.memory.search_memory(user_text)
            memories_text = self.memory.format_memories_for_prompt(memories)
            
            # Prompt
            state = self.emotions.get_state()
            system_prompt = get_system_prompt_with_emotions(
                **state.__dict__, 
                use_chain_of_thought=settings.chain_of_thought
            )
            
            messages = self.brain.build_prompt(system_prompt, memories_text, user_text)
            
            # Generate
            full_response = ""
            self.current_thought = "Denke nach..."
            
            is_in_thought = False
            
            for token in self.brain.generate(messages):
                full_response += token
                
                if "<gedanke>" in full_response:
                    is_in_thought = True
                
                if is_in_thought:
                    try:
                        temp_thought = full_response.split("<gedanke>")[1]
                        if "</gedanke>" in temp_thought:
                            temp_thought = temp_thought.split("</gedanke>")[0]
                            is_in_thought = False
                        self.current_thought = temp_thought
                    except:
                        pass
            
            # Final Parse for Output
            from brain.response_parser import parse_chain_of_thought
            if settings.chain_of_thought:
                parsed = parse_chain_of_thought(full_response)
                self.current_thought = parsed.thought if parsed.thought else ""
                display_response = parsed.answer
                
                # Wenn Thought fertig ist, zum Verlauf hinzufuegen
                if parsed.thought:
                    self.thought_history.add("system", parsed.thought)
            else:
                display_response = full_response
                self.current_thought = ""
            
            # Fallback fuer leere Antworten
            if not display_response or not display_response.strip():
                 self.chat_history.add("system", "CHAPPiE schaut dich stumm an und weiss nicht, was er sagen soll.")
                 self.log_debug("Antwort war leer -> Fallback ausgeloest")
            else:
                self.chat_history.add("assistant", display_response)
                self.log_debug(f"Antwort generiert ({len(display_response)} Zeichen)")
            
            # Speichere ASYNCHRON im Hintergrund
            def save_background(u_text, a_text):
                try:
                    self.memory.add_memory(u_text, role="user")
                    self.memory.add_memory(a_text, role="assistant")
                    # Nur fuer Debugging im Main Thread sichtbar machen via Log
                    if settings.debug:
                        # self.log_debug("Erinnerungen im Hintergrund gespeichert")
                        pass
                except Exception as ex:
                    pass

            threading.Thread(target=save_background, args=(user_text, display_response), daemon=True).start()



        except Exception as e:
            self.log_debug(f"[{Theme.ERROR}]FEHLER: {e}[/{Theme.ERROR}]")
            self.chat_history.add("system", f"Fehler bei der Verarbeitung: {str(e)}")

    def run(self):
        """Der neue non-blocking Main Loop."""
        layout = self._make_layout()
        
        with Live(layout, refresh_per_second=24, screen=True) as live:
            while True:
                self._update_ui(layout)
                live.refresh()
                
                if msvcrt.kbhit():
                    char = msvcrt.getwch()

                    
                    # Special Keys (Arrow Keys, Page Up/Down, Home/End) - IMMER erlauben, auch im Schlafmodus
                    if char in ('\x00', '\xe0'):
                        try:
                            # Das zweite Byte des Special Keys lesen (ohne kbhit check, da \xe0 es garantiert)
                            special = msvcrt.getwch()
                            
                            # Page Up (I) / Pfeil Hoch (H) 
                            if special == 'H':  # Arrow Up
                                if self.focus_mode == "chat":
                                    self.chat_history.scroll_up(1)
                                else:
                                    self.thought_history.scroll_up(1)
                            elif special == 'I':  # Page Up
                                if self.focus_mode == "chat":
                                    self.chat_history.scroll_up(5)
                                else:
                                    self.thought_history.scroll_up(5)
                            # Page Down (Q) / Pfeil Runter (P)
                            elif special == 'P':  # Arrow Down
                                if self.focus_mode == "chat":
                                    self.chat_history.scroll_down(1)
                                else:
                                    self.thought_history.scroll_down(1)
                            elif special == 'Q':  # Page Down
                                if self.focus_mode == "chat":
                                    self.chat_history.scroll_down(5)
                                else:
                                    self.thought_history.scroll_down(5)
                            # Home (G) / End (O)
                            elif special == 'G':  # Home
                                if self.focus_mode == "chat":
                                    self.chat_history.scroll_to_top()
                                else:
                                    self.thought_history.scroll_to_top()
                            elif special == 'O':  # End
                                if self.focus_mode == "chat":
                                    self.chat_history.scroll_to_bottom()
                                else:
                                    self.thought_history.scroll_to_bottom()
                            else:
                                # Unbekannter Spezial-Key Code loggen fuer Debug
                                self.log_debug(f"Spezial-Key Code: {special}")
                                
                            # UI sofort updaten fuer fluessiges Scrolling
                            self._update_ui(layout)
                            live.refresh()
                        except Exception as e:
                            self.log_debug(f"Scroll-Fehler: {e}")
                        continue
                    
                    # TAB Switch Focus
                    if char == '\t' and not self.input_buffer.startswith("/"):
                         self.focus_mode = "thoughts" if self.focus_mode == "chat" else "chat"
                         self._update_ui(layout)
                         live.refresh()
                         continue
                    
                    # Check fuer Commands im Schlafmodus
                    if self.is_sleeping:
                        # Erlaube Befehls-Eingabe im Schlafmodus
                        if char == '\r' and self.input_buffer.strip().startswith('/'):
                            user_msg = self.input_buffer
                            self.input_buffer = ""
                            self.process_user_input(user_msg, skip_history=True)
                            continue
                        # Normale Taste = Aufwachen
                        elif char.isprintable() or char == '\r':
                            self.is_sleeping = False
                            self.chat_history.add("system", "CHAPPiE ist aufgewacht!")
                            self.log_debug("Aus Schlafmodus aufgewacht")
                            # Verarbeite den Character normal weiter
                        else:
                            continue
                    
                    if char == '\r':  # Enter
                        if self.input_buffer.strip():
                            user_msg = self.input_buffer
                            self.input_buffer = ""
                            
                            # Zeige Input sofort im Chat (nur wenn kein Command)
                            if not user_msg.startswith("/"):
                                self.chat_history.add("user", user_msg)
                            self._update_ui(layout)
                            live.refresh()
                            
                            # Verarbeite
                            self.process_user_input(user_msg, skip_history=True)
                            
                    elif char == '\x08':  # Backspace
                        self.input_buffer = self.input_buffer[:-1]
                    
                    elif char == '\x03':  # Ctrl+C
                        raise KeyboardInterrupt
                    
                    elif char == '\t':  # Tab - Autocomplete Commands
                        if self.input_buffer.startswith("/"):
                            matches = [c for c in self.COMMANDS.keys() if c.startswith(self.input_buffer)]
                            if len(matches) == 1:
                                self.input_buffer = matches[0]
                    
                    elif char == ' ':  # Leertaste - Intelligente Behandlung
                        # Nur als normales Zeichen wenn bereits Text eingegeben wurde
                        if self.input_buffer:
                            self.input_buffer += char
                            self.last_input_time = time.time()
                        # Sonst wird PTT durch keyboard-Library gehandhabt
                        
                    elif char and char.isprintable():
                        self.input_buffer += char
                        self.last_input_time = time.time()

                time.sleep(0.05)


def main():
    try:
        chapie = CHAPPiE()
        chapie.run()
    except KeyboardInterrupt:
        console.print(f"\n[{Theme.TEXT_DIM}]Auf Wiedersehen![/{Theme.TEXT_DIM}]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[{Theme.ERROR}]Kritischer Fehler: {e}[/{Theme.ERROR}]")
        sys.exit(1)

if __name__ == "__main__":
    main()

