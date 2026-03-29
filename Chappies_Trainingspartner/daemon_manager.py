"""
Daemon Manager - Training Daemon Control
=========================================
Steuert den Training-Daemon als separaten Prozess.
Ermoeglicht Start/Stop, Status-Snapshot und Log-Abruf aus der Web-UI.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

PROJECT_ROOT = Path(__file__).parent.parent
PID_FILE = PROJECT_ROOT / "training.pid"
LOG_FILE = PROJECT_ROOT / "training_daemon.log"
STATE_FILE = PROJECT_ROOT / "training_state.json"
CONFIG_FILE = PROJECT_ROOT / "training_config.json"

DEFAULT_TRAINING_CONFIG = {
    "persona": "Ein kritischer aber fairer Nutzer",
    "focus_area": "Allgemeines Wissen und Konversation",
    "curriculum": [{"topic": "Allgemeines Wissen und Konversation", "duration_minutes": "infinite"}],
    "timeout_seconds": 60,
    "start_prompt": "Hallo Chappie! Lass uns ein Gespraech fuehren.",
    "provider": "local",
    "model_name": None,
    "sleep_interval_messages": 25,
    "loop_pause_seconds": 0.5,
    "request_pause_seconds": 2.5,
}


@dataclass
class TrainingControlSnapshot:
    running: bool = False
    pid: Optional[int] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    loops: int = 0
    memory_count: int = 0
    errors: int = 0
    dreams: int = 0
    messages_since_dream: int = 0
    focus: Optional[str] = None
    persona: Optional[str] = None
    start_time: Optional[str] = None
    last_activity: Optional[str] = None
    daemon_healthy: bool = False
    diagnostic_messages: list[str] = None
    heartbeat_memory_count: int = 0
    total_exchanges: int = 0
    curriculum: list[Dict[str, Any]] = None
    start_prompt: Optional[str] = None
    sleep_interval_messages: int = 25
    loop_pause_seconds: float = 0.5
    request_pause_seconds: float = 2.5
    current_topic: Optional[str] = None
    current_topic_index: int = 0
    topic_started_at: Optional[str] = None
    topics_completed: int = 0
    status_code: str = "stopped_idle"
    status_label: str = "Gestoppt"
    state_age_minutes: Optional[int] = None
    process_mismatch: bool = False

    def __post_init__(self) -> None:
        if self.diagnostic_messages is None:
            self.diagnostic_messages = []
        if self.curriculum is None:
            self.curriculum = []

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_training_config(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    merged = {**DEFAULT_TRAINING_CONFIG, **(config or {})}
    curriculum = merged.get("curriculum") or []

    normalized_curriculum = []
    for item in curriculum:
        topic = str((item or {}).get("topic", "")).strip()
        duration = (item or {}).get("duration_minutes", "infinite")
        if not topic:
            continue
        normalized_curriculum.append({"topic": topic, "duration_minutes": duration})

    focus = str(merged.get("focus_area") or "").strip()
    if not normalized_curriculum and focus:
        normalized_curriculum = [{"topic": focus, "duration_minutes": "infinite"}]
    if not normalized_curriculum:
        normalized_curriculum = list(DEFAULT_TRAINING_CONFIG["curriculum"])

    merged["curriculum"] = normalized_curriculum
    merged["focus_area"] = focus or normalized_curriculum[0]["topic"]
    merged["sleep_interval_messages"] = max(5, _safe_int(merged.get("sleep_interval_messages", 25), 25))
    merged["timeout_seconds"] = max(10, _safe_int(merged.get("timeout_seconds", 60), 60))
    merged["loop_pause_seconds"] = max(0.0, _safe_float(merged.get("loop_pause_seconds", 0.5), 0.5))
    merged["request_pause_seconds"] = max(0.5, _safe_float(merged.get("request_pause_seconds", 2.5), 2.5))
    return merged


def _read_json(path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if not path.exists():
        return None, None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            return None, f"{path.name} hat kein Objektformat"
        return data, None
    except Exception as exc:
        return None, f"{path.name} unlesbar: {str(exc)[:100]}"


def _write_json_atomic(path: Path, payload: Dict[str, Any]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def _read_pid_from_file() -> Tuple[Optional[int], Optional[str]]:
    if not PID_FILE.exists():
        return None, None
    try:
        raw = PID_FILE.read_text(encoding="utf-8").strip()
        pid = int(raw)
        if pid <= 0:
            _safe_unlink(PID_FILE)
            return None, "PID-Datei enthielt ungueltige PID und wurde bereinigt"
        return pid, None
    except Exception:
        _safe_unlink(PID_FILE)
        return None, "PID-Datei war defekt und wurde bereinigt"


def _process_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            output = (result.stdout or "").strip()
            if not output:
                return False
            return str(pid) in output and "Keine Aufgaben" not in output
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _process_looks_like_training(pid: int) -> bool:
    if pid <= 0:
        return False
    marker = "Chappies_Trainingspartner.training_daemon"
    if os.name == "nt":
        # Best effort auf Windows: wenn kein cmdline-Zugriff moeglich ist, nur Prozess-Existenz verwenden.
        try:
            result = subprocess.run(
                ["wmic", "process", "where", f"ProcessId={pid}", "get", "CommandLine", "/value"],
                capture_output=True,
                text=True,
                timeout=6,
            )
            cmdline = (result.stdout or "").lower()
            if not cmdline.strip():
                return _process_exists(pid)
            return marker.lower() in cmdline
        except Exception:
            return _process_exists(pid)

    proc_cmdline = Path(f"/proc/{pid}/cmdline")
    try:
        if not proc_cmdline.exists():
            return _process_exists(pid)
        cmdline = proc_cmdline.read_text(encoding="utf-8", errors="ignore").replace("\x00", " ").lower()
        if not cmdline.strip():
            return _process_exists(pid)
        return marker.lower() in cmdline
    except Exception:
        return _process_exists(pid)


def _resolve_daemon_pid() -> Tuple[Optional[int], list[str], bool]:
    diagnostics: list[str] = []
    pid, pid_error = _read_pid_from_file()
    if pid_error:
        diagnostics.append(pid_error)
    if pid is None:
        return None, diagnostics, False

    if not _process_exists(pid):
        diagnostics.append(f"Stale PID entdeckt ({pid}) und bereinigt")
        _safe_unlink(PID_FILE)
        return None, diagnostics, False

    if not _process_looks_like_training(pid):
        diagnostics.append(f"PID {pid} gehoert nicht eindeutig zum Training-Daemon")
        _safe_unlink(PID_FILE)
        return None, diagnostics, True

    return pid, diagnostics, False


def _write_pid_file(pid: int) -> None:
    with open(PID_FILE, "w", encoding="utf-8") as handle:
        handle.write(str(pid))


def _parse_timestamp(value: Any) -> Optional[datetime]:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _format_minutes_ago(ts: Optional[datetime]) -> Tuple[Optional[int], Optional[str]]:
    if ts is None:
        return None, None
    minutes = max(0, int((_utc_now() - ts).total_seconds() // 60))
    return minutes, f"vor {minutes} Min."


def load_training_config() -> Dict[str, Any]:
    payload, _ = _read_json(CONFIG_FILE)
    if payload is None:
        return _normalize_training_config()
    return _normalize_training_config(payload)


def save_training_config(config: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_training_config(config)
    _write_json_atomic(CONFIG_FILE, normalized)
    return normalized


def is_daemon_running() -> Optional[int]:
    pid, _diagnostics, _mismatch = _resolve_daemon_pid()
    return pid


def start_daemon(
    focus: str = None,
    new: bool = False,
    config_overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    current_pid = is_daemon_running()
    if current_pid:
        return {
            "success": False,
            "pid": current_pid,
            "message": f"Training laeuft bereits (PID: {current_pid})",
        }

    try:
        daemon_module_root = PROJECT_ROOT / "Chappies_Trainingspartner"
        if not daemon_module_root.exists():
            return {
                "success": False,
                "pid": None,
                "message": "Chappies_Trainingspartner Modul nicht gefunden",
            }

        config = load_training_config()
        if config_overrides:
            config.update(config_overrides)
        if focus:
            config["focus_area"] = focus
            if not config.get("curriculum"):
                config["curriculum"] = [{"topic": focus, "duration_minutes": "infinite"}]
        save_training_config(config)

        if new:
            _safe_unlink(STATE_FILE)

        cmd = [sys.executable, "-m", "Chappies_Trainingspartner.training_daemon"]
        if os.name == "nt":
            detached = 0x00000008
            new_process_group = 0x00000200
            no_window = 0x08000000
            process = subprocess.Popen(
                cmd,
                creationflags=detached | new_process_group | no_window,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
        else:
            process = subprocess.Popen(
                cmd,
                start_new_session=True,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )

        expected_pid = process.pid
        deadline = time.time() + 6.0
        while time.time() < deadline:
            live_pid = is_daemon_running()
            if live_pid:
                return {
                    "success": True,
                    "pid": live_pid,
                    "message": f"Training gestartet (PID: {live_pid})",
                }
            time.sleep(0.25)

        if _process_exists(expected_pid):
            _write_pid_file(expected_pid)
            return {
                "success": True,
                "pid": expected_pid,
                "message": f"Training gestartet, Heartbeat folgt (PID: {expected_pid})",
            }

        return {
            "success": False,
            "pid": None,
            "message": "Training konnte nicht bestaetigt gestartet werden",
        }
    except Exception as exc:
        return {
            "success": False,
            "pid": None,
            "message": f"Fehler beim Starten: {str(exc)}",
        }


def stop_daemon() -> Dict[str, Any]:
    pid = is_daemon_running()
    if not pid:
        _safe_unlink(PID_FILE)
        return {"success": True, "message": "Kein Training aktiv (bereits gestoppt)"}

    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
                text=True,
                timeout=20,
            )
        else:
            os.kill(pid, signal.SIGTERM)
            for _ in range(12):
                if not _process_exists(pid):
                    break
                time.sleep(0.5)
            if _process_exists(pid):
                os.kill(pid, signal.SIGKILL)

        time.sleep(0.5)
        _safe_unlink(PID_FILE)
        if _process_exists(pid):
            return {"success": False, "message": f"Konnte Training nicht stoppen (PID: {pid})"}
        return {"success": True, "message": f"Training gestoppt (PID: {pid})"}
    except Exception as exc:
        return {"success": False, "message": f"Fehler beim Stoppen: {str(exc)}"}


def restart_daemon(
    focus: str = None,
    new: bool = False,
    config_overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    stop_result = stop_daemon()
    if not stop_result.get("success", False) and is_daemon_running():
        return {
            "success": False,
            "pid": is_daemon_running(),
            "message": f"Neustart abgebrochen: {stop_result.get('message', 'Stop fehlgeschlagen')}",
        }
    return start_daemon(focus=focus, new=new, config_overrides=config_overrides)


def get_daemon_logs(lines: int = 100) -> str:
    if not LOG_FILE.exists():
        return "Noch keine Logs vorhanden. Starte das Training, um Logs zu sehen."
    try:
        line_limit = max(1, min(5000, int(lines)))
    except (TypeError, ValueError):
        line_limit = 100
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as handle:
            recent = deque(handle, maxlen=line_limit)
        return "".join(recent)
    except Exception as exc:
        return f"Fehler beim Lesen der Logs: {str(exc)}"


def _count_log_signals() -> Tuple[int, int]:
    if not LOG_FILE.exists():
        return 0, 0
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as handle:
            recent = deque(handle, maxlen=800)
        merged = "".join(recent).lower()
        errors = merged.count("error")
        dreams = merged.count("traum-phase")
        return errors, dreams
    except Exception:
        return 0, 0


def get_training_snapshot() -> Dict[str, Any]:
    snapshot = TrainingControlSnapshot()

    had_pid_file = PID_FILE.exists()
    pid, pid_diagnostics, process_mismatch = _resolve_daemon_pid()
    snapshot.running = pid is not None
    snapshot.pid = pid
    snapshot.process_mismatch = process_mismatch
    snapshot.diagnostic_messages.extend(pid_diagnostics)

    state_data, state_error = _read_json(STATE_FILE)
    if state_error:
        snapshot.diagnostic_messages.append(state_error)

    if state_data:
        heartbeat = state_data.get("heartbeat", {}) if isinstance(state_data.get("heartbeat"), dict) else {}
        snapshot.loops = _safe_int(heartbeat.get("loop_count", len(state_data.get("history", []))), 0)
        snapshot.messages_since_dream = _safe_int(state_data.get("messages_since_dream", 0), 0)
        snapshot.current_topic = state_data.get("current_topic")
        snapshot.current_topic_index = _safe_int(state_data.get("current_topic_index", 0), 0)
        snapshot.topic_started_at = state_data.get("topic_started_at")
        stats = state_data.get("stats", {}) if isinstance(state_data.get("stats"), dict) else {}
        snapshot.topics_completed = _safe_int(stats.get("topics_completed", 0), 0)
        snapshot.start_time = state_data.get("start_time") or state_data.get("timestamp")
        snapshot.heartbeat_memory_count = _safe_int(heartbeat.get("memory_count", 0), 0)
        snapshot.total_exchanges = _safe_int(heartbeat.get("total_exchanges", 0), 0)

        state_timestamp = _parse_timestamp(state_data.get("timestamp"))
        age_minutes, activity = _format_minutes_ago(state_timestamp)
        snapshot.state_age_minutes = age_minutes
        snapshot.last_activity = activity

        if snapshot.running:
            if age_minutes is None:
                snapshot.daemon_healthy = False
                snapshot.diagnostic_messages.append("Daemon aktiv, aber kein gueltiger Heartbeat im State")
            elif age_minutes <= 10:
                snapshot.daemon_healthy = True
            elif age_minutes <= 30:
                snapshot.daemon_healthy = True
                snapshot.diagnostic_messages.append("Lange keine Aktivitaet (>10 Min)")
            else:
                snapshot.daemon_healthy = False
                snapshot.diagnostic_messages.append("Keine Aktivitaet seit >30 Min, Daemon wirkt haengend")
    elif snapshot.running:
        snapshot.daemon_healthy = False
        snapshot.diagnostic_messages.append("Daemon laeuft, aber training_state.json fehlt")

    config_data, config_error = _read_json(CONFIG_FILE)
    if config_error:
        snapshot.diagnostic_messages.append(config_error)
    config = _normalize_training_config(config_data or {})
    snapshot.focus = config.get("focus_area")
    snapshot.persona = config.get("persona")
    snapshot.curriculum = config.get("curriculum", [])
    snapshot.start_prompt = config.get("start_prompt")
    snapshot.sleep_interval_messages = _safe_int(config.get("sleep_interval_messages", 25), 25)
    snapshot.loop_pause_seconds = _safe_float(config.get("loop_pause_seconds", 0.5), 0.5)
    snapshot.request_pause_seconds = _safe_float(config.get("request_pause_seconds", 2.5), 2.5)

    from config.config import get_active_model, settings

    snapshot.model = get_active_model()
    snapshot.provider = settings.llm_provider.value.upper()

    log_errors, log_dreams = _count_log_signals()
    snapshot.errors = log_errors
    snapshot.dreams = log_dreams
    if snapshot.errors > 10:
        snapshot.diagnostic_messages.append(f"Viele Fehler im Log: {snapshot.errors}")

    if snapshot.heartbeat_memory_count > 0:
        snapshot.memory_count = snapshot.heartbeat_memory_count
    elif snapshot.running:
        try:
            from memory.memory_engine import MemoryEngine

            memory = MemoryEngine()
            snapshot.memory_count = memory.get_memory_count()
        except Exception as exc:
            snapshot.diagnostic_messages.append(f"Memory-Fehler: {str(exc)[:80]}")
    else:
        snapshot.memory_count = 0

    if not snapshot.running and had_pid_file:
        snapshot.diagnostic_messages.append("PID-Datei war vorhanden, aber kein laufender Daemon wurde gefunden")
    if not snapshot.running and STATE_FILE.exists():
        snapshot.diagnostic_messages.append("Training war zuvor aktiv, laeuft aktuell aber nicht")

    if snapshot.running and snapshot.daemon_healthy:
        snapshot.status_code = "running_healthy"
        snapshot.status_label = "Laufend"
    elif snapshot.running and not snapshot.daemon_healthy:
        snapshot.status_code = "running_degraded"
        snapshot.status_label = "Laufend (Diagnose noetig)"
    elif process_mismatch:
        snapshot.status_code = "stopped_pid_mismatch"
        snapshot.status_label = "Gestoppt (PID-Mismatch)"
    elif had_pid_file:
        snapshot.status_code = "stopped_stale_pid"
        snapshot.status_label = "Gestoppt (Stale PID bereinigt)"
    elif STATE_FILE.exists():
        snapshot.status_code = "stopped_with_state"
        snapshot.status_label = "Gestoppt (State vorhanden)"
    else:
        snapshot.status_code = "stopped_idle"
        snapshot.status_label = "Gestoppt"

    return snapshot.to_dict()


def get_training_stats() -> Dict[str, Any]:
    return get_training_snapshot()


def clear_logs() -> bool:
    try:
        _safe_unlink(LOG_FILE)
        return True
    except Exception:
        return False


if __name__ == "__main__":
    print("=== Daemon Manager Test ===")
    print(f"PID File: {PID_FILE}")
    print(f"Log File: {LOG_FILE}")
    print(f"Running: {is_daemon_running()}")
    print(f"Stats: {get_training_snapshot()}")
