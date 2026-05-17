"""CHAPPiE Terminal Interface v5.0

Rich-formatted terminal client with live token streaming,
full debug output, and backend+SSE connectivity.

Modes:
  Local  - Direct backend (create_chappie_backend), no server needed
  Remote - Connects to running chappie-web via SSE (HTTP)

Usage:
  python chappie_brain_cli.py              # Local mode (default)
  python chappie_brain_cli.py --remote     # Remote mode (connects to :8010)
  python chappie_brain_cli.py --remote --url http://100.105.94.71:8010
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional, Generator

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.live import Live
    from rich.markdown import Markdown
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


if HAS_RICH:
    console = Console()
else:
    console = None


def _print_fallback(msg: str, style: str = ""):
    if console and HAS_RICH:
        console.print(msg, style=style)
    else:
        print(msg)


class Colors:
    DEBUG = "\033[36m"
    MEMORY = "\033[35m"
    EMOTION = "\033[33m"
    THOUGHT = "\033[90m"
    AI = "\033[34m"
    USER = "\033[32m"
    STEER = "\033[31m"
    SUCCESS = "\033[32m"
    ERROR = "\033[91m"
    WARN = "\033[93m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _log(category: str, msg: str, color: str = Colors.DEBUG):
    print(f"{color}[{_ts()}] [{category}] {msg}{Colors.RESET}")


def _success(msg: str):
    _log("OK", msg, Colors.SUCCESS)


def _error(msg: str):
    _log("ERROR", msg, Colors.ERROR)


def _warn(msg: str):
    _log("WARN", msg, Colors.WARN)


def _bar(value: int, max_val: int = 100, width: int = 10) -> str:
    filled = int(width * value / max_val)
    return "\u2588" * filled + "\u2591" * (width - filled)


def _format_emotion_row(name: str, value: int) -> str:
    bar = _bar(value)
    return f"  {name:>12} {bar} {value:>3}/100"


def _format_debug_entries(entries: list) -> str:
    if not entries:
        return ""
    lines = []
    for entry in entries:
        if isinstance(entry, dict):
            cat = entry.get("category", "?")
            detail = entry.get("detail", "")
            data = entry.get("data", {})
            if isinstance(data, dict) and len(str(data)) > 200:
                data = {k: ("..." if isinstance(v, (dict, list)) and len(str(v)) > 80 else v) for k, v in data.items()}
            lines.append(f"  [{cat}] {detail}")
            if data:
                for k, v in (data.items() if isinstance(data, dict) else []):
                    lines.append(f"    {k}: {v}")
        else:
            lines.append(f"  {entry}")
    return "\n".join(lines)


class RemoteBackend:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session_id = None

    def get_status(self) -> Dict[str, Any]:
        try:
            r = requests.get(f"{self.base_url}/", timeout=5)
            return r.json()
        except Exception:
            return {}

    def stream_chat(self, message: str, debug_mode: bool = True) -> Generator[Dict[str, Any], None, None]:
        payload = {
            "message": message,
            "debug_mode": debug_mode,
        }
        if self.session_id:
            payload["session_id"] = self.session_id
        try:
            r = requests.post(
                f"{self.base_url}/chat/stream",
                json=payload,
                stream=True,
                headers={"Accept": "text/event-stream"},
                timeout=120,
            )
            r.raise_for_status()
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("event: "):
                    event_type = line[7:].strip()
                    continue
                if line.startswith("data: "):
                    data_str = line[6:]
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    yield data
        except Exception as e:
            _error(f"Connection error: {e}")

    def handle_command(self, command: str) -> str:
        try:
            r = requests.post(
                f"{self.base_url}/command",
                json={"command": command},
                timeout=10,
            )
            r.raise_for_status()
            result = r.json()
            return result.get("output", json.dumps(result))
        except Exception as e:
            return f"Error: {e}"


class CHAPPiEBrainCLI:
    def __init__(self, remote_url: Optional[str] = None):
        self.remote_url = remote_url
        self.backend = None
        self.history: list = []
        self.last_result: Optional[Dict[str, Any]] = None
        self._use_remote = remote_url is not None

        _log("INIT", "Initialisiere CHAPPiE Brain Interface v5.0...", Colors.AI)

        if self._use_remote:
            if not HAS_REQUESTS:
                _error("'requests' muss installiert sein fuer Remote-Modus (pip install requests)")
                sys.exit(1)
            self.remote = RemoteBackend(remote_url)
            _log("INIT", f"Remote-Modus: {remote_url}", Colors.AI)
            status = self.remote.get_status()
            if status:
                _log("INIT", f"Backend erreichbar: {status.get('model', '?')}", Colors.SUCCESS)
            else:
                _warn("Backend nicht erreichbar - versuche es trotzdem")
        else:
            from web_infrastructure.backend_wrapper import create_chappie_backend
            self.backend = create_chappie_backend()
            self.emotions = self.backend.emotions
            self.memory = self.backend.memory
            self.steering = self.backend.steering_manager
            self.context = self.backend.context_files
            status = self.backend.get_status()
            model = status.get("model", "?")
            _log("INIT", f"Lokaler Modus: {model}", Colors.AI)
            _log("INIT", f"Provider: {self._settings().llm_provider.value}", Colors.AI)
            from config.config import settings as _s
            if _s.enable_steering:
                is_local = self.steering.is_local_provider()
                mode = "LOKAL (Vektor-Injection)" if is_local else "CLOUD (Prompt-basiert)"
                _log("INIT", f"Steering: {mode}", Colors.STEER)
            else:
                _log("INIT", "Steering: DEAKTIVIERT", Colors.DIM)

    @staticmethod
    def _settings():
        from config.config import settings
        return settings

    def _process_local(self, user_text: str):
        backend = self.backend
        _log("STEP1", "Intent-Analyse + Emotion-Update...", Colors.EMOTION)
        result = backend.process(user_text, self.history, debug_mode=True)
        self.last_result = result
        self._display_full_result(user_text, result)

    def _process_remote(self, user_text: str):
        collected_tokens = {"reasoning": "", "answer": ""}
        turn_finished_data = None
        for data in self.remote.stream_chat(user_text):
            event_type = data.get("event", "token")
            if event_type == "token" or "content" in data:
                token_type = data.get("token_type", "answer")
                content = data.get("content", "")
                if token_type == "reasoning":
                    collected_tokens["reasoning"] += content
                    print(f"{Colors.THOUGHT}{content}{Colors.RESET}", end="", flush=True)
                else:
                    collected_tokens["answer"] += content
                    print(f"{Colors.AI}{content}{Colors.RESET}", end="", flush=True)
            elif event_type == "turn_finished" or "assistant_message" in data:
                turn_finished_data = data
                break
            elif event_type == "turn_error":
                _error(data.get("error", "Unbekannter Fehler"))
                break
            elif event_type == "status":
                step = data.get("step", "?")
                status_text = data.get("status_text", "")
                _log(f"STEP{step}", status_text, Colors.EMOTION)
        print()
        if turn_finished_data:
            msg = turn_finished_data.get("assistant_message", turn_finished_data)
            metadata = msg.get("metadata", {}) if isinstance(msg, dict) else {}
            self._display_metadata(metadata, collected_tokens.get("answer", ""))

    def _display_full_result(self, user_text: str, result: Dict[str, Any]):
        metadata = result.get("metadata", result)
        response_text = result.get("response_text", "")
        formatted_cot = metadata.get("formatted_cot", "")
        formatted_answer = metadata.get("formatted_answer", "")
        display_text = formatted_answer if formatted_answer else response_text
        reasoning_text = formatted_cot if formatted_cot else metadata.get("model_reasoning", "")
        intent_type = metadata.get("intent_type", "?")
        confidence = metadata.get("intent_confidence", 0.0)
        tools = metadata.get("selected_tools", [])
        steering = metadata.get("emotion_steering", metadata.get("emotion_delta", {}))
        proc_time = metadata.get("processing_time_ms", 0)
        provider = result.get("provider", metadata.get("provider", "?"))
        model = result.get("model", metadata.get("model", "?"))
        rag_count = len(metadata.get("rag_memories", []))
        emotions_before = metadata.get("emotions_before", {})
        emotions_after = metadata.get("emotions", {})
        emotions_delta = metadata.get("emotions_delta", {})
        debug_entries = metadata.get("debug_entries", [])
        workspace = metadata.get("global_workspace", {})
        memory_trace = metadata.get("memory_trace", {})
        prompt_mode = metadata.get("prompt_emotion_mode", "?")
        tone_decision = metadata.get("tone_decision", {})
        action_plan = metadata.get("action_plan", {})
        context_budget = metadata.get("context_budget", {})

        if reasoning_text:
            if HAS_RICH and console:
                console.print(Panel(reasoning_text, title="[dim]CHAPPiEs Gedanken (CoT)[/dim]", border_style="dim", padding=(0, 1)))
            else:
                print(f"\n{Colors.THOUGHT}--- CHAPPiEs Gedanken ---")
                print(reasoning_text)
                print(f"---{Colors.RESET}\n")

        if display_text:
            print(f"\n{Colors.AI}{Colors.BOLD}CHAPPiE >{Colors.RESET} {display_text}\n")

        print(f"{Colors.DEBUG}{'─' * 60}")
        print(f"  [INTENT]  {intent_type} (Confidence: {confidence:.2f})")
        if tools:
            print(f"  [TOOLS]   {', '.join(tools[:5])}")
        else:
            print(f"  [TOOLS]   keine")
        print(f"  [MEM]     {rag_count} RAG-Memories")
        if memory_trace:
            query = memory_trace.get("query", "?")[:60]
            print(f"  [QUERY]   {query}")
        print(f"  [STEER]   [{prompt_mode}] {steering.get('dominant_vector', 'neutral')} ({steering.get('dominant_strength', 0):.2f})")
        if workspace:
            focus = workspace.get("dominant_focus", {})
            print(f"  [FOCUS]   {focus.get('label', '?')}")
        print(f"  [TIME]    {proc_time:.0f} ms | {provider}/{model}")
        if context_budget:
            used = context_budget.get("used", 0)
            limit = context_budget.get("limit", 0)
            print(f"  [CTX]     {used}/{limit} tokens")
        if tone_decision:
            print(f"  [TONE]    {tone_decision.get('strategy', '?')} | {tone_decision.get('tone', '?')}")
        if action_plan:
            actions = action_plan.get("recommended_actions", [])
            if actions:
                print(f"  [ACTIONS] {', '.join(str(a) for a in actions[:3])}")

        if emotions_before:
            print(f"\n  {Colors.EMOTION}Emotionen:{Colors.RESET}")
            for emo in ("happiness", "trust", "energy", "curiosity", "motivation", "frustration", "sadness"):
                before = emotions_before.get(emo, 0)
                after = emotions_after.get(emo, 0)
                delta = after - before
                sign = "+" if delta > 0 else ""
                bar = _bar(after)
                emo_color = Colors.SUCCESS if after >= 50 else Colors.WARN if after >= 25 else Colors.ERROR
                print(f"    {emo:>12} {bar} {after:>3} ({sign}{delta})")

        if debug_entries:
            debug_text = _format_debug_entries(debug_entries[:15])
            if debug_text and HAS_RICH and console:
                console.print(Panel(debug_text, title="[dim]Debug[/dim]", border_style="dim"))
            elif debug_text:
                print(f"\n{Colors.DIM}{debug_text}{Colors.RESET}")

        print(f"{'─' * 60}{Colors.RESET}")

        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": display_text})

    def _display_metadata(self, metadata: Dict[str, Any], fallback_text: str = ""):
        if not metadata:
            return
        formatted_answer = metadata.get("formatted_answer", fallback_text)
        formatted_cot = metadata.get("formatted_cot", "")
        emotions = metadata.get("emotions", {})
        proc_time = metadata.get("processing_time_ms", 0)
        intent_type = metadata.get("intent_type", "?")
        confidence = metadata.get("intent_confidence", 0.0)
        tools = metadata.get("selected_tools", [])
        steering = metadata.get("emotion_steering", {})
        debug_entries = metadata.get("debug_entries", [])

        if formatted_cot:
            print(f"\n{Colors.THOUGHT}--- CHAPPiEs Gedanken ---")
            print(formatted_cot)
            print(f"---{Colors.RESET}\n")

        if formatted_answer:
            print(f"\n{Colors.AI}{Colors.BOLD}CHAPPiE >{Colors.RESET} {formatted_answer}\n")

        print(f"{Colors.DEBUG}[INTENT] {intent_type} ({confidence:.2f}) | [TOOLS] {', '.join(tools[:5]) or 'keine'} | [TIME] {proc_time:.0f}ms")
        if steering:
            print(f"[STEER] {steering.get('dominant_vector', '?')} ({steering.get('dominant_strength', 0):.2f})")
        if emotions:
            emo_str = " | ".join(f"{k}:{v}" for k, v in emotions.items())
            print(f"[EMOTIONS] {emo_str}")
        if debug_entries:
            debug_text = _format_debug_entries(debug_entries[:10])
            if debug_text:
                print(f"{Colors.DIM}{debug_text}{Colors.RESET}")
        print(f"{Colors.RESET}")

    def _show_status(self):
        if self._use_remote:
            try:
                r = requests.get(f"{self.remote_url}/", timeout=5)
                status = r.json()
            except Exception:
                _error("Backend nicht erreichbar")
                return
        else:
            status = self.backend.get_status()

        emotions = status.get("emotions", {})
        if not emotions and not self._use_remote:
            state = self.emotions.get_state()
            emotions = state.to_dict()
        life = status.get("life_state", {})

        print(f"\n{Colors.EMOTION}{'═' * 50}")
        print(f"  CHAPPiE Status")
        print(f"{'═' * 50}")

        if emotions:
            mood = "neutral"
            if isinstance(emotions, dict):
                h = emotions.get("happiness", 50)
                s = emotions.get("sadness", 0)
                f = emotions.get("frustration", 0)
                if h > 60: mood = "positiv"
                elif s > 40 or f > 50: mood = "angespannt"
            print(f"  Stimmung: {mood}")
            for name in ("happiness", "trust", "energy", "curiosity", "motivation", "frustration", "sadness"):
                val = emotions.get(name, 0) if isinstance(emotions, dict) else 0
                bar = _bar(val)
                emo_color = Colors.SUCCESS if val >= 50 else Colors.WARN if val >= 25 else Colors.ERROR
                print(f"    {name:>12} {bar} {val:>3}")

        if life:
            print(f"\n  Phase: {life.get('clock', {}).get('phase_label', '?')}")
            goal = life.get('active_goal', {})
            if goal:
                print(f"  Ziel: {goal.get('title', '?')} ({goal.get('progress', 0):.0%})")

        print(f"  Modell: {status.get('model', '?')} | Provider: {status.get('provider', '?')}")
        two_step = "AN" if status.get("two_step_enabled") else "AUS"
        print(f"  Two-Step: {two_step}")
        print(f"{'═' * 50}{Colors.RESET}\n")

    def _handle_command(self, cmd: str) -> bool:
        cmd_lower = cmd.lower().strip()

        if cmd_lower in ("/exit", "/quit"):
            return False

        if cmd_lower == "/status":
            self._show_status()
            return True

        if cmd_lower == "/help":
            print(f"""
{Colors.AI}{Colors.BOLD}CHAPPiE Terminal Interface v5.0{Colors.RESET}
{Colors.DEBUG}───────────────────────────────────────────────
  /status     Emotionaler Status + Life-Simulation
  /last       Letzter Turn: Metriken & Debug-Info
  /runtime    Modell, Provider, Steering-Konfiguration
  /steering   Detaillierter Steering-Report
  /emotion <name> <0-100>  Emotion manuell setzen
  /resetemotions           Emotionen zuruecksetzen
  /sleep      Schlafphase erzwingen
  /memory     Kurzzeitgedaechtnis anzeigen
  /history    Chat-Verlauf anzeigen
  /clear      Chat-Verlauf loeschen
  /debug on/off           Debug-Output ein/ausschalten
  /exit       Beenden
  /help       Diese Hilfe{Colors.RESET}
