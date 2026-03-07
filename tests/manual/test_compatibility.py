"""Manueller Kompatibilitätscheck für Training, Memory und Deployment."""

import inspect
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    from Chappies_Trainingspartner import daemon_manager
    from life import get_life_simulation_service
    from memory.memory_engine import MemoryEngine
    from memory.sleep_phase import get_sleep_phase_handler

    print("=" * 60)
    print("CHAPPiE Compatibility Check")
    print("=" * 60)

    failures = []

    service_file = REPO_ROOT / "chappie-training.service"
    service_content = service_file.read_text(encoding="utf-8")
    if "Chappies_Trainingspartner.training_daemon" in service_content or "training_daemon.py" in service_content:
        print("[OK] Service points to training_daemon entry point")
    else:
        print("[FAIL] Service does not point to training_daemon")
        failures.append("service")

    daemon_source = inspect.getsource(daemon_manager.start_daemon)
    if "Chappies_Trainingspartner.training_daemon" in daemon_source:
        print("[OK] Daemon manager starts the training daemon module")
    else:
        print("[FAIL] Daemon manager start command outdated")
        failures.append("daemon_manager")

    signature = inspect.signature(MemoryEngine.add_memory)
    required = {"content", "role", "mem_type", "label", "source"}
    if required.issubset(signature.parameters):
        print(f"[OK] MemoryEngine.add_memory signature: {list(signature.parameters.keys())}")
    else:
        print(f"[FAIL] MemoryEngine.add_memory signature mismatch: {list(signature.parameters.keys())}")
        failures.append("memory_signature")

    life_service = get_life_simulation_service()
    snapshot = life_service.get_snapshot()
    required_keys = {"homeostasis", "active_goal", "planning_state", "forecast_state", "social_arc"}
    if required_keys.issubset(snapshot):
        print("[OK] Life snapshot contains phase 1-6 integration fields")
    else:
        print(f"[FAIL] Missing life snapshot fields: {sorted(required_keys - set(snapshot.keys()))}")
        failures.append("life_snapshot")

    sleep_handler = get_sleep_phase_handler()
    status = sleep_handler.get_status()
    if isinstance(status, dict):
        print("[OK] Sleep phase handler reachable")
    else:
        print("[FAIL] Sleep phase handler returned unexpected state")
        failures.append("sleep_phase")

    result = subprocess.run(
        [sys.executable, "-m", "Chappies_Trainingspartner.training_daemon", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode == 0:
        print("[OK] training_daemon module starts successfully with --help")
    else:
        print(result.stdout)
        print(result.stderr)
        print("[FAIL] training_daemon --help failed")
        failures.append("training_daemon_help")

    print("\n" + "=" * 60)
    if failures:
        print(f"Compatibility issues: {', '.join(failures)}")
        return 1
    print("All compatibility checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())