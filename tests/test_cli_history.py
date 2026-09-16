"""Persistent history survives prompt recreation; sessions remain separate."""
import asyncio
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from cli.input import create_prompt_session

async def main(root):
    with create_pipe_input() as pipe:
        session = create_prompt_session(root, "a", input=pipe, output=DummyOutput())
        task = asyncio.create_task(session.prompt_async("> "))
        pipe.send_text("Mein erster Satz\r")
        assert await asyncio.wait_for(task, 3) == "Mein erster Satz"
    with create_pipe_input() as pipe:
        restored = create_prompt_session(root, "a", input=pipe, output=DummyOutput())
        task = asyncio.create_task(restored.prompt_async("> "))
        await asyncio.sleep(.1)
        pipe.send_text("\x1b[A\r")
        assert await asyncio.wait_for(task, 3) == "Mein erster Satz"
    with create_pipe_input() as pipe:
        other = create_prompt_session(root, "b", input=pipe, output=DummyOutput())
        assert list(other.history.load_history_strings()) == []
    assert list(restored.history.load_history_strings()) == ["Mein erster Satz"]
    assert (root / "a.history").stat().st_mode & 0o777 == 0o600

if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as directory:
        asyncio.run(main(Path(directory)))
    print("CLI history: actual arrow-up after restart and session isolation passed")
