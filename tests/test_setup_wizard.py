"""Modellfreie Tests fuer den gefuehrten Setup-Wizard."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WIZARD_PATH = PROJECT_ROOT / "scripts" / "setup_wizard.py"


def _load_wizard():
    spec = importlib.util.spec_from_file_location("chappie_setup_wizard", WIZARD_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


wizard = _load_wizard()


def _options(model_key: str, groq_key: str = ""):
    return wizard.SetupOptions(
        model_key=model_key,
        venv_dir=PROJECT_ROOT / "venv-test",
        install_dependencies=False,
        install_frontend=False,
        download_model=False,
        groq_api_key=groq_key,
        hf_token="",
        dry_run=True,
    )


def test_qwen_is_default_supported_profile():
    parser = wizard.build_parser()
    args = parser.parse_args(["--non-interactive"])
    assert args.model is None
    assert wizard.QWEN_MODEL == "Qwen/Qwen3.5-4B"
    assert wizard.MODEL_PROFILES["qwen"]["model"] == wizard.QWEN_MODEL


def test_config_merge_preserves_unknown_existing_values():
    existing = {
        "custom_future_section": {"keep": True},
        "memory": {"memory_top_k": 17},
        "api": {"groq_api_key": "old-key"},
    }
    config = wizard.build_setup_config(existing, _options("qwen"))
    assert config["custom_future_section"] == {"keep": True}
    assert config["memory"]["memory_top_k"] == 17
    assert config["api"]["groq_api_key"] == ""
    assert config["cloud_models"]["groq_auxiliary_enabled"] is False
    assert config["small_tasks"]["emotion_analysis_provider"] == "vllm"
    assert config["local_models"]["vllm_model"] == wizard.QWEN_MODEL
    assert config["local_models"]["steering_model"] == wizard.QWEN_MODEL


def test_gemma_profile_updates_every_local_model_reference():
    config = wizard.build_setup_config({}, _options("gemma", "gsk-test"))
    assert config["local_models"]["vllm_model"] == wizard.GEMMA_MODEL
    assert config["local_models"]["steering_model"] == wizard.GEMMA_MODEL
    assert config["local_models"]["gemma4_model"] == wizard.GEMMA_MODEL
    assert config["local_models"]["gemma4_steering_model"] == wizard.GEMMA_MODEL
    assert config["local_models"]["steering_quantize"] is True
    assert config["local_models"]["steering_context_length"] == 4096
    assert config["generation"]["temperature"] == 1.0
    assert config["api"]["groq_api_key"] == "gsk-test"
    assert config["cloud_models"]["groq_auxiliary_enabled"] is True


def test_placeholder_keys_are_treated_as_missing():
    assert wizard.is_missing_secret("DEIN_GROQ_API_KEY_HIER") is True
    assert wizard.is_missing_secret("") is True
    assert wizard.is_missing_secret("gsk-real") is False


def test_node_version_matrix_matches_vite_requirement():
    assert wizard._node_version_supported((20, 19, 0)) is True
    assert wizard._node_version_supported((20, 18, 9)) is False
    assert wizard._node_version_supported((21, 7, 3)) is False
    assert wizard._node_version_supported((22, 12, 0)) is True
    assert wizard._node_version_supported((23, 0, 0)) is True


def test_existing_broken_venv_is_rejected():
    with TemporaryDirectory() as temporary_dir:
        path = Path(temporary_dir) / "venv"
        path.mkdir()
        try:
            wizard._check_existing_venv(path)
        except wizard.SetupError as exc:
            assert "keine gültige virtuelle Umgebung" in str(exc)
        else:
            raise AssertionError("Defekte virtuelle Umgebung wurde akzeptiert")


def test_config_write_is_private_and_creates_backup():
    with TemporaryDirectory() as temporary_dir:
        path = Path(temporary_dir) / "CHAPPIE_CONFIG.json"
        path.write_text('{"old": true}\n', encoding="utf-8")
        first_backup = wizard.write_config_safely({"new": True}, path)
        second_backup = wizard.write_config_safely({"newer": True}, path)
        assert first_backup is not None and first_backup.exists()
        assert second_backup is not None and second_backup.exists()
        assert first_backup != second_backup
        assert json.loads(first_backup.read_text(encoding="utf-8")) == {"old": True}
        assert json.loads(second_backup.read_text(encoding="utf-8")) == {"new": True}
        assert json.loads(path.read_text(encoding="utf-8")) == {"newer": True}
        assert os.stat(first_backup).st_mode & 0o077 == 0
        assert os.stat(second_backup).st_mode & 0o077 == 0
        assert os.stat(path).st_mode & 0o077 == 0


def test_non_interactive_dry_run_has_no_side_effects():
    result = subprocess.run(
        [
            sys.executable,
            str(WIZARD_PATH),
            "--non-interactive",
            "--model",
            "qwen",
            "--skip-dependencies",
            "--no-frontend",
            "--no-download-model",
            "--dry-run",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Qwen 3.5 4B" in result.stdout
    assert "Setup abgeschlossen" in result.stdout


if __name__ == "__main__":
    tests = [
        test_qwen_is_default_supported_profile,
        test_config_merge_preserves_unknown_existing_values,
        test_gemma_profile_updates_every_local_model_reference,
        test_placeholder_keys_are_treated_as_missing,
        test_node_version_matrix_matches_vite_requirement,
        test_existing_broken_venv_is_rejected,
        test_config_write_is_private_and_creates_backup,
        test_non_interactive_dry_run_has_no_side_effects,
    ]
    for test in tests:
        test()
    print(f"OK: {len(tests)} setup wizard tests")
