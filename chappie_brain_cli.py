"""CHAPPiE Terminal Interface v16.8.7

Rich-formatted terminal client with live token streaming (CoT + Answer),
full debug output, compact auto-report, and backend+SSE connectivity.
Inkl. /thinking Command zum Aktivieren/Deaktivieren des Reasonings.
Paritaet zur Web-UI (API 16.8.7): Sessions, command_mode, alle Slash-Commands.

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

from config.emotions import EMOTION_ORDER

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


HELP_COLUMNS = (
    ("Chat-Befehle", [
        ("/status", "Status + Life"),
        ("/clear", "Neue Sitzung"),
        ("/new", "Neue Sitzung"),
        ("/sessions", "Sessions auflisten"),
        ("/session <id>", "Session wechseln"),
        ("/history", "Verlauf anzeigen"),
        ("/md", "soul, user, Prefs"),
        ("/restart", "Neustart: chappie | cli"),
        ("/exit", "Beenden"),
        ("/help", "Diese Hilfe"),
    ]),
    ("Forschungs-Befehle", [
        ("/runtime", "Modell, Provider"),
        ("/model", "Modell wechseln"),
        ("/thinking", "Reasoning an/aus"),
        ("/steering", "Steering Report"),
        ("/emotion", "Emotionen setzen"),
        ("/resetemotions", "Emotionen reset"),
        ("/sleep", "Schlafphase"),
        ("/memory", "Gedaechtnis Suche"),
        ("/debug", "Debug an/aus"),
    ]),
    ("Nach Ausgabe Befehle", [
        ("/last", "Voller Report"),
        ("/raw", "Step 1 + Raw Output"),
        ("/trace", "Causal Trace"),
        ("/compact", "Kompakter Report"),
        ("/full", "Voller Report"),
    ]),
)


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


# ═══════════════════════════════════════════════════════════════════
# CHAPPiEBrainCLI
# ═══════════════════════════════════════════════════════════════════

class CHAPPiEBrainCLI:
    CLI_VERSION = "16.8.7"

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
            session = self.backend.chat_manager.load_session(session_id)
            messages = list(session.get("messages", []))
            # Pending-Logik der API ist hier nicht noetig, direkt beide Nachrichten speichern.
            messages.extend([user_message, assistant_message])
            self.backend.chat_manager.save_session(session_id, messages, title=session.get("title"))
            self.history = list(messages)
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
            from api.services.command_service import execute_slash_command
            try:
                session_id, _ = self._ensure_local_session()
                result = execute_slash_command(user_text.strip(), self.backend)
                replacement = result.get("replacement_session_id")
                if replacement:
                    session_id = replacement
                    self.backend.chat_manager.set_active_session(session_id)
                    self.session_id = session_id
                self.last_result = result
                output = result.get("response_text", "")
                if HAS_RICH:
                    console.print(Panel(output, title="[bold magenta]Command[/]", border_style="magenta", padding=(0, 1)))
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
        token_count = 0
        last_tps_update = 0.0
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
                                if now - last_tps_update > 0.5:
                                    tps = token_count / (now - streaming_start) if (now - streaming_start) > 0 else 0
                                    last_tps_update = now
                                live.update(self._render_streaming(collected, token_count, tps, now - streaming_start))
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
                                last_tps_update = streaming_start
                            collected[event.get("token_type", "answer")] += event.get("content", "")
                            token_count += 1

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
        token_count = 0
        last_tps_update = 0.0
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
                                if now - last_tps_update > 0.5:
                                    tps = token_count / (now - streaming_start) if (now - streaming_start) > 0 else 0
                                    last_tps_update = now
                                live.update(self._render_streaming(collected, token_count, tps, now - streaming_start))
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
                                last_tps_update = streaming_start
                            collected[event.get("token_type", "answer")] += event.get("content", "")
                            token_count += 1

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
    def _render_streaming(collected: dict, token_count: int, tps: float, elapsed: float):
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
            title=f"[bold bright_cyan]Antwort[/]  [dim]{token_count} tk  {tps:.0f} tk/s  {elapsed:.1f}s[/]",
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
            table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
            table.add_column("k", style="dim")
            table.add_column("v")

            intent_str = f"{intent} ({confidence:.2f})" if confidence else str(intent)
            tools_str = ", ".join(tools) if tools else "none"
            table.add_row("Intent:", f"{intent_str}    Tools: {tools_str}")

            emo_parts = []
            for name in EMOTION_NAMES:
                b = emotion_before.get(name, 0)
                a = emotion_after.get(name, 0)
                d = a - b
                if d == 0:
                    continue
                sign = f"[green]↑+{d}[/]" if d > 0 else f"[red]↓{d}[/]"
                emo_parts.append(f"{name} [bold]{a}[/] {sign}")
            if emo_parts:
                table.add_row("Emotionen:", "  ".join(emo_parts))

            steer_str = "VECTOR" if ("vector" in prompt_mode or "layer" in prompt_mode) else "PROMPT"
            dom = steering.get("dominant_vector", "neutral")
            dom_s = steering.get("dominant_strength", 0)
            table.add_row("Steering:", f"[{_emo_color(int(dom_s * 100))}]{steer_str} | dominant: {dom} ({dom_s:.2f})[/]")

            table.add_row("Tone:", f"{tone.get('tone', '?')}  ({tone.get('tone_reason', '')[:80]})")

            fmt_source = result.get("formatting_source", "local_fallback")
            fmt_model = result.get("formatting_model", "?")
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
            table.add_row("Format:", f"[{fmt_color}]{fmt_label}[/] ({fmt_model})")

            focus = (workspace.get("dominant_focus") or {})
            focus_label = focus.get("label", "?")
            focus_sal = focus.get("salience", 0)
            mem_count = mem_trace.get("memories_found", 0) if isinstance(mem_trace, dict) else 0
            mem_rel = mem_trace.get("top_relevance", 0) if isinstance(mem_trace, dict) else 0
            table.add_row("Focus:", f"{focus_label} ({focus_sal:.2f})    Memory: {mem_count} matches @{mem_rel:.2f}")

            est = budget.get("estimated_tokens", 0)
            lim = budget.get("token_limit", 4096)
            trimmed = "TRIMMED" if budget.get("was_trimmed") else "ok"
            table.add_row("Budget:", f"{est}/{lim} tokens ({trimmed})")

            if timing:
                ttft = timing.get("ttft_ms", 0)
                rtk = timing.get("reasoning_tokens", 0)
                atk = timing.get("answer_tokens", 0)
                gen = timing.get("total_gen_ms", 0)
                has_cot = bool(result.get("formatted_cot", "")) and result.get("formatted_cot", "") != "CHAPPiE hat nicht darueber nachgedacht und sofort geantwortet."
                if rtk > 0:
                    r_label = f"r:{rtk}tk"
                elif has_cot:
                    r_label = "r:~tk"
                else:
                    r_label = "r:0tk (kein CoT)"
                table.add_row("Timing:", f"TTFT:{ttft}ms  {r_label}  a:{atk}tk  gen:{gen}ms  total:{proc_time:.0f}ms")

            if rep_events:
                parts = []
                for key, val in sorted(rep_events.items()):
                    parts.append(f"[bold red]{key}[/]")
                table.add_row("Repetition:", ", ".join(parts))

            causal_chain = " → ".join(c.get("phase", "?") for c in (causal or [])[:5])
            if causal_chain:
                table.add_row("Trace:", causal_chain)

            debug_entries = result.get("debug_entries", [])
            if debug_entries:
                table.add_row("Debug:", f"[dim]{len(debug_entries)} entries[/]")

            console.print(Panel(table, title=f"[bold]CHAPPiE Report[/]  [dim]{proc_time:.0f}ms · {provider}/{model}[/]", border_style="blue"))
        else:
            print(f"{Colors.DEBUG}{'─' * 60}")
            print(f"  [INTENT]  {intent} ({confidence:.2f}) | Tools: {', '.join(tools) or 'none'}")
            for name in EMOTION_NAMES:
                b = emotion_before.get(name, 0)
                a = emotion_after.get(name, 0)
                d = a - b
                if d != 0:
                    print(f"  [EMO]     {name}: {b} → {a} ({'+' if d > 0 else ''}{d})")
            dom = steering.get("dominant_vector", "neutral")
            print(f"  [STEER]   {prompt_mode} | {dom} ({steering.get('dominant_strength', 0):.2f})")
            print(f"  [TONE]    {tone.get('tone', '?')}")
            fmt_source = result.get("formatting_source", "local_fallback")
            fmt_failed = result.get("formatting_failed", False)
            if fmt_failed:
                fmt_label = "LOCAL (Groq-API fehlgeschlagen)"
                print(f"  {Colors.ERROR}[FORMAT]  {fmt_label} ({result.get('formatting_model', '?')}){Colors.RESET}")
            else:
                fmt_label = "GROQ" if fmt_source == "groq" else "LOCAL"
                print(f"  [FORMAT]  {fmt_label} ({result.get('formatting_model', '?')})")
            if rep_events:
                print(f"  [REP]     {', '.join(rep_events.keys())}")
            print(f"  [TIME]    {proc_time:.0f} ms | {provider}/{model}")
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

        panels: list = []

        panels.append(self._panel_emotions(result))
        panels.append(self._panel_intent_json(result))
        panels.append(self._panel_tools(result))
        panels.append(self._panel_memory(result))
        panels.append(self._panel_workspace(result))
        panels.append(self._panel_steering(result))
        panels.append(self._panel_tone(result))
        panels.append(self._panel_budget(result))
        panels.append(self._panel_timing(result))
        panels.append(self._panel_causal(result))
        panels.append(self._panel_consolidation(result))
        panels.append(self._panel_repetition(result))
        panels.append(self._panel_debug(result))

        proc_time = result.get("processing_time_ms", 0)
        provider = result.get("provider", "?")
        model = result.get("model", "?")

        for panel in panels:
            if panel:
                console.print(panel)

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
            if fmt_failed:
                console.print(f"[red]Format: LOCAL (Groq-API fehlgeschlagen) ({fmt_model})[/]")
            else:
                fmt_color = "green" if fmt_source == "groq" else "yellow"
                fmt_label = "GROQ" if fmt_source == "groq" else "LOCAL"
                console.print(f"[{fmt_color}]Format: {fmt_label} ({fmt_model})[/]")
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
            if fmt_failed:
                print(f"{Colors.ERROR}  [FORMAT] LOCAL (Groq-API fehlgeschlagen) ({metadata.get('formatting_model', '?')}){Colors.RESET}")
            else:
                fmt_label = "GROQ" if fmt_source == "groq" else "LOCAL"
                print(f"  [FORMAT]  {fmt_label} ({metadata.get('formatting_model', '?')})")

    # ── full report panels ────────────────────────────────────────

    @staticmethod
    def _panel_emotions(result: dict) -> Optional[Panel]:
        before = result.get("emotions_before", {})
        after = result.get("emotions", {})
        if not before or not after:
            return None
        lines = []
        for name in EMOTION_NAMES:
            b = before.get(name, 0)
            a = after.get(name, 0)
            d = a - b
            if d == 0:
                continue
            sign = "[green]+[/]" if d > 0 else "[red]-[/]"
            lines.append(f"  {name:>12}: {b:>3} → [bold]{a:>3}[/]  ({sign}{abs(d)})")
        if not lines:
            lines.append("  (keine Aenderungen)")
        return Panel("\n".join(lines), title="[bold yellow]Emotionen[/]", border_style="yellow")

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
        s = result.get("emotion_steering", {})
        mode = result.get("prompt_emotion_mode", "?")
        if not s:
            return None
        lines = [
            f"  Mode:      {mode}",
            f"  Aktiv:     {'JA' if s.get('steering_active') else 'NEIN'}",
            f"  Dominant:  {s.get('dominant_vector', 'neutral')} ({s.get('dominant_strength', 0):.2f})",
        ]
        for v in s.get("active_vectors", [])[:5]:
            if isinstance(v, dict):
                lines.append(f"  Vector:    {v.get('name', '?')} alpha={v.get('alpha', 0):.2f}")
        for m in s.get("composite_modes", [])[:3]:
            if isinstance(m, dict):
                lines.append(f"  Composite: {m.get('name', '?')} ({m.get('strength', 0):.2f})")
        return Panel("\n".join(lines), title="[bold red]Steering Report[/]", border_style="red")

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
        t = result.get("timing", {})
        proc = result.get("processing_time_ms", 0)
        if not t:
            return Panel(f"  Total: {proc:.0f}ms", title="[bold blue]Timing[/]", border_style="blue")
        lines = [
            f"  TTFT:             {t.get('ttft_ms', 0)}ms",
            f"  Reasoning:        {t.get('reasoning_tokens', 0)} tk in {t.get('reasoning_time_ms', 0)}ms",
            f"  Answer:           {t.get('answer_tokens', 0)} tk in {t.get('answer_time_ms', 0)}ms",
            f"  Total tokens:     {t.get('total_tokens', 0)}",
            f"  Generation:       {t.get('total_gen_ms', 0)}ms",
            f"  Total processing: {proc:.0f}ms",
        ]
        return Panel("\n".join(lines), title="[bold blue]Timing[/]", border_style="blue")

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
            state = self.emotions.get_state()
            emotions = state.to_dict()
        life = status.get("life_state", {}) or status.get("life_snapshot", {}) or status.get("life", {})

        if HAS_RICH:
            table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
            table.add_column("k", style="dim")
            table.add_column("v")

            mood = "neutral"
            h = emotions.get("happiness", 50)
            s = emotions.get("sadness", 0)
            f = emotions.get("frustration", 0)
            if h > 60:
                mood = "[green]positiv[/]"
            elif s > 40 or f > 50:
                mood = "[red]angespannt[/]"
            table.add_row("Stimmung:", mood)

            for name in EMOTION_NAMES:
                val = emotions.get(name, 0) if isinstance(emotions, dict) else 0
                bar_str = _bar(val, width=15)
                table.add_row(name, f"[{_emo_color(val)}]{bar_str} {val:>3}[/]")

            if life:
                clock = life.get("clock", {})
                goal = life.get("active_goal", {})
                table.add_row("Phase:", clock.get("phase_label", "?"))
                if goal:
                    table.add_row("Ziel:", f"{goal.get('title', '?')} ({goal.get('progress', 0):.0%})")

            table.add_row("Modell:", f"{status.get('model', '?')} | {status.get('provider', '?')}")
            table.add_row("Two-Step:", "AN" if status.get("two_step_enabled") else "AUS")
            console.print(Panel(table, title="[bold]CHAPPiE Status[/]", border_style="cyan"))
        else:
            print(f"\n{Colors.EMOTION}{'═' * 50}")
            print("  CHAPPiE Status")
            for name in EMOTION_NAMES:
                val = emotions.get(name, 0) if isinstance(emotions, dict) else 0
                print(f"    {name:>12} {_bar(val)} {val:>3}")
            if life:
                print(f"  Phase: {life.get('clock', {}).get('phase_label', '?')}")
            print(f"  Modell: {status.get('model', '?')} | Provider: {status.get('provider', '?')}")
            print(f"{'═' * 50}{Colors.RESET}\n")

    # ── commands ──────────────────────────────────────────────────

    def _handle_command(self, cmd: str) -> bool:
        cmd_lower = cmd.lower().strip()

        if cmd_lower in ("/exit", "/quit"):
            return False

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

        if cmd_lower == "/thinking":
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
            print(f"  vLLM: {'enable_thinking' if s.chain_of_thought else 'kein Reasoning'}")
            print(f"  Ollama: {'think aktiv' if s.chain_of_thought else 'think deaktiviert'}")
            print(f"  Groq: {'CoT-Prompt aktiv' if s.chain_of_thought else 'kein CoT-Prompt'}")
            print(f"\n{Colors.DIM}Syntax: /thinking true | /thinking false{Colors.RESET}\n")
            return True

        if cmd_lower.startswith("/thinking "):
            _, val = cmd.split(maxsplit=1)
            val = val.lower().strip()
            if val in ("true", "on", "an", "1", "ja", "yes"):
                new_val = True
            elif val in ("false", "off", "aus", "0", "nein", "no"):
                new_val = False
            else:
                _error(f"Ungueltiger Wert: {val}. Nutze: /thinking true | /thinking false")
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
            return True

        if cmd_lower == "/steering":
            if self._use_remote:
                try:
                    base = getattr(getattr(self, "remote", None), "base_url", self.remote_url or "")
                    data = requests.get(f"{base}/emotions/state", timeout=10).json()
                    steering = data.get("steering", {}) if isinstance(data, dict) else {}
                    print(f"\n{Colors.STEER}Steering (remote): {steering.get('dominant_vector', '?')} ({steering.get('dominant_strength', 0):.2f}){Colors.RESET}\n")
                except Exception:
                    _log("STEERING", "Remote-Status nicht abrufbar", Colors.WARN)
                return True
            report = self.steering.build_debug_report(self.emotions.get_state().to_dict())
            if HAS_RICH:
                table = Table(box=box.SIMPLE, show_header=False)
                table.add_column("k", style="bold red")
                table.add_column("v")
                table.add_row("Modus:", report.get("mode", "?"))
                table.add_row("Aktiv:", "JA" if report.get("steering_active") else "NEIN")
                table.add_row("Dominant:", f"{report.get('dominant_vector', 'neutral')} ({report.get('dominant_strength', 0):.2f})")
                table.add_row("Vektoren:", ", ".join(v.get("name", "?") for v in report.get("base_vectors", [])[:5]))
                console.print(Panel(table, title="[bold red]Steering Report[/]", border_style="red"))
            else:
                print(f"\n{Colors.STEER}Steering: {report.get('dominant_vector', '?')} ({report.get('dominant_strength', 0):.2f}){Colors.RESET}\n")
            return True

        if cmd_lower.startswith("/emotion"):
            parts = cmd.split()
            # /emotion ohne Argumente: Status + Hilfe anzeigen
            if len(parts) == 1:
                state = self.emotions.get_state() if not self._use_remote else None
                if state:
                    _log("EMOTION", "Aktuelle Emotions-Werte:", Colors.EMOTION)
                    for name in EMOTION_NAMES:
                        val = getattr(state, name, 0)
                        bar_st = _bar(val, width=15)
                        print(f"  {name:>12} [{Colors.AI}{bar_st}{Colors.RESET}] {val}")
                else:
                    try:
                        r = requests.get(f"{self.remote_url}/emotions/state", timeout=5)
                        data = r.json().get("emotions", {})
                        _log("EMOTION", "Aktuelle Emotions-Werte:", Colors.EMOTION)
                        for name in EMOTION_NAMES:
                            val = data.get(name, "?")
                            print(f"  {name:>12}  {val}")
                    except Exception:
                        _log("EMOTION", "Remote-Status nicht abrufbar", Colors.WARN)
                print(f"\n{Colors.EMOTION}Syntax: /emotion <name> [+/-]<0-100>{Colors.RESET}")
                print("  Beispiel: /emotion happiness +10  (erhoeht um 10)")
                print("  Beispiel: /emotion sadness -5     (senkt um 5)")
                print("  Beispiel: /emotion energy 50      (setzt absolut)")
                return True

            if len(parts) < 2:
                _log("EMOTION", "Nutze: /emotion <name> [+/-]<0-100>", Colors.EMOTION)
                return True

            _, emotion, *rest = parts
            valid = set(EMOTION_NAMES)
            if emotion not in valid:
                _error(f"Unbekannte Emotion: {emotion}")
                return True

            if not rest:
                _log("EMOTION", f"Nutze: /emotion {emotion} [+/-]<0-100>", Colors.EMOTION)
                return True

            val_str = rest[0]
            is_delta = val_str.startswith("+") or val_str.startswith("-")
            try:
                parsed = int(val_str)
            except ValueError:
                _error(f"Ungueltiger Wert: {val_str}")
                return True

            # Aktuellen Wert holen
            if self._use_remote:
                try:
                    r = requests.get(f"{self.remote_url}/emotions/state", timeout=5)
                    current = r.json().get("emotions", {}).get(emotion, 50)
                except Exception:
                    _error("Remote-Status nicht abrufbar")
                    return True
            else:
                state = self.emotions.get_state()
                current = getattr(state, emotion, 50)

            # Zielwert berechnen
            if is_delta:
                target = current + parsed
            else:
                target = parsed

            # Clamping
            clamped = max(0, min(100, target))
            if target != clamped:
                direction = "Maximum" if target > 100 else "Minimum"
                overflow = abs(target - clamped)
                _warn(f"{emotion}: {current} {'+' if parsed > 0 else ''}{parsed} → {clamped} ({direction} erreicht, um {overflow} {'reduziert' if target > 100 else 'erhoeht'})")
            else:
                delta_str = f" {'+' if parsed > 0 else ''}{parsed}" if is_delta else ""
                _success(f"{emotion}: {current}{delta_str} → {clamped}")

            # Anwenden
            if self._use_remote:
                try:
                    requests.post(f"{self.remote_url}/emotions/state", json={emotion: clamped}, timeout=5)
                except Exception as e:
                    _error(f"Remote-Fehler: {e}")
            else:
                self.emotions.set_emotion(emotion, clamped)
            return True

        if cmd_lower == "/resetemotions":
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
                    print(f"\n{Colors.MEMORY}{output}{Colors.RESET}\n")
                else:
                    _error(output or "Sleep fehlgeschlagen")
                return True
            from api.services.command_service import execute_slash_command as _exec_sleep
            result = _exec_sleep("/sleep", self.backend)
            self.last_result = result
            print(f"\n{Colors.MEMORY}{result.get('response_text', '')}{Colors.RESET}\n")
            return True

        if cmd_lower == "/memory" or cmd_lower.startswith("/memory "):
            query = cmd.split(maxsplit=1)[1] if len(cmd.split(maxsplit=1)) > 1 else ""
            if self._use_remote:
                try:
                    if query:
                        from urllib.parse import quote
                        data = requests.get(f"{self.remote_url}/memories?q={quote(query)}&limit=10", timeout=10).json()
                        items = data.get("items", [])
                        if not items:
                            _log("LTM", "Keine Erinnerungen gefunden", Colors.MEMORY)
                        else:
                            print(f"\n{Colors.MEMORY}Erinnerungen ({len(items)}):")
                            for it in items[:10]:
                                print(f"  [{it.get('label', '?')}] {str(it.get('content', ''))[:100]}")
                            print(Colors.RESET)
                    else:
                        data = requests.get(f"{self.remote_url}/memories/short-term", timeout=10).json()
                        items = data.get("items", [])
                        if not items:
                            _log("STM", "Keine Eintraege im Kurzzeitgedaechtnis", Colors.MEMORY)
                        else:
                            print(f"\n{Colors.MEMORY}Kurzzeitgedaechtnis ({len(items)} Eintraege):")
                            for e in items[:15]:
                                print(f"  [{e.get('category', '?')}] {str(e.get('content', ''))[:80]}")
                            print(Colors.RESET)
                except Exception as e:
                    _error(f"Memory-Abfrage fehlgeschlagen: {e}")
                return True
            if query:
                try:
                    results = self.memory.search_memory(query, top_k=10)
                    if not results:
                        _log("LTM", "Keine Erinnerungen gefunden", Colors.MEMORY)
                    else:
                        print(f"\n{Colors.MEMORY}Erinnerungen ({len(results)}):")
                        for e in results[:10]:
                            print(f"  [{getattr(e, 'label', '?')}] {str(getattr(e, 'content', ''))[:100]}")
                        print(Colors.RESET)
                except Exception as e:
                    _error(f"LTM-Suche fehlgeschlagen: {e}")
                return True
            entries = self.short_term.get_active_entries()
            if not entries:
                _log("STM", "Keine Eintraege im Kurzzeitgedaechtnis", Colors.MEMORY)
            else:
                print(f"\n{Colors.MEMORY}Kurzzeitgedaechtnis ({len(entries)} Eintraege):")
                for e in entries[:15]:
                    print(f"  [{e.category}] {e.content[:80]}{'...' if len(e.content) > 80 else ''}")
                print(Colors.RESET)
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
                    data = requests.get(f"{self.remote_url}/sessions", timeout=10).json()
                    sessions = data if isinstance(data, list) else data.get("sessions", data)
                    print(f"\n{Colors.AI}Sessions ({len(sessions) if isinstance(sessions, list) else '?'}):")
                    for s in (sessions if isinstance(sessions, list) else [])[:20]:
                        mark = "*" if s.get("id") == self.session_id else " "
                        print(f" {mark} {s.get('id', '?')}  {s.get('title', '')}  ({len(s.get('messages', []))} Nachrichten)")
                    print()
                except Exception as e:
                    _error(f"Sessions konnten nicht geladen werden: {e}")
                return True
            try:
                sessions = self.backend.chat_manager.list_sessions()
                print(f"\n{Colors.AI}Sessions ({len(sessions)}):")
                for s in sessions[:20]:
                    mark = "*" if s.get("id") == self.session_id else " "
                    print(f" {mark} {s.get('id', '?')}  {s.get('title', '')}")
                print()
            except Exception as e:
                _error(f"Sessions konnten nicht geladen werden: {e}")
            return True

        if cmd_lower.startswith("/session "):
            target = cmd.split(maxsplit=1)[1].strip()
            if self._use_remote:
                try:
                    data = requests.get(f"{self.remote_url}/sessions/{target}", timeout=10).json()
                    if isinstance(data, dict) and data.get("id"):
                        self.session_id = data["id"]
                        self.remote.session_id = data["id"]
                        self.history = list(data.get("messages", []))
                        _success(f"Session gewechselt: {self.session_id}")
                    else:
                        _error("Session nicht gefunden")
                except Exception as e:
                    _error(f"Session-Wechsel fehlgeschlagen: {e}")
                return True
            try:
                session = self.backend.chat_manager.load_session(target)
                self.backend.chat_manager.set_active_session(target)
                self.session_id = target
                self.history = list(session.get("messages", []))
                _success(f"Session gewechselt: {target}")
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
                print(f"\n{Colors.MEMORY}{result}{Colors.RESET}\n")
                return True

        if self.backend:
            from api.services.command_service import execute_slash_command as _exec_fallback
            try:
                cmd_result = _exec_fallback(backend_cmd, self.backend)
                replacement = cmd_result.get("replacement_session_id")
                if replacement:
                    self.session_id = replacement
                    self.backend.chat_manager.set_active_session(replacement)
                output = cmd_result.get("response_text", "")
                if output and output != f"Unbekannter Command: {backend_cmd}":
                    print(f"\n{Colors.MEMORY}{output}{Colors.RESET}\n")
                    self.last_result = cmd_result
                    return True
            except Exception:
                pass
            result = self.backend.handle_command(backend_cmd)
            if not result.startswith("Unbekannter Command:"):
                print(f"\n{Colors.MEMORY}{result}{Colors.RESET}\n")
                return True

        _warn(f"Unbekannter Befehl: {cmd}")
        print("  Tippe /help fuer alle Befehle")
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
            "Weitere: /stats /think /deep think /life /growth /world /habits ... wie in der Web-UI"[:total],
            "Tipp: /emotion <name> [+/-]<0-100>, z.B. /emotion happiness +10"[:total],
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
  ██████╗ ██████╗  █████╗ ██╗███╗   ██╗
  ██╔══██╗██╔══██╗██╔══██╗██║████╗  ██║
  ██████╔╝██████╔╝███████║██║██╔██╗ ██║
  ██╔══██╗██╔══██╗██╔══██║██║██║╚██╗██║
  ██████╔╝██║  ██║██║  ██║██║██║ ╚████║
  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝
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
                    real_stdout.write(self._input_prompt())
                    real_stdout.flush()
                    if self._out_capture is not None:
                        self._out_capture.main_capturing = True
                    try:
                        user_input = input("")
                    finally:
                        if self._out_capture is not None:
                            self._out_capture.main_capturing = False
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
    parser = argparse.ArgumentParser(description="CHAPPiE Terminal Interface v16.8.7")
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
