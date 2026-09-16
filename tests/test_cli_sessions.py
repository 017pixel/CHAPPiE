"""End-to-End Stress fuer CLI Sessions: Liste, Wechsel per ID und Praefix, Autocomplete, remote."""

import importlib
import io
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

TEST_DIR = str(Path(__file__).resolve().parent)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prompt_toolkit.completion import CompleteEvent  # noqa: E402
from prompt_toolkit.document import Document  # noqa: E402

from memory.chat_manager import ChatManager  # noqa: E402
from cli.input import ChappieCommandCompleter  # noqa: E402


def _get_cli_module():
    sys.modules.pop("chappie_brain_cli", None)
    return importlib.import_module("chappie_brain_cli")


def _manager(root: Path) -> ChatManager:
    return ChatManager(str(root / "data"))


def _seed(manager: ChatManager, session_id: str, first: str, extra: int = 0):
    messages = [{"role": "user", "content": first}]
    for i in range(extra):
        messages.append({"role": "assistant", "content": f"Antwort {i} zu {first[:10]}"})
    return manager.save_session(session_id, messages)


def _build_cli(manager: ChatManager):
    m = _get_cli_module()
    cli = m.CHAPPiEBrainCLI.__new__(m.CHAPPiEBrainCLI)
    cli.remote_url = None
    cli._use_remote = False
    cli._show_full_report = False
    cli.history = []
    cli.session_id = None
    cli.last_result = {"stale": True}
    cli.backend = SimpleNamespace(chat_manager=manager)
    return m, cli


def _capture(fn, *args):
    saved = sys.stdout
    sys.stdout = io.StringIO()
    try:
        result = fn(*args)
        return result, sys.stdout.getvalue()
    finally:
        sys.stdout = saved


def _completer(manager: ChatManager):
    entries = manager.list_sessions()

    def provider():
        return [(s["id"], s.get("title", "")) for s in entries if s.get("id")]

    return ChappieCommandCompleter(provider)


# ── Liste ─────────────────────────────────────────────────────────

def test_list_sessions_has_message_count(root: Path):
    manager = _manager(root)
    _seed(manager, "sess-count-1", "Hallo Welt", extra=2)
    found = {s["id"]: s for s in manager.list_sessions()}
    assert found["sess-count-1"]["message_count"] == 3
    assert "Hallo Welt" in found["sess-count-1"]["title"]


def test_sessions_display_short_id_title_and_count(root: Path):
    manager = _manager(root)
    sid = _seed(manager, "fed4b66c-9e02-4d76-8e7b-b5cc522775bd", "Was bist du?", extra=1)
    _, cli = _build_cli(manager)
    cli.session_id = sid
    _, output = _capture(cli._handle_command, "/sessions")
    assert "fed4b66c" in output
    assert "fed4b66c-9e02-4d76-8e7b-b5cc522775bd" not in output
    assert "Was bist du?" in output
    assert "2 Nachrichten" in output
    assert "*" in output


# ── Wechsel ───────────────────────────────────────────────────────

def test_switch_by_full_id_prefix_and_short_id(root: Path):
    manager = _manager(root)
    first = _seed(manager, "aaa11111-1111-4111-8111-111111111111", "Erste Frage", extra=1)
    second = _seed(manager, "bbb22222-2222-4222-8222-222222222222", "Zweite Frage", extra=2)
    _, cli = _build_cli(manager)

    assert cli._handle_command(f"/session {first}") is True
    assert cli.session_id == first
    assert cli.history[0]["content"] == "Erste Frage"
    assert cli.last_result is None
    assert manager.get_active_session_id() == first

    assert cli._handle_command("/session bbb2") is True
    assert cli.session_id == second
    assert len(cli.history) == 3

    assert cli._handle_command(f"/session {second[:8]}") is True
    assert cli.session_id == second
    assert cli.history[0]["content"] == "Zweite Frage"


def test_switch_ambiguous_and_unknown_keep_session(root: Path):
    manager = _manager(root)
    _seed(manager, "sess-alpha-1", "Alpha eins")
    _seed(manager, "sess-alpha-2", "Alpha zwei")
    _, cli = _build_cli(manager)
    cli.session_id = "sess-alpha-1"
    cli.history = [{"role": "user", "content": "Alpha eins"}]

    _, output = _capture(cli._handle_command, "/session sess-alpha")
    assert "Mehrdeutig" in output
    assert cli.session_id == "sess-alpha-1"

    _, output = _capture(cli._handle_command, "/session gibt-es-nicht")
    assert "nicht gefunden" in output
    assert cli.session_id == "sess-alpha-1"


def test_session_bare_shows_usage(root: Path):
    manager = _manager(root)
    _, cli = _build_cli(manager)
    result, output = _capture(cli._handle_command, "/session")
    assert result is True
    assert "/session" in output and "/sessions" in output


# ── Autocomplete ──────────────────────────────────────────────────

def test_completion_suggests_sessions_with_titles(root: Path):
    manager = _manager(root)
    _seed(manager, "fed4b66c-9e02-4d76-8e7b-b5cc522775bd", "Was bist du?")
    _seed(manager, "fed90000-0000-4000-8000-000000000000", "Anderes Thema")
    completer = _completer(manager)

    explicit = CompleteEvent(completion_requested=True)
    got = [c.text for c in completer.get_completions(Document("/session fed4"), explicit)]
    assert "fed4b66c-9e02-4d76-8e7b-b5cc522775bd" in got
    assert "fed90000-0000-4000-8000-000000000000" not in got

    metas = {c.text: c.display_meta_text for c in completer.get_completions(Document("/session fed"), explicit)}
    assert "Was bist du?" in metas["fed4b66c-9e02-4d76-8e7b-b5cc522775bd"]

    typing = CompleteEvent(completion_requested=False)
    assert len(list(completer.get_completions(Document("/session "), typing))) <= 3


def test_completion_without_provider_keeps_commands():
    completer = ChappieCommandCompleter()
    explicit = CompleteEvent(completion_requested=True)
    assert "/session" in [c.text for c in completer.get_completions(Document("/sess"), explicit)]


def test_completion_provider_failure_returns_nothing():
    completer = ChappieCommandCompleter(lambda: 1 / 0)
    explicit = CompleteEvent(completion_requested=True)
    assert list(completer.get_completions(Document("/session ab"), explicit)) == []


# ── Stress ────────────────────────────────────────────────────────

def test_stress_many_sessions_and_switches(root: Path):
    manager = _manager(root)
    ids = []
    for i in range(25):
        ids.append(_seed(manager, f"stress-{i:04d}-aaaa-4aaa-8aaa-aaaaaaaaaaaa", f"Thema Nummer {i}", extra=i % 3))
    _, cli = _build_cli(manager)
    order = list(range(25))[::2] + list(range(25))[1::2]
    for step, i in enumerate(order):
        if step % 3 == 0:
            arg = ids[i]
        elif step % 3 == 1:
            arg = ids[i][:12]
        else:
            arg = ids[i][:-1]
        assert cli._handle_command(f"/session {arg}") is True, arg
        assert cli.session_id == ids[i]
        assert cli.history[0]["content"] == f"Thema Nummer {i}"
    result, output = _capture(cli._handle_command, "/sessions")
    assert result is True
    assert "Sessions (25)" in output
    for i in (0, 12, 24):
        assert ids[i][:8] in output


# ── Remote ────────────────────────────────────────────────────────

def _remote_cli(m):
    cli = m.CHAPPiEBrainCLI.__new__(m.CHAPPiEBrainCLI)
    cli._use_remote = True
    cli.remote_url = "http://remote-test:8010"
    cli.remote = SimpleNamespace(base_url="http://remote-test:8010", session_id="old")
    cli.session_id = "old"
    cli.history = []
    cli.last_result = {"stale": True}
    cli.backend = SimpleNamespace()
    return cli


def test_remote_list_switch_and_prefix():
    m = _get_cli_module()
    cli = _remote_cli(m)
    sessions = [
        {"id": "aaa11111-1111-4111-8111-111111111111", "title": "Erste Frage", "message_count": 2},
        {"id": "bbb22222-2222-4222-8222-222222222222", "title": "Zweite Frage", "message_count": 4},
    ]

    def fake_get(url, timeout=10):
        response = MagicMock()
        if url.endswith("/sessions"):
            response.json.return_value = sessions
        elif url.endswith(sessions[0]["id"]):
            response.json.return_value = {"id": sessions[0]["id"], "messages": [{"role": "user", "content": "Erste Frage"}]}
        else:
            response.json.return_value = {}
        return response

    with patch.object(m.requests, "get", side_effect=fake_get):
        result, output = _capture(cli._handle_command, "/sessions")
        assert result is True
        assert "aaa11111" in output and "Erste Frage" in output and "2 Nachrichten" in output
        assert "aaa11111-1111-4111-8111-111111111111" not in output

        assert cli._handle_command("/session aaa1") is True
        assert cli.session_id == sessions[0]["id"]
        assert cli.history[0]["content"] == "Erste Frage"
        assert cli.last_result is None

        _, output = _capture(cli._handle_command, "/session fehlt")
        assert "nicht gefunden" in output


def test_remote_unreachable_stays_usable():
    m = _get_cli_module()
    cli = _remote_cli(m)
    with patch.object(m.requests, "get", side_effect=TimeoutError("down")):
        assert cli._handle_command("/sessions") is True
        assert cli._session_completions() == []
        assert cli._resolve_session_target("aaa") is None


if __name__ == "__main__":
    import tempfile as _tempfile

    with _tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        test_list_sessions_has_message_count(root / "t1")
        test_sessions_display_short_id_title_and_count(root / "t2")
        test_switch_by_full_id_prefix_and_short_id(root / "t3")
        test_switch_ambiguous_and_unknown_keep_session(root / "t4")
        test_session_bare_shows_usage(root / "t5")
        test_completion_suggests_sessions_with_titles(root / "t6")
        test_completion_without_provider_keeps_commands()
        test_completion_provider_failure_returns_nothing()
        test_stress_many_sessions_and_switches(root / "t7")
    test_remote_list_switch_and_prefix()
    test_remote_unreachable_stays_usable()
    print("OK: CLI sessions list, switch, prefix, completion and remote")
