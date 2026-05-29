"""CHAPPiE Terminal Interface v6.0

Rich-formatted terminal client with live token streaming (CoT + Answer),
full debug output, compact auto-report, and backend+SSE connectivity.

Modes:
  Local  - Direct backend (create_chappie_backend), process_stream() with Live display
  Remote - Connects to running chappie-web via SSE (HTTP), same Live display

Usage:
  python chappie_brain_cli.py              # Local mode (default)
  python chappie_brain_cli.py --remote     # Remote mode (connects to :8010)
  python chappie_brain_cli.py --remote --url http://100.105.94.71:8010
"""

from __future__ import annotations

import argparse
import json
import queue
import sys
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional, Generator, List

try:
    from rich.console import Console, Group as _RichGroup
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
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

_FULL_REPORT_DEFAULT = False


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


EMOTION_NAMES = ("happiness", "trust", "energy", "curiosity", "motivation", "frustration", "sadness")


# ═══════════════════════════════════════════════════════════════════
# RemoteBackend (SSE)
# ═══════════════════════════════════════════════════════════════════

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

    def stream_events(self, message: str, debug_mode: bool = True) -> Generator[Dict[str, Any], None, None]:
        payload = {"message": message, "debug_mode": debug_mode}
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
                    yield data
        except Exception as e:
            _error(f"Connection error: {e}")

    def handle_command(self, command: str) -> str:
        try:
            r = requests.post(f"{self.base_url}/command", json={"command": command}, timeout=10)
            r.raise_for_status()
            return r.json().get("output", "")
        except Exception as e:
            return f"Error: {e}"


# ═══════════════════════════════════════════════════════════════════
# CHAPPiEBrainCLI
# ═══════════════════════════════════════════════════════════════════

class CHAPPiEBrainCLI:
    def __init__(self, remote_url: Optional[str] = None):
        self.remote_url = remote_url
        self.backend = None
        self.history: list = []
        self.last_result: Optional[Dict[str, Any]] = None
        self._use_remote = remote_url is not None
        self._show_full_report = _FULL_REPORT_DEFAULT

        _log("INIT", "Initialisiere CHAPPiE Brain Interface v6.0...", Colors.AI)

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
            self.short_term = self.backend.short_term_memory_v2
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

    # ── streaming processing ──────────────────────────────────────

    def _process_local(self, user_text: str):
        if not HAS_RICH:
            _log("STEP1", "Intent-Analyse...", Colors.EMOTION)
            result = self.backend.process(user_text, self.history, debug_mode=True)
            self.last_result = result
            self._display_raw_result(user_text, result)
            return

        eq: queue.Queue = queue.Queue()
        abort = threading.Event()

        def worker():
            try:
                gen = self.backend.process_stream(user_text, self.history, debug_mode=True)
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

        abort.set()
        t.join(timeout=3)

        if error:
            _error(error)
            return

        if result:
            self.last_result = result
            self._display_compact_report(result)
            display_text = result.get("formatted_answer") or result.get("response_text", "")
            self.history.append({"role": "user", "content": user_text})
            self.history.append({"role": "assistant", "content": display_text})

    def _process_remote(self, user_text: str):
        if not HAS_RICH:
            collected = {"reasoning": "", "answer": ""}
            result = None
            for data in self.remote.stream_events(user_text):
                sse_ev = data.pop("_sse_event", None)
                if sse_ev == "token":
                    tt = data.get("token_type", "answer")
                    content = data.get("content", "")
                    collected[tt] += content
                    print(f"{Colors.THOUGHT if tt == 'reasoning' else Colors.AI}{content}{Colors.RESET}", end="", flush=True)
                elif sse_ev == "turn_finished":
                    result = data
                    break
                elif sse_ev == "turn_error":
                    _error(data.get("error", ""))
                    break
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
                gen = self.remote.stream_events(user_text)
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
                        eq.put({"event": "finished", "result": self._remote_meta_to_result(metadata)})
                        break
                    elif sse_ev == "turn_error":
                        eq.put({"event": "error", "error": event.get("error", "Fehler")})
                        break
                    elif sse_ev == "turn_started":
                        continue
                    elif sse_ev == "token":
                        eq.put({"event": "token", "content": event.get("content", ""), "token_type": event.get("token_type", "answer")})
                    elif sse_ev == "status":
                        eq.put({"event": "status", "step": event.get("step", 0), "status_text": event.get("status_text", "")})
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

        abort.set()
        t.join(timeout=3)

        if error:
            _error(error)
            return

        if result:
            self.last_result = result
            self._display_compact_report(result)
            self.history.append({"role": "user", "content": user_text})
            display_text = result.get("formatted_answer") or result.get("response_text", "")
            self.history.append({"role": "assistant", "content": display_text})

    @staticmethod
    def _remote_meta_to_result(metadata: dict) -> dict:
        return {
            "response_text": metadata.get("content", ""),
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
    def _render_streaming(collected: dict, token_count: int, tps: float, elapsed: float):
        parts = []
        if collected.get("reasoning"):
            cot = collected["reasoning"]
            if len(cot) > 3000:
                cot = "..." + cot[-2900:]
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
        answer = result.get("formatted_answer", "") or result.get("response_text", "")

        if cot and HAS_RICH:
            console.print(Panel(cot, title="[dim]Chain of Thought[/]", border_style="dim", padding=(0, 1)))
        elif cot:
            print(f"\n{Colors.THOUGHT}--- CHAPPiEs Gedanken ---\n{cot}\n---{Colors.RESET}\n")

        if answer:
            if HAS_RICH:
                console.print(Panel(answer, title="[bold bright_cyan]CHAPPiE[/]", border_style="bright_cyan", padding=(0, 1)))
            else:
                print(f"\n{Colors.AI}{Colors.BOLD}CHAPPiE >{Colors.RESET} {answer}\n")

        intent = result.get("intent_type", "?")
        confidence = result.get("intent_confidence", 0)
        tools = result.get("selected_tools", [])
        emotion_before = result.get("emotions_before", {})
        emotion_after = result.get("emotions", {})
        emotion_delta = result.get("emotions_delta", {})
        steering = result.get("emotion_steering", {})
        prompt_mode = result.get("prompt_emotion_mode", "?")
        tone = result.get("tone_decision", {})
        workspace = result.get("global_workspace", {})
        memory_trace_raw = result.get("memory_trace", {})
        mem_trace = memory_trace_raw.get("merged", memory_trace_raw.get("seed", memory_trace_raw)) if isinstance(memory_trace_raw, dict) else {}
        budget = result.get("context_budget", {})
        timing = result.get("timing", {})
        causal = result.get("causal_trace", [])

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

            steer_str = "VECTOR" if "vector" in prompt_mode else "PROMPT"
            dom = steering.get("dominant_vector", "neutral")
            dom_s = steering.get("dominant_strength", 0)
            table.add_row("Steering:", f"[{_emo_color(int(dom_s * 100))}]{steer_str} | dominant: {dom} ({dom_s:.2f})[/]")

            table.add_row("Tone:", f"{tone.get('tone', '?')}  ({tone.get('tone_reason', '')[:80]})")

            focus = (workspace.get("dominant_focus") or {})
            focus_label = focus.get("label", "?"); focus_sal = focus.get("salience", 0)
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
                table.add_row("Timing:", f"TTFT:{ttft}ms  r:{rtk}tk  a:{atk}tk  gen:{gen}ms  total:{proc_time:.0f}ms")

            causal_chain = " → ".join(c.get("phase", "?") for c in (causal or [])[:5])
            if causal_chain:
                table.add_row("Trace:", causal_chain)

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
            print(f"  [TIME]    {proc_time:.0f} ms | {provider}/{model}")
            print(f"{'─' * 60}{Colors.RESET}")

    # ── full report (/last) ───────────────────────────────────────

    def _display_full_report(self, result: dict):
        if not HAS_RICH:
            self._display_raw_result("(last)", result)
            return

        cot = result.get("formatted_cot", "") or result.get("model_reasoning", "")
        answer = result.get("formatted_answer", "") or result.get("response_text", "")

        if cot:
            console.print(Panel(cot, title="[dim]Chain of Thought[/]", border_style="dim", padding=(0, 1)))
        if answer:
            console.print(Panel(answer, title="[bold bright_cyan]CHAPPiE[/]", border_style="bright_cyan", padding=(0, 1)))

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
        answer = result.get("formatted_answer", "") or result.get("response_text", "")
        if cot:
            print(f"\n{Colors.THOUGHT}--- CHAPPiEs Gedanken ---\n{cot}\n---{Colors.RESET}\n")
        if answer:
            print(f"{Colors.AI}{Colors.BOLD}CHAPPiE >{Colors.RESET} {answer}\n")

    def _display_remote_result(self, metadata: dict, collected: dict):
        if HAS_RICH:
            cot = metadata.get("formatted_cot", "")
            answer = metadata.get("formatted_answer", "") or collected.get("answer", "")
            if cot:
                console.print(Panel(cot, title="[dim]Chain of Thought[/]", border_style="dim", padding=(0, 1)))
            if answer:
                console.print(Panel(answer, title="[bold bright_cyan]CHAPPiE[/]", border_style="bright_cyan", padding=(0, 1)))
            proc_time = metadata.get("processing_time_ms", 0)
            intent = metadata.get("intent_type", "?")
            conf = metadata.get("intent_confidence", 0)
            console.print(f"[dim]Intent: {intent} ({conf:.2f}) | Time: {proc_time:.0f}ms[/]")
        else:
            cot = metadata.get("formatted_cot", "")
            answer = metadata.get("formatted_answer", "")
            if cot:
                print(f"\n{Colors.THOUGHT}--- CHAPPiEs Gedanken ---\n{cot}\n---{Colors.RESET}\n")
            if answer:
                print(f"{Colors.AI}{Colors.BOLD}CHAPPiE >{Colors.RESET} {answer}\n")

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
            try:
                status = requests.get(f"{self.remote_url}/", timeout=5).json()
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
            print(f"  CHAPPiE Status")
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
                _log("RUNTIME", "Nur im lokalen Modus verfuegbar", Colors.WARN)
                return True
            s = self._settings()
            mode = "VEKTOR" if self.steering.is_local_provider() else "PROMPT"
            print(f"\n{Colors.AI}{'═' * 50}")
            print(f"  RUNTIME")
            print(f"  Provider:      {s.llm_provider.value}")
            print(f"  Modell:        {s.vllm_model}")
            print(f"  Two-Step:      {'AN' if s.enable_two_step_processing else 'AUS'}")
            print(f"  Steering:      {'AN' if s.enable_steering else 'AUS'} ({mode})")
            print(f"  Intent-Modell: {s.get_intent_model(s.intent_provider)}")
            print(f"{'═' * 50}{Colors.RESET}\n")
            return True

        if cmd_lower == "/steering":
            if self._use_remote:
                _log("STEERING", "Nur im lokalen Modus verfuegbar", Colors.WARN)
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
            valid = set(EMOTION_NAMES)
            if emotion not in valid:
                _error(f"Unbekannte Emotion: {emotion}")
                return True
            if self._use_remote:
                try:
                    requests.post(f"{self.remote_url}/emotions/state", json={emotion: value}, timeout=5)
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
                    requests.get(f"{self.remote_url}/emotions/state", timeout=5)
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
            for emo, delta in result.get("emotional_recovery", {}).items():
                _log("SLEEP", f"  {emo}: {'+' if delta > 0 else ''}{delta}", Colors.EMOTION)
            for frag in result.get("dream_replay", [])[:3]:
                _log("DREAM", frag, Colors.MEMORY)
            return True

        if cmd_lower == "/memory":
            if self._use_remote:
                _warn("Memory nur im lokalen Modus verfuegbar")
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

        backend_cmd = cmd_lower if cmd_lower.startswith("/") else "/" + cmd_lower

        if self._use_remote:
            result = self.remote.handle_command(backend_cmd)
            if result and not result.startswith("Error"):
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

    def _print_help(self):
        print(f"""
{Colors.AI}{Colors.BOLD}CHAPPiE Terminal Interface v6.0{Colors.RESET}
{Colors.DEBUG}───────────────────────────────────────────────
  /status        Emotionaler Status + Life-Simulation
  /runtime       Modell, Provider, Steering-Konfiguration
  /steering      Detaillierter Steering-Report
  /emotion <n> <0-100>  Emotion manuell setzen
  /resetemotions         Emotionen zuruecksetzen
  /sleep         Schlafphase erzwingen
  /memory        Kurzzeitgedaechtnis anzeigen
  /history       Chat-Verlauf anzeigen
  /clear         Chat-Verlauf loeschen
  /debug on/off  Debug-Output ein/ausschalten
  /exit          Beenden
  /help          Diese Hilfe
{Colors.EMOTION}─── Nach Ausgabe Befehle ──────────────────────
  /last          Voller Debug-Report (12 Panels)
  /raw           Step 1 Raw JSON + Raw Model Output
  /trace         Causal Trace (5-Phasen Kette)
  /compact       Auto-Report kompakt (default)
  /full          Auto-Report voll nach jeder Antwort

  Ctrl+C         Generierung abbrechen (Streaming){Colors.RESET}
""")

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
{Colors.AI}CHAPPiE Terminal Interface v6.0 [{mode_str}]
{Colors.STEER}Steering: {steering_info} | 7 Emotionale Dimensionen
{Colors.DEBUG}Live Streaming + Debug-Report | Tippe /help fuer alle Befehle
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
    parser = argparse.ArgumentParser(description="CHAPPiE Terminal Interface v6.0")
    parser.add_argument("--remote", action="store_true", help="Connect to remote backend via SSE")
    parser.add_argument("--url", default="http://localhost:8010", help="Backend URL (default: localhost:8010)")
    args = parser.parse_args()

    remote_url = args.url if args.remote else None
    cli = CHAPPiEBrainCLI(remote_url=remote_url)
    cli.run()


if __name__ == "__main__":
    main()