""")
            return True

        if cmd_lower == "/last":
            if self.last_result:
                self._display_full_result("(last)", self.last_result)
            else:
                _log("LAST", "Noch keine Antwort vorhanden.", Colors.DIM)
            return True

        if cmd_lower == "/runtime":
            if self._use_remote:
                _log("RUNTIME", "Nur im lokalen Modus verfuegbar", Colors.WARN)
                return True
            s = self._settings()
            steering = self.backend.steering_manager
            is_local = steering.is_local_provider()
            mode = "VEKTOR" if is_local else "PROMPT"
            print(f"\n{Colors.AI}{'═' * 50}")
            print(f"  RUNTIME")
            print(f"{'═' * 50}")
            print(f"  Provider:     {s.llm_provider.value}")
            print(f"  Modell:        {s.vllm_model}")
            print(f"  vLLM URL:      {s.vllm_url}")
            print(f"  Two-Step:      {'AN' if s.enable_two_step_processing else 'AUS'}")
            print(f"  Steering:      {'AN' if s.enable_steering else 'AUS'} ({mode})")
            print(f"  Intent-Modell: {s.get_intent_model(s.intent_provider)}")
            print(f"  Steering-Modell: {s.steering_model}")
            print(f"  Context-Laenge: {s.steering_context_length}")
            print(f"  Quantisierung: {'AN' if s.steering_quantize else 'AUS'}")
            print(f"{'═' * 50}{Colors.RESET}\n")
            return True

        if cmd_lower == "/steering":
            if self._use_remote:
                _log("STEERING", "Nur im lokalen Modus verfuegbar", Colors.WARN)
                return True
            report = self.backend.steering_manager.build_debug_report(self.emotions.get_state().to_dict())
            print(f"\n{Colors.STEER}{'═' * 50}")
            print(f"  STEERING REPORT")
            print(f"{'═' * 50}")
            print(f"  Modus:     {report.get('mode', '?')}")
            print(f"  Aktiv:     {'JA' if report.get('steering_active') else 'NEIN'}")
            print(f"  Dominant:  {report.get('dominant_vector', 'neutral')} ({report.get('dominant_strength', 0):.2f})")
            print(f"  Vektoren:  {', '.join(v.get('name', '?') for v in report.get('base_vectors', [])[:5])}")
            print(f"{'═' * 50}{Colors.RESET}\n")
            return True

        if cmd_lower.startswith("/emotion "):
            parts = cmd.split()
            if len(parts) != 3:
                _log("EMOTION", "Nutze: /emotion <name> <0-100>", Colors.EMOTION)
                return True
            _, emotion, val = parts
            try:
                value = int(val)
            except ValueError:
                _error(f"Ungueltiger Wert: {val}")
                return True
            valid = {"happiness", "trust", "energy", "curiosity", "frustration", "motivation", "sadness"}
            if emotion not in valid:
                _error(f"Unbekannte Emotion: {emotion}")
                return True
            if self._use_remote:
                try:
                    r = requests.post(f"{self.remote_url}/emotions/state", json={emotion: value}, timeout=5)
                    _success(f"{emotion} auf {value} gesetzt (remote)")
                except Exception as e:
                    _error(f"Remote-Fehler: {e}")
            else:
                self.emotions.set_emotion(emotion, value)
                _success(f"{emotion} auf {value} gesetzt")
            return True

        if cmd_lower == "/resetemotions":
            if self._use_remote:
                try:
                    r = requests.get(f"{self.remote_url}/emotions/state", timeout=5)
                    _log("RESET", "Emotionen remote zurueckgesetzt (manuell)", Colors.EMOTION)
                except Exception:
                    pass
            else:
                self.emotions.reset()
            self._show_status()
            return True

        if cmd_lower == "/sleep":
            if self._use_remote:
                _warn("Sleep nur im lokalen Modus verfuegbar")
                return True
            from memory.sleep_phase import get_sleep_phase_handler
            handler = get_sleep_phase_handler()
            result = handler.execute_sleep_phase(memory_engine=self.memory, context_files=self.context)
            if result.get("energy_restored"):
                _success(f"Energie wiederhergestellt: {result.get('energy_value', 100)}%")
            recovery = result.get("emotional_recovery", {})
            for emo, delta in recovery.items():
                sign = "+" if delta > 0 else ""
                _log("SLEEP", f"  {emo}: {sign}{delta}", Colors.EMOTION)
            for frag in result.get("dream_replay", [])[:3]:
                _log("DREAM", frag, Colors.MEMORY)
            return True

        if cmd_lower == "/memory":
            if self._use_remote:
                _warn("Memory nur im lokalen Modus verfuegbar")
                return True
            entries = self.backend.short_term_memory_v2.get_active_entries()
            if not entries:
                _log("STM", "Keine Eintraege im Kurzzeitgedaechtnis", Colors.MEMORY)
            else:
                print(f"\n{Colors.MEMORY}Kurzzeitgedaechtnis ({len(entries)} Eintraege):")
                for e in entries[:10]:
                    print(f"  [{e.category}] {e.content[:80]}{'...' if len(e.content) > 80 else ''}")
                print(f"{Colors.RESET}")
            return True

        if cmd_lower == "/history":
            if not self.history:
                _log("HISTORY", "Kein Chat-Verlauf", Colors.DIM)
            else:
                print(f"\n{Colors.AI}Chat-Verlauf ({len(self.history)} Nachrichten):")
                for msg in self.history[-20:]:
                    role = msg.get("role", "?")
                    content = msg.get("content", "")[:80]
                    color = Colors.USER if role == "user" else Colors.AI
                    print(f"  {color}[{role}] {content}{'...' if len(msg.get('content', '')) > 80 else ''}{Colors.RESET}")
                print()
            return True

        if cmd_lower == "/clear":
            self.history = []
            self.last_result = None
            _success("Chat-Verlauf geloescht")
            return True

        if cmd_lower.startswith("/debug "):
            mode = cmd_lower.split()[1]
            if mode == "on":
                if not self._use_remote and self.backend:
                    self.backend.debug_logger.enable()
                _success("Debug-Output aktiviert")
            elif mode == "off":
                if not self._use_remote and self.backend:
                    self.backend.debug_logger.disable()
                _log("DEBUG", "Debug-Output deaktiviert", Colors.DIM)
            else:
                _log("DEBUG", "Nutze: /debug on oder /debug off", Colors.WARN)
            return True

        backend_cmd = cmd_lower
        if not backend_cmd.startswith("/"):
            backend_cmd = "/" + backend_cmd

        if self._use_remote:
            result = self.remote.handle_command(backend_cmd)
            print(f"\n{Colors.MEMORY}{result}{Colors.RESET}\n")
            return True

        if self.backend:
            result = self.backend.handle_command(backend_cmd)
            if not result.startswith("Unbekannter Command:"):
                print(f"\n{Colors.MEMORY}{result}{Colors.RESET}\n")
                return True

        _warn(f"Unbekannter Befehl: {cmd}")
        print("  Tippe /help fuer alle Befehle")
        return True

    def run(self):
        steering_info = "?"
        if not self._use_remote and self.backend:
            is_local = self.backend.steering_manager.is_local_provider()
            steering_info = "VEKTOR-STEERING" if is_local else "PROMPT-STEERING"

        mode_str = "REMOTE" if self._use_remote else "LOKAL"

        print(f"""
{Colors.AI}{Colors.BOLD}
  ██████╗ ██████╗  █████╗ ██╗███╗   ██╗
  ██╔══██╗██╔══██╗██╔══██╗██║████╗  ██║
  ██████╔╝██████╔╝███████║██║██╔██╗ ██║
  ██╔══██╗██╔══██╗██╔══██║██║██║╚██╗██║
  ██████╔╝██║  ██║██║  ██║██║██║ ╚████║
  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝
{Colors.AI}CHAPPiE Terminal Interface v5.0 [{mode_str}]
{Colors.STEER}Steering: {steering_info} | 7 Emotionale Dimensionen
{Colors.DEBUG}Tippe /help fuer alle Befehle
{Colors.RESET}""")

        self._show_status()

        while True:
            try:
                user_input = input(f"\n{Colors.USER}{Colors.BOLD}Benjamin >{Colors.RESET} ")
            except (KeyboardInterrupt, EOFError):
                break

            if not user_input.strip():
                continue

            if user_input.startswith("/"):
                result = self._handle_command(user_input)
                if result is False:
                    break
                continue

            try:
                if self._use_remote:
                    self._process_remote(user_input)
                else:
                    self._process_local(user_input)
            except Exception as e:
                _error(f"Fehler: {e}")
                import traceback
                traceback.print_exc()

        _log("EXIT", "CHAPPiE beendet. Bis bald!", Colors.AI)


def main():
    parser = argparse.ArgumentParser(description="CHAPPiE Terminal Interface v5.0")
    parser.add_argument("--remote", action="store_true", help="Connect to remote backend via SSE instead of local mode")
    parser.add_argument("--url", default="http://localhost:8010", help="Backend URL for remote mode (default: http://localhost:8010)")
    args = parser.parse_args()

    remote_url = args.url if args.remote else None
    cli = CHAPPiEBrainCLI(remote_url=remote_url)
    cli.run()


if __name__ == "__main__":
    main()