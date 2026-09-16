"""CHAPPiE Terminal Interface v17.2.0-dev.2

Rich-formatted terminal client with live token streaming (CoT + Answer),
full debug output, compact auto-report, and backend+SSE connectivity.
Inkl. /thinking Command zum Aktivieren/Deaktivieren des Reasonings.
Paritaet zur Web-UI (API 17.2.0-dev.2): Sessions, command_mode, alle Slash-Commands.

Modes:
  Local  - Direct backend (create_chappie_backend), process_stream() with Live display
  Remote - Connects to running chappie-web via SSE (HTTP), same Live display

Usage:
  python chappie_brain_cli.py              # Local mode (default)
  python chappie_brain_cli.py --remote     # Remote mode (connects to :8010)
  python chappie_brain_cli.py --remote --url http://100.105.94.71:8010
"""

# Command aus meiner neuen Dev Workbench :) (hat nix mit dem Projekt zu tun)

from __future__ import annotations

import argparse
import io
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional, Generator
from urllib.parse import urlsplit

from config.emotions import EMOTION_ORDER
from config.commands import HELP_COLUMNS

try:
    from rich.console import Console, Group as _RichGroup
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.markdown import Markdown
    from rich.live import Live
    from rich import box
    HAS_RICH = True
except ImportError:
    _RichGroup = None
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


def _response_panel(content: str, title: str, border_style: str):
    """Rendert die sichtbare Antwort als Markdown, Rohtext bleibt literal."""
    return Panel(
        Markdown(content or ""),
        title=title,
        border_style=border_style,
        padding=(0, 1),
    )


def _print_command_output(output: str) -> None:
    """Gibt Befehlsausgaben als gerendertes Markdown aus, damit **fett** nicht literal erscheint."""
    text = output if isinstance(output, str) else str(output)
    if HAS_RICH:
        console.print(_response_panel(text, "[bold magenta]Command[/]", "magenta"))  # type: ignore[union-attr]
    else:
        print(f"\n{Colors.MEMORY}{text}{Colors.RESET}\n")

_FULL_REPORT_DEFAULT = False


_REAL_STDOUT = sys.stdout

CLI_USER_LABEL = "User"


class _StrayOutputCapture:
    """Puffert fremde Prints (Backend- und Sleep-Threads), damit Live-Display und Eingabe sauber bleiben.

    Der Hauptthread schreibt direkt auf das echte stdout, solange kein
    Streaming und keine Eingabe laeuft. Alle anderen Threads landen immer
    im Puffer und werden an sicheren Stellen per drain() als eigener
    Infobereich ausgegeben.
    """

    def __init__(self, real):
        self._real = real
        self._lock = threading.Lock()
        self._buf = io.StringIO()
        self.main_capturing = False

    def write(self, s):
        if threading.current_thread() is threading.main_thread() and not self.main_capturing:
            return self._real.write(s)
        with self._lock:
            return self._buf.write(s)

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    def flush(self):
        try:
            self._real.flush()
        except Exception:
            pass

    def drain(self) -> str:
        with self._lock:
            text = self._buf.getvalue()
            self._buf = io.StringIO()
        return text

    def __getattr__(self, name):
        return getattr(self._real, name)




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


SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

MODEL_ALIASES = {
    "qwen": "Qwen/Qwen3.5-4B",
    "qwen3.5": "Qwen/Qwen3.5-4B",
    "gemma": "google/gemma-4-26B-A4B-it",
    "gemma4": "google/gemma-4-26B-A4B-it",
    "gemma4-26b": "google/gemma-4-26B-A4B-it",
    "gemma4-e4b": "google/gemma-4-E4B-it",
}


def _v(d: dict, key: str, default: Any = "") -> Any:
    return d.get(key, default) if isinstance(d, dict) else default


def _emoji_delta(before: int, after: int) -> str:
    d = after - before
    if d == 0:
        return " →"
    return f"↑+{d}" if d > 0 else f"↓{d}"


def _emo_color(value: int) -> str:
    if value >= 60:
        return "green"
    elif value >= 30:
        return "yellow"
    return "red"


def _count_words(text: str) -> int:
    """V18: Live-Anzeige zaehlt Woerter aus sichtbarem Text, keine SSE-Events."""
    if not isinstance(text, str) or not text.strip():
        return 0
    return len(text.strip().split())


EMOTION_NAMES = EMOTION_ORDER


# ═══════════════════════════════════════════════════════════════════
# RemoteBackend (SSE)
# ═══════════════════════════════════════════════════════════════════

class RemoteBackend:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session_id = None

    def get_status(self) -> Dict[str, Any]:
        # Aktueller Vertrag: /status, Fallback /health und / fuer alte Server.
        for path in ("/status", "/health", "/"):
            try:
                r = requests.get(f"{self.base_url}{path}", timeout=5)
                data = r.json()
            except Exception:
                continue
            if not isinstance(data, dict):
                continue
            # Root / liefert brain.model, /status liefert model direkt.
            if path == "/" and "brain" in data and "model" not in data:
                brain = data.get("brain", {}) or {}
                normalized = {
                    "model": brain.get("model", "?"),
                    "provider": brain.get("provider", "?"),
                    "brain_available": brain.get("available", True),
                    "emotions": data.get("emotions", {}),
                    "life_state": data.get("life", {}),
                    "life_snapshot": data.get("life", {}),
                    "two_step_enabled": brain.get("two_step_processing", False),
                    "_raw": data,
                }
                return normalized
            return data
        return {}

    def stream_events(self, message: str, debug_mode: bool = True, session_id: Optional[str] = None, command_mode: Optional[bool] = None) -> Generator[Dict[str, Any], None, None]:
        sid = session_id if session_id is not None else self.session_id
        if command_mode is None:
            command_mode = message.strip().startswith("/")
        payload: Dict[str, Any] = {"message": message, "debug_mode": debug_mode, "command_mode": command_mode}
        if sid:
            payload["session_id"] = sid
        try:
            r = requests.post(
                f"{self.base_url}/chat/stream",
                json=payload,
                stream=True,
                headers={"Accept": "text/event-stream"},
                timeout=120,
            )
            r.raise_for_status()
            current_event = None
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("event: "):
                    current_event = line[7:].strip()
                    continue
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue
                    data["_sse_event"] = current_event
                    current_event = None
                    # Session aus turn_started und turn_finished uebernehmen.
                    if isinstance(data, dict):
                        incoming_sid = data.get("session_id") or data.get("replacement_session_id")
                        if incoming_sid:
                            self.session_id = incoming_sid
                    yield data
        except Exception as e:
            _error(f"Connection error: {e}")

    def handle_command(self, command: str, session_id: Optional[str] = None) -> str:
        sid = session_id if session_id is not None else self.session_id
        payload: Dict[str, Any] = {"command": command}
        if sid:
            payload["session_id"] = sid
        try:
            r = requests.post(f"{self.base_url}/command", json=payload, timeout=10)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict):
                incoming = data.get("session_id") or data.get("replacement_session_id")
                if incoming:
                    self.session_id = incoming
                # Neue Session aus eingebetteter Session uebernehmen.
                session = data.get("session")
                if isinstance(session, dict) and session.get("id"):
                    self.session_id = session["id"]
                return data.get("output", "")
            return ""
        except Exception as e:
            return f"Error: {e}"

    def export_session(self, mode: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        sid = session_id if session_id is not None else self.session_id
        if not sid:
            return {"error": "Keine aktive Session vorhanden."}
        try:
            response = requests.get(
                f"{self.base_url}/sessions/{sid}/export",
                params={"mode": mode},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict):
                incoming = data.get("session_id")
                if incoming:
                    self.session_id = incoming
                return data
            return {"error": "Ungültige Export-Antwort vom Server."}
        except Exception as exc:
            return {"error": str(exc)}


# ═══════════════════════════════════════════════════════════════════
# CHAPPiEBrainCLI
# ═══════════════════════════════════════════════════════════════════

class CHAPPiEBrainCLI:
    CLI_VERSION = "17.2.0-dev.2"

    def __init__(self, remote_url: Optional[str] = None):
        self.remote_url = remote_url
        self.backend = None
        self.history: list = []
        self.last_result: Optional[Dict[str, Any]] = None
        self._use_remote = remote_url is not None
        self._show_full_report = _FULL_REPORT_DEFAULT
        self.session_id: Optional[str] = None

        _log("INIT", f"Initialisiere CHAPPiE Brain Interface v{self.CLI_VERSION}...", Colors.AI)

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
            # Aktive Session uebernehmen, falls der Server eine hat.
            try:
                active = requests.get(f"{self.remote.base_url}/sessions/active", timeout=5).json()
                if isinstance(active, dict) and active.get("id"):
                    self.session_id = active["id"]
                    self.remote.session_id = self.session_id
            except Exception:
                pass
        else:
            from web_infrastructure.backend_wrapper import create_chappie_backend
            self.backend = create_chappie_backend()
            self.emotions = self.backend.emotions
            self.memory = self.backend.memory
            self.steering = self.backend.steering_manager
            self.context = self.backend.context_files
            self.short_term = self.backend.short_term_memory
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
            thinking_status = "AN" if _s.chain_of_thought else "AUS"
            _log("INIT", f"Thinking/CoT: {thinking_status}", Colors.THOUGHT)
            # Lokale Session wie in der Web-UI sicherstellen.
            try:
                active = self.backend.chat_manager.load_active_session()
                self.session_id = active.get("id")
                self.history = list(active.get("messages", []))
            except Exception:
                pass

    def _ensure_local_session(self) -> tuple[str, list]:
        normalized = self.backend.chat_manager.ensure_session_id(self.session_id)
        session = self.backend.chat_manager.load_session(normalized)
        self.backend.chat_manager.set_active_session(normalized)
        self.session_id = normalized
        history = list(session.get("messages", []))
        self.history = history
        return normalized, history

    def _persist_local_turn(self, session_id: str, user_text: str, result: Dict[str, Any]) -> None:
        # Wie api/routers/chat.py: Assistant Message bauen, speichern, History syncen.
        try:
            user_message = {
                "id": self.backend.chat_manager.create_message_id(),
                "role": "user",
                "content": user_text,
                "created_at": datetime.now().astimezone().isoformat(),
            }
            message_id = self.backend.chat_manager.create_message_id()
            assistant_message = self.backend.build_assistant_message(user_text, result, message_id=message_id)
            session = self.backend.chat_manager.append_messages(session_id, [user_message, assistant_message])
            self.history = list(session.get("messages", []))
            # Neue Session nach /clear und /new uebernehmen.
            replacement = result.get("replacement_session_id")
            if replacement:
                self.session_id = replacement
                fresh = self.backend.chat_manager.load_session(replacement)
                self.history = list(fresh.get("messages", []))
            if result.get("clear_history"):
                self.history = list(self.backend.chat_manager.load_session(self.session_id).get("messages", []))
        except Exception:
            # Verlauf darf nie den Chat abbrechen.
            pass

    def _apply_remote_session(self, data: Dict[str, Any]) -> None:
        if not isinstance(data, dict):
            return
        incoming = data.get("session_id") or data.get("replacement_session_id")
        if incoming:
            self.session_id = incoming
            self.remote.session_id = incoming
        session = data.get("session")
        if isinstance(session, dict) and session.get("id"):
            self.session_id = session["id"]
            self.remote.session_id = session["id"]
        assistant = data.get("assistant_message")
        if isinstance(assistant, dict):
            metadata = assistant.get("metadata", {}) or {}
            replacement = metadata.get("replacement_session_id") or data.get("replacement_session_id")
            if replacement:
                self.session_id = replacement
                self.remote.session_id = replacement
            if metadata.get("clear_history"):
                self.history = []

    def _drain_background_output(self) -> None:
        """Gibt gepufferte Backend-Ausgaben (z.B. Schlafphase) als eigenen Infobereich aus."""
        cap = getattr(self, "_out_capture", None)
        if cap is None:
            return
        text = cap.drain().strip()
        if text:
            print(f"\n{Colors.DIM}─── Hintergrund ───{Colors.RESET}\n{text}\n")

    def _input_prompt(self) -> str:
        return f"\n{Colors.USER}{Colors.BOLD}{CLI_USER_LABEL} >{Colors.RESET} "

    @staticmethod
    def _settings():
        from config.config import settings
        return settings

    @staticmethod
    def _resolve_model_alias(value: str) -> str:
        raw = value.strip()
        return MODEL_ALIASES.get(raw.lower(), raw)

    @staticmethod
    def _steering_base_url() -> str:
        s = CHAPPiEBrainCLI._settings()
        return str(s.vllm_url or "http://localhost:8000/v1").rstrip("/").removesuffix("/v1")

    # ── streaming processing ──────────────────────────────────────

    def _process_local(self, user_text: str):
        # Slash-Commands laufen wie in der Web-UI ueber command_service.
        if user_text.strip().startswith("/"):
            if (user_text.strip().lower().split() or [""])[0] == "/copy":
                return self._handle_copy_command(user_text)
            from api.services.command_service import execute_slash_command
            try:
                session_id, _ = self._ensure_local_session()
                result = execute_slash_command(user_text.strip(), self.backend, session_id=session_id)
                replacement = result.get("replacement_session_id")
                if replacement:
                    session_id = replacement
                    self.backend.chat_manager.set_active_session(session_id)
                    self.session_id = session_id
                self.last_result = result
                output = result.get("response_text", "")
                if HAS_RICH:
                    console.print(_response_panel(output, "[bold magenta]Command[/]", "magenta"))
                else:
                    print(f"\n{Colors.MEMORY}{output}{Colors.RESET}\n")
                self._persist_local_turn(session_id, user_text, result)
                # Verlauf nach /clear und /new ist leer auf dem Server.
                if result.get("replacement_session_id") or result.get("clear_history"):
                    self.last_result = result
                return
            except Exception:
                # Fallback fuer unvollstaendige Backends (z.B. in Tests).
                fallback = self.backend.handle_command(user_text.strip())
                print(f"\n{Colors.MEMORY}{fallback}{Colors.RESET}\n")
                return
        session_id, history = self._ensure_local_session()
        if not HAS_RICH:
            _log("STEP1", "Intent-Analyse...", Colors.EMOTION)
            from datetime import datetime as _dt
            result = self.backend.process(
                user_text,
                history,
                debug_mode=True,
                temporal_context={"user_message_created_at": _dt.now().astimezone().isoformat()},
                session_id=session_id,
            )
            self.last_result = result
            self._persist_local_turn(session_id, user_text, result)
            self._display_raw_result(user_text, result)
            return

        eq: queue.Queue = queue.Queue()
        abort = threading.Event()

        def worker():
            try:
                from datetime import datetime as _dt2
                gen = self.backend.process_stream(
                    user_text,
                    history,
                    debug_mode=True,
                    temporal_context={"user_message_created_at": _dt2.now().astimezone().isoformat()},
                    session_id=session_id,
                )
                for event in gen:
                    if abort.is_set():
                        try:
                            gen.close()
                        except Exception:
                            pass
                        break
                    eq.put(event)
                eq.put(None)
            except Exception as exc:
                eq.put({"event": "error", "error": str(exc)})
                eq.put(None)

        t = threading.Thread(target=worker, daemon=True)
        t.start()

        collected = {"reasoning": "", "answer": ""}
        result = None
        error = None
        step1_done = False
        step1_start = time.time()
        streaming_start = 0.0
        word_count = 0
        tps = 0.0
        last_progress_print = 0.0
        last_progress_stage = ""
        self._print_progress_line("[STEP 1] Nachricht gesendet, Intent-Analyse startet...")

        cap = getattr(self, "_out_capture", None)
        if cap is not None:
            cap.main_capturing = True
        try:
            try:
                with Live(self._render_spinner(0), refresh_per_second=15, screen=False, console=console) as live:
                    while True:
                        try:
                            event = eq.get(timeout=0.06)
                        except queue.Empty:
                            if not step1_done:
                                live.update(self._render_spinner(time.time() - step1_start))
                            elif streaming_start > 0:
                                now = time.time()
                                elapsed = max(0.01, now - streaming_start)
                                tps = round(word_count / elapsed, 1)
                                live.update(self._render_streaming(collected, word_count, tps, now - streaming_start))
                            continue

                        if event is None:
                            break

                        ev = event.get("event", "")

                        if ev == "status":
                            now_ev = time.time()
                            stage_ev = str(event.get("stage", ""))
                            # Echte Zeilen drucken (immer sichtbar), Live nur als Bonus.
                            if stage_ev != last_progress_stage or (now_ev - last_progress_print) > 4.0:
                                self._print_progress_line(self._progress_line(event, now_ev - step1_start))
                                last_progress_stage = stage_ev
                                last_progress_print = now_ev
                            if self._step_of(event) >= 2:
                                # STEP-2-Fortschritt live zeigen (TTFT-Luecke etc.).
                                # Sobald Tokens fliessen, bleibt das Token-Panel.
                                if not collected.get("answer"):
                                    live.update(self._render_step2_progress(event, now_ev - step1_start))
                            else:
                                step1_done = True
                                live.update(self._render_step1_done(event.get("status_text", "")))

                        elif ev == "token":
                            if streaming_start == 0:
                                streaming_start = time.time()
                            collected[event.get("token_type", "answer")] += event.get("content", "")
                            word_count = _count_words(collected.get("answer", ""))
                            elapsed = max(0.01, time.time() - streaming_start)
                            tps = round(word_count / elapsed, 1)

                        elif ev == "error":
                            error = event.get("error", "Unbekannter Fehler")
                            break

                        elif ev == "finished":
                            result = event["result"]
                            break
            except KeyboardInterrupt:
                abort.set()
                _warn("Generierung abgebrochen")
        finally:
            if cap is not None:
                cap.main_capturing = False
        self._drain_background_output()

        abort.set()
        t.join(timeout=3)

        if error:
            _error(error)
            return

        if result:
            self.last_result = result
            self._display_compact_report(result)
            self._persist_local_turn(session_id, user_text, result)

    def _process_remote(self, user_text: str):
        if not HAS_RICH:
            collected = {"reasoning": "", "answer": ""}
            result = None
            for data in self.remote.stream_events(user_text, session_id=self.session_id):
                if isinstance(data, dict) and (data.get("session_id") or data.get("replacement_session_id")):
                    self._apply_remote_session(data)
                sse_ev = data.pop("_sse_event", None)
                if sse_ev == "token":
                    tt = data.get("token_type", "answer")
                    content = data.get("content", "")
                    collected[tt] += content
                    print(f"{Colors.THOUGHT if tt == 'reasoning' else Colors.AI}{content}{Colors.RESET}", end="", flush=True)
                elif sse_ev == "turn_finished":
                    self._apply_remote_session(data)
                    result = data
                    break
                elif sse_ev == "turn_error":
                    _error(data.get("error", ""))
                    break
                elif sse_ev == "status":
                    stage = data.get("stage", "")
                    text = data.get("status_text", "")
                    extra = ""
                    if data.get("answer_tokens"):
                        extra = f" ({data['answer_tokens']} Woerter)"
                    print(f"{Colors.DIM}[STEP {data.get('step', '?')}/{stage}] {text}{extra}{Colors.RESET}", flush=True)
            print()
            if result:
                msg = result.get("assistant_message", result)
                metadata = msg.get("metadata", {}) if isinstance(msg, dict) else {}
                metadata["emotions"] = result.get("emotion_snapshot", metadata.get("emotions", {}))
                metadata["life_snapshot"] = result.get("life_snapshot", metadata.get("life_snapshot", {}))
                metadata["debug_entries"] = result.get("debug_entries", metadata.get("debug_entries", []))
                self._display_remote_result(metadata, collected)
            return

        eq: queue.Queue = queue.Queue()
        abort = threading.Event()

        def worker():
            try:
                gen = self.remote.stream_events(user_text, session_id=self.session_id)
                for event in gen:
                    if abort.is_set():
                        break
                    sse_ev = event.pop("_sse_event", None)
                    if sse_ev == "turn_finished":
                        msg = event.get("assistant_message", {})
                        metadata = msg.get("metadata", {}) if isinstance(msg, dict) else {}
                        metadata["emotions"] = event.get("emotion_snapshot", metadata.get("emotions", {}))
                        metadata["life_snapshot"] = event.get("life_snapshot", metadata.get("life_snapshot", {}))
                        metadata["debug_entries"] = event.get("debug_entries", metadata.get("debug_entries", []))
                        eq.put({"event": "finished", "result": self._remote_meta_to_result(metadata), "_raw": event})
                        break
                    elif sse_ev == "turn_error":
                        eq.put({"event": "error", "error": event.get("error", "Fehler")})
                        break
                    elif sse_ev == "turn_started":
                        eq.put({"event": "session", "session_id": event.get("session_id"), "message_id": event.get("message_id")})
                        continue
                    elif sse_ev == "token":
                        eq.put({"event": "token", "content": event.get("content", ""), "token_type": event.get("token_type", "answer")})
                    elif sse_ev == "status":
                        eq.put({"event": "status", "step": event.get("step", 0), "status_text": event.get("status_text", ""),
                                "stage": event.get("stage", ""), "token_count": event.get("token_count", event.get("answer_tokens", 0)),
                                "tokens_per_second": event.get("tokens_per_second", 0), "ttft_ms": event.get("ttft_ms"),
                                "retry_attempt": event.get("retry_attempt"), "model": event.get("model", ""),
                                "provider": event.get("provider", ""), "elapsed_ms": event.get("elapsed_ms")})
                    else:
                        eq.put(event)
                eq.put(None)
            except Exception as exc:
                eq.put({"event": "error", "error": str(exc)})
                eq.put(None)

        t = threading.Thread(target=worker, daemon=True)
        t.start()

        collected = {"reasoning": "", "answer": ""}
        result = None
        error = None
        step1_done = False
        step1_start = time.time()
        streaming_start = 0.0
        word_count = 0
        tps = 0.0
        last_progress_print = 0.0
        last_progress_stage = ""
        self._print_progress_line("[STEP 1] Nachricht gesendet, Intent-Analyse startet...")

        cap = getattr(self, "_out_capture", None)
        if cap is not None:
            cap.main_capturing = True
        try:
            try:
                with Live(self._render_spinner(0), refresh_per_second=15, screen=False, console=console) as live:
                    while True:
                        try:
                            event = eq.get(timeout=0.06)
                        except queue.Empty:
                            if not step1_done:
                                live.update(self._render_spinner(time.time() - step1_start))
                            elif streaming_start > 0:
                                now = time.time()
                                elapsed = max(0.01, now - streaming_start)
                                tps = round(word_count / elapsed, 1)
                                live.update(self._render_streaming(collected, word_count, tps, now - streaming_start))
                            continue

                        if event is None:
                            break

                        ev = event.get("event", "")

                        if ev == "status":
                            now_ev = time.time()
                            stage_ev = str(event.get("stage", ""))
                            # Echte Zeilen drucken (immer sichtbar), Live nur als Bonus.
                            if stage_ev != last_progress_stage or (now_ev - last_progress_print) > 4.0:
                                self._print_progress_line(self._progress_line(event, now_ev - step1_start))
                                last_progress_stage = stage_ev
                                last_progress_print = now_ev
                            if self._step_of(event) >= 2:
                                # STEP-2-Fortschritt live zeigen (TTFT-Luecke etc.).
                                # Sobald Tokens fliessen, bleibt das Token-Panel.
                                if not collected.get("answer"):
                                    live.update(self._render_step2_progress(event, now_ev - step1_start))
                            else:
                                step1_done = True
                                live.update(self._render_step1_done(event.get("status_text", "")))

                        elif ev == "token":
                            if streaming_start == 0:
                                streaming_start = time.time()
                            collected[event.get("token_type", "answer")] += event.get("content", "")
                            word_count = _count_words(collected.get("answer", ""))
                            elapsed = max(0.01, time.time() - streaming_start)
                            tps = round(word_count / elapsed, 1)

                        elif ev == "error":
                            error = event.get("error", "Unbekannter Fehler")
                            break

                        elif ev == "finished":
                            result = event["result"]
                            self._apply_remote_session(event.get("_raw", {}))
                            break

                        elif ev == "session":
                            incoming = event.get("session_id")
                            if incoming:
                                self.session_id = incoming
                                self.remote.session_id = incoming
            except KeyboardInterrupt:
                abort.set()
                _warn("Generierung abgebrochen")
        finally:
            if cap is not None:
                cap.main_capturing = False
        self._drain_background_output()

        abort.set()
        t.join(timeout=3)

        if error:
            _error(error)
            return

        if result:
            self.last_result = result
            self._display_compact_report(result)
            # Verlauf liegt auf dem Server, lokal nur Anzeige-Cache.
            try:
                session_data = requests.get(f"{self.remote.base_url}/sessions/{self.session_id}", timeout=5).json()
                if isinstance(session_data, dict) and isinstance(session_data.get("messages"), list):
                    self.history = session_data["messages"]
            except Exception:
                pass

    @staticmethod
    def _remote_meta_to_result(metadata: dict) -> dict:
        content = metadata.get("content", "") or metadata.get("formatted_answer", "") or metadata.get("raw_response", "")
        return {
            "response_text": content,
            "formatted_cot": metadata.get("formatted_cot", ""),
            "formatted_answer": metadata.get("formatted_answer", ""),
            "emotions": metadata.get("emotions", {}),
            "emotions_before": metadata.get("emotions_before", {}),
            "emotions_delta": metadata.get("emotions_delta", {}),
            "intent_type": metadata.get("intent_type", "?"),
            "intent_confidence": metadata.get("intent_confidence", 0),
            "selected_tools": metadata.get("selected_tools", []),
            "tool_calls_executed": metadata.get("tool_calls_executed", 0),
            "available_tools": metadata.get("available_tools", []),
            "emotion_steering": metadata.get("emotion_steering", {}),
            "prompt_emotion_mode": metadata.get("prompt_emotion_mode", ""),
            "tone_decision": metadata.get("tone_decision", {}),
            "global_workspace": metadata.get("global_workspace", {}),
            "memory_trace": metadata.get("memory_trace", {}),
            "causal_trace": metadata.get("causal_trace", []),
            "context_budget": metadata.get("context_budget", {}),
            "rag_memories": metadata.get("rag_memories", []),
            "debug_entries": metadata.get("debug_entries", []),
            "debug_log": metadata.get("debug_log", ""),
            "intent_raw_json": metadata.get("intent_raw_json", {}),
            "action_plan": metadata.get("action_plan", {}),
            "life_snapshot": metadata.get("life_snapshot", {}),
            "memory_consolidation": metadata.get("memory_consolidation", {}),
            "processing_time_ms": metadata.get("processing_time_ms", 0),
            "timing": metadata.get("timing", {}),
            "provider": metadata.get("provider", ""),
            "model": metadata.get("model", ""),
            "sleep_status": metadata.get("sleep_status", {}),
            "auto_sleep_triggered": metadata.get("auto_sleep_triggered", False),
            "reasoning_only": metadata.get("reasoning_only", False),
            "formatting_failed": metadata.get("formatting_failed", False),
            "formatting_warning": metadata.get("formatting_warning", ""),
            "formatting_error": metadata.get("formatting_error", ""),
            "formatting_source": metadata.get("formatting_source", "local_fallback"),
            "formatting_model": metadata.get("formatting_model", "?"),
            "formatting_reason": metadata.get("formatting_reason", metadata.get("formatting_skip_reason", "")),
            "formatting_skip_reason": metadata.get("formatting_skip_reason", metadata.get("formatting_reason", "")),
            "finish_reason": metadata.get("finish_reason", (metadata.get("timing", {}) or {}).get("finish_reason", "unknown") if isinstance(metadata.get("timing"), dict) else "unknown"),
            "cot_leak": metadata.get("cot_leak", {"is_unexpected_cot": False, "score": 0.0, "reasons": []}),
            "command_trace": metadata.get("command_trace", {}),
            "replacement_session_id": metadata.get("replacement_session_id", ""),
            "clear_history": metadata.get("clear_history", False),
        }

    # ── live rendering ────────────────────────────────────────────

    @staticmethod
    def _render_spinner(elapsed: float):
        spinner = SPINNER_FRAMES[int(elapsed * 12) % len(SPINNER_FRAMES)]
        return Panel(
            f"{spinner}  Intent-Analyse laeuft... ({elapsed:.1f}s)",
            title="[bold cyan]STEP 1: Intent-Analyse[/]",
            border_style="cyan",
        )

    @staticmethod
    def _render_step1_done(status_text: str):
        return Panel(
            f"✓  {status_text}\n   Starte Antwortgenerierung...",
            title="[bold green]STEP 1: Abgeschlossen[/]",
            border_style="green",
        )

    @staticmethod
    def _step_of(event: dict) -> int:
        try:
            return int(event.get("step", 1) or 1)
        except (TypeError, ValueError):
            return 1

    @staticmethod
    def _progress_line(event: dict, total_elapsed: float) -> str:
        """Einzeilige Fortschrittsmeldung mit Zeilenumbruch (immer sichtbar)."""
        stage = str(event.get("stage", "") or "")
        text = str(event.get("status_text", "") or "arbeitet...")
        label = {
            "intent": "STEP 1", "memory": "STEP 1", "ttft": "STEP 2",
            "streaming": "STEP 2", "format": "STEP 2", "done": "STEP 2",
        }.get(stage, f"STEP {event.get('step', '?')}")
        details = []
        token_count = event.get("token_count", event.get("answer_tokens"))
        if isinstance(token_count, (int, float)) and token_count:
            details.append(f"{int(token_count)} Woerter")
        tps = event.get("tokens_per_second")
        if isinstance(tps, (int, float)) and tps:
            details.append(f"{tps:.1f} W/s")
        if details:
            text += f" ({', '.join(details)})"
        return f"[{label}] {text} · {total_elapsed:.0f}s"

    @staticmethod
    def _print_progress_line(line: str) -> None:
        if HAS_RICH:
            console.print(f"[dim]{line}[/]")
        else:
            print(f"{Colors.DIM}{line}{Colors.RESET}", flush=True)

    @staticmethod
    def _render_step2_progress(event: dict, total_elapsed: float):
        """Live-Fortschritt waehrend STEP 2 (TTFT-Luecke, Streaming, Format)."""
        stage = str(event.get("stage", "") or "")
        text = str(event.get("status_text", "") or "Antwortgenerierung laeuft...")
        stage_label = {
            "ttft": "Warte auf erstes Token",
            "streaming": "Streame Antwort",
            "format": "Formatiere Antwort",
            "done": "Abgeschlossen",
            "intent": "Intent-Analyse",
            "memory": "Memory-Aufbau",
        }.get(stage, stage or "Generierung")
        details = []
        token_count = event.get("token_count", event.get("answer_tokens"))
        if isinstance(token_count, (int, float)) and token_count:
            details.append(f"{int(token_count)} Woerter")
        tps = event.get("tokens_per_second")
        if isinstance(tps, (int, float)) and tps:
            details.append(f"{tps:.1f} W/s")
        if event.get("ttft_ms") is not None:
            try:
                details.append(f"TTFT {float(event['ttft_ms']) / 1000:.1f}s")
            except (TypeError, ValueError):
                pass
        if event.get("retry_attempt"):
            details.append(f"Versuch {event['retry_attempt']}")
        if event.get("model"):
            details.append(str(event["model"]))
        body = f"{stage_label}: {text}"
        if details:
            body += f"\n[dim]{'  ·  '.join(details)}  ·  gesamt {total_elapsed:.1f}s[/]"
        else:
            body += f"\n[dim]gesamt {total_elapsed:.1f}s[/]"
        return Panel(
            body,
            title="[bold yellow]STEP 2: Antwortgenerierung[/]",
            border_style="yellow",
        )

    @staticmethod
    def _render_streaming(collected: dict, word_count: int, tps: float, elapsed: float):
        parts = []
        if collected.get("reasoning"):
            cot = collected["reasoning"]
            if len(cot) > 10000:
                cot = cot[:9800] + "..."
            parts.append(Panel(
                Text(cot, style="dim"),
                title="[dim]Chain of Thought[/]",
                border_style="dim",
            ))
        answer = collected.get("answer", "")
        if len(answer) > 4000:
            answer = "..." + answer[-3900:]
        cursor = "█" if int(time.time() * 2) % 2 == 0 else " "
        parts.append(Panel(
            Text(answer + cursor, style="bold bright_cyan"),
            title=f"[bold bright_cyan]Live[/]  [dim]{word_count} Woerter  {tps:.1f} W/s  {elapsed:.1f}s[/]",
            border_style="bright_cyan",
        ))
        if not parts:
            return Panel("", title="Streaming...")
        if len(parts) > 1:
            if _RichGroup:
                return _RichGroup(*parts)
            return parts[0]
        return parts[0]

    # ── compact auto-report ──────────────────────────────────────

    def _display_compact_report(self, result: dict):
        if self._show_full_report:
            self._display_full_report(result)
            return

        proc_time = result.get("processing_time_ms", 0)
        provider = result.get("provider", "?")
        model = result.get("model", "?")

        cot = result.get("formatted_cot", "") or result.get("model_reasoning", "")
        raw_answer = result.get("response_text", "")
        formatted_answer = result.get("formatted_answer", "")
        show_both = raw_answer and formatted_answer and formatted_answer != raw_answer

        if cot and HAS_RICH:
            console.print(Panel(cot, title="[dim]Chain of Thought[/]", border_style="dim", padding=(0, 1)))
        elif cot:
            print(f"\n{Colors.THOUGHT}--- CHAPPiEs Gedanken ---\n{cot}\n---{Colors.RESET}\n")

        if show_both:
            if HAS_RICH:
                console.print(Panel(Text(raw_answer[:2000], style="dim"), title="[dim]Raw Output[/]", border_style="dim", padding=(0, 1)))
                console.print(_response_panel(formatted_answer, "[bold bright_cyan]CHAPPiE (formatted)[/]", "bright_cyan"))
            else:
                print(f"\n{Colors.DIM}--- Raw ---\n{raw_answer[:1000]}\n{Colors.RESET}")
                print(f"\n{Colors.AI}{Colors.BOLD}CHAPPiE (formatted) >{Colors.RESET} {formatted_answer}\n")
        elif formatted_answer:
            if HAS_RICH:
                console.print(_response_panel(formatted_answer, "[bold bright_cyan]CHAPPiE[/]", "bright_cyan"))
            else:
                print(f"\n{Colors.AI}{Colors.BOLD}CHAPPiE >{Colors.RESET} {formatted_answer}\n")
        elif raw_answer:
            if HAS_RICH:
                console.print(Panel(Text(raw_answer, style="bright_cyan"), title="[bold bright_cyan]CHAPPiE (raw)[/]", border_style="bright_cyan", padding=(0, 1)))
            else:
                print(f"\n{Colors.AI}{Colors.BOLD}CHAPPiE >{Colors.RESET} {raw_answer}\n")

        # Schlafphase-Hinweis als eigener Infobereich (Details folgen im Hintergrund-Block).
        if result.get("auto_sleep_triggered"):
            sleep_msg = "Automatische Schlafphase gestartet, laeuft im Hintergrund. Details folgen unten."
            if HAS_RICH:
                console.print(Panel(sleep_msg, title="[dim]Schlafphase[/]", border_style="dim", padding=(0, 1)))
            else:
                print(f"\n{Colors.DIM}--- Schlafphase ---\n{sleep_msg}\n{Colors.RESET}")

        # CoT Leakage Warning
        cot_leak = result.get("cot_leak", {})
        if cot_leak.get("is_unexpected_cot"):
            reasons = cot_leak.get("reasons", [])
            score = cot_leak.get("score", 0)
            leak_msg = f"Unerwartetes Reasoning in Antwort (Score: {score:.2f})"
            if reasons:
                leak_msg += f" — {', '.join(reasons)}"
            if HAS_RICH:
                console.print(Panel(leak_msg, title="[bold red]CoT Leakage[/]", border_style="red", padding=(0, 1)))
            else:
                print(f"{Colors.WARN}WARNUNG: CoT-Leakage in Antwort: {leak_msg}{Colors.RESET}")

        # Sanitization-Hinweis: Rohtext wird gezeigt, Filtergruende bleiben sichtbar.
        if result.get("sanitization_fallback"):
            reasons = ", ".join(result.get("sanitization_reasons", [])) or "Filter"
            fb_msg = f"Sichtbare Ausgabe bereinigt ({reasons}); Rohtext bleibt im Debug-Feld."
            if HAS_RICH:
                console.print(Panel(fb_msg, title="[bold yellow]Ausgabe-Hinweis[/]", border_style="yellow", padding=(0, 1)))
            else:
                print(f"{Colors.WARN}HINWEIS: {fb_msg}{Colors.RESET}")

        intent = result.get("intent_type", "?")
        confidence = result.get("intent_confidence", 0)
        tools = result.get("selected_tools", [])
        emotion_before = result.get("emotions_before", {})
        emotion_after = result.get("emotions", {})
        steering = result.get("emotion_steering", {})
        prompt_mode = result.get("prompt_emotion_mode", "?")
        tone = result.get("tone_decision", {})
        workspace = result.get("global_workspace", {})
        memory_trace_raw = result.get("memory_trace", {})
        mem_trace = memory_trace_raw.get("merged", memory_trace_raw.get("seed", memory_trace_raw)) if isinstance(memory_trace_raw, dict) else {}
        budget = result.get("context_budget", {})
        timing = result.get("timing", {})
        causal = result.get("causal_trace", [])
        rep_events = result.get("repetition_events", {})

        if HAS_RICH:
            left = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
            left.add_column("k", style="dim")
            left.add_column("v")

            right = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
            right.add_column("k", style="dim")
            right.add_column("v")

            intent_str = f"{intent} ({confidence:.2f})" if confidence else str(intent)
            tools_str = ", ".join(tools) if tools else "none"
            left.add_row("Intent:", f"{intent_str}    Tools: {tools_str}")

            left.add_row("Tone:", f"{tone.get('tone', '?')}  ({tone.get('tone_reason', '')[:80]})")

            fmt_source = result.get("formatting_source", "local_fallback")
            fmt_model = result.get("formatting_model", "?")
            fmt_reason = result.get("formatting_reason", result.get("formatting_skip_reason", ""))
            fmt_failed = result.get("formatting_failed", False)
            if fmt_failed:
                fmt_color = "red"
                fmt_label = "LOCAL (Groq-API fehlgeschlagen)"
            elif fmt_source == "groq":
                fmt_color = "green"
                fmt_label = "GROQ"
            else:
                fmt_color = "yellow"
                fmt_label = "LOCAL"
            fmt_detail = f"[{fmt_color}]{fmt_label}[/] ({fmt_model})"
            if fmt_reason:
                fmt_detail += f" Grund: {fmt_reason}"
            left.add_row("Format:", fmt_detail)

            focus = (workspace.get("dominant_focus") or {})
            focus_label = focus.get("label", "?")
            focus_sal = focus.get("salience", 0)
            mem_count = mem_trace.get("memories_found", 0) if isinstance(mem_trace, dict) else 0
            mem_rel = mem_trace.get("top_relevance", 0) if isinstance(mem_trace, dict) else 0
            left.add_row("Focus:", f"{focus_label} ({focus_sal:.2f})    Memory: {mem_count} matches @{mem_rel:.2f}")

            est = budget.get("estimated_tokens", 0)
            lim = budget.get("token_limit", 4096)
            trimmed = "TRIMMED" if budget.get("was_trimmed") else "ok"
            left.add_row("Budget:", f"{est}/{lim} tokens ({trimmed})")

            if timing:
                ttft = timing.get("ttft_ms", 0)
                rtk = timing.get("reasoning_tokens", 0)
                atk = timing.get("answer_tokens", 0)
                gen = timing.get("total_gen_ms", 0)
                finish = timing.get("finish_reason", result.get("finish_reason", "unknown"))
                has_cot = bool(result.get("formatted_cot", "")) and result.get("formatted_cot", "") != "CHAPPiE hat nicht darueber nachgedacht und sofort geantwortet."
                if rtk > 0:
                    r_label = f"r:{rtk}tk"
                elif has_cot:
                    r_label = "r:~tk"
                else:
                    r_label = "r:0tk (kein CoT)"
                timing_str = f"TTFT:{ttft}ms  {r_label}  a:{atk}tk  gen:{gen}ms  total:{proc_time:.0f}ms"
                if finish and finish != "unknown":
                    timing_str += f"  finish:{finish}"
                left.add_row("Timing:", timing_str)

            if rep_events:
                parts = []
                for key, val in sorted(rep_events.items()):
                    parts.append(f"[bold red]{key}[/]")
                left.add_row("Repetition:", ", ".join(parts))

            causal_chain = " → ".join(c.get("phase", "?") for c in (causal or [])[:5])
            if causal_chain:
                left.add_row("Trace:", causal_chain)

            debug_entries = result.get("debug_entries", [])
            if debug_entries:
                left.add_row("Debug:", f"[dim]{len(debug_entries)} entries[/]")

            mood, mood_color = self._status_mood(emotion_after if isinstance(emotion_after, dict) else {})
            right.add_row("[bold]Stimmung:[/]", f"[bold {mood_color}]{mood.upper()}[/]")
            for name in EMOTION_NAMES:
                b = emotion_before.get(name, 0)
                a = emotion_after.get(name, 0)
                d = a - b
                if d == 0:
                    right.add_row(name, f"[dim]{b} → {a} (+0)[/]")
                    continue
                sign = f"[green]↑+{d}[/]" if d > 0 else f"[red]↓{d}[/]"
                right.add_row(name, f"{b} → [bold]{a}[/] {sign}")

            steer_str = "VECTOR" if ("vector" in prompt_mode or "layer" in prompt_mode) else "PROMPT"
            dom = steering.get("dominant_vector", "neutral")
            dom_s = steering.get("dominant_strength", 0)
            right.add_row("Steering:", f"[{_emo_color(int(dom_s * 100))}]{steer_str} | {dom} ({dom_s:.2f})[/]")

            try:
                width = console.width or shutil.get_terminal_size(fallback=(100, 24)).columns  # type: ignore[union-attr]
            except Exception:
                width = shutil.get_terminal_size(fallback=(100, 24)).columns
            if width >= self.STATUS_TWO_COLUMN_MIN_WIDTH:
                grid = Table.grid(expand=True, padding=(0, 1))
                grid.add_column(ratio=1)
                grid.add_column(width=1)
                grid.add_column(ratio=1)
                sep_height = max(left.row_count, right.row_count)
                grid.add_row(
                    left,
                    Text("\n".join([self.STATUS_SEP] * max(1, sep_height)), style="dim", justify="center"),
                    right,
                )
                content = grid
            else:
                content = _RichGroup(left, Text(""), right) if _RichGroup else left
            console.print(Panel(content, title=f"[bold]CHAPPiE Final Report[/]  [dim]{proc_time:.0f}ms · {provider}/{model}[/]", border_style="blue"))
        else:
            left_lines = [f"  [INTENT]  {intent} ({confidence:.2f}) | Tools: {', '.join(tools) or 'none'}"]
            left_lines.append(f"  [TONE]    {tone.get('tone', '?')}")
            fmt_source = result.get("formatting_source", "local_fallback")
            fmt_failed = result.get("formatting_failed", False)
            fmt_reason = result.get("formatting_reason", result.get("formatting_skip_reason", ""))
            if fmt_failed:
                fmt_label = "LOCAL (Groq-API fehlgeschlagen)"
                left_lines.append(f"  {Colors.ERROR}[FORMAT]  {fmt_label} ({result.get('formatting_model', '?')}){Colors.RESET}")
            else:
                fmt_label = "GROQ" if fmt_source == "groq" else "LOCAL"
                reason_txt = f" Grund: {fmt_reason}" if fmt_reason else ""
                left_lines.append(f"  [FORMAT]  {fmt_label} ({result.get('formatting_model', '?')}){reason_txt}")
            if rep_events:
                left_lines.append(f"  [REP]     {', '.join(rep_events.keys())}")
            left_lines.append(f"  [TIME]    {proc_time:.0f} ms | {provider}/{model}")
            right_lines = []
            try:
                mood, _ = self._status_mood(emotion_after if isinstance(emotion_after, dict) else {})
            except Exception:
                mood = "neutral"
            right_lines.append(f"  Stimmung: {mood.upper()}")
            for name in EMOTION_NAMES:
                b = emotion_before.get(name, 0)
                a = emotion_after.get(name, 0)
                d = a - b
                right_lines.append(f"  [EMO]     {name}: {b} → {a} ({'+' if d > 0 else ''}{d})")
            dom = steering.get("dominant_vector", "neutral")
            right_lines.append(f"  [STEER]   {prompt_mode} | {dom} ({steering.get('dominant_strength', 0):.2f})")
            try:
                width = shutil.get_terminal_size(fallback=(100, 24)).columns
            except Exception:
                width = 100
            print(f"{Colors.DEBUG}{'─' * 60}")
            if width >= self.STATUS_TWO_COLUMN_MIN_WIDTH:
                left_w = max((len(line) for line in left_lines), default=0)
                sep = f" {self.STATUS_SEP} "
                for i in range(max(len(left_lines), len(right_lines))):
                    left_part = left_lines[i] if i < len(left_lines) else " " * left_w
                    right_part = right_lines[i] if i < len(right_lines) else ""
                    print(f"{left_part:<{left_w}}{sep}{right_part}")
            else:
                for line in left_lines:
                    print(line)
                print(f"  {self.STATUS_SEP * 2} Gefuehle {self.STATUS_SEP * 2}")
                for line in right_lines:
                    print(line)
            print(f"{'─' * 60}{Colors.RESET}")

    # ── full report (/last) ───────────────────────────────────────

    def _display_full_report(self, result: dict):
        if not HAS_RICH:
            self._display_raw_result("(last)", result)
            return

        cot = result.get("formatted_cot", "") or result.get("model_reasoning", "")
        raw_answer = result.get("response_text", "")
        formatted_answer = result.get("formatted_answer", "")
        show_both = raw_answer and formatted_answer and formatted_answer != raw_answer

        if cot:
            console.print(Panel(cot, title="[dim]Chain of Thought[/]", border_style="dim", padding=(0, 1)))
        if show_both:
            console.print(Panel(Text(raw_answer[:2000], style="dim"), title="[dim]Raw Output[/]", border_style="dim", padding=(0, 1)))
            console.print(_response_panel(formatted_answer, "[bold bright_cyan]CHAPPiE (formatted)[/]", "bright_cyan"))
        elif formatted_answer:
            console.print(_response_panel(formatted_answer, "[bold bright_cyan]CHAPPiE[/]", "bright_cyan"))
        elif raw_answer:
            console.print(Panel(Text(raw_answer, style="bright_cyan"), title="[bold bright_cyan]CHAPPiE (raw)[/]", border_style="bright_cyan", padding=(0, 1)))

        from cli.report import responsive_report, runtime_panel
        left = [runtime_panel(result), self._panel_intent_json(result), self._panel_tools(result),
                self._panel_memory(result), self._panel_workspace(result), self._panel_budget(result),
                self._panel_timing(result), self._panel_causal(result), self._panel_consolidation(result)]
        right = [self._panel_steering(result), self._panel_emotions(result), self._panel_tone(result),
                 self._panel_repetition(result)]
        console.print(responsive_report(left, right, console.width))
        debug_panel = self._panel_debug(result)
        if debug_panel:
            console.print(debug_panel)
        proc_time = result.get("processing_time_ms", 0)
        provider = result.get("provider", "?")
        model = result.get("model", "?")

        console.print(f"[dim]━━━ CHAPPiE Full Report · {proc_time:.0f}ms · {provider}/{model} ━━━[/]")

    def _display_raw_result(self, user_text: str, result: dict):
        cot = result.get("formatted_cot", "") or result.get("model_reasoning", "")
        raw_answer = result.get("response_text", "")
        formatted_answer = result.get("formatted_answer", "")
        show_both = raw_answer and formatted_answer and formatted_answer != raw_answer
        if cot:
            print(f"\n{Colors.THOUGHT}--- CHAPPiEs Gedanken ---\n{cot}\n---{Colors.RESET}\n")
        if show_both:
            print(f"\n{Colors.DIM}--- Raw ---\n{raw_answer[:1000]}\n{Colors.RESET}")
            print(f"{Colors.AI}{Colors.BOLD}CHAPPiE (formatted) >{Colors.RESET} {formatted_answer}\n")
        elif formatted_answer:
            print(f"{Colors.AI}{Colors.BOLD}CHAPPiE >{Colors.RESET} {formatted_answer}\n")
        elif raw_answer:
            print(f"{Colors.AI}{Colors.BOLD}CHAPPiE (raw) >{Colors.RESET} {raw_answer}\n")

    def _display_remote_result(self, metadata: dict, collected: dict):
        cot_leak = metadata.get("cot_leak", {})
        if metadata.get("sanitization_fallback"):
            reasons = ", ".join(metadata.get("sanitization_reasons", [])) or "Filter"
            fb_msg = f"Sichtbare Ausgabe bereinigt ({reasons}); Rohtext bleibt im Debug-Feld."
            if HAS_RICH:
                console.print(Panel(fb_msg, title="[bold yellow]Ausgabe-Hinweis[/]", border_style="yellow", padding=(0, 1)))
            else:
                print(f"{Colors.WARN}HINWEIS: {fb_msg}{Colors.RESET}")
        if HAS_RICH:
            cot = metadata.get("formatted_cot", "")
            answer = metadata.get("formatted_answer", "") or collected.get("answer", "")
            if cot_leak.get("is_unexpected_cot"):
                reasons = cot_leak.get("reasons", [])
                score = cot_leak.get("score", 0)
                leak_msg = f"Unerwartetes Reasoning in Antwort (Score: {score:.2f})"
                if reasons:
                    leak_msg += f" — {', '.join(reasons)}"
                console.print(Panel(leak_msg, title="[bold red]CoT Leakage[/]", border_style="red", padding=(0, 1)))
            if cot:
                console.print(Panel(cot, title="[dim]Chain of Thought[/]", border_style="dim", padding=(0, 1)))
            if answer:
                console.print(_response_panel(answer, "[bold bright_cyan]CHAPPiE[/]", "bright_cyan"))
            proc_time = metadata.get("processing_time_ms", 0)
            intent = metadata.get("intent_type", "?")
            conf = metadata.get("intent_confidence", 0)
            fmt_source = metadata.get("formatting_source", "local_fallback")
            fmt_failed = metadata.get("formatting_failed", False)
            fmt_model = metadata.get("formatting_model", "?")
            fmt_reason = metadata.get("formatting_reason", metadata.get("formatting_skip_reason", ""))
            if fmt_failed:
                console.print(f"[red]Format: LOCAL (Groq-API fehlgeschlagen) ({fmt_model})[/]")
            else:
                fmt_color = "green" if fmt_source == "groq" else "yellow"
                fmt_label = "GROQ" if fmt_source == "groq" else "LOCAL"
                reason_txt = f" Grund: {fmt_reason}" if fmt_reason else ""
                console.print(f"[{fmt_color}]Format: {fmt_label} ({fmt_model}){reason_txt}[/]")
            console.print(f"[dim]Intent: {intent} ({conf:.2f}) | Time: {proc_time:.0f}ms[/]")
        else:
            cot = metadata.get("formatted_cot", "")
            answer = metadata.get("formatted_answer", "")
            if cot_leak.get("is_unexpected_cot"):
                score = cot_leak.get("score", 0)
                print(f"{Colors.WARN}WARNUNG: CoT-Leakage in Antwort (Score: {score:.2f}){Colors.RESET}")
            if cot:
                print(f"\n{Colors.THOUGHT}--- CHAPPiEs Gedanken ---\n{cot}\n---{Colors.RESET}\n")
            if answer:
                print(f"{Colors.AI}{Colors.BOLD}CHAPPiE >{Colors.RESET} {answer}\n")
            fmt_source = metadata.get("formatting_source", "local_fallback")
            fmt_failed = metadata.get("formatting_failed", False)
            fmt_reason = metadata.get("formatting_reason", metadata.get("formatting_skip_reason", ""))
            if fmt_failed:
                print(f"{Colors.ERROR}  [FORMAT] LOCAL (Groq-API fehlgeschlagen) ({metadata.get('formatting_model', '?')}){Colors.RESET}")
            else:
                fmt_label = "GROQ" if fmt_source == "groq" else "LOCAL"
                reason_txt = f" Grund: {fmt_reason}" if fmt_reason else ""
                print(f"  [FORMAT]  {fmt_label} ({metadata.get('formatting_model', '?')}){reason_txt}")

    # ── full report panels ────────────────────────────────────────

    @staticmethod
    def _panel_emotions(result: dict) -> Optional[Panel]:
        from cli.report import emotion_panel
        return emotion_panel(result)

    @staticmethod
    def _panel_intent_json(result: dict) -> Optional[Panel]:
        raw = result.get("intent_raw_json", {})
        if not raw:
            return None
        text = json.dumps(raw, indent=2, ensure_ascii=False)
        if len(text) > 2000:
            text = text[:1997] + "..."
        from rich.syntax import Syntax
        return Panel(Syntax(text, "json", theme="monokai"), title="[bold magenta]Step 1: Intent Raw JSON[/]", border_style="magenta")

    @staticmethod
    def _panel_tools(result: dict) -> Optional[Panel]:
        available = result.get("available_tools", [])
        selected = result.get("selected_tools", [])
        unused = result.get("unused_tools", [])
        executed = result.get("tool_calls_executed", 0)
        if not available:
            return None
        lines = [f"  Ausgefuehrt: {executed}"]
        lines.append(f"  Selected:    {', '.join(selected) if selected else 'none'}")
        lines.append(f"  Unused:      {', '.join(unused) if unused else 'none'}")
        lines.append(f"  Available:   {', '.join(available)}")
        return Panel("\n".join(lines), title="[bold magenta]Tool Calls[/]", border_style="magenta")

    @staticmethod
    def _panel_memory(result: dict) -> Optional[Panel]:
        mt = result.get("memory_trace", {})
        if not mt or not isinstance(mt, dict):
            return None
        lines = []
        for stage in ("seed", "generation", "merged"):
            s = mt.get(stage)
            if not isinstance(s, dict):
                continue
            q = s.get("query", "")[:80]
            found = s.get("memories_found", 0)
            rel = s.get("top_relevance", 0)
            lines.append(f"  [{stage}] query={q}  found={found}  top_rel={rel:.2f}")
            for pv in s.get("preview", [])[:3]:
                if isinstance(pv, dict):
                    lines.append(f"    [{pv.get('role', '?')}|{pv.get('label', '?')}] rel={pv.get('relevance', 0):.2f}  {pv.get('content_preview', '')[:80]}")
        if not lines:
            return None
        return Panel("\n".join(lines), title="[bold magenta]Memory Trace[/]", border_style="magenta")

    @staticmethod
    def _panel_workspace(result: dict) -> Optional[Panel]:
        ws = result.get("global_workspace", {})
        if not ws:
            return None
        lines = []
        df = ws.get("dominant_focus") or {}
        lines.append(f"  Dominant: {df.get('label', '?')} (source={df.get('source', '?')}, salience={df.get('salience', 0):.2f})")
        lines.append(f"  Mode: {ws.get('attention_mode', '?')}")
        lines.append(f"  Broadcast: {ws.get('broadcast', '')[:120]}")
        items = ws.get("workspace_items", [])[:5]
        if items:
            lines.append("  Top Items:")
            for it in items:
                if isinstance(it, dict):
                    lines.append(f"    [{it.get('source', '?')}] {it.get('label', '?')} sal={it.get('salience', 0):.2f}")
        mtr = ws.get("math_trace", [])
        if mtr:
            lines.append(f"  Math Steps: {len(mtr)}")
        return Panel("\n".join(lines), title="[bold magenta]Global Workspace[/]", border_style="magenta")

    @staticmethod
    def _panel_steering(result: dict) -> Optional[Panel]:
        from cli.report import steering_panel
        return steering_panel(result)

    @staticmethod
    def _panel_tone(result: dict) -> Optional[Panel]:
        t = result.get("tone_decision", {})
        if not t:
            return None
        lines = [
            f"  Tone:       {t.get('tone', '?')}",
            f"  Reason:     {t.get('tone_reason', '')[:120]}",
        ]
        for d in t.get("tone_drivers", [])[:7]:
            if isinstance(d, dict):
                lines.append(f"  Driver:     {d.get('signal', '?')}={d.get('value', '?')}")
        return Panel("\n".join(lines), title="[bold yellow]Tone Decision[/]", border_style="yellow")

    @staticmethod
    def _panel_budget(result: dict) -> Optional[Panel]:
        b = result.get("context_budget", {})
        if not b:
            return None
        lines = [
            f"  Estimated:    {b.get('estimated_tokens', '?')}",
            f"  Near limit:   {b.get('near_limit', False)}",
            f"  Was trimmed:  {b.get('was_trimmed', False)}",
        ]
        if b.get("was_trimmed"):
            lines.append(f"  Original:     {b.get('original_tokens', '?')}")
            lines.append(f"  Trimmed to:   {b.get('trimmed_tokens', '?')}")
            lines.append(f"  Removed msgs: {b.get('removed_messages', 0)}")
        return Panel("\n".join(lines), title="[bold magenta]Context Budget[/]", border_style="magenta")

    @staticmethod
    def _panel_timing(result: dict) -> Optional[Panel]:
        from cli.report import timing_panel
        return timing_panel(result)

    @staticmethod
    def _panel_causal(result: dict) -> Optional[Panel]:
        causal = result.get("causal_trace", [])
        if not causal:
            return None
        lines = []
        for c in causal:
            if isinstance(c, dict):
                lines.append(f"  [{c.get('phase', '?')}] driver={c.get('driver', '')[:60]}")
        return Panel("\n".join(lines), title="[bold magenta]Causal Trace[/]", border_style="magenta")

    @staticmethod
    def _panel_consolidation(result: dict) -> Optional[Panel]:
        mc = result.get("memory_consolidation", {})
        if not mc:
            return None
        lines = [
            f"  LTM loaded:      {mc.get('ltm_loaded', 0)}",
            f"  STM loaded:      {mc.get('stm_loaded', 0)}",
            f"  LTM consolidated:{mc.get('ltm_consolidated', 0)}",
            f"  STM consolidated:{mc.get('stm_consolidated', 0)}",
            f"  Duplicates:      {mc.get('duplicates_merged', 0)}",
            f"  Critical events: {mc.get('critical_events', 0)}",
        ]
        return Panel("\n".join(lines), title="[bold magenta]Memory Consolidation[/]", border_style="magenta")

    @staticmethod
    def _panel_repetition(result: dict) -> Optional[Panel]:
        events = result.get("repetition_events", {})
        if not events:
            return None
        lines = []
        for key, val in sorted(events.items()):
            if isinstance(val, dict):
                detail = ", ".join(f"{k}={v}" for k, v in val.items())
                lines.append(f"  [bold red]{key}[/]: {detail}")
            else:
                lines.append(f"  [bold red]{key}[/]")
        return Panel("\n".join(lines), title="[bold red]Repetition Events[/]", border_style="red")

    @staticmethod
    def _panel_debug(result: dict) -> Optional[Panel]:
        entries = result.get("debug_entries", [])
        if not entries:
            return None
        lines = []
        for entry in entries[:30]:
            if isinstance(entry, dict):
                cat = entry.get("category", "?")
                msg = entry.get("message", entry.get("detail", ""))[:100]
                lines.append(f"  [{cat}] {msg}")
        return Panel("\n".join(lines), title="[dim]Debug Log[/]", border_style="dim")

    # ── status display ────────────────────────────────────────────

    STATUS_TWO_COLUMN_MIN_WIDTH = 100
    STATUS_THREE_COLUMN_MIN_WIDTH = 150
    STATUS_SEP = "│"

    @staticmethod
    def _status_mood(emotions: Dict[str, Any]) -> tuple[str, str]:
        """Stimmungslabel plus Rich-Farbe, robust gegen leere Dicts."""
        try:
            h = int(emotions.get("happiness", 50) or 0)
            s = int(emotions.get("sadness", 0) or 0)
            f = int(emotions.get("frustration", 0) or 0)
        except (TypeError, ValueError):
            return "neutral", "dim"
        if h > 60:
            return "positiv", "green"
        if s > 40 or f > 50:
            return "angespannt", "red"
        return "neutral", "dim"

    @staticmethod
    def _short_session_id(session_id: Any) -> str:
        if not session_id:
            return "?"
        text = str(session_id)
        return text[:8] if len(text) > 8 else text

    @staticmethod
    def _format_goal(goal: Any) -> str:
        if not isinstance(goal, dict) or not goal:
            return "?"
        title = str(goal.get("title", "?") or "?")
        try:
            progress = float(goal.get("progress", 0) or 0)
        except (TypeError, ValueError):
            return title
        if progress > 1:
            progress = progress / 100.0
        return f"{title} ({progress:.0%})"

    def _status_remote_settings(self) -> Dict[str, Any]:
        """Best-effort /settings fuer Remote, nie blockierend."""
        if not self._use_remote or not HAS_REQUESTS:
            return {}
        try:
            base = getattr(getattr(self, "remote", None), "base_url", self.remote_url or "")
            if not base:
                return {}
            data = requests.get(f"{base}/settings", timeout=3).json()
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _remote_session_flag(self, name: str) -> Any:
        """Best-effort Session Flag aus der Remote Session, sonst '?'."""
        if not self._use_remote or not HAS_REQUESTS:
            return "?"
        try:
            base = getattr(getattr(self, "remote", None), "base_url", self.remote_url or "")
            sid = getattr(self, "session_id", None)
            if not base or not sid:
                return "?"
            data = requests.get(f"{base}/sessions/{sid}/settings", timeout=3).json()
            if isinstance(data, dict):
                value = data.get(name, "?")
                return value if isinstance(value, bool) else "?"
            return "?"
        except Exception:
            return "?"

    def _status_right_rows(self, status: Dict[str, Any], life: Dict[str, Any], remote_settings: Optional[Dict[str, Any]] = None) -> list:
        """Zehn kompakte (key, rich_value, plain_value) fuer die mittlere Tabelle."""
        status = status if isinstance(status, dict) else {}
        life = life if isinstance(life, dict) else {}
        if remote_settings is None:
            remote_settings = self._status_remote_settings()
        remote_settings = remote_settings if isinstance(remote_settings, dict) else {}

        model = str(status.get("model", "?") or "?")
        provider = str(status.get("provider", "?") or "?")
        mode = "REMOTE" if self._use_remote else "LOKAL"

        if self._use_remote:
            steering_on = remote_settings.get("enable_steering", status.get("emotion_steering_active"))
            two_step = status.get("two_step_enabled", remote_settings.get("enable_two_step_processing", "?"))
            thinking = remote_settings.get("chain_of_thought", "?")
            if steering_on is True:
                steering = "AN"
            elif steering_on is False:
                steering = "AUS"
            else:
                steering = "?"
        else:
            try:
                s = self._settings()
            except Exception:
                s = None
            if model == "?":
                model = str(getattr(s, "vllm_model", "?") or "?")
            if provider == "?":
                try:
                    provider = str(s.llm_provider.value)  # type: ignore[union-attr]
                except Exception:
                    pass
            try:
                local_steering = bool(getattr(s, "enable_steering", True))
                is_local = bool(self.steering.is_local_provider())  # type: ignore[attr-defined]
                steering = f"AN ({'VEKTOR' if is_local else 'PROMPT'})" if local_steering else "AUS"
            except Exception:
                steering = "AN" if status.get("emotion_steering_active") else "?"
            two_step = status.get("two_step_enabled", getattr(s, "enable_two_step_processing", "?") if s else "?")
            thinking = getattr(s, "chain_of_thought", "?") if s else "?"

        def on_off(value: Any) -> tuple[str, str]:
            if value is True:
                return "[green]AN[/]", "AN"
            if value is False:
                return "[red]AUS[/]", "AUS"
            if isinstance(value, str) and value.startswith("AN ("):
                return f"[green]{value}[/]", value
            text = str(value) if value not in (None, "") else "?"
            return text, text

        two_rich, two_plain = on_off(two_step)
        think_rich, think_plain = on_off(thinking)
        if isinstance(steering, str) and steering.startswith("AN"):
            steer_rich = f"[green]{steering}[/]"
        elif steering == "AUS":
            steer_rich = "[red]AUS[/]"
        else:
            steer_rich = str(steering)

        try:
            history_len = len(self.history) if isinstance(getattr(self, "history", None), list) else 0
        except Exception:
            history_len = 0
        session_plain = f"{self._short_session_id(getattr(self, 'session_id', None))} ({history_len} Nachrichten)"
        session_rich = session_plain

        daily = status.get("daily_info_count")
        if daily is None and not self._use_remote:
            try:
                daily = self.short_term.get_count()  # type: ignore[attr-defined]
            except Exception:
                daily = None
        short_txt = str(daily) if isinstance(daily, int) else "?"
        if self._use_remote:
            long_count: Any = "?"
            memory_on: Any = self._remote_session_flag("memory_enabled")
        else:
            try:
                raw_long = self.backend.memory.get_memory_count()  # type: ignore[attr-defined]
                long_count = raw_long if isinstance(raw_long, int) else "?"
            except Exception:
                long_count = "?"
            try:
                runtime_settings = self.backend.chat_manager.get_runtime_settings(self.session_id)  # type: ignore[attr-defined]
                memory_on = bool(runtime_settings.memory_enabled)
            except Exception:
                memory_on = "?"
        long_txt = str(long_count) if isinstance(long_count, int) else "?"
        if memory_on is True:
            mem_state_rich, mem_state_plain = "[green]AN[/]", "AN"
        elif memory_on is False:
            mem_state_rich, mem_state_plain = "[red]AUS[/]", "AUS"
        else:
            mem_state_rich, mem_state_plain = "?", "?"
        memory_plain = f"{mem_state_plain} ({long_txt} Langzeit / {short_txt} Kurzzeit)"
        memory_rich = f"{mem_state_rich} ({long_txt} Langzeit / {short_txt} Kurzzeit)"

        clock = life.get("clock", {}) if isinstance(life.get("clock"), dict) else {}
        phase_plain = str(clock.get("phase_label", "?") or "?")
        goal_plain = self._format_goal(life.get("active_goal"))
        activity = str(life.get("current_activity", "?") or "?")
        current_mode = str(life.get("current_mode", "?") or "?")
        activity_plain = f"{activity} / {current_mode}" if "?" not in (activity, current_mode) else (activity if current_mode == "?" else current_mode)

        return [
            ("Modell:", model, model),
            ("Provider:", f"{provider} [{mode}]", f"{provider} [{mode}]"),
            ("Steering:", steer_rich, steering),
            ("Two-Step:", two_rich, two_plain),
            ("Thinking:", think_rich, think_plain),
            ("Session:", session_rich, session_plain),
            ("Memory:", memory_rich, memory_plain),
            ("Phase:", phase_plain, phase_plain),
            ("Ziel:", goal_plain, goal_plain),
            ("Aktivitaet:", activity_plain, activity_plain),
        ]

    def _status_links(self) -> tuple[str, str]:
        """(Web-UI URL, API URL) fuer klickbare Links, lokal Defaults, remote vom Backend Host."""
        if self._use_remote:
            base = getattr(getattr(self, "remote", None), "base_url", self.remote_url or "") or ""
            api_url = base.rstrip("/") or "?"
            try:
                parts = urlsplit(base)
                host = parts.hostname or ""
                web_url = f"{parts.scheme or 'http'}://{host}:4173" if host else "?"
            except Exception:
                web_url = "?"
            return web_url, api_url
        return "http://localhost:4173", "http://localhost:8010"

    def _status_model_details(self, remote_settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Modelldetailwerte fuer die dritte Spalte, lokal aus Settings, remote aus /settings."""
        if self._use_remote:
            if remote_settings is None:
                remote_settings = self._status_remote_settings()
            remote = remote_settings if isinstance(remote_settings, dict) else {}
            provider = str(remote.get("intent_provider", "") or "").lower()
            if provider == "groq":
                intent_model = remote.get("intent_processor_model_groq", "?")
            elif provider == "ollama":
                intent_model = remote.get("intent_processor_model_ollama", "?")
            else:
                intent_model = remote.get("intent_processor_model_vllm", remote.get("vllm_model", "?"))
            return {
                "embedding_model": remote.get("embedding_model", "?"),
                "context_token_limit": remote.get("context_token_limit", "?"),
                "max_tokens": remote.get("max_tokens", "?"),
                "thinking_limit": remote.get("chappie_thinking_token_limit", "?"),
                "temperature": remote.get("temperature", "?"),
                "top_p": remote.get("top_p", "?"),
                "top_k": remote.get("top_k", "?"),
            "steering_model": remote.get("steering_model", "?"),
            "intent_model": intent_model,
            "web_url": self._status_links()[0],
            "api_url": self._status_links()[1],
        }
        try:
            s = self._settings()
        except Exception:
            return {}
        try:
            intent_model = s.get_intent_model()
        except Exception:
            intent_model = "?"
        return {
            "embedding_model": getattr(s, "embedding_model", "?"),
            "context_token_limit": getattr(s, "context_token_limit", "?"),
            "max_tokens": getattr(s, "max_tokens", "?"),
            "thinking_limit": getattr(s, "chappie_thinking_token_limit", "?"),
            "temperature": getattr(s, "temperature", "?"),
            "top_p": getattr(s, "top_p", "?"),
            "top_k": getattr(s, "top_k", "?"),
            "steering_model": getattr(s, "steering_model", "?"),
            "intent_model": intent_model,
            "web_url": self._status_links()[0],
            "api_url": self._status_links()[1],
        }

    def _status_extra_rows(self, details: Dict[str, Any]) -> list:
        """Zehn kompakte (key, rich_value, plain_value) fuer die dritte Tabelle."""
        d = details if isinstance(details, dict) else {}

        def known(key: str) -> str:
            value = d.get(key, "?")
            return "?" if value in (None, "") else str(value)

        def tokens(key: str) -> str:
            value = d.get(key, "?")
            try:
                return f"{int(value)} Tokens"
            except (TypeError, ValueError):
                return "?"

        top_p, top_k = known("top_p"), known("top_k")
        sampling = f"{top_p} / {top_k}" if "?" not in (top_p, top_k) else "?"

        def link(key: str) -> tuple[str, str]:
            url = known(key)
            if url == "?":
                return "?", "?"
            return f"[link={url}]{url}[/link]", url

        web_rich, web_plain = link("web_url")
        api_rich, api_plain = link("api_url")

        return [
            ("Embedding:", known("embedding_model"), known("embedding_model")),
            ("Kontext:", tokens("context_token_limit"), tokens("context_token_limit")),
            ("Max Tokens:", known("max_tokens"), known("max_tokens")),
            ("Denken-Limit:", known("thinking_limit"), known("thinking_limit")),
            ("Temperatur:", known("temperature"), known("temperature")),
            ("Top-P/K:", sampling, sampling),
            ("Steering-Mod:", known("steering_model"), known("steering_model")),
            ("Intent-Mod:", known("intent_model"), known("intent_model")),
            ("Web-UI:", web_rich, web_plain),
            ("API:", api_rich, api_plain),
        ]

    @staticmethod
    def _status_top_emotions(emotions: Dict[str, Any], count: int = 3) -> set:
        """Namen der hoechsten Emotionswerte, Gleichstand nach Kanalreihenfolge. Leer wenn alle Null sind."""
        scored = []
        for index, name in enumerate(EMOTION_NAMES):
            try:
                value = int((emotions or {}).get(name, 0) or 0)
            except (TypeError, ValueError, AttributeError):
                value = 0
            scored.append((-value, index, name))
        scored.sort()
        return {name for neg, _, name in scored[:count] if -neg > 0}

    def _status_left_table(self, emotions: Dict[str, Any]):
        left = Table(box=None, show_header=False, padding=(0, 1))
        left.add_column("k", style="dim")
        left.add_column("v")
        mood, color = self._status_mood(emotions if isinstance(emotions, dict) else {})
        left.add_row("[bold]Stimmung:[/]", f"[bold {color}]{mood.upper()}[/]")
        top = self._status_top_emotions(emotions)
        for name in EMOTION_NAMES:
            try:
                val = int((emotions or {}).get(name, 0) or 0)
            except (TypeError, ValueError, AttributeError):
                val = 0
            bar_str = _bar(max(0, min(100, val)), width=15)
            marker = "[bold cyan]◀[/]" if name in top else ""
            left.add_row(name, f"[{_emo_color(val)}]{bar_str} {val:>3}[/] {marker}".rstrip())
        return left

    def _status_key_value_table(self, rows: list):
        """Zwei Spalten Key und Wert ohne eigene Trennlinie, der Teiler steht aussen."""
        table = Table(box=None, show_header=False, padding=(0, 1))
        table.add_column("k", style="dim")
        table.add_column("v", overflow="fold")
        for key, rich_val, _plain in rows:
            table.add_row(key, rich_val)
        return table

    def _status_right_table(self, rows: list):
        return self._status_key_value_table(rows)

    def _status_extra_table(self, rows: list):
        return self._status_key_value_table(rows)

    def _status_plain_lines(self, emotions: Dict[str, Any], rows: list, extra_rows: list) -> tuple[list, list, list]:
        mood, _ = self._status_mood(emotions if isinstance(emotions, dict) else {})
        left_lines = [f"Stimmung: {mood.upper()}"]
        top = self._status_top_emotions(emotions)
        for name in EMOTION_NAMES:
            try:
                val = int((emotions or {}).get(name, 0) or 0)
            except (TypeError, ValueError, AttributeError):
                val = 0
            marker = " ◀" if name in top else ""
            left_lines.append(f"{name:>12} {_bar(max(0, min(100, val)), width=15)} {val:>3}{marker}")
        middle_lines = [f"{key:<14} {plain}" for key, _rich, plain in rows]
        extra_lines = [f"{key:<14} {plain}" for key, _rich, plain in extra_rows]
        return left_lines, middle_lines, extra_lines

    def _show_status(self):
        if self._use_remote:
            status = self.remote.get_status()
            if not status:
                _error("Backend nicht erreichbar")
                return
        else:
            status = self.backend.get_status()

        emotions = status.get("emotions", {})
        if not emotions and not self._use_remote:
            try:
                state = self.emotions.get_state()
                emotions = state.to_dict()
            except Exception:
                emotions = {}
        life = status.get("life_state", {}) or status.get("life_snapshot", {}) or status.get("life", {})
        if not isinstance(life, dict):
            life = {}
        remote_settings = self._status_remote_settings()
        rows = self._status_right_rows(status, life, remote_settings)
        extra_rows = self._status_extra_rows(self._status_model_details(remote_settings))

        def _sep_cell(height: int):
            """Trennlinie ueber die volle Blockhoehe, nicht nur ein Zeichen oben."""
            height = max(1, int(height or 1))
            return Text("\n".join([self.STATUS_SEP] * height), style="dim", justify="center")

        if HAS_RICH:
            left = self._status_left_table(emotions)
            middle = self._status_right_table(rows)
            extra = self._status_extra_table(extra_rows)
            try:
                width = console.width or shutil.get_terminal_size(fallback=(100, 24)).columns  # type: ignore[union-attr]
            except Exception:
                width = shutil.get_terminal_size(fallback=(100, 24)).columns
            if width >= self.STATUS_THREE_COLUMN_MIN_WIDTH:
                grid = Table.grid(expand=True, padding=(0, 1))
                grid.add_column(ratio=3)
                grid.add_column(width=1)
                grid.add_column(ratio=4)
                grid.add_column(width=1)
                grid.add_column(ratio=4)
                full_height = max(len(EMOTION_NAMES) + 1, len(rows), len(extra_rows))
                grid.add_row(left, _sep_cell(full_height), middle, _sep_cell(full_height), extra)
                content = grid
            elif width >= self.STATUS_TWO_COLUMN_MIN_WIDTH:
                grid = Table.grid(expand=True, padding=(0, 1))
                grid.add_column(ratio=1)
                grid.add_column(width=1)
                grid.add_column(ratio=1)
                grid.add_row(left, _sep_cell(max(len(EMOTION_NAMES) + 1, len(rows))), middle)
                content = _RichGroup(grid, Text(""), extra) if _RichGroup else grid
            else:
                content = _RichGroup(left, Text(""), middle, Text(""), extra) if _RichGroup else left
            if _RichGroup:
                content = _RichGroup(Text(""), content, Text(""))
            console.print(Panel(content, title="[bold]CHAPPiE Status[/]", border_style="cyan"))  # type: ignore[union-attr]
        else:
            left_lines, middle_lines, extra_lines = self._status_plain_lines(emotions, rows, extra_rows)
            try:
                width = shutil.get_terminal_size(fallback=(100, 24)).columns
            except Exception:
                width = 100
            print(f"\n{Colors.EMOTION}{'═' * 50}")
            print("  CHAPPiE Status")
            print()
            if width >= self.STATUS_THREE_COLUMN_MIN_WIDTH:
                left_w = max((len(line) for line in left_lines), default=0)
                middle_w = max((len(line) for line in middle_lines), default=0)
                sep = f" {self.STATUS_SEP} "
                for i in range(max(len(left_lines), len(middle_lines), len(extra_lines))):
                    left_part = left_lines[i] if i < len(left_lines) else " " * left_w
                    middle_part = middle_lines[i] if i < len(middle_lines) else " " * middle_w
                    extra_part = extra_lines[i] if i < len(extra_lines) else ""
                    print(f"    {left_part:<{left_w}}{sep}{middle_part:<{middle_w}}{sep}{extra_part}")
            elif width >= self.STATUS_TWO_COLUMN_MIN_WIDTH:
                left_w = max((len(line) for line in left_lines), default=0)
                sep = f" {self.STATUS_SEP} "
                for i in range(max(len(left_lines), len(middle_lines))):
                    left_part = left_lines[i] if i < len(left_lines) else " " * left_w
                    middle_part = middle_lines[i] if i < len(middle_lines) else ""
                    print(f"    {left_part:<{left_w}}{sep}{middle_part}")
                print(f"  {self.STATUS_SEP * 2} Modelldetails {self.STATUS_SEP * 2}")
                for line in extra_lines:
                    print(f"    {line}")
            else:
                for line in left_lines:
                    print(f"    {line}")
                print(f"  {self.STATUS_SEP * 2} System {self.STATUS_SEP * 2}")
                for line in middle_lines:
                    print(f"    {line}")
                print(f"  {self.STATUS_SEP * 2} Modelldetails {self.STATUS_SEP * 2}")
                for line in extra_lines:
                    print(f"    {line}")
            print()
            print(f"{'═' * 50}{Colors.RESET}\n")

    # ── commands ──────────────────────────────────────────────────

    def _session_entries(self) -> list:
        """Sessionliste lokal oder remote, nie werfend, immer als Liste."""
        try:
            if self._use_remote:
                base = getattr(getattr(self, "remote", None), "base_url", self.remote_url or "")
                if not base:
                    return []
                data = requests.get(f"{base}/sessions", timeout=3).json()
                sessions = data if isinstance(data, list) else data.get("sessions", [])
            else:
                sessions = self.backend.chat_manager.list_sessions()  # type: ignore[union-attr]
        except Exception:
            return []
        return list(sessions) if isinstance(sessions, list) else []

    def _session_completions(self) -> list:
        """(id, titel) Paare fuer Tab Vervollstaendigung nach /session."""
        out = []
        for entry in self._session_entries():
            if isinstance(entry, dict) and entry.get("id"):
                out.append((str(entry["id"]), str(entry.get("title", ""))[:60]))
        return out

    @staticmethod
    def _session_message_count(entry: Any) -> Any:
        """Nachrichtenzahl aus message_count oder messages, sonst '?'."""
        if not isinstance(entry, dict):
            return "?"
        count = entry.get("message_count")
        if isinstance(count, int):
            return count
        messages = entry.get("messages")
        if isinstance(messages, list):
            return len(messages)
        return "?"

    def _resolve_session_target(self, target: str) -> Optional[str]:
        """Exakte ID gewinnt, sonst eindeutiges Praefix. Fehler werden gemeldet, dann None."""
        ids = [str(e["id"]) for e in self._session_entries() if isinstance(e, dict) and e.get("id")]
        if target in ids:
            return target
        matches = [i for i in ids if i.startswith(target)]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            _error(f"Session nicht gefunden: {target}")
            print("  Tippe /sessions fuer die Liste, /session <Anfang der ID> reicht.")
            return None
        short = ", ".join(self._short_session_id(m) for m in matches[:8])
        _error(f"Mehrdeutig: {target} passt auf {len(matches)} Sessions ({short})")
        return None

    def _refresh_session_view(self, session_id: Any, title: Any, messages: Any) -> None:
        try:
            if HAS_RICH and console is not None:
                try:
                    console.clear()
                except Exception:
                    pass
            else:
                try:
                    os.system("clear" if os.name != "nt" else "cls")
                except Exception:
                    print("\033c", end="")
        except Exception:
            pass
        short = self._short_session_id(session_id)
        clean_title = str(title or "").strip() or "Ohne Titel"
        count = len(messages) if isinstance(messages, list) else 0
        _success(f"Session gewechselt: {short} ({count} Nachrichten)")
        print(f"{Colors.DIM}{clean_title}{Colors.RESET}\n")
        if not messages:
            print(f"{Colors.DIM}Noch keine Nachrichten in dieser Session.{Colors.RESET}\n")
        else:
            for msg in messages if isinstance(messages, list) else []:
                if not isinstance(msg, dict):
                    continue
                role = str(msg.get("role", "?"))
                content = str(msg.get("content", "") or "")
                if not content.strip():
                    continue
                if role == "user":
                    if HAS_RICH and console is not None:
                        console.print(_response_panel(content, "[bold green]User[/]", "green"))
                    else:
                        print(f"\n{Colors.USER}{Colors.BOLD}User >{Colors.RESET} {content}\n")
                else:
                    if HAS_RICH and console is not None:
                        console.print(_response_panel(content, "[bold bright_cyan]CHAPPiE[/]", "bright_cyan"))
                    else:
                        print(f"\n{Colors.AI}{Colors.BOLD}CHAPPiE >{Colors.RESET} {content}\n")
        try:
            if not self._use_remote and hasattr(self, "backend") and self.backend is not None:
                try:
                    runtime = self.backend.chat_manager.get_runtime_settings(self.session_id)
                    print(f"{Colors.DIM}Session-Flags: Memory {'AN' if runtime.memory_enabled else 'AUS'} | Steering {'AN' if runtime.steering_enabled else 'AUS'} ({runtime.steering_mode}) | Live {'AN' if runtime.live_enabled else 'AUS'}{Colors.RESET}")
                except Exception:
                    pass
        except Exception:
            pass
        try:
            self._show_status()
        except Exception:
            pass

    def _handle_emotion_fallback(self, cmd: str) -> None:
        parts = cmd.split()
        try:
            state_fn = getattr(getattr(self.backend, "emotions", None), "get_state", None)
            state = state_fn().to_dict() if callable(state_fn) else {}
        except Exception:
            state = {}
        if len(parts) == 1:
            lines = ["**Aktuelle Emotions-Werte:**\n"]
            for name in EMOTION_NAMES:
                lines.append(f"- **{name}**: {state.get(name, '?')}/100")
            lines.append("\n*Syntax: /emotion <name> [+/-]<0-100>*")
            lines.append("*Beispiel: /emotion happiness +10, /emotion sadness -5*")
            _print_command_output("\n".join(lines))
            return
        if len(parts) != 3:
            _print_command_output("Nutze: `/emotion <name> [+/-]<0-100>`")
            return
        _, emotion, val_str = parts
        if emotion not in EMOTION_NAMES:
            _print_command_output(f"Unbekannte Emotion: `{emotion}`.")
            return
        try:
            frozen_fn = getattr(getattr(self.backend, "emotions", None), "is_frozen", None)
            if callable(frozen_fn) and frozen_fn() is True:
                _print_command_output("Emotionen sind eingefroren. Nutze `/emofreeze off` zum Freigeben.")
                return
        except Exception:
            pass
        try:
            parsed = int(val_str)
        except ValueError:
            _print_command_output(f"Ungueltiger Wert: `{val_str}`.")
            return
        current = state.get(emotion, 50)
        try:
            current = int(current)
        except (TypeError, ValueError):
            current = 50
        is_delta = val_str.startswith("+") or val_str.startswith("-")
        target = current + parsed if is_delta else parsed
        clamped = max(0, min(100, target))
        try:
            self.backend.emotions.set_emotion(emotion, clamped)
        except Exception:
            pass
        if target != clamped:
            direction = "Maximum" if target > 100 else "Minimum"
            overflow = abs(target - clamped)
            _print_command_output(f"**{emotion}**: {current} {'+' if parsed > 0 else ''}{parsed} -> **{clamped}**/100 ({direction} erreicht, {overflow})")
        else:
            _print_command_output(f"**{emotion}**: {current} -> **{clamped}**/100")

    def _handle_command(self, cmd: str) -> bool:
        cmd_lower = cmd.lower().strip()

        if cmd_lower in ("/exit", "/quit"):
            return False

        if (cmd_lower.split() or [""])[0] in {"/memory", "/steering", "/live", "/emotion", "/preset", "/emofreeze", "/default"}:
            if self._use_remote:
                output = self.remote.handle_command(cmd, session_id=self.session_id)
                self.session_id = self.remote.session_id
                _print_command_output(output)
            else:
                try:
                    from api.services.command_service import execute_slash_command
                    session_id, _ = self._ensure_local_session()
                    result = execute_slash_command(cmd, self.backend, session_id=session_id)
                    self.last_result = result
                    replacement = result.get("replacement_session_id")
                    if replacement:
                        self.session_id = replacement
                        try:
                            self.backend.chat_manager.set_active_session(replacement)
                        except Exception:
                            pass
                    _print_command_output(result["response_text"])
                except (AttributeError, TypeError):
                    fallback = None
                    try:
                        fallback = self.backend.handle_command(cmd)
                    except Exception:
                        fallback = None
                    if fallback is not None and not str(fallback).startswith("Unbekannter Command:") and (cmd_lower.split() or [""])[0] != "/emotion":
                        _print_command_output(str(fallback))
                    else:
                        self._handle_emotion_fallback(cmd)
            return True

        if cmd_lower == "/status":
            self._show_status()
            return True

        if cmd_lower == "/help":
            self._print_help()
            return True

        if cmd_lower == "/last":
            if self.last_result:
                self._display_full_report(self.last_result)
            else:
                _log("LAST", "Noch keine Antwort vorhanden.", Colors.DIM)
            return True

        if cmd_lower == "/raw":
            if not self.last_result:
                _log("RAW", "Noch keine Antwort vorhanden.", Colors.DIM)
                return True
            result = self.last_result
            intent_raw = result.get("intent_raw_json", {})
            response_text = result.get("response_text", "")
            if intent_raw and HAS_RICH:
                from rich.syntax import Syntax
                console.print(Panel(Syntax(json.dumps(intent_raw, indent=2, ensure_ascii=False), "json", theme="monokai"), title="[bold magenta]Step 1 Raw JSON[/]", border_style="magenta"))
            elif intent_raw:
                print(f"\n{Colors.MEMORY}--- Step 1 Raw JSON ---\n{json.dumps(intent_raw, indent=2, ensure_ascii=False)}\n{Colors.RESET}")
            if response_text and HAS_RICH:
                console.print(Panel(response_text[:4000], title="[dim]Raw Model Output (vor Formatting)[/]", border_style="dim"))
            elif response_text:
                print(f"\n{Colors.DIM}--- Raw Model Output ---\n{response_text[:2000]}\n{Colors.RESET}")
            return True

        if cmd_lower == "/trace":
            if not self.last_result:
                _log("TRACE", "Noch keine Antwort vorhanden.", Colors.DIM)
                return True
            if HAS_RICH and self.last_result.get("causal_trace"):
                console.print(self._panel_causal(self.last_result) or "")
            else:
                causal = self.last_result.get("causal_trace", [])
                for c in causal:
                    if isinstance(c, dict):
                        print(f"  [{c.get('phase', '?')}] {c.get('driver', '')} → {c.get('effect', '')}")
            return True

        if cmd_lower == "/compact":
            self._show_full_report = False
            _success("Compact-Mode: Nur kompakter Report nach jeder Antwort. /last fuer vollen Report.")
            return True

        if cmd_lower == "/full":
            self._show_full_report = True
            _success("Full-Mode: Voller Report nach jeder Antwort.")
            return True

        if cmd_lower == "/runtime":
            if self._use_remote:
                try:
                    base = getattr(getattr(self, "remote", None), "base_url", self.remote_url or "")
                    settings_data = requests.get(f"{base}/settings", timeout=10).json()
                    status = self.remote.get_status() if hasattr(self, "remote") else {}
                    print(f"\n{Colors.AI}{'═' * 50}")
                    print("  RUNTIME (remote)")
                    print(f"  Provider:      {settings_data.get('llm_provider', status.get('provider', '?'))}")
                    print(f"  Modell:        {settings_data.get('vllm_model', status.get('model', '?'))}")
                    print(f"  Two-Step:      {'AN' if settings_data.get('enable_two_step_processing') else 'AUS'}")
                    print(f"  Thinking/CoT:  {'AN' if settings_data.get('chain_of_thought') else 'AUS'}")
                    print(f"  Steering:      {'AN' if settings_data.get('enable_steering') else 'AUS'}")
                    print(f"{'═' * 50}{Colors.RESET}\n")
                except Exception:
                    _log("RUNTIME", "Remote-Status nicht abrufbar", Colors.WARN)
                return True
            s = self._settings()
            mode = "VEKTOR" if self.steering.is_local_provider() else "PROMPT"
            print(f"\n{Colors.AI}{'═' * 50}")
            print("  RUNTIME")
            print(f"  Provider:      {s.llm_provider.value}")
            print(f"  Modell:        {s.vllm_model}")
            print(f"  Two-Step:      {'AN' if s.enable_two_step_processing else 'AUS'}")
            print(f"  Thinking/CoT:  {'AN' if s.chain_of_thought else 'AUS'}")
            print(f"  Steering:      {'AN' if s.enable_steering else 'AUS'} ({mode})")
            print(f"  Intent-Modell: {s.get_intent_model(s.intent_provider)}")
            print(f"{'═' * 50}{Colors.RESET}\n")
            return True

        if cmd_lower == "/model" or cmd_lower.startswith("/model "):
            args = cmd.split(maxsplit=1)
            if self._use_remote:
                try:
                    base = getattr(getattr(self, "remote", None), "base_url", self.remote_url or "")
                    settings_data = requests.get(f"{base}/settings", timeout=10).json()
                    print(f"\n{Colors.AI}Aktives Modell (remote): {Colors.BOLD}{settings_data.get('vllm_model', '?')}{Colors.RESET}")
                    print(f"  Provider: {settings_data.get('llm_provider', '?')}")
                    if len(args) > 1:
                        _warn("Modellwechsel remote: bitte in der Web-UI unter Settings aendern (POST /settings).")
                    print()
                except Exception:
                    _log("MODEL", "Remote-Status nicht abrufbar", Colors.WARN)
                return True
            if len(args) == 1:
                s = self._settings()
                print(f"\n{Colors.AI}Aktives Modell: {Colors.BOLD}{s.vllm_model}{Colors.RESET}")
                print(f"  Provider: {s.llm_provider.value}")
                print(f"  Steering: {s.steering_model}")
                print("  Presets: qwen | gemma4-e4b | gemma4-26b")
                print(f"\n{Colors.DIM}Syntax: /model <preset|model-name>{Colors.RESET}\n")
                return True
            self._handle_model_command(args[1])
            return True

        if cmd_lower == "/thinking" or cmd_lower == "/thinking status":
            if self._use_remote:
                try:
                    base = getattr(getattr(self, "remote", None), "base_url", self.remote_url or "")
                    settings_data = requests.get(f"{base}/settings", timeout=10).json()
                    status_str = "AN" if settings_data.get("chain_of_thought") else "AUS"
                    print(f"\n{Colors.AI}Thinking/Reasoning (remote): {Colors.BOLD}{status_str}{Colors.RESET}\n")
                except Exception:
                    _log("THINKING", "Remote-Status nicht abrufbar", Colors.WARN)
                return True
            s = self._settings()
            status_str = "AN" if s.chain_of_thought else "AUS"
            provider_label = s.llm_provider.value.upper() if not self._use_remote else "REMOTE"
            print(f"\n{Colors.AI}Thinking/Reasoning: {Colors.BOLD}{status_str}{Colors.RESET}")
            print(f"  Provider: {provider_label}")
            print("  vLLM: natives Thinking auf Qwen3.5-4B deaktiviert (Build ohne Reasoning-Support, Prosa-Leak verifiziert)")
            print(f"  Ollama: {'think aktiv' if s.chain_of_thought else 'think deaktiviert'}")
            print(f"  Groq: {'CoT-Prompt aktiv' if s.chain_of_thought else 'kein CoT-Prompt'}")
            print(f"\n{Colors.DIM}Syntax: /thinking on | /thinking off | /thinking status{Colors.RESET}\n")
            return True

        if cmd_lower.startswith("/thinking "):
            _, val = cmd.split(maxsplit=1)
            val = val.lower().strip()
            if val in ("status", "show"):
                return self._handle_command("/thinking")
            if val in ("true", "on", "an", "1", "ja", "yes"):
                new_val = True
            elif val in ("false", "off", "aus", "0", "nein", "no"):
                new_val = False
            else:
                _error(f"Ungueltiger Wert: {val}. Nutze: /thinking on | /thinking off")
                return True
            s = self._settings()
            s.update_from_ui(chain_of_thought=new_val)
            if self._use_remote:
                try:
                    base = getattr(getattr(self, "remote", None), "base_url", self.remote_url or "")
                    requests.post(f"{base}/settings", json={"chain_of_thought": new_val}, timeout=10)
                except Exception as e:
                    _warn(f"Remote-Update fehlgeschlagen, lokal gespeichert: {e}")
            if not self._use_remote and self.backend:
                self.backend.apply_runtime_settings(force=True)
            status_str = "AN" if new_val else "AUS"
            _success(f"Thinking/Reasoning: {status_str}")
            if new_val:
                _log("THINKING", "Hinweis: Qwen3.5-4B hat keinen nativen Reasoning-Support, kein CoT sichtbar. Wirkt auf Ollama/Groq.", Colors.WARN)
            return True

        if cmd_lower == "/resetemotions":
            try:
                frozen = bool(self.backend.emotions.is_frozen()) if not self._use_remote and hasattr(self.backend, "emotions") and hasattr(self.backend.emotions, "is_frozen") else False
            except Exception:
                frozen = False
            if frozen:
                _error("Emotionen sind eingefroren. Nutze /emofreeze off zum Freigeben.")
                return True
            if self._use_remote:
                try:
                    response = requests.post(f"{self.remote_url}/emotions/reset", timeout=5)
                    response.raise_for_status()
                    _success("Remote-Emotionen zurueckgesetzt")
                except Exception as e:
                    _error(f"Remote-Reset fehlgeschlagen: {e}")
                    return True
            else:
                self.emotions.reset()
                _success("Emotionen zurueckgesetzt")
            self._show_status()
            return True

        if cmd_lower == "/sleep":
            if self._use_remote:
                output = self.remote.handle_command("/sleep", session_id=self.session_id)
                self.session_id = self.remote.session_id
                if output and not output.startswith("Error"):
                    _print_command_output(output)
                else:
                    _error(output or "Sleep fehlgeschlagen")
                return True
            from api.services.command_service import execute_slash_command as _exec_sleep
            result = _exec_sleep("/sleep", self.backend)
            self.last_result = result
            _print_command_output(result.get("response_text", ""))
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

        if cmd_lower == "/copy" or cmd_lower.startswith("/copy "):
            return self._handle_copy_command(cmd)

        if cmd_lower in ("/clear", "/new"):
            if self._use_remote:
                output = self.remote.handle_command("/new", session_id=self.session_id)
                self.session_id = self.remote.session_id
                self.history = []
                self.last_result = None
                _success("Neue Chat-Sitzung gestartet")
                if output and output != "Neue Chat-Sitzung gestartet.":
                    print(f"\n{Colors.MEMORY}{output}{Colors.RESET}\n")
                return True
            from api.services.command_service import execute_slash_command as _exec_new
            try:
                result = _exec_new("/new", self.backend)
                self.session_id = result.get("replacement_session_id", self.session_id)
            except Exception:
                result = None
            self.history = []
            self.last_result = None
            if result is not None:
                try:
                    fresh = self.backend.chat_manager.load_session(self.session_id)
                    self.history = list(fresh.get("messages", []))
                except Exception:
                    pass
            _success("Neue Chat-Sitzung gestartet")
            return True

        if cmd_lower == "/sessions":
            if self._use_remote:
                try:
                    sessions = self._session_entries()
                    print(f"\n{Colors.AI}Sessions ({len(sessions)}):")
                    for s in sessions[:20]:
                        mark = "*" if s.get("id") == self.session_id else " "
                        print(f" {mark} {self._short_session_id(s.get('id', '?')):<8}  {str(s.get('title', ''))[:60]}  ({self._session_message_count(s)} Nachrichten)")
                    print()
                except Exception as e:
                    _error(f"Sessions konnten nicht geladen werden: {e}")
                return True
            try:
                sessions = self.backend.chat_manager.list_sessions()  # type: ignore[union-attr]
                print(f"\n{Colors.AI}Sessions ({len(sessions)}):")
                for s in sessions[:20]:
                    mark = "*" if s.get("id") == self.session_id else " "
                    print(f" {mark} {self._short_session_id(s.get('id', '?')):<8}  {str(s.get('title', ''))[:60]}  ({self._session_message_count(s)} Nachrichten)")
                print()
            except Exception as e:
                _error(f"Sessions konnten nicht geladen werden: {e}")
            return True

        if cmd_lower == "/session":
            print(f"\n{Colors.DIM}Syntax: /session <ID oder Anfang der ID>  (Tab vervollstaendigt, /sessions listet auf){Colors.RESET}\n")
            return True

        if cmd_lower.startswith("/session "):
            target = cmd.split(maxsplit=1)[1].strip()
            if self._use_remote:
                try:
                    resolved = self._resolve_session_target(target)
                    if resolved is None:
                        return True
                    data = requests.get(f"{self.remote_url}/sessions/{resolved}", timeout=10).json()
                    if isinstance(data, dict) and data.get("id"):
                        self.session_id = data["id"]
                        self.remote.session_id = data["id"]
                        self.history = list(data.get("messages", []))
                        self.last_result = None
                        self._refresh_session_view(data.get("id"), data.get("title", ""), self.history)
                    else:
                        _error("Session nicht gefunden")
                except Exception as e:
                    _error(f"Session-Wechsel fehlgeschlagen: {e}")
                return True
            try:
                resolved = self._resolve_session_target(target)
                if resolved is None:
                    return True
                session = self.backend.chat_manager.load_session(resolved)  # type: ignore[union-attr]
                self.backend.chat_manager.set_active_session(resolved)  # type: ignore[union-attr]
                self.session_id = resolved
                self.history = list(session.get("messages", []))
                self.last_result = None
                self._refresh_session_view(resolved, session.get("title", ""), self.history)
            except Exception as e:
                _error(f"Session-Wechsel fehlgeschlagen: {e}")
            return True

        if cmd_lower == "/restart" or cmd_lower.startswith("/restart "):
            parts = cmd.split(maxsplit=1)
            target = parts[1].strip().lower() if len(parts) > 1 else ""
            if not target:
                try:
                    choice = input("Neustart: [1] CHAPPiE (Backend + Frontend)  [2] nur CLI > ").strip().lower()
                except (KeyboardInterrupt, EOFError):
                    print()
                    return True
                if choice in ("1", "chappie", "backend", "server"):
                    target = "chappie"
                elif choice in ("2", "cli"):
                    target = "cli"
                else:
                    _warn("Ungueltige Auswahl. Nutze: /restart chappie | /restart cli")
                    return True
            return self._handle_restart_command(target)

        if cmd_lower == "/debug":
            if not self._use_remote and self.backend:
                if self.backend.debug_logger.enabled:
                    self.backend.debug_logger.disable()
                    _log("DEBUG", "Debug-Output deaktiviert", Colors.DIM)
                else:
                    self.backend.debug_logger.enable()
                    count = len(self.backend.debug_logger.get_entries_as_dict())
                    _success(f"Debug-Output aktiviert ({count} entries)")
            return True

        if cmd_lower == "/debug on":
            if not self._use_remote and self.backend:
                self.backend.debug_logger.enable()
            _success("Debug-Output aktiviert")
            return True

        if cmd_lower == "/debug off":
            if not self._use_remote and self.backend:
                self.backend.debug_logger.disable()
            _log("DEBUG", "Debug-Output deaktiviert", Colors.DIM)
            return True

        if cmd_lower == "/md":
            """Zeigt alle drei .md-Kontextdateien an (soul, user, preferences)."""
            if self._use_remote:
                try:
                    soul = requests.get(f"{self.remote_url}/context-files/soul", timeout=10).json().get("content", "(leer)")
                    user = requests.get(f"{self.remote_url}/context-files/user", timeout=10).json().get("content", "(leer)")
                    prefs = requests.get(f"{self.remote_url}/context-files/preferences", timeout=10).json().get("content", "(leer)")
                except Exception:
                    soul = self.remote.handle_command("/soul", session_id=self.session_id)
                    user = self.remote.handle_command("/user", session_id=self.session_id)
                    prefs = self.remote.handle_command("/prefs", session_id=self.session_id)
            elif hasattr(self, 'context') and self.context:
                soul = self.context.get_soul_context() or "(leer)"
                user = self.context.get_user_context() or "(leer)"
                prefs = self.context.get_preferences_context() or "(leer)"
            else:
                _warn("Context-Dateien nicht verfuegbar (kein Backend)")
                return True

            if HAS_RICH:
                console.print(Panel(
                    soul.strip() if soul else "(leer)",
                    title="[bold cyan]soul.md[/]",
                    border_style="cyan",
                ))
                console.print(Panel(
                    user.strip() if user else "(leer)",
                    title="[bold green]user.md[/]",
                    border_style="green",
                ))
                console.print(Panel(
                    prefs.strip() if prefs else "(leer)",
                    title="[bold yellow]CHAPPiEsPreferences.md[/]",
                    border_style="yellow",
                ))
            else:
                print(f"\n{Colors.AI}{'═' * 60}")
                print(f"  soul.md\n{'═' * 60}")
                print(f"{soul.strip()}{Colors.RESET}\n")
                print(f"\n{Colors.USER}{'═' * 60}")
                print(f"  user.md\n{'═' * 60}")
                print(f"{user.strip()}{Colors.RESET}\n")
                print(f"\n{Colors.EMOTION}{'═' * 60}")
                print(f"  CHAPPiEsPreferences.md\n{'═' * 60}")
                print(f"{prefs.strip()}{Colors.RESET}\n")
            return True

        backend_cmd = cmd_lower if cmd_lower.startswith("/") else "/" + cmd_lower

        if self._use_remote:
            result = self.remote.handle_command(backend_cmd, session_id=self.session_id)
            self.session_id = self.remote.session_id
            if result and not result.startswith("Error"):
                _print_command_output(result)
                return True

        if self.backend:
            from api.services.command_service import execute_slash_command as _exec_fallback
            try:
                cmd_result = _exec_fallback(backend_cmd, self.backend, session_id=self.session_id)
                replacement = cmd_result.get("replacement_session_id")
                if replacement:
                    self.session_id = replacement
                    self.backend.chat_manager.set_active_session(replacement)
                output = cmd_result.get("response_text", "")
                if output and output != f"Unbekannter Command: {backend_cmd}":
                    _print_command_output(output)
                    self.last_result = cmd_result
                    return True
            except Exception:
                pass
            result = self.backend.handle_command(backend_cmd)
            if not result.startswith("Unbekannter Command:"):
                _print_command_output(result)
                return True

        _warn(f"Unbekannter Befehl: {cmd}")
        print("  Tippe /help fuer alle Befehle")
        return True

    def _handle_copy_command(self, cmd: str) -> bool:
        """Exports the active session and sends a safe OSC 52 clipboard request."""
        parts = cmd.strip().split()
        mode = parts[1].lower() if len(parts) == 2 else ""
        if len(parts) == 1:
            try:
                choice = input(
                    "Kopieren: [1] Standard (UI-Daten)  [2] Debug (vollständiger Export) > "
                ).strip().lower()
            except (KeyboardInterrupt, EOFError):
                print()
                return True
            if choice in ("1", "standard", "ui"):
                mode = "standard"
            elif choice in ("2", "debug", "vollständig", "vollstaendig"):
                mode = "debug"
            else:
                _warn("Ungueltige Auswahl. Nutze: /copy standard | /copy debug")
                return True
        elif len(parts) != 2 or mode not in ("standard", "debug"):
            _warn("Ungueltiger Modus. Nutze: /copy standard | /copy debug")
            return True

        fallback_path = ""
        if self._use_remote:
            response = self.remote.export_session(mode, session_id=self.session_id)
            if response.get("error"):
                _error(f"Session-Export fehlgeschlagen: {response['error']}")
                return True
            export = response.get("export")
            fallback_path = str(response.get("fallback_path") or "")
        else:
            try:
                from web_infrastructure.session_export import (
                    SessionExportError,
                    backend_data_directory,
                    build_session_export,
                    write_session_export,
                )

                export = build_session_export(self.backend, self.session_id, mode=mode)
                fallback_path = str(
                    write_session_export(export, backend_data_directory(self.backend))
                )
            except SessionExportError as exc:
                _error(f"Session-Export fehlgeschlagen: {exc}")
                return True
            except Exception as exc:
                _error(f"Session-Export fehlgeschlagen: {exc}")
                return True

        if not isinstance(export, dict):
            _error("Session-Export lieferte kein gültiges JSON-Objekt.")
            return True

        from web_infrastructure.session_export import build_clipboard_text, emit_osc52, serialize_session_export

        payload = serialize_session_export(export)
        clipboard = emit_osc52(payload)
        label = "Standard" if mode == "standard" else "Debug"
        if clipboard.get("sent"):
            _success(f"{label}-Export als JSON an die Terminal-Zwischenablage gesendet.")
        else:
            # Volle JSON-Exports (live: 302 KB Standard) passen nie in OSC 52.
            # Die Zwischenablage bekommt den kompakten Verlauf, die Datei das volle JSON.
            compact = build_clipboard_text(export)
            clipboard_compact = emit_osc52(compact)
            if clipboard_compact.get("sent"):
                _success(f"Gesprächsverlauf in Zwischenablage kopiert (kompakt lesbar, {len(compact.encode('utf-8')) // 1024} KB).")
                _log("COPY", "Vollständiges JSON liegt in der Fallback-Datei (siehe unten).", Colors.MEMORY)
            elif clipboard_compact.get("reason") == "stdout_not_tty" or clipboard.get("reason") == "stdout_not_tty":
                _warn("Keine interaktive Terminal-Zwischenablage erkannt.")
            elif clipboard.get("reason") == "payload_too_large":
                _warn("JSON ist für eine sichere OSC-52-Übertragung zu groß.")
            else:
                _warn("OSC-52-Zwischenablage konnte nicht angesprochen werden.")
        if fallback_path:
            _log("COPY", f"Vollständige Fallback-Datei: {fallback_path}", Colors.MEMORY)
        else:
            _warn("Keine Fallback-Datei vom Server gemeldet.")
        return True

    def _handle_model_command(self, args: str) -> None:
        model_name = self._resolve_model_alias(args)
        if not model_name:
            _error("Kein Modell angegeben")
            return

        s = self._settings()
        old_model = s.vllm_model
        is_gemma_26b = "gemma" in model_name.lower() and ("26b" in model_name.lower() or "a4b" in model_name.lower())
        context_length = 4096 if is_gemma_26b else 8192
        s.update_from_ui(
            llm_provider="vllm",
            vllm_model=model_name,
            steering_model=model_name,
            steering_quantize=is_gemma_26b,
            steering_context_length=context_length,
            use_model_defaults=True,
        )

        print(f"\nModell-Wechsel: {old_model} -> {model_name}")
        if s.enable_steering:
            self._restart_steering_server(model_name, quantize=is_gemma_26b)
        if self.backend:
            self.backend.apply_runtime_settings(force=True)
        _success(f"Modell gewechselt zu: {model_name}")

    def _handle_restart_command(self, target: str) -> bool:
        if target in ("chappie", "backend", "server"):
            return self._restart_chappie_services()
        if target == "cli":
            return self._restart_cli_process()
        _warn("Ungueltiges Ziel. Nutze: /restart chappie | /restart cli")
        return True

    @staticmethod
    def _run_systemctl(service: str) -> tuple[bool, str]:
        try:
            completed = subprocess.run(
                ["sudo", "systemctl", "restart", service],
                capture_output=True,
                text=True,
                timeout=120,
            )
            output = (completed.stdout or "") + (completed.stderr or "")
            return completed.returncode == 0, output.strip()
        except Exception as exc:
            return False, str(exc)

    def _restart_chappie_services(self) -> bool:
        _log("RESTART", "Starte CHAPPiE Backend + Frontend neu...", Colors.AI)
        ok = True
        for service in ("chappie-web", "chappie-frontend"):
            success, output = self._run_systemctl(service)
            if success:
                _success(f"{service} neugestartet")
            else:
                ok = False
                _error(f"{service} Neustart fehlgeschlagen{(': ' + output) if output else ''}")
        if ok:
            _success("CHAPPiE laeuft neu (Backend + Frontend)")
        else:
            _warn("Mindestens ein Dienst meldet einen Fehler, Details siehe oben")
        return True

    def _restart_cli_process(self) -> bool:
        _log("RESTART", "Starte CLI neu...", Colors.AI)
        sys.stdout.flush()
        try:
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as exc:
            _error(f"CLI-Neustart fehlgeschlagen: {exc}")
        return True

    def _restart_steering_server(self, model_name: str, quantize: bool = False) -> None:
        if not HAS_REQUESTS:
            _warn("requests nicht installiert; Steering-Restart uebersprungen")
            return
        base_url = self._steering_base_url()
        try:
            requests.post(f"{base_url}/v1/steering/restart", json={"model": model_name, "quantize": quantize}, timeout=10)
        except Exception as exc:
            _warn(f"Steering-Restart konnte nicht gestartet werden: {exc}")
            return

        start_time = time.time()
        timeout = 180
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{base_url}/v1/steering/restart-status", timeout=5)
                response.raise_for_status()
                status = response.json()
            except Exception:
                print("\r  Steering-Server startet...", end="", flush=True)
                time.sleep(2)
                continue

            progress = int(status.get("progress", 0) or 0)
            step = status.get("current_step", "")
            remaining = int(status.get("estimated_remaining", 0) or 0)
            filled = int(30 * progress / 100)
            bar = "=" * filled + "-" * (30 - filled)
            print(f"\r  [{bar}] {progress}% - {step} (~{remaining}s)", end="", flush=True)

            if status.get("status") == "ready":
                print("\nSteering-Server ist bereit.")
                return
            if status.get("status") == "error":
                print(f"\nSteering-Fehler: {status.get('error') or step}")
                return
            time.sleep(2)
        print("\nTimeout: Steering-Server meldet keinen Abschluss.")

    def _build_help_lines(self, width: Optional[int] = None) -> str:
        total = width or shutil.get_terminal_size(fallback=(100, 24)).columns
        total = max(40, total)
        sep = "  │  "
        col_width = max(10, (total - len(sep) * 2) // 3)
        lines = [
            f"{Colors.AI}{Colors.BOLD}CHAPPiE Terminal Interface v{self.CLI_VERSION}{Colors.RESET}",
            "",
        ]
        header = sep.join(
            f"{Colors.AI}{Colors.BOLD}{title:<{col_width}}{Colors.RESET}"
            for title, _ in HELP_COLUMNS
        )
        lines.append(header)
        rows = max(len(items) for _, items in HELP_COLUMNS)
        for i in range(rows):
            cells = []
            for _, items in HELP_COLUMNS:
                cmd_width = min(max(len(cmd) for cmd, _ in items) + 2, col_width // 2)
                if i < len(items):
                    cmd, desc = items[i]
                    cell = f"{cmd:<{cmd_width}} {desc}"[:col_width].ljust(col_width)
                else:
                    cell = " " * col_width
                cells.append(cell)
            lines.append(sep.join(cells))
        lines += [
            "",
            "Weitere: /stats /life /world /habits ..."[:total],
            "Tipp: /emotion <name> [+/-]<0-100>, z.B. /emotion happiness +10"[:total],
            "Tipp: /preset <schlecht|neutral|wohl> setzt eine Gefuehlslage"[:total],
            "Tipp: /emofreeze on|off friert Emotionen fuer Tests ein"[:total],
            "Tipp: /default stellt alle Settings auf Standard zurueck"[:total],
            "Tipp: /thinking on|off zeigt Chain of Thought an oder aus"[:total],
            "Tipp: /session <ID> wechselt mit Refresh und laedt den Verlauf"[:total],
            "",
            "Ctrl+C         Generierung abbrechen (Streaming)",
        ]
        return "\n".join(lines)

    def _print_help(self, width: Optional[int] = None):
        print(self._build_help_lines(width))

    # ── run ───────────────────────────────────────────────────────

    def run(self):
        steering_info = "?"
        if not self._use_remote and self.backend:
            steering_info = "VEKTOR-STEERING" if self.steering.is_local_provider() else "PROMPT-STEERING"

        mode_str = "REMOTE" if self._use_remote else "LOKAL"

        print(f"""
{Colors.AI}{Colors.BOLD}
   ██████╗ ██╗  ██╗  █████╗  ██████╗  ██████╗  ██╗ ███████╗
  ██╔════╝ ██║  ██║ ██╔══██╗ ██╔══██╗ ██╔══██╗ ██║ ██╔════╝
  ██║      ███████║ ███████║ ██████╔╝ ██████╔╝ ██║ █████╗  
  ██║      ██╔══██║ ██╔══██║ ██╔═══╝  ██╔═══╝  ██║ ██╔══╝  
  ╚██████╗ ██║  ██║ ██║  ██║ ██║      ██║      ██║ ███████╗
   ╚═════╝ ╚═╝  ╚═╝ ╚═╝  ╚═╝ ╚═╝      ╚═╝      ╚═╝ ╚══════╝
{Colors.AI}CHAPPiE Terminal Interface v{self.CLI_VERSION} [{mode_str}]
{Colors.STEER}Steering: {steering_info} | {len(EMOTION_NAMES)} Emotionale Dimensionen
{Colors.DEBUG}Live Streaming + Debug-Report | Tippe /help fuer alle Befehle
{Colors.RESET}""")

        self._show_status()

        real_stdout = sys.stdout
        self._out_capture = None
        if not self._use_remote:
            # Backend-Threads (Memory, Schlafphase) drucken direkt auf stdout.
            # Der Puffer haelt Live-Display und Eingabezeile sauber.
            self._out_capture = _StrayOutputCapture(real_stdout)
            sys.stdout = self._out_capture
        try:
            while True:
                self._drain_background_output()
                try:
                    if not sys.stdin.isatty():
                        # Pipes remain usable for command scripts.
                        user_input = input("")
                    else:
                        try:
                            from cli.input import create_prompt_session
                            from config.config import DATA_DIR
                            from prompt_toolkit.formatted_text import ANSI
                            from prompt_toolkit.patch_stdout import patch_stdout
                        except ImportError:
                            # prompt_toolkit is declared in requirements/runtime.txt
                            # and installed in venv. Fall back to plain input so
                            # the CLI still works with a bare system python.
                            if not getattr(self, "_plain_input_warned", False):
                                _error("Hinweis: prompt_toolkit fehlt, nutze einfache Eingabe (venv nutzen fuer Verlauf und Vervollstaendigung).")
                                self._plain_input_warned = True
                            user_input = input("")
                        else:
                            history_session = self.session_id or "new-session"
                            if getattr(self, "_prompt_session_id", None) != history_session:
                                self._prompt_session = create_prompt_session(DATA_DIR / "cli_history", history_session, session_provider=self._session_completions)
                                self._prompt_session_id = history_session
                            # Bypass the live-render capture during input. patch_stdout
                            # redraws the prompt safely after background output.
                            previous_stdout = sys.stdout
                            sys.stdout = real_stdout
                            try:
                                with patch_stdout():
                                    user_input = self._prompt_session.prompt(ANSI(self._input_prompt()))
                            finally:
                                sys.stdout = previous_stdout
                except (KeyboardInterrupt, EOFError):
                    break

                self._drain_background_output()

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
        finally:
            if self._out_capture is not None:
                sys.stdout = real_stdout
                self._out_capture = None

        _log("EXIT", "CHAPPiE beendet. Bis bald!", Colors.AI)


def main():
    parser = argparse.ArgumentParser(description="CHAPPiE Terminal Interface v17.2.0-dev.2")
    parser.add_argument("--remote", action="store_true", help="Connect to remote backend via SSE")
    parser.add_argument("--url", default="http://localhost:8010", help="Backend URL (default: localhost:8010)")
    parser.add_argument("--model", type=str, default=None, help="Lokales vLLM-Modell ueberschreiben (z.B. gemma4-26b)")
    args = parser.parse_args()

    if args.model and not args.remote:
        from config.config import settings

        model_name = CHAPPiEBrainCLI._resolve_model_alias(args.model)
        is_gemma_26b = "gemma" in model_name.lower() and ("26b" in model_name.lower() or "a4b" in model_name.lower())
        context_length = 4096 if is_gemma_26b else 8192
        settings.update_from_ui(
            llm_provider="vllm",
            vllm_model=model_name,
            steering_model=model_name,
            steering_quantize=is_gemma_26b,
            steering_context_length=context_length,
            use_model_defaults=True,
        )

    remote_url = args.url if args.remote else None
    cli = CHAPPiEBrainCLI(remote_url=remote_url)
    cli.run()


if __name__ == "__main__":
    main()
