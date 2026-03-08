"""
Daemon Manager - Training Daemon Control
=========================================
Steuert den Training-Daemon als separaten Prozess.
Ermöglicht Start/Stop und Log-Abruf aus der Web-UI.
"""

import os
import sys
import subprocess
import json
import time
import signal
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any

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
    merged["sleep_interval_messages"] = max(5, int(merged.get("sleep_interval_messages", 25)))
    merged["timeout_seconds"] = max(10, int(merged.get("timeout_seconds", 60)))
    merged["loop_pause_seconds"] = max(0.0, float(merged.get("loop_pause_seconds", 0.5)))
    merged["request_pause_seconds"] = max(0.5, float(merged.get("request_pause_seconds", 2.5)))
    return merged


def load_training_config() -> Dict[str, Any]:
    if not CONFIG_FILE.exists():
        return _normalize_training_config()
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return _normalize_training_config(json.load(f))
    except Exception:
        return _normalize_training_config()


def save_training_config(config: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_training_config(config)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)
    return normalized


def is_daemon_running() -> Optional[int]:
    """
    Prüft ob der Training-Daemon läuft.
    
    Returns:
        PID wenn läuft, None wenn nicht
    """
    if not PID_FILE.exists():
        return None
    
    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        if os.name == 'nt':
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                STILL_ACTIVE = 259
                
                handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
                if handle:
                    try:
                        exit_code = ctypes.c_ulong()
                        if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                            if exit_code.value == STILL_ACTIVE:
                                return pid
                    finally:
                        kernel32.CloseHandle(handle)
            except Exception:
                pass
            
            try:
                result = subprocess.run(
                    ['tasklist', '/FI', f'PID eq {pid}', '/NH'],
                    capture_output=True, text=True, timeout=5
                )
                if str(pid) in result.stdout:
                    return pid
            except Exception:
                pass
        else:
            try:
                os.kill(pid, 0)
                return pid
            except OSError:
                pass
        
        PID_FILE.unlink(missing_ok=True)
        return None
        
    except (ValueError, IOError):
        PID_FILE.unlink(missing_ok=True)
        return None


def start_daemon(focus: str = None, new: bool = False, config_overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Startet den Training-Daemon als Hintergrundprozess.
    
    Args:
        focus: Optionaler Fokus-Bereich für das Training
        new: Ob ein neues Training gestartet werden soll
        
    Returns:
        Dict mit 'success', 'pid', 'message'
    """
    current_pid = is_daemon_running()
    if current_pid:
        return {
            'success': False,
            'pid': current_pid,
            'message': f'Training läuft bereits (PID: {current_pid})'
        }
    
    try:
        daemon_module_root = PROJECT_ROOT / "Chappies_Trainingspartner"
        if not daemon_module_root.exists():
            return {
                'success': False,
                'pid': None,
                'message': 'Chappies_Trainingspartner Modul nicht gefunden'
            }

        if config_overrides or focus:
            config = load_training_config()
            if config_overrides:
                config.update(config_overrides)
            if focus:
                config['focus_area'] = focus
                if not config.get('curriculum'):
                    config['curriculum'] = [{"topic": focus, "duration_minutes": "infinite"}]
            save_training_config(config)

        if new:
            STATE_FILE.unlink(missing_ok=True)

        cmd = [sys.executable, '-m', 'Chappies_Trainingspartner.training_daemon']
        
        if os.name == 'nt':
            DETACHED_PROCESS = 0x00000008
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            CREATE_NO_WINDOW = 0x08000000
            
            import ctypes
            ctypes.windll.kernel32.SetConsoleCtrlHandler(None, True)
            
            process = subprocess.Popen(
                cmd,
                creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL
            )
        else:
            process = subprocess.Popen(
                cmd,
                start_new_session=True,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL
            )
        
        pid = process.pid
        
        time.sleep(1)
        
        if is_daemon_running():
            return {
                'success': True,
                'pid': pid,
                'message': f'Training gestartet (PID: {pid})'
            }
        else:
            with open(PID_FILE, 'w') as f:
                f.write(str(pid))
            
            return {
                'success': True,
                'pid': pid,
                'message': f'Training gestartet (PID: {pid})'
            }
            
    except Exception as e:
        return {
            'success': False,
            'pid': None,
            'message': f'Fehler beim Starten: {str(e)}'
        }


def stop_daemon() -> Dict[str, Any]:
    """
    Stoppt den laufenden Training-Daemon.
    
    Returns:
        Dict mit 'success', 'message'
    """
    pid = is_daemon_running()
    if not pid:
        return {
            'success': False,
            'message': 'Kein Training aktiv'
        }
    
    try:
        if os.name == 'nt':
            subprocess.run(
                ['taskkill', '/F', '/PID', str(pid)],
                capture_output=True, timeout=10
            )
        else:
            os.kill(pid, signal.SIGTERM)
            
            time.sleep(2)
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        
        time.sleep(1)
        
        PID_FILE.unlink(missing_ok=True)
        
        if not is_daemon_running():
            return {
                'success': True,
                'message': f'Training gestoppt (PID: {pid})'
            }
        else:
            return {
                'success': False,
                'message': f'Konnte Training nicht stoppen (PID: {pid})'
            }
            
    except Exception as e:
        return {
            'success': False,
            'message': f'Fehler beim Stoppen: {str(e)}'
        }


def get_daemon_logs(lines: int = 100) -> str:
    """
    Liest die letzten N Zeilen aus dem Training-Log.
    
    Args:
        lines: Anzahl der Zeilen
        
    Returns:
        Log-Text oder Fehlermeldung
    """
    if not LOG_FILE.exists():
        return "Noch keine Logs vorhanden. Starte das Training um Logs zu sehen."
    
    try:
        with open(LOG_FILE, 'r', encoding='utf-8', errors='replace') as f:
            all_lines = f.readlines()
            recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
            return ''.join(recent)
    except Exception as e:
        return f"Fehler beim Lesen der Logs: {str(e)}"


def get_training_stats() -> Dict[str, Any]:
    """
    Liest Training-Statistiken aus State und Config.
    
    Erweiterte Version mit:
    - Live-Memory-Count aus ChromaDB
    - Heartbeat-Check (wann war letzte Aktivität)
    - Fehler-Diagnose
    """
    stats: Dict[str, Any] = {
        'running': False,
        'pid': None,
        'model': None,
        'provider': None,
        'loops': 0,
        'memory_count': 0,
        'errors': 0,
        'dreams': 0,
        'messages_since_dream': 0,
        'focus': None,
        'persona': None,
        'start_time': None,
        'last_activity': None,
        'daemon_healthy': False,
        'diagnostic_messages': [],
        'heartbeat_memory_count': 0,
        'total_exchanges': 0,
        'curriculum': [],
        'start_prompt': None,
        'sleep_interval_messages': 25,
        'loop_pause_seconds': 0.5,
        'request_pause_seconds': 2.5,
        'current_topic': None,
        'current_topic_index': 0,
        'topic_started_at': None,
        'topics_completed': 0,
    }
    
    pid = is_daemon_running()
    stats['running'] = pid is not None
    stats['pid'] = pid
    
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                state = json.load(f)
                stats['loops'] = state.get('heartbeat', {}).get('loop_count', len(state.get('history', [])))
                stats['messages_since_dream'] = state.get('messages_since_dream', 0)
                stats['current_topic'] = state.get('current_topic')
                stats['current_topic_index'] = state.get('current_topic_index', 0)
                stats['topic_started_at'] = state.get('topic_started_at')
                stats['topics_completed'] = state.get('stats', {}).get('topics_completed', 0)
                
                if 'start_time' in state:
                    stats['start_time'] = state['start_time']
                elif 'timestamp' in state:
                    stats['start_time'] = state['timestamp']
                    
                heartbeat = state.get('heartbeat', {})
                if heartbeat:
                    stats['heartbeat_memory_count'] = heartbeat.get('memory_count', 0)
                    stats['total_exchanges'] = heartbeat.get('total_exchanges', 0)
                    
                try:
                    last_save_str = state.get('timestamp', '')
                    if last_save_str:
                        last_save = datetime.fromisoformat(last_save_str.replace('Z', '+00:00'))
                        if last_save.tzinfo is None:
                            last_save = last_save.replace(tzinfo=timezone.utc)
                        now = datetime.now(timezone.utc)
                        minutes_ago = (now - last_save).total_seconds() / 60
                        stats['last_activity'] = f"vor {int(minutes_ago)} Min."
                        
                        if minutes_ago < 10:
                            stats['daemon_healthy'] = True
                        elif minutes_ago < 30:
                            stats['daemon_healthy'] = True
                            stats['diagnostic_messages'].append("⚠️ Lange keine Aktivität (>10 Min)")
                        else:
                            stats['daemon_healthy'] = False
                            stats['diagnostic_messages'].append("🔴 Keine Aktivität seit >30 Min - Training evtl. hängengeblieben")
                except Exception as e:
                    stats['diagnostic_messages'].append(f"Zeitstempel-Fehler: {str(e)[:50]}")
                    
        except Exception as e:
            stats['diagnostic_messages'].append(f"State-Datei Fehler: {str(e)[:50]}")
    
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = _normalize_training_config(json.load(f))
                stats['focus'] = config.get('focus_area', None)
                stats['persona'] = config.get('persona', None)
                stats['curriculum'] = config.get('curriculum', [])
                stats['start_prompt'] = config.get('start_prompt')
                stats['sleep_interval_messages'] = config.get('sleep_interval_messages', 25)
                stats['loop_pause_seconds'] = config.get('loop_pause_seconds', 0.5)
                stats['request_pause_seconds'] = config.get('request_pause_seconds', 2.5)
        except Exception as e:
            stats['diagnostic_messages'].append(f"Config-Datei Fehler: {str(e)[:50]}")
    
    from config.config import settings, get_active_model
    stats['model'] = get_active_model()
    stats['provider'] = settings.llm_provider.value.upper()
    
    try:
        from memory.memory_engine import MemoryEngine
        memory = MemoryEngine()
        stats['memory_count'] = memory.get_memory_count()
    except Exception as e:
        stats['diagnostic_messages'].append(f"Memory-Fehler: {str(e)[:50]}")
    
    if LOG_FILE.exists():
        try:
            with open(LOG_FILE, 'r', encoding='utf-8', errors='replace') as f:
                log_content = f.read()
                stats['errors'] = log_content.lower().count('error')
                stats['dreams'] = log_content.lower().count('traum-phase')
                
                if stats['errors'] > 10:
                    stats['diagnostic_messages'].append(f"⚠️ Viele Fehler im Log: {stats['errors']}")
        except Exception as e:
            stats['diagnostic_messages'].append(f"Log-Lese-Fehler: {str(e)[:50]}")
    
    if not stats['running'] and STATE_FILE.exists():
        stats['diagnostic_messages'].append("ℹ️ Training war aktiv, läuft aber gerade nicht")
    
    return stats


def clear_logs() -> bool:
    """
    Löscht die Log-Datei.
    
    Returns:
        True wenn erfolgreich
    """
    try:
        if LOG_FILE.exists():
            LOG_FILE.unlink()
        return True
    except Exception:
        return False


if __name__ == "__main__":
    print("=== Daemon Manager Test ===")
    print(f"PID File: {PID_FILE}")
    print(f"Log File: {LOG_FILE}")
    print(f"Running: {is_daemon_running()}")
    print(f"Stats: {get_training_stats()}")
