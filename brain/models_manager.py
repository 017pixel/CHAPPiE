"""CHAPPiE Fine-Tune Model Manager - Standalone CLI + API Backend.

Usage:
    python brain/models_manager.py          # Interactive CLI
    python brain/models_manager.py --status  # Show all model statuses
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.config import settings


def _log(msg: str) -> None:
    print(f"[ModelManager] {msg}")


def get_models_dir() -> Path:
    return Path(settings.finetune_models_dir)


def get_chats_dir() -> Path:
    return Path(settings.finetune_chats_dir)


# ───────────────────────── Status & Config Helpers ─────────────────────────


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


# ───────────────────────── Model Discovery ─────────────────────────


def list_models() -> List[Dict[str, Any]]:
    models_dir = get_models_dir()
    if not models_dir.exists():
        return []
    models = []
    for subdir in sorted(models_dir.iterdir()):
        if not subdir.is_dir():
            continue
        meta = _read_json(subdir / "meta.json")
        adapter_exists = (subdir / "adapter" / "adapter_config.json").exists()
        status = _read_json(subdir / "training_status.json")
        models.append({
            "name": subdir.name,
            "target_person": meta.get("target_person", "?"),
            "status": meta.get("status", "unknown"),
            "adapter_ready": adapter_exists,
            "created": meta.get("created", ""),
            "total_pairs": meta.get("total_pairs", 0),
            "final_loss": status.get("current_loss", None) if status.get("status") == "completed" else None,
            "adapter_path": str(subdir / "adapter") if adapter_exists else None,
        })
    return models


# ───────────────────────── Service Management ─────────────────────────


def _has_systemd() -> bool:
    return shutil.which("systemctl") is not None and Path("/etc/systemd/system").exists()


def _sudo_cmd(cmd: List[str]) -> List[str]:
    if os.geteuid() == 0:
        return cmd
    return ["sudo"] + cmd


def _systemctl(*args: str) -> subprocess.CompletedProcess:
    cmd = _sudo_cmd(["systemctl"] + list(args))
    return subprocess.run(cmd, capture_output=True, text=True)


def _is_vllm_running() -> bool:
    if not _has_systemd():
        return False
    result = _systemctl("is-active", "chappie-vllm.service")
    return result.stdout.strip() == "active"


def _stop_vllm() -> bool:
    if not _has_systemd():
        return False
    _log("Stoppe chappie-vllm.service...")
    result = _systemctl("stop", "chappie-vllm.service")
    return result.returncode == 0


def _restart_vllm() -> bool:
    if not _has_systemd():
        return False
    _log("Starte chappie-vllm.service neu...")
    result = _systemctl("restart", "chappie-vllm.service")
    return result.returncode == 0


def _wait_for_health(url: str = "http://localhost:8000/health", timeout: int = 120) -> bool:
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(2)
    return False


def _set_adapter_env(adapter_path: Optional[str]) -> bool:
    """Schreibt oder loescht systemd Drop-In fuer CHAPPIE_STEERING_ADAPTER."""
    if not _has_systemd():
        return False
    dropin_dir = Path("/etc/systemd/system/chappie-vllm.service.d")
    dropin_file = dropin_dir / "adapter.conf"
    try:
        if adapter_path:
            dropin_dir.mkdir(parents=True, exist_ok=True)
            content = f'[Service]\nEnvironment="CHAPPIE_STEERING_ADAPTER={adapter_path}"\n'
            dropin_file.write_text(content, encoding="utf-8")
            _log(f"Drop-In erstellt: {dropin_file}")
        else:
            if dropin_file.exists():
                dropin_file.unlink()
                _log(f"Drop-In entfernt: {dropin_file}")
        # daemon-reload
        result = _systemctl("daemon-reload")
        return result.returncode == 0
    except Exception as e:
        _log(f"Fehler beim Setzen des Adapter-Env: {e}")
        return False


# ───────────────────────── Model Switching ─────────────────────────


def switch_active_model(model_name: Optional[str]) -> Dict[str, Any]:
    models = list_models()
    if model_name:
        model_names = [m["name"] for m in models]
        if model_name not in model_names:
            return {"success": False, "message": f"Modell '{model_name}' nicht gefunden"}
        model_dir = get_models_dir() / model_name
        adapter_path = str(model_dir / "adapter")
        if not Path(adapter_path).exists():
            return {"success": False, "message": f"Adapter fuer '{model_name}' nicht gefunden"}
    else:
        adapter_path = None

    # Update config
    settings.finetune_active_adapter = adapter_path
    settings._persist_to_root_config()

    # Set systemd env
    if not _set_adapter_env(adapter_path):
        return {"success": False, "message": "Konnte systemd Drop-In nicht setzen"}

    # Restart service
    if _is_vllm_running():
        _stop_vllm()
    if not _restart_vllm():
        return {"success": False, "message": "Konnte chappie-vllm.service nicht neu starten"}

    # Wait for health
    if not _wait_for_health():
        return {"success": False, "message": "Steering-Server startete nicht innerhalb von 120s"}

    return {
        "success": True,
        "message": f"Aktives Modell: {model_name or 'Qwen3.5-4B (Base)'}",
        "adapter_path": adapter_path,
    }


# ───────────────────────── Training Orchestration ─────────────────────────


def start_training(config_path: str) -> Dict[str, Any]:
    config = _read_json(Path(config_path))
    if not config:
        return {"success": False, "message": f"Config nicht lesbar: {config_path}"}
    model_name = Path(config_path).parent.name

    # Stop vllm to free GPU
    _stop_vllm()

    # Start training via systemd or subprocess
    if _has_systemd():
        result = _systemctl("start", f"chappie-finetune@{model_name}.service")
        if result.returncode != 0:
            return {"success": False, "message": f"systemd start fehlgeschlagen: {result.stderr}"}
    else:
        # Fallback: direct subprocess
        cmd = [sys.executable, "-m", "brain.whatsapp_finetune_trainer",
               "--config", config_path, "--background"]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return {"success": True, "message": f"Training gestartet: {model_name}"}


def get_training_status(model_name: str) -> Dict[str, Any]:
    status_path = get_models_dir() / model_name / "training_status.json"
    return _read_json(status_path)


def stop_training(model_name: str) -> Dict[str, Any]:
    if _has_systemd():
        result = _systemctl("stop", f"chappie-finetune@{model_name}.service")
        if result.returncode == 0:
            return {"success": True, "message": f"Training gestoppt: {model_name}"}
    return {"success": False, "message": "Konnte Training nicht stoppen"}


def delete_model(model_name: str) -> Dict[str, Any]:
    model_dir = get_models_dir() / model_name
    if not model_dir.exists():
        return {"success": False, "message": f"Modell nicht gefunden: {model_name}"}
    # If this is the active model, switch back to base
    active = settings.finetune_active_adapter
    if active and model_dir / "adapter" == Path(active):
        switch_active_model(None)
    shutil.rmtree(model_dir)
    return {"success": True, "message": f"Modell geloescht: {model_name}"}


# ───────────────────────── CLI Interface ─────────────────────────


def _colored(text: str, color: str) -> str:
    colors = {
        "green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m",
        "blue": "\033[94m", "cyan": "\033[96m", "bold": "\033[1m",
        "reset": "\033[0m",
    }
    return f"{colors.get(color, '')}{text}{colors['reset']}"


def _header(title: str) -> None:
    print(f"\n{'=' * 50}")
    print(f"  {title}")
    print(f"{'=' * 50}\n")


def _print_models() -> None:
    models = list_models()
    if not models:
        print("Keine Modelle vorhanden.")
        return
    print(f"{'Name':<25} {'Ziel':<15} {'Status':<12} {'Adapter':<8} {'Pairs':<8} {'Loss':<8}")
    print("-" * 80)
    for m in models:
        adapter = "✓" if m["adapter_ready"] else "✗"
        loss = f"{m['final_loss']:.3f}" if m["final_loss"] else "-"
        print(f"{m['name']:<25} {m['target_person']:<15} {m['status']:<12} {adapter:<8} {m['total_pairs']:<8} {loss:<8}")


def _select_model(prompt: str, allow_none: bool = False) -> Optional[str]:
    models = list_models()
    if not models:
        print("Keine Modelle verfuegbar.")
        return None
    print(f"\n{prompt}")
    for i, m in enumerate(models, 1):
        adapter = "✓" if m["adapter_ready"] else "✗"
        print(f"  [{i}] {m['name']} ({m['target_person']}, Adapter: {adapter})")
    if allow_none:
        print(f"  [0] Base Model (Qwen3.5-4B, kein Adapter)")
    try:
        choice = int(input("\nAuswahl > "))
        if allow_none and choice == 0:
            return None
        if 1 <= choice <= len(models):
            return models[choice - 1]["name"]
    except ValueError:
        pass
    print("Ungueltige Auswahl.")
    return None


def cli_switch_model() -> None:
    model_name = _select_model("Aktives Modell auswaehlen:", allow_none=True)
    if model_name is None and not input("Base Model aktivieren? (j/n) ").lower().startswith("j"):
        return
    print("\nWechsle Modell... (dies kann bis zu 2 Minuten dauern)")
    result = switch_active_model(model_name)
    if result["success"]:
        print(_colored(f"✓ {result['message']}", "green"))
    else:
        print(_colored(f"✗ {result['message']}", "red"))


def cli_show_status() -> None:
    _header("Modelle & Status")
    _print_models()
    active = settings.finetune_active_adapter
    print(f"\nAktiver Adapter: {active or 'Keiner (Base Model)'}")
    print(f"vLLM Service: {'● online' if _is_vllm_running() else '○ offline'}")


def cli_delete_model() -> None:
    model_name = _select_model("Zu loeschendes Modell:")
    if not model_name:
        return
    if input(f"'{model_name}' wirklich loeschen? (j/n) ").lower().startswith("j"):
        result = delete_model(model_name)
        print(_colored(result["message"], "green" if result["success"] else "red"))


def main_menu() -> None:
    while True:
        _header("CHAPPiE Model Manager")
        active = settings.finetune_active_adapter
        adapter_name = Path(active).parent.name if active else "Base (Qwen3.5-4B)"
        vllm_status = "● online" if _is_vllm_running() else "○ offline"
        print(f"Aktives Modell: {adapter_name}  |  vLLM: {vllm_status}\n")
        print("[1] Aktives Modell wechseln")
        print("[2] Status anzeigen")
        print("[3] Modell loeschen")
        print("[4] Beenden")
        choice = input("\nAuswahl > ").strip()
        if choice == "1":
            cli_switch_model()
        elif choice == "2":
            cli_show_status()
        elif choice == "3":
            cli_delete_model()
        elif choice == "4":
            break
        else:
            print("Ungueltige Eingabe.")
        input("\nEnter zum Fortfahren...")


# ───────────────────────── Entry Point ─────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="CHAPPiE Model Manager")
    parser.add_argument("--status", action="store_true", help="Status aller Modelle anzeigen")
    parser.add_argument("--switch", metavar="MODEL", help="Zu einem Modell wechseln (oder 'base')")
    args = parser.parse_args()

    if args.status:
        cli_show_status()
    elif args.switch:
        model_name = None if args.switch.lower() == "base" else args.switch
        result = switch_active_model(model_name)
        print(result["message"])
        sys.exit(0 if result["success"] else 1)
    else:
        main_menu()


if __name__ == "__main__":
    main()
