"""Leichter manueller Smoke-Test für Memory, Life und Replay ohne Live-API-Calls."""

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    from life.defaults import build_default_life_state
    from life.service import LifeSimulationService
    from memory.memory_engine import MemoryEngine

    print("=" * 60)
    print("CHAPPiE Local Smoke Test")
    print("=" * 60)

    memory = MemoryEngine()
    print(f"[OK] Memory initialized with count: {memory.get_memory_count()}")

    service = LifeSimulationService()
    service.state_path = Path(tempfile.mkdtemp()) / "life_state.json"
    service._state = build_default_life_state()
    service.personality.add_insight = lambda *args, **kwargs: None

    prepare = service.prepare_turn(
        "Bitte plane die nächste Entwicklungsphase und stabilisiere das Dashboard",
        history=[],
        emotions={"trust": 66, "frustration": 3},
    )
    finalize = service.finalize_turn(
        "Sehr gut, wir machen weiter",
        "Ich strukturiere Planung, Forecast und Timeline weiter aus.",
        emotions_after={"trust": 72, "frustration": 4},
        prefrontal={"response_guidance": "Mehrstufig weiterbauen"},
        global_workspace={"dominant_focus": {"label": "Kognitive Entwicklung"}},
    )
    sleep = service.process_sleep_cycle()

    print(f"[OK] Prepare goal: {prepare.get('active_goal', {}).get('title', '---')}")
    print(f"[OK] Planning horizon: {finalize.get('planning_state', {}).get('planning_horizon', '---')}")
    print(f"[OK] Forecast: {finalize.get('forecast_state', {}).get('next_turn_outlook', '---')}")
    print(f"[OK] Social arc: {finalize.get('social_arc', {}).get('arc_name', '---')}")
    print(f"[OK] Timeline entries: {finalize.get('timeline_summary', {}).get('entries', 0)}")
    print(f"[OK] Replay summary: {sleep.get('replay_state', {}).get('summary', '---')}")

    required = [
        bool(finalize.get("planning_state")),
        bool(finalize.get("forecast_state")),
        bool(finalize.get("social_arc")),
        bool(finalize.get("timeline_history")),
        bool(sleep.get("replay_state", {}).get("summary")),
    ]
    return 0 if all(required) else 1


if __name__ == "__main__":
    raise SystemExit(main())