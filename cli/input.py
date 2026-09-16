"""Session-scoped prompt_toolkit input with shared command completion."""
from pathlib import Path
import re
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from config.commands import command_candidates, COMMAND_REGISTRY
from config.config import CLI_INTERACTION_CONFIG

class ChappieCommandCompleter(Completer):
    """Vervollstaendigt Commands und, per Provider, Session IDs nach /session."""

    def __init__(self, session_provider=None):
        self._session_provider = session_provider

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        prefix = text.split()[-1] if text and not text.endswith(" ") else ""
        parts = text.split()
        if parts[:1] == ["/session"] and (len(parts) > 1 or text.endswith(" ")) and self._session_provider is not None:
            try:
                candidates = [(sid, label) for sid, label in self._session_provider() if sid.startswith(prefix)]
            except Exception:
                candidates = []
            if not complete_event.completion_requested:
                candidates = candidates[:CLI_INTERACTION_CONFIG["completion_rows"]]
            for sid, label in candidates:
                yield Completion(sid, start_position=-len(prefix), display_meta=label)
            return
        candidates = command_candidates(text)
        # Typing shows three suggestions; explicit Tab can reach all candidates.
        if not complete_event.completion_requested:
            candidates = candidates[:CLI_INTERACTION_CONFIG["completion_rows"]]
        for item in candidates:
            spec = COMMAND_REGISTRY.get(item)
            yield Completion(item, start_position=-len(prefix),
                             display_meta=spec.description if spec else "")


def create_prompt_session(history_root: Path, session_id: str, session_provider=None, **kwargs):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,160}", session_id):
        raise ValueError("Invalid CLI history session identifier")
    history_root.mkdir(parents=True, exist_ok=True)
    path = history_root / f"{session_id}.history"
    path.touch(mode=0o600, exist_ok=True)
    bindings = KeyBindings()

    @bindings.add("tab")
    def complete(event):
        buffer = event.current_buffer
        if buffer.complete_state:
            buffer.complete_next()
        else:
            buffer.start_completion(select_first=True)

    @bindings.add("enter")
    def accept(event):
        buffer = event.current_buffer
        if buffer.complete_state and buffer.complete_state.current_completion:
            # The selected completion is already reflected in the buffer.
            buffer.complete_state = None
        else:
            buffer.validate_and_handle()

    return PromptSession(history=FileHistory(str(path)), completer=ChappieCommandCompleter(session_provider),
                         auto_suggest=AutoSuggestFromHistory(), complete_while_typing=True,
                         reserve_space_for_menu=CLI_INTERACTION_CONFIG["completion_rows"], key_bindings=bindings, **kwargs)
