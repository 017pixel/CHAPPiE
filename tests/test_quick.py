"""
CHAPPiE Quick Tests
==================
Quick tests without API calls.

Run with: python tests/test_quick.py
"""

import sys
import os
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

for mod in (
    "chromadb", "chromadb.config", "requests", "openai",
    "brain.nvidia_brain",
    "brain.steering_api_server", "brain.steering_backend",
    "brain.deep_think", "brain.global_workspace",
    "brain.action_response", "brain.response_parser",
    "brain.cerebras_limits", "life", "memory.emotions_engine",
    "memory.chat_manager", "memory.short_term_memory",
    "memory.short_term_memory_v2", "memory.personality_manager",
    "memory.function_registry", "memory.intent_processor", "memory.debug_logger",
    "sentence_transformers",
):
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

sys.modules["ollama"] = MagicMock()

print("=" * 60)
print("CHAPPiE Quick Tests (No API Calls)")
print("=" * 60)

def test_imports():
    print("\nTEST 1: Importing modules...")
    try:
        from config.config import settings, LLMProvider
        print(f"  [OK] Provider: {settings.llm_provider.value}")
        print(f"  [OK] Groq Model: {settings.groq_model}")
        print(f"  [OK] Groq Key: {'SET' if settings.groq_api_key else 'NOT SET'}")

        from config.brain_config import BRAIN_AGENT_CONFIGS
        print(f"  [OK] Brain configs: {len(BRAIN_AGENT_CONFIGS)} agents")

        from memory.forgetting_curve import get_forgetting_curve
        curve = get_forgetting_curve()
        retention = curve.calculate_retention(1.0, 1.0)
        print(f"  [OK] Forgetting curve: retention@1h = {retention:.2%}")

        from memory.sleep_phase import get_sleep_phase_handler
        handler = get_sleep_phase_handler()
        status = handler.get_status()
        print(f"  [OK] Sleep handler: {status.get('next_sleep_trigger')}")

        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agents_creation():
    print("\nTEST 2: Creating agents...")
    try:
        from brain.agents import (
            SensoryCortexAgent,
            AmygdalaAgent,
            HippocampusAgent,
            PrefrontalCortexAgent,
            BasalGangliaAgent,
            NeocortexAgent,
            MemoryAgent,
        )

        agents = [
            ("SensoryCortex", SensoryCortexAgent()),
            ("Amygdala", AmygdalaAgent()),
            ("Hippocampus", HippocampusAgent()),
            ("PrefrontalCortex", PrefrontalCortexAgent()),
            ("BasalGanglia", BasalGangliaAgent()),
            ("Neocortex", NeocortexAgent()),
            ("MemoryAgent", MemoryAgent()),
        ]

        for name, agent in agents:
            print(f"  [OK] {name}: {agent.name}")

        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_context_files():
    print("\nTEST 3: Testing context files...")
    try:
        from memory.context_files import get_context_files_manager

        manager = get_context_files_manager()

        soul = manager.get_soul_context()
        print(f"  [OK] Soul: {len(soul)} chars")

        user = manager.get_user_context()
        print(f"  [OK] User: {len(user)} chars")

        prefs = manager.get_preferences_context()
        print(f"  [OK] Preferences: {len(prefs)} chars")

        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pipeline():
    print("\nTEST 4: Testing brain pipeline...")
    try:
        from brain.brain_pipeline import get_brain_pipeline

        pipeline = get_brain_pipeline()
        status = pipeline.get_status()
        print(f"  [OK] Provider: {status['provider']}")
        print(f"  [OK] Model: {status['model']}")

        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_forgetting_curve_math():
    print("\nTEST 5: Testing forgetting curve math...")
    try:
        from memory.forgetting_curve import get_forgetting_curve

        curve = get_forgetting_curve()

        r_20min = curve.calculate_retention(0.33, 1.0)
        print(f"  [OK] Retention @20min: {r_20min:.2%} (expected ~58%)")

        r_1h = curve.calculate_retention(1.0, 1.0)
        print(f"  [OK] Retention @1h: {r_1h:.2%} (expected ~44%)")

        r_24h = curve.calculate_retention(24.0, 1.0)
        print(f"  [OK] Retention @24h: {r_24h:.2%} (expected ~33%)")

        checks = [
            (abs(r_20min - 0.58) <= 0.05, "20min-Wert weicht zu stark vom Ebbinghaus-Referenzwert ab"),
            (abs(r_1h - 0.44) <= 0.05, "1h-Wert weicht zu stark vom Ebbinghaus-Referenzwert ab"),
            (abs(r_24h - 0.33) <= 0.05, "24h-Wert weicht zu stark vom Ebbinghaus-Referenzwert ab"),
        ]
        for ok, message in checks:
            if not ok:
                raise AssertionError(message)

        boosted = curve.calculate_strength_boost(1.0, 0)
        print(f"  [OK] Strength boost: {boosted:.2f}")

        optimal = curve.get_optimal_review_time(1.0, 0.7)
        print(f"  [OK] Optimal review: {optimal:.1f} hours")

        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_key_format():
    print("\nTEST 6: Testing API key formats...")
    try:
        from config.config import settings

        if settings.groq_api_key:
            print("  [OK] Groq key: SET")
        else:
            print("  [INFO] Groq key not set")

        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False


def test_provider_enum():
    print("\nTEST 7: Testing provider enum...")
    try:
        from config.config import LLMProvider

        providers = list(LLMProvider)
        names = [p.value for p in providers]
        print(f"  [OK] Providers: {names}")

        assert "vllm" in names, "vLLM missing"
        assert "ollama" in names, "Ollama missing"
        assert "groq" in names, "Groq missing"
        assert "cerebras" not in names, "Cerebras should be removed"
        assert "nvidia" not in names, "NVIDIA should be removed"
        assert len(providers) == 3, f"Expected 3 providers, got {len(providers)}"

        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False


def test_groq_brain_import():
    print("\nTEST 8: Testing Groq brain import...")
    try:
        from brain.groq_brain import GroqBrain, GROQ_MODELS

        assert len(GROQ_MODELS) >= 6, "Groq models dict should have at least 6 entries"
        assert "llama-3.1-8b-instant" in GROQ_MODELS
        assert "llama-3.3-70b-versatile" in GROQ_MODELS

        brain = GroqBrain(api_key="test-key", model="llama-3.1-8b")
        info = brain.get_model_info()
        print(f"  [OK] GroqBrain created: {info}")

        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False


def run_tests():
    tests = [
        test_imports,
        test_agents_creation,
        test_context_files,
        test_pipeline,
        test_forgetting_curve_math,
        test_api_key_format,
        test_provider_enum,
        test_groq_brain_import,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"  [ERROR] {e}")
            results.append(False)

    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print("=" * 60)

    return all(results)


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
