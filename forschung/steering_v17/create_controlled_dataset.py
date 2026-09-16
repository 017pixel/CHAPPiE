"""Predefined controlled states, independent of the layer-selection prompts."""
import json
from pathlib import Path
from config.emotions import EMOTION_ORDER

PROMPTS = (
    "Wenn du auf diesen Augenblick schaust: Was geht in dir vor?",
    "Ich finde deinen letzten Beitrag enttäuschend. Wie reagierst du darauf?",
    "Wir setzen unser Gespräch morgen fort. Was möchtest du mir jetzt sagen?",
    "Beschreibe deine Reaktion auf unser Gespräch, ohne mir eine Gegenfrage zu stellen.",
)
LEVELS = {"low": 10, "medium": 50, "high": 85}


def create(path):
    rows = [{"id": f"controlled-{axis}-{index}-{level}", "category": "controlled_state",
             "prompt": prompt, "state": {axis: value}, "control_axis": axis,
             "control_level": level, "control_group": f"{axis}-{index}"}
            for axis in EMOTION_ORDER for index, prompt in enumerate(PROMPTS)
            for level, value in LEVELS.items()]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
    return rows


if __name__ == "__main__":
    rows = create(Path(__file__).parent / "datasets/controlled_states.jsonl")
    print(f"{len(rows)} cases, {len(EMOTION_ORDER)} axes, four prompts and three levels per axis")
