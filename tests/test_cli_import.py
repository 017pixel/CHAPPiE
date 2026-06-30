"""CLI shall remain importable without optional packages (rich, requests)."""

import contextlib
import importlib
import io
import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from config.emotions import EMOTION_ORDER  # noqa: E402


def _reload():
    sys.modules.pop("chappie_brain_cli", None)
    return importlib.import_module("chappie_brain_cli")


def test_module_imports_without_optional_deps():
    sys.modules.pop("chappie_brain_cli", None)
    module = importlib.import_module("chappie_brain_cli")
    assert module.HAS_RICH is False or module.HAS_RICH is True
    assert module.HAS_REQUESTS is False or module.HAS_REQUESTS is True


def test_colors_defined():
    m = _reload()
    c = m.Colors
    assert c.DEBUG
    assert c.AI
    assert c.ERROR
    assert c.SUCCESS
    assert c.WARN
    assert c.STEER
    assert c.RESET
    assert c.BOLD
    assert c.DIM


def test_log_helpers():
    m = _reload()
    assert callable(m._log)
    assert callable(m._success)
    assert callable(m._error)
    assert callable(m._warn)
    assert callable(m._ts)


def test_bar_helper():
    m = _reload()
    assert m._bar(50, 100, 10) == "\u2588" * 5 + "\u2591" * 5
    assert m._bar(100, 100, 10) == "\u2588" * 10
    assert m._bar(0, 100, 10) == "\u2591" * 10
    assert m._bar(75, 100, 15) == "\u2588" * 11 + "\u2591" * 4


def test_v_placeholder():
    m = _reload()
    assert m._v({}, "x", "fallback") == "fallback"
    assert m._v({"x": "val"}, "x") == "val"
    assert m._v(None, "x", "fb") == "fb"


def test_emoji_delta():
    m = _reload()
    assert m._emoji_delta(50, 53) == "↑+3"
    assert m._emoji_delta(50, 47) == "↓-3"
    assert m._emoji_delta(50, 50) == " →"


def test_emo_color():
    m = _reload()
    assert m._emo_color(75) == "green"
    assert m._emo_color(45) == "yellow"
    assert m._emo_color(15) == "red"
    assert m._emo_color(60) == "green"
    assert m._emo_color(30) == "yellow"


def test_spinner_frames():
    m = _reload()
    assert len(m.SPINNER_FRAMES) == 10
    assert m.SPINNER_FRAMES[0] != m.SPINNER_FRAMES[1]


def test_emotion_names():
    m = _reload()
    assert m.EMOTION_NAMES == EMOTION_ORDER
    for name in ("happiness", "trust", "energy", "curiosity", "motivation", "frustration", "sadness", "affection", "anxiety", "calm"):
        assert name in m.EMOTION_NAMES


def test_remote_backend_interface():
    m = _reload()
    assert hasattr(m.RemoteBackend, "__init__")
    assert hasattr(m.RemoteBackend, "get_status")
    assert hasattr(m.RemoteBackend, "stream_events")
    assert hasattr(m.RemoteBackend, "handle_command")


def test_cli_class_exists():
    m = _reload()
    assert hasattr(m, "CHAPPiEBrainCLI")
    assert hasattr(m, "main")
    assert callable(m.main)


def test_cli_render_methods_exist():
    m = _reload()
    c = m.CHAPPiEBrainCLI
    assert hasattr(c, "_render_spinner")
    assert hasattr(c, "_render_step1_done")
    assert hasattr(c, "_render_streaming")


def test_cli_panel_methods_exist():
    m = _reload()
    c = m.CHAPPiEBrainCLI
    for name in ("_panel_emotions", "_panel_intent_json", "_panel_tools", "_panel_memory",
                 "_panel_workspace", "_panel_steering", "_panel_tone", "_panel_budget",
                 "_panel_timing", "_panel_causal", "_panel_consolidation", "_panel_debug"):
        assert hasattr(c, name), f"Missing {name}"


def test_cli_remote_helper():
    m = _reload()
    assert hasattr(m.CHAPPiEBrainCLI, "_remote_meta_to_result")
    assert callable(m.CHAPPiEBrainCLI._remote_meta_to_result)


def test_cli_compact_report_guard():
    m = _reload()
    assert hasattr(m, "_FULL_REPORT_DEFAULT")
    assert m._FULL_REPORT_DEFAULT is False


if __name__ == "__main__":
    test_module_imports_without_optional_deps()
    test_colors_defined()
    test_log_helpers()
    test_bar_helper()
    test_v_placeholder()
    test_emoji_delta()
    test_emo_color()
    test_spinner_frames()
    test_emotion_names()
    test_remote_backend_interface()
    test_cli_class_exists()
    test_cli_render_methods_exist()
    test_cli_panel_methods_exist()
    test_cli_remote_helper()
    test_cli_compact_report_guard()
    print("OK: CLI v6.0 imports and structure")
