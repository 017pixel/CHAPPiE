"""CLI soll auch ohne optionale Pakete importierbar bleiben."""

import contextlib
import importlib
import io
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
    assert callable(module._log)
    assert callable(module._success)
    assert callable(module._error)


def test_chappie_cli_colors_defined():
    module = importlib.import_module("chappie_brain_cli")
    c = module.Colors
    assert c.DEBUG
    assert c.AI
    assert c.ERROR
    assert c.SUCCESS
    assert c.RESET


def test_chappie_cli_bar_helper():
    module = importlib.import_module("chappie_brain_cli")
    assert module._bar(50, 100, 10) == "\u2588\u2588\u2588\u2588\u2588\u2591\u2591\u2591\u2591\u2591"
    assert module._bar(100, 100, 10) == "\u2588" * 10
    assert module._bar(0, 100, 10) == "\u2591" * 10


def test_chappie_cli_format_emotion_row():
    module = importlib.import_module("chappie_brain_cli")
    row = module._format_emotion_row("happiness", 75)
    assert "happiness" in row
    assert "75" in row


def test_chappie_cli_remote_backend_class():
    module = importlib.import_module("chappie_brain_cli")
    assert hasattr(module.RemoteBackend, "__init__")
    assert hasattr(module.RemoteBackend, "stream_chat")
    assert hasattr(module.RemoteBackend, "get_status")
    assert hasattr(module.RemoteBackend, "handle_command")


def test_chappie_cli_has_argparse():
    module = importlib.import_module("chappie_brain_cli")
    assert hasattr(module, "main")
    assert callable(module.main)


if __name__ == "__main__":
    test_chappie_cli_imports_without_colorama()
    test_chappie_cli_colors_defined()
    test_chappie_cli_bar_helper()
    test_chappie_cli_format_emotion_row()
    test_chappie_cli_remote_backend_class()
    test_chappie_cli_has_argparse()
    print("OK: CLI import and structure")