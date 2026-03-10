"""CLI soll auch ohne optionales colorama importierbar bleiben."""

import importlib
import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)


def test_chappie_cli_imports_without_colorama():
    sys.modules.pop("colorama", None)
    sys.modules.pop("chappie_brain_cli", None)

    module = importlib.import_module("chappie_brain_cli")

    assert module.Colors.RESET is not None
    assert callable(module.print_log)


if __name__ == "__main__":
    test_chappie_cli_imports_without_colorama()
    print("OK: CLI import fallback")