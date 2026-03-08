"""Regressionstest: config-Paket muss auch ohne secrets.py importierbar sein."""

import importlib
import shutil
import sys
import tempfile
from pathlib import Path


TEST_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_DIR.parent


def test_config_package_imports_without_optional_secrets_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)
        copied_config = tmp_root / "config"
        shutil.copytree(
            PROJECT_ROOT / "config",
            copied_config,
            ignore=shutil.ignore_patterns("secrets.py", "__pycache__"),
        )

        sys.path.insert(0, str(tmp_root))
        previous_modules = {name: module for name, module in sys.modules.items() if name == "config" or name.startswith("config.")}
        for name in list(previous_modules):
            sys.modules.pop(name, None)

        try:
            imported = importlib.import_module("config")
            assert hasattr(imported, "settings")
            assert hasattr(imported, "LLMProvider")
        finally:
            sys.path.remove(str(tmp_root))
            for name in [name for name in list(sys.modules) if name == "config" or name.startswith("config.")]:
                sys.modules.pop(name, None)
            sys.modules.update(previous_modules)


if __name__ == "__main__":
    test_config_package_imports_without_optional_secrets_file()
    print("OK: config package imports without secrets.py")