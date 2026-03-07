"""Manueller Live-Chat-Smoke-Test mit realem Brain Pipeline Call."""

import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    from brain.brain_pipeline import get_brain_pipeline
    from memory.context_files import get_context_files_manager
    from config.config import settings

    pipeline = get_brain_pipeline()
    context_files = get_context_files_manager()
    emotions = {
        "happiness": 52,
        "trust": 58,
        "energy": 100,
        "curiosity": 65,
        "frustration": 0,
        "motivation": 85,
    }
    messages = [
        "Hallo CHAPPiE, wir testen heute deine integrierte Architektur.",
        "Kannst du mir kurz sagen, worauf du dich intern fokussierst?",
    ]

    print("=" * 60)
    print("CHAPPiE Live Chat Smoke Test")
    print("=" * 60)
    print(f"Provider: {settings.llm_provider.value}")

    for index, message in enumerate(messages, start=1):
        started = datetime.now()
        result = pipeline.process(
            user_input=message,
            history=[],
            current_emotions=emotions,
            memory_engine=None,
            context_files=context_files,
            run_background=False,
        )
        elapsed = (datetime.now() - started).total_seconds()
        if not result.get("success"):
            print(f"[FAIL] Message {index} failed")
            return 1
        emotions = result["emotions_after"]
        print(f"[OK] Message {index} in {elapsed:.2f}s | Focus={result.get('global_workspace', {}).get('dominant_focus', {}).get('label', '---')}")

    print("Live chat smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())