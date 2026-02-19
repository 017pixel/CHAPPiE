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
from typing import Optional, Dict, Any

PROJECT_ROOT = Path(__file__).parent.parent
PID_FILE = PROJECT_ROOT / "training.pid"
LOG_FILE = PROJECT_ROOT / "training_daemon.log"
STATE_FILE = PROJECT_ROOT / "training_state.json"
CONFIG_FILE = PROJECT_ROOT / "training_config.json"


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


def start_daemon(focus: str = None, new: bool = False) -> Dict[str, Any]:
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
        daemon_script = Path(__file__).parent / "training_daemon.py"
        if not daemon_script.exists():
            daemon_script = PROJECT_ROOT / "Chappies_Trainingspartner" / "training_daemon.py"
        
        if not daemon_script.exists():
            return {
                'success': False,
                'pid': None,
                'message': 'training_daemon.py nicht gefunden'
            }
        
        cmd = [sys.executable, str(daemon_script)]
        
        if new:
            cmd.append('--neu')
        
        if focus:
            cmd.extend(['--fokus', focus])
        
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
    
    Returns:
        Dict mit allen Stats
    """
    stats = {
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
        'start_time': None
    }
    
    stats['running'] = is_daemon_running() is not None
    stats['pid'] = is_daemon_running()
    
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                state = json.load(f)
                stats['loops'] = len(state.get('history', []))
                stats['messages_since_dream'] = state.get('messages_since_dream', 0)
                
                if 'timestamp' in state:
                    stats['start_time'] = state['timestamp']
        except Exception:
            pass
    
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                stats['focus'] = config.get('focus_area', None)
                stats['persona'] = config.get('persona', None)
        except Exception:
            pass
    
    from config.config import settings, get_active_model
    stats['model'] = get_active_model()
    stats['provider'] = settings.llm_provider.value.upper()
    
    try:
        from memory.memory_engine import MemoryEngine
        memory = MemoryEngine()
        stats['memory_count'] = memory.get_memory_count()
    except Exception:
        pass
    
    if LOG_FILE.exists():
        try:
            with open(LOG_FILE, 'r', encoding='utf-8', errors='replace') as f:
                log_content = f.read()
                stats['errors'] = log_content.lower().count('error')
                stats['dreams'] = log_content.lower().count('traum-phase')
        except Exception:
            pass
    
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
