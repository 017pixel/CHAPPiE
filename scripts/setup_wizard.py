#!/usr/bin/env python3
"""Gefuehrtes, wiederholbares Setup fuer eine lokale CHAPPiE-Installation."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "CHAPPIE_CONFIG.json"
REQUIREMENTS_PATH = PROJECT_ROOT / "requirements.txt"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

QWEN_MODEL = "Qwen/Qwen3.5-4B"
GEMMA_MODEL = "google/gemma-4-E4B-it"

MODEL_PROFILES: dict[str, dict[str, Any]] = {
    "qwen": {
        "label": "Qwen 3.5 4B",
        "model": QWEN_MODEL,
        "context_length": 4096,
        "quantize": True,
        "temperature": 0.7,
        "top_p": 0.9,
        "top_k": 50,
    },
    "gemma": {
        "label": "Gemma 4 E4B",
        "model": GEMMA_MODEL,
        "context_length": 4096,
        "quantize": True,
        "temperature": 1.0,
        "top_p": 0.95,
        "top_k": 64,
    },
}

MISSING_SECRET_VALUES = {
    "",
    "DEIN_GROQ_API_KEY_HIER",
    "YOUR_GROQ_API_KEY_HERE",
    "none",
    "null",
}


class SetupError(RuntimeError):
    """Fehler, der mit einer klaren Setup-Meldung ausgegeben werden kann."""


@dataclass(frozen=True)
class SetupOptions:
    model_key: str
    venv_dir: Path
    install_dependencies: bool
    install_frontend: bool
    download_model: bool
    groq_api_key: str
    hf_token: str
    dry_run: bool

    @property
    def profile(self) -> dict[str, Any]:
        return MODEL_PROFILES[self.model_key]


def _print_step(message: str) -> None:
    print(f"\n[{message}]")


def _command_text(command: Sequence[str]) -> str:
    return " ".join(command)


def run_command(
    command: Sequence[str],
    *,
    cwd: Path = PROJECT_ROOT,
    env: Mapping[str, str] | None = None,
    dry_run: bool = False,
) -> None:
    print(f"  $ {_command_text(command)}")
    if dry_run:
        return
    try:
        subprocess.run(list(command), cwd=cwd, env=dict(env) if env else None, check=True)
    except FileNotFoundError as exc:
        raise SetupError(f"Befehl nicht gefunden: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise SetupError(f"Befehl fehlgeschlagen (Exit {exc.returncode}): {_command_text(command)}") from exc


def _parse_version(raw: str) -> tuple[int, int, int]:
    match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", raw)
    if not match:
        raise SetupError(f"Version konnte nicht gelesen werden: {raw.strip()}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3) or 0)


def _read_tool_version(command: Sequence[str]) -> tuple[int, int, int]:
    try:
        result = subprocess.run(list(command), text=True, capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise SetupError(f"{command[0]} ist nicht installiert oder nicht auf PATH.") from exc
    return _parse_version(result.stdout or result.stderr)


def _node_version_supported(version: tuple[int, int, int]) -> bool:
    major, minor, patch = version
    return (major == 20 and (minor, patch) >= (19, 0)) or (major >= 22 and not (major == 22 and (minor, patch) < (12, 0)))


def _nearest_existing_parent(path: Path) -> Path:
    candidate = path
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate


def _check_writable_target(path: Path, label: str) -> None:
    target = path if path.exists() and path.is_dir() else path.parent
    target = _nearest_existing_parent(target)
    if not os.access(target, os.W_OK | os.X_OK):
        raise SetupError(f"Keine Schreibrechte für {label}: {target}")


def _check_existing_venv(venv_dir: Path) -> None:
    python_path = _venv_python(venv_dir)
    if not venv_dir.exists():
        return
    if not python_path.is_file():
        raise SetupError(
            f"Der vorhandene Pfad ist keine gültige virtuelle Umgebung: {venv_dir}. "
            "Verschiebe oder lösche ihn und starte den Wizard erneut."
        )
    version = _read_tool_version([str(python_path), "--version"])
    if version < (3, 11, 0):
        raise SetupError(f"Die vorhandene virtuelle Umgebung verwendet Python {version}; benötigt wird 3.11 oder neuer.")


def check_prerequisites(*, install_frontend: bool, dry_run: bool = False) -> list[str]:
    warnings: list[str] = []
    if not sys.platform.startswith("linux"):
        raise SetupError("Der automatische lokale vLLM-/Steering-Pfad wird derzeit nur unter Linux eingerichtet.")
    if sys.version_info < (3, 11):
        raise SetupError(f"Python 3.11 oder neuer ist erforderlich, gefunden: {platform.python_version()}")
    if not REQUIREMENTS_PATH.is_file():
        raise SetupError(f"requirements.txt fehlt: {REQUIREMENTS_PATH}")
    if not (PROJECT_ROOT / "config" / "config.py").is_file():
        raise SetupError("Bitte den Wizard aus einem vollständigen CHAPPiE-Checkout starten.")

    if sys.version_info >= (3, 13):
        warnings.append(
            f"Python {platform.python_version()} ist neuer als die in CI geprüfte Version 3.11. "
            "Falls Torch oder vLLM keine passenden Wheels anbietet, verwende Python 3.11 oder 3.12."
        )

    if install_frontend and not dry_run:
        node_version = _read_tool_version(["node", "--version"])
        if not _node_version_supported(node_version):
            raise SetupError(
                "Node.js 20.19 oder 22.12 und neuer ist für den Frontend-Build erforderlich, "
                f"gefunden: {'.'.join(map(str, node_version))}"
            )
        _read_tool_version(["npm", "--version"])

    if not shutil.which("nvidia-smi"):
        warnings.append(
            "Keine NVIDIA-GPU erkannt. Das Steering-Backend kann auf der CPU starten, "
            "ist dort aber für interaktive Nutzung sehr langsam."
        )
    return warnings


def _ask_text(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        value = input(f"{prompt}{suffix}: ").strip()
    except EOFError:
        return default
    return value or default


def _ask_yes_no(prompt: str, *, default: bool) -> bool:
    hint = "J/n" if default else "j/N"
    while True:
        answer = _ask_text(f"{prompt} ({hint})").casefold()
        if not answer:
            return default
        if answer in {"j", "ja", "y", "yes"}:
            return True
        if answer in {"n", "nein", "no"}:
            return False
        print("Bitte mit j oder n antworten.")


def _ask_model(default: str = "qwen") -> str:
    print("\nLokales Hauptmodell:")
    print("  1. Qwen 3.5 4B (Standard, am besten mit CHAPPiE getestet)")
    print("  2. Gemma 4 E4B")
    while True:
        answer = _ask_text("Auswahl", "1" if default == "qwen" else "2").casefold()
        if answer in {"1", "qwen", "qwen3.5"}:
            return "qwen"
        if answer in {"2", "gemma", "gemma4"}:
            return "gemma"
        print("Bitte 1 oder 2 eingeben.")


def is_missing_secret(value: Any) -> bool:
    return str(value or "").strip() in MISSING_SECRET_VALUES


def load_existing_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SetupError(f"Vorhandene Config ist kein gültiges JSON: {path}") from exc
    if not isinstance(data, dict):
        raise SetupError(f"Vorhandene Config muss ein JSON-Objekt enthalten: {path}")
    return data


def deep_merge(base: dict[str, Any], updates: Mapping[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in updates.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _default_config() -> dict[str, Any]:
    sys.path.insert(0, str(PROJECT_ROOT))
    try:
        from config.config import DEFAULT_CONFIG
    finally:
        try:
            sys.path.remove(str(PROJECT_ROOT))
        except ValueError:
            pass
    return deepcopy(DEFAULT_CONFIG)


def build_setup_config(existing: Mapping[str, Any], options: SetupOptions) -> dict[str, Any]:
    profile = options.profile
    model_name = str(profile["model"])
    has_groq = not is_missing_secret(options.groq_api_key)
    base = deep_merge(_default_config(), existing)
    updates = {
        "api": {"groq_api_key": options.groq_api_key if has_groq else ""},
        "local_models": {
            "llm_provider": "vllm",
            "vllm_url": "http://127.0.0.1:8000/v1",
            "vllm_model": model_name,
            "gemma4_model": GEMMA_MODEL,
            "gemma4_steering_model": GEMMA_MODEL,
            "vllm_force_single_model": True,
            "enable_steering": True,
            "steering_provider": "vllm",
            "steering_model": model_name,
            "steering_quantize": bool(profile["quantize"]),
            "steering_context_length": int(profile["context_length"]),
        },
        "cloud_models": {"groq_auxiliary_enabled": has_groq},
        "small_tasks": {
            "intent_provider": "vllm",
            "intent_processor_model_vllm": model_name,
            "query_extraction_provider": "vllm",
            "query_extraction_vllm_model": model_name,
            "emotion_analysis_provider": "groq" if has_groq else "vllm",
        },
        "generation": {
            "temperature": float(profile["temperature"]),
            "top_p": float(profile["top_p"]),
            "top_k": int(profile["top_k"]),
            "use_model_defaults": True,
        },
    }
    return deep_merge(base, updates)


def write_config_safely(config: Mapping[str, Any], path: Path = CONFIG_PATH, *, dry_run: bool = False) -> Path | None:
    if dry_run:
        print(f"  Würde Konfiguration schreiben: {path}")
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    backup: Path | None = None
    if path.exists():
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup = path.with_name(f"{path.name}.backup-{timestamp}")
        shutil.copy2(path, backup)
        os.chmod(backup, 0o600)
        print(f"  Sicherung: {backup.name}")
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)
    return backup


def _venv_python(venv_dir: Path) -> Path:
    return venv_dir / "bin" / "python"


def install_python_dependencies(options: SetupOptions) -> None:
    python_path = _venv_python(options.venv_dir)
    _check_existing_venv(options.venv_dir)
    if not python_path.exists():
        run_command([sys.executable, "-m", "venv", str(options.venv_dir)], dry_run=options.dry_run)
    run_command([str(python_path), "-m", "pip", "install", "--upgrade", "pip"], dry_run=options.dry_run)
    run_command(
        [str(python_path), "-m", "pip", "install", "-r", str(REQUIREMENTS_PATH)],
        dry_run=options.dry_run,
    )
    run_command([str(python_path), "-m", "pip", "check"], dry_run=options.dry_run)


def install_frontend_dependencies(options: SetupOptions) -> None:
    run_command(["npm", "ci", "--legacy-peer-deps"], cwd=FRONTEND_DIR, dry_run=options.dry_run)
    run_command(["npm", "run", "build"], cwd=FRONTEND_DIR, dry_run=options.dry_run)


def download_model(options: SetupOptions) -> None:
    python_path = _venv_python(options.venv_dir)
    script = (
        "import os; "
        "from huggingface_hub import snapshot_download; "
        f"snapshot_download({options.profile['model']!r}, token=os.environ.get('HF_TOKEN') or None)"
    )
    env = os.environ.copy()
    if options.hf_token:
        env["HF_TOKEN"] = options.hf_token
    run_command([str(python_path), "-c", script], env=env, dry_run=options.dry_run)


def validate_installation(options: SetupOptions) -> None:
    python_path = _venv_python(options.venv_dir)
    expected_model = str(options.profile["model"])
    script = (
        "from config.config import settings; "
        "assert settings.llm_provider.value == 'vllm'; "
        f"assert settings.vllm_model == {expected_model!r}; "
        "assert settings.steering_model == settings.vllm_model; "
        "print('Konfiguration gültig:', settings.vllm_model)"
    )
    run_command([str(python_path), "-c", script], dry_run=options.dry_run)
    import_smoke = (
        "from api.main import app; "
        "from brain.steering_backend import LocalSteeringEngine; "
        "from memory.memory_engine import MemoryEngine; "
        "assert '/health' in {route.path for route in app.routes}; "
        "assert LocalSteeringEngine and MemoryEngine; "
        "print('Laufzeitimporte gültig')"
    )
    run_command([str(python_path), "-c", import_smoke], dry_run=options.dry_run)
    run_command([str(python_path), "tests/test_gemma4_integration.py"], dry_run=options.dry_run)
    run_command([str(python_path), "tests/test_root_config.py"], dry_run=options.dry_run)


def _existing_groq_key(existing: Mapping[str, Any]) -> str:
    api = existing.get("api", {})
    if not isinstance(api, Mapping):
        return ""
    value = str(api.get("groq_api_key", "") or "").strip()
    return "" if is_missing_secret(value) else value


def collect_interactive_options(args: argparse.Namespace, existing: Mapping[str, Any]) -> SetupOptions:
    model_key = args.model or _ask_model()
    venv_dir = Path(args.venv).expanduser().resolve()
    install_dependencies = not args.skip_dependencies
    install_frontend = args.frontend if args.frontend is not None else _ask_yes_no("Frontend installieren und bauen?", default=True)
    download = args.download_model if args.download_model is not None else _ask_yes_no("Modell jetzt herunterladen?", default=True)

    existing_key = _existing_groq_key(existing)
    if args.non_interactive:
        groq_key = os.getenv("GROQ_API_KEY", "").strip() or existing_key
        hf_token = os.getenv("HF_TOKEN", "").strip()
    else:
        if existing_key and _ask_yes_no("Vorhandenen Groq API-Key behalten?", default=True):
            groq_key = existing_key
        else:
            groq_key = getpass.getpass("Groq API-Key (optional, Enter überspringt): ").strip()
        hf_token = os.getenv("HF_TOKEN", "").strip()
        if model_key == "gemma" and download and not hf_token:
            hf_token = getpass.getpass(
                "Hugging-Face-Token für das freigeschaltete Gemma-Modell "
                "(optional bei gespeichertem Login): "
            ).strip()

    return SetupOptions(
        model_key=model_key,
        venv_dir=venv_dir,
        install_dependencies=install_dependencies,
        install_frontend=bool(install_frontend),
        download_model=bool(download),
        groq_api_key=groq_key,
        hf_token=hf_token,
        dry_run=bool(args.dry_run),
    )


def _print_summary(options: SetupOptions) -> None:
    print("\nGeplante Installation")
    print(f"  Modell:              {options.profile['label']} ({options.profile['model']})")
    print(f"  Python-Umgebung:     {options.venv_dir}")
    print(f"  requirements.txt:    {'ja' if options.install_dependencies else 'übersprungen'}")
    print(f"  Frontend:            {'ja' if options.install_frontend else 'nein'}")
    print(f"  Modell-Download:     {'ja' if options.download_model else 'nein'}")
    print(f"  Groq-Hilfsaufrufe:   {'ja' if not is_missing_secret(options.groq_api_key) else 'nein'}")
    print(f"  Config:              {CONFIG_PATH}")


def execute_setup(options: SetupOptions) -> None:
    _print_step("1/6 Voraussetzungen")
    for warning in check_prerequisites(install_frontend=options.install_frontend, dry_run=options.dry_run):
        print(f"  Hinweis: {warning}")
    if not options.dry_run:
        _check_writable_target(CONFIG_PATH, "CHAPPIE_CONFIG.json")
        _check_writable_target(options.venv_dir, "virtuelle Python-Umgebung")
        if options.install_frontend:
            _check_writable_target(FRONTEND_DIR, "Frontend-Verzeichnis")
        if options.download_model:
            cache_root = Path(os.getenv("HF_HOME", Path.home() / ".cache" / "huggingface")).expanduser()
            _check_writable_target(cache_root, "Hugging-Face-Cache")
            free_gib = shutil.disk_usage(_nearest_existing_parent(cache_root)).free / (1024 ** 3)
            if free_gib < 15:
                print(f"  Hinweis: Nur {free_gib:.1f} GiB frei. Modell und Paketinstallation können mehr Speicher benötigen.")

    if options.install_dependencies:
        _print_step("2/6 Python-Abhängigkeiten")
        install_python_dependencies(options)
    elif not options.dry_run:
        _check_existing_venv(options.venv_dir)
        if not _venv_python(options.venv_dir).exists():
            raise SetupError("--skip-dependencies benötigt bereits eine vorhandene virtuelle Umgebung.")
    else:
        _print_step("2/6 Python-Abhängigkeiten übersprungen")

    if options.install_frontend:
        _print_step("3/6 Frontend")
        install_frontend_dependencies(options)
    else:
        _print_step("3/6 Frontend übersprungen")

    if options.download_model:
        _print_step("4/6 Modell-Download")
        download_model(options)
    else:
        _print_step("4/6 Modell-Download übersprungen")

    _print_step("5/6 Konfiguration")
    existing = load_existing_config()
    config = build_setup_config(existing, options)
    write_config_safely(config, dry_run=options.dry_run)

    _print_step("6/6 Prüfung")
    validate_installation(options)

    print("\nSetup abgeschlossen.")
    print("Starte CHAPPiE in drei Terminals:")
    print(f"  1. {options.venv_dir}/bin/python -m brain.steering_api_server")
    print(f"  2. {options.venv_dir}/bin/python app.py")
    print("  3. cd frontend && npm run dev")
    print("Alternativ lokal im Terminal:")
    print(f"     {options.venv_dir}/bin/python chappie_brain_cli.py")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CHAPPiE Setup-Wizard für Linux")
    parser.add_argument("--non-interactive", action="store_true", help="Defaults und Umgebungsvariablen verwenden")
    parser.add_argument("--model", choices=sorted(MODEL_PROFILES), help="Lokales Hauptmodell")
    parser.add_argument("--venv", default=str(PROJECT_ROOT / "venv"), help="Pfad zur virtuellen Python-Umgebung")
    parser.add_argument("--skip-dependencies", action="store_true", help="Vorhandene Python-Umgebung weiterverwenden")
    parser.add_argument("--frontend", action=argparse.BooleanOptionalAction, default=None, help="Frontend installieren und bauen")
    parser.add_argument("--download-model", action=argparse.BooleanOptionalAction, default=None, help="Modellgewichte herunterladen")
    parser.add_argument("--dry-run", action="store_true", help="Schritte anzeigen, ohne Dateien oder Pakete zu ändern")
    parser.add_argument("--yes", action="store_true", help="Interaktive Abschlussbestätigung überspringen")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.non_interactive:
        args.model = args.model or "qwen"
        if args.frontend is None:
            args.frontend = True
        if args.download_model is None:
            args.download_model = True
        args.yes = True

    try:
        existing = load_existing_config()
        options = collect_interactive_options(args, existing)
        _print_summary(options)
        if not args.yes and not _ask_yes_no("Installation mit diesen Werten starten?", default=True):
            print("Setup abgebrochen. Es wurden keine weiteren Änderungen vorgenommen.")
            return 0
        execute_setup(options)
        return 0
    except KeyboardInterrupt:
        print("\nSetup abgebrochen.", file=sys.stderr)
        return 130
    except SetupError as exc:
        print(f"\nSetup-Fehler: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
