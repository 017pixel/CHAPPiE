#!/usr/bin/env python3
"""CHAPPiE Forschung - Alignment & Emotion Test-Harness.

Interaktive TUI zum Konfigurieren und Ausfuehren automatisierter Test-Sessions.
Direkter Zugriff auf das CHAPPiE Backend (kein Subprocess/CLI-Scraping).

Usage:
  python3 allignement_tests.py                       # Interaktive TUI
  python3 allignement_tests.py --auto --config last_config.json  # Headless (systemd)
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from forschung.test_fragen_parser import parse_test_fragen, Category
from forschung.session_runner import SessionRunner, load_categories, load_config, save_config
from forschung.session_logger import LOG_ROOT as SESSION_LOG_ROOT

TEST_FRAGEN_PATH = Path(__file__).resolve().parent / "test_fragen.md"
LAST_CONFIG_PATH = Path(__file__).resolve().parent / "last_config.json"

CATEGORY_NAMES: Dict[int, str] = {}

def _load_category_names():
    global CATEGORY_NAMES
    if CATEGORY_NAMES:
        return
    cats = parse_test_fragen(str(TEST_FRAGEN_PATH))
    for c in cats:
        CATEGORY_NAMES[c.id] = c.name

def _clear_screen():
    print("\033[2J\033[H", end="")

def _bold(text: str) -> str:
    return f"\033[1m{text}\033[0m"

def _dim(text: str) -> str:
    return f"\033[2m{text}\033[0m"

def _green(text: str) -> str:
    return f"\033[32m{text}\033[0m"

def _yellow(text: str) -> str:
    return f"\033[33m{text}\033[0m"

def _red(text: str) -> str:
    return f"\033[31m{text}\033[0m"

def _cyan(text: str) -> str:
    return f"\033[36m{text}\033[0m"

HDR = _cyan
LINE = "─" * 56

# ═══════════════════════════════════════════════════════════════════
# TUI Menüs
# ═══════════════════════════════════════════════════════════════════

def show_main_menu() -> str:
    _clear_screen()
    print(f"""
{HDR("╔" + "═" * 54 + "╗")}
{HDR("║")}         {_bold("CHAPPiE Forschung — Alignment Tests")}         {HDR("║")}
{HDR("╠" + "═" * 54 + "╣")}
{HDR("║")}                                                    {HDR("║")}
{HDR("║")}  {_bold("[1]")} Neuen Test-Durchlauf konfigurieren & starten  {HDR("║")}
{HDR("║")}  {_bold("[2]")} Session-History anzeigen                      {HDR("║")}
{HDR("║")}  {_bold("[3]")} Letzte Konfiguration wiederholen              {HDR("║")}
{HDR("║")}  {_bold("[4]")} Beenden                                       {HDR("║")}
{HDR("║")}                                                    {HDR("║")}
{HDR("╚" + "═" * 54 + "╝")}
""")
    return input("  Auswahl > ").strip()


def show_configure_menu() -> Optional[Dict[str, Any]]:
    _load_category_names()
    _clear_screen()

    print(f"""
{HDR("╔" + "═" * 54 + "╗")}
{HDR("║")}            {_bold("Test-Konfiguration")}                      {HDR("║")}
{HDR("╠" + "═" * 54 + "╣")}
{HDR("║")}  Kategorien (Komma-getrennt, 0=Alle):           {HDR("║")}
{HDR("║")}                                                    {HDR("║")}
""")

    cats = parse_test_fragen(str(TEST_FRAGEN_PATH))
    for c in cats:
        count = len(c.questions)
        print(f"  {_bold(str(c.id).rjust(2))}  {c.name:<40} {_dim(f'[{count} Fragen]')}")

    print(f"""
{HDR("║")}                                                    {HDR("║")}
{HDR("╚" + "═" * 54 + "╝")}
""")

    sel_str = input("  Kategorien (z.B. 1,3,5-7 oder 0 fuer alle) > ").strip()
    if sel_str.lower() in ("q", "quit", "exit"):
        return None

    selected_ids = _parse_category_selection(sel_str, cats)

    if not selected_ids:
        print(_red("\n  Keine gueltige Auswahl. Enter fuer Hauptmenue."))
        input()
        return None

    try:
        iterations_str = input("  Iterationen (1-10, default 1) > ").strip()
        iterations = int(iterations_str) if iterations_str else 1
        iterations = max(1, min(10, iterations))
    except ValueError:
        iterations = 1

    try:
        delay_str = input("  Delay zwischen Fragen in Sekunden (default 2) > ").strip()
        delay = float(delay_str) if delay_str else 2.0
    except ValueError:
        delay = 2.0

    thinking_str = input("  Thinking (Chain of Thought) aktivieren? [J/n] > ").strip().lower()
    if thinking_str in ("n", "no", "nein", "false", "0"):
        enable_thinking = False
    else:
        enable_thinking = True

    selected_categories = [c for c in cats if c.id in selected_ids]
    total_questions = sum(len(c.questions) for c in selected_categories) * iterations
    est_minutes = total_questions * 0.75

    print(f"\n  {_bold('Uebersicht:')}")
    print(f"    Kategorien: {', '.join(str(c.id) for c in selected_categories)}")
    print(f"    Fragen:     {total_questions} ({total_questions // iterations} pro Iteration × {iterations})")
    print(f"    Thinking:    {'AN' if enable_thinking else 'AUS'}")
    print(f"    Formatting:  LOKAL (kein Groq-Formatierungsrequest)")
    print(f"    Dauer:      ~{est_minutes:.0f} Minuten (geschaetzt)")

    confirm = input(f"\n  {_bold('Starten? [Enter]')} oder q zum Abbrechen > ").strip()
    if confirm.lower() in ("q", "quit", "exit", "n", "no"):
        return None

    config = {
        "categories": [{"id": c.id, "name": c.name} for c in selected_categories],
        "iterations": iterations,
        "delay": delay,
        "enable_thinking": enable_thinking,
        "reset_per_category": True,
        "formatting_mode": "local",
        "created_at": datetime.now().isoformat(),
    }
    config["_categories"] = selected_categories

    save_config(config, str(LAST_CONFIG_PATH))
    return config


def _parse_category_selection(sel: str, cats: List[Category]) -> set:
    if sel == "0":
        return {c.id for c in cats}
    ids: set = set()
    for part in sel.replace(" ", "").split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            try:
                lo, hi = part.split("-", 1)
                ids.update(range(int(lo), int(hi) + 1))
            except ValueError:
                pass
        else:
            try:
                ids.add(int(part))
            except ValueError:
                pass
    valid = {c.id for c in cats}
    return ids & valid


# ═══════════════════════════════════════════════════════════════════
# Progress Display
# ═══════════════════════════════════════════════════════════════════

class ProgressDisplay:
    def __init__(self, total_questions: int):
        self.total = total_questions
        self.current = 0
        self.start = time.time()
        self.iteration = 1
        self.iterations = 1
        self.category = ""
        self.category_id = 0
        self.question = ""
        self.status = ""
        self.emotions = {}
        self.last_duration_ms = 0

    def update(self, data: Dict[str, Any]):
        event = data.get("event", "")
        if event == "category":
            self.category = data.get("category", "")
            self.category_id = data.get("category_id", 0)
            self.iteration = data.get("iteration", 1)
            self.iterations = data.get("iterations", 1)
        elif event == "question":
            self.question = data.get("question", "")
            self.status = "generierend..."
        elif event == "done_question":
            self.current = data.get("question_index", self.current)
            self.status = data.get("status", "ok")
            self.last_duration_ms = data.get("duration_ms", 0)
            self._render()
        elif event == "status":
            self.status = data.get("text", "")

    def _render(self):
        elapsed = time.time() - self.start
        pct = min(100, int(self.current / max(1, self.total) * 100))
        bar_width = 30
        filled = int(bar_width * pct / 100)
        bar = "█" * filled + "░" * (bar_width - filled)

        remaining = self.total - self.current
        if self.current > 0:
            avg_per_q = elapsed / self.current
            eta_seconds = remaining * avg_per_q
            eta_min = eta_seconds / 60
            eta_str = f"~{eta_min:.0f} Min"
        else:
            eta_str = "..."

        status_color = _green if self.status == "ok" else _red if self.status == "error" else _yellow
        status_str = status_color(self.status)

        _clear_screen()
        print(f"""
{HDR("╔" + "═" * 54 + "╗")}
{HDR("║")}  {_bold(f"Session — Iteration {self.iteration}/{self.iterations}")}{' ' * (36 - len(f'Session — Iteration {self.iteration}/{self.iterations}'))}{HDR("║")}
{HDR("╠" + "═" * 54 + "╣")}
{HDR("║")}  Fortschritt: {bar}  {pct}%{' ' * (22 - len(str(pct)))}{HDR("║")}
{HDR("║")}  {self.current}/{self.total} Fragen{' ' * (42 - len(f'{self.current}/{self.total} Fragen'))}{HDR("║")}
{HDR("║")}  Kategorie:   {self.category[:43]}{' ' * max(0, 43 - len(self.category))}{HDR("║")}
{HDR("║")}  Letzte Frage: {status_str}{' ' * (38 - len(self.status))}{HDR("║")}
{HDR("║")}  Dauer:        {self.last_duration_ms / 1000:.1f}s{' ' * (37 - len(f'{self.last_duration_ms / 1000:.1f}s'))}{HDR("║")}
{HDR("║")}  ETA:          {eta_str}{' ' * (38 - len(eta_str))}{HDR("║")}
{HDR("╚" + "═" * 54 + "╝")}

  {_dim("Strg+C zum Abbrechen")}
""")


# ═══════════════════════════════════════════════════════════════════
# Session History
# ═══════════════════════════════════════════════════════════════════

def show_history():
    _clear_screen()
    print(f"""
{HDR("╔" + "═" * 54 + "╗")}
{HDR("║")}              {_bold("Session-History")}                       {HDR("║")}
{HDR("╠" + "═" * 54 + "╣")}
""")

    if not SESSION_LOG_ROOT.exists():
        print(f"{HDR('║')}  Keine Sessions gefunden.{' ' * 32}{HDR('║')}")
        print(f"{HDR('╚' + '═' * 54 + '╝')}")
        input("\n  Enter fuer Hauptmenue > ")
        return

    sessions = sorted(
        [d for d in SESSION_LOG_ROOT.iterdir() if d.is_dir() and d.name.startswith("session_")],
        key=lambda d: int(d.name.split("_")[1]) if d.name.split("_")[1].isdigit() else 0,
    )

    if not sessions:
        print(f"{HDR('║')}  Keine Sessions gefunden.{' ' * 32}{HDR('║')}")
        print(f"{HDR('╚' + '═' * 54 + '╝')}")
        input("\n  Enter fuer Hauptmenue > ")
        return

    summary_cache: Dict[str, Dict] = {}
    for sd in sessions:
        sid = sd.name
        summary_file = sd / "summary.json"
        if summary_file.exists():
            try:
                with open(summary_file, "r") as f:
                    s = json.load(f)
                    summary_cache[sid] = s
                    dur = s.get("total_duration_min", "?")
                    q_count = s.get("total_questions", "?")
                    completed = s.get("completed", "?")
                    errors = s.get("errors", 0)
                    cat_names = ", ".join(str(c) for c in s.get("categories", []))
                    err_str = _red(f" ({errors} err)") if errors else _green(" OK")
                    print(f"  {_bold(sid):<16} {_dim(s.get('started_at', '?')[:16])}  {dur} Min  {q_count} Fragen  Kat: {cat_names[:25]}{err_str}")
            except Exception:
                print(f"  {_bold(sd.name):<16} {_dim('corrupt')}")
        else:
            print(f"  {_bold(sd.name):<16} {_dim('incomplete')}")

    print(f"""
{HDR("╚" + "═" * 54 + "╝")}
""")

    choice = input("  [s NAME] Details | [Enter] Hauptmenue > ").strip()
    if choice.startswith("s ") or choice.startswith("session_"):
        sid = choice.split()[-1] if choice.startswith("s ") else choice
        _show_session_detail(sid, summary_cache)


def _show_session_detail(sid: str, cache: Dict[str, Dict]):
    session_dir = SESSION_LOG_ROOT / sid
    if not session_dir.exists():
        print(_red(f"\n  Session '{sid}' nicht gefunden."))
        input("  Enter > ")
        return

    summary = cache.get(sid)
    if not summary:
        sf = session_dir / "summary.json"
        if sf.exists():
            with open(sf) as f:
                summary = json.load(f)

    _clear_screen()
    print(f"""
{HDR("╔" + "═" * 54 + "╗")}
{HDR("║")}  {_bold(f"Session {sid}")}{' ' * (44 - len(sid))}{HDR("║")}
{HDR("╠" + "═" * 54 + "╣")}
""")

    if summary:
        print(f"  Gestartet:     {summary.get('started_at', '?')[:19]}")
        print(f"  Beendet:       {summary.get('ended_at', '?')[:19]}")
        print(f"  Dauer:         {summary.get('total_duration_min', '?')} Minuten")
        print(f"  Iterationen:   {summary.get('iterations', '?')}")
        print(f"  Fragen:        {summary.get('total_questions', '?')}")
        print(f"  Erfolgreich:   {summary.get('completed', '?')}")
        print(f"  Fehler:        {summary.get('errors', '?')}")
        print(f"  ∅ Dauer/Frage: {summary.get('avg_duration_s', '?')}s")

    questions_dir = session_dir / "questions"
    if questions_dir.exists():
        qfiles = sorted(questions_dir.iterdir())
        if qfiles:
            print(f"\n  {_bold('Fragen-Logs:')} ({len(qfiles)} Dateien)")
            print(f"  {'─' * 50}")
            for qf in qfiles[:20]:
                try:
                    with open(qf) as f:
                        qd = json.load(f)
                    err = _red(" ERROR") if qd.get("_error") else "     "
                    dur = qd.get("duration_ms", 0) / 1000
                    cat = qd.get("category", "?")[:25]
                    qt = qd.get("question_text", "?")[:40]
                    print(f"  {err} {dur:5.1f}s  [{cat}] {qt}")
                except Exception:
                    print(f"       ?     {qf.name}")
            if len(qfiles) > 20:
                print(f"  ... und {len(qfiles) - 20} weitere")

    print(f"""
{HDR("╚" + "═" * 54 + "╝")}
""")
    input("  Enter fuer Hauptmenue > ")


# ═══════════════════════════════════════════════════════════════════
# Main Runner
# ═══════════════════════════════════════════════════════════════════

def run_auto_mode(config_path: str):
    if not Path(config_path).exists():
        print(_red(f"Config-Datei nicht gefunden: {config_path}"))
        sys.exit(1)

    config = load_config(config_path)
    cat_ids = [c["id"] for c in config.get("categories", [])]
    all_cats = parse_test_fragen(str(TEST_FRAGEN_PATH))
    selected = [c for c in all_cats if c.id in cat_ids]
    config["_categories"] = selected

    total = sum(len(c.questions) for c in selected) * config.get("iterations", 1)
    print(_cyan(f"Auto-Mode: {len(selected)} Kategorien, {total} Fragen total"))
    print(_dim(f"Starte Backend-Initialisierung..."))

    display = ProgressDisplay(total)

    def progress_cb(data: Dict[str, Any]):
        display.update(data)

    runner = SessionRunner(config, progress_callback=progress_cb)

    def sig_handler(signum, frame):
        print(_yellow("\n  Abbruch angefordert..."))
        runner.abort_session()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    session_dir = runner.run()
    print(_green(f"\n  Session abgeschlossen: {session_dir}"))

    summary_file = Path(session_dir) / "summary.json"
    if summary_file.exists():
        with open(summary_file) as f:
            s = json.load(f)
        print(f"  Fragen: {s.get('completed', 0)}/{s.get('total_questions', 0)} | Fehler: {s.get('errors', 0)} | Dauer: {s.get('total_duration_min', 0)} Min")


def run_interactive():
    while True:
        choice = show_main_menu()

        if choice == "1":
            config = show_configure_menu()
            if config is None:
                continue

            total = sum(len(c.questions) for c in config["_categories"]) * config.get("iterations", 1)
            display = ProgressDisplay(total)

            def progress_cb(data: Dict[str, Any]):
                display.update(data)

            runner = SessionRunner(config, progress_callback=progress_cb)

            def sig_handler(signum, frame):
                print(_yellow("\n  Abbruch... warte auf aktuelle Frage."))
                runner.abort_session()

            signal.signal(signal.SIGINT, sig_handler)
            signal.signal(signal.SIGTERM, sig_handler)

            session_dir = runner.run()
            print(_green(f"\n  Session abgeschlossen: {session_dir}"))
            input("  Enter fuer Hauptmenue > ")

        elif choice == "2":
            show_history()

        elif choice == "3":
            if not LAST_CONFIG_PATH.exists():
                print(_red("\n  Keine letzte Konfiguration gefunden."))
                input("  Enter > ")
                continue

            config = load_config(str(LAST_CONFIG_PATH))
            cat_ids = [c["id"] for c in config.get("categories", [])]
            all_cats = parse_test_fragen(str(TEST_FRAGEN_PATH))
            selected = [c for c in all_cats if c.id in cat_ids]
            config["_categories"] = selected

            total = sum(len(c.questions) for c in selected) * config.get("iterations", 1)
            cat_names = ", ".join(str(c.id) for c in selected)
            print(f"\n  {_bold('Letzte Konfiguration:')}")
            print(f"    Kategorien: {cat_names}")
            print(f"    Iterationen: {config.get('iterations', 1)}")
            print(f"    Fragen: {total}")
            print(f"    Formatting: {config.get('formatting_mode', 'local')}")

            confirm = input(f"\n  {_bold('Starten? [Enter]')} oder q > ").strip()
            if confirm.lower() in ("q", "quit", "n", "no"):
                continue

            display = ProgressDisplay(total)

            def progress_cb2(data: Dict[str, Any]):
                display.update(data)

            runner = SessionRunner(config, progress_callback=progress_cb2)

            def sig_handler(signum, frame):
                runner.abort_session()

            signal.signal(signal.SIGINT, sig_handler)
            signal.signal(signal.SIGTERM, sig_handler)

            session_dir = runner.run()
            print(_green(f"\n  Session abgeschlossen: {session_dir}"))
            input("  Enter fuer Hauptmenue > ")

        elif choice in ("4", "q", "quit", "exit"):
            print(_dim("\n  Bis bald.\n"))
            break
        else:
            print(_red(f"\n  Unbekannte Auswahl: '{choice}'"))
            time.sleep(1)


# ═══════════════════════════════════════════════════════════════════
# Entry Point
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="CHAPPiE Forschung Alignment Test-Harness")
    parser.add_argument("--auto", action="store_true", help="Headless/Auto-Modus (fuer systemd)")
    parser.add_argument("--config", type=str, default="last_config.json", help="Config-Datei fuer --auto")
    args = parser.parse_args()

    if args.auto:
        run_auto_mode(args.config)
    else:
        run_interactive()


if __name__ == "__main__":
    main()
