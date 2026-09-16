"""Exercise actual toolkit completion, Tab and Enter using a terminal input pipe."""
import asyncio
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from cli.input import ChappieCommandCompleter, create_prompt_session

def candidates(text, explicit=False):
    return [item.text for item in ChappieCommandCompleter().get_completions(Document(text), CompleteEvent(completion_requested=explicit))]

async def keys_test(root):
    with create_pipe_input() as pipe:
        session = create_prompt_session(root, "one", input=pipe, output=DummyOutput())
        task = asyncio.create_task(session.prompt_async("> "))
        pipe.send_text("/em")
        await asyncio.sleep(.1)
        pipe.send_text("\t")
        await asyncio.sleep(.1)
        pipe.send_text("\r")
        await asyncio.sleep(.1)
        # Enter selects a menu item, then a second Enter submits it.
        if not task.done():
            pipe.send_text("\r")
        assert await asyncio.wait_for(task, 3) == "/emotion"

if __name__ == "__main__":
    assert candidates("/e")[0] == "/emotion"
    assert len(candidates("/")) == 3
    assert len(candidates("/", True)) > 3
    assert candidates("/memory ", True) == ["on", "off", "status", "search"]
    assert candidates("/steering mode ", True) == ["off", "activation", "sequence", "combined"]
    assert candidates("/emotion fr") == ["frustration"]
    assert not candidates("normal chat")
    with tempfile.TemporaryDirectory() as directory:
        asyncio.run(keys_test(Path(directory)))
    print("CLI command/subcommand completion and real Tab/Enter passed")
