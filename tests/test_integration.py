"""
CHAPPiE Integration Test
=======================
Full integration test that actually talks to CHAPPiE.

Run with: python tests/test_integration.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime

print("=" * 60)
print("CHAPPiE Integration Test")
print("=" * 60)
print()


def test_full_conversation():
    """Test a full conversation with CHAPPiE using the new brain system."""
    print("TEST: Full Conversation with Brain Pipeline")
    print("-" * 40)
    
    try:
        from brain.brain_pipeline import get_brain_pipeline
        from memory.context_files import get_context_files_manager
        from config.config import settings, LLMProvider
        
        pipeline = get_brain_pipeline()
        context_files = get_context_files_manager()
        
        print(f"\nConfiguration:")
        print(f"  Provider: {settings.llm_provider.value}")
        if settings.llm_provider == LLMProvider.NVIDIA:
            print(f"  Model: {settings.nvidia_model}")
        
        test_messages = [
            "Hallo, ich heisse Benjamin!",
            "Ich interessiere mich fuer kuenstliche Intelligenz.",
            "Was weisst du ueber neuronale Netzwerke?",
        ]
        
        current_emotions = {
            "happiness": 50,
            "trust": 50,
            "energy": 100,
            "curiosity": 50,
            "frustration": 0,
            "motivation": 80
        }
        
        for i, message in enumerate(test_messages):
            print(f"\n{'='*40}")
            print(f"Message {i+1}: {message}")
            print("-" * 40)
            
            start_time = datetime.now()
            
            result = pipeline.process(
                user_input=message,
                history=[],
                current_emotions=current_emotions,
                memory_engine=None,
                context_files=context_files,
                run_background=False
            )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            
            if result["success"]:
                print(f"  [OK] Processing successful ({elapsed:.2f}s)")
                print(f"  [INFO] Sensory: {result['sensory'].data.get('input_type', 'unknown')}")
                print(f"  [INFO] Amygdala: {result['amygdala'].data.get('primary_emotion', 'unknown')}")
                print(f"  [INFO] Hippocampus: encode={result['hippocampus'].data.get('should_encode', False)}")
                print(f"  [INFO] Prefrontal: {result['prefrontal'].data.get('response_strategy', 'unknown')}")
                print(f"  [INFO] Tool calls: {len(result['tool_calls'])}")
                
                current_emotions = result["emotions_after"]
                print(f"  [INFO] Emotions after: happiness={current_emotions['happiness']}, trust={current_emotions['trust']}")
            else:
                print(f"  [FAIL] Processing failed")
                return False
        
        print(f"\n{'='*40}")
        print("Integration test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_nvidia_connection():
    """Test NVIDIA API connection directly."""
    print("\nTEST: NVIDIA API Connection")
    print("-" * 40)
    
    try:
        from brain.nvidia_brain import NVIDIABrain
        from brain.base_brain import Message, GenerationConfig
        
        brain = NVIDIABrain()
        print(f"  [INFO] Model: {brain.model}")
        
        if not brain.is_available():
            print("  [FAIL] NVIDIA API not available - check API key")
            return False
        
        print("  [OK] NVIDIA API is available")
        
        messages = [
            Message(role="system", content="Du bist CHAPPiE, ein freundlicher AI-Assistent. Antworte kurz auf Deutsch."),
            Message(role="user", content="Sag 'Hallo' in einem Satz.")
        ]
        
        config = GenerationConfig(
            max_tokens=50,
            temperature=0.7,
            stream=False
        )
        
        print("  [INFO] Sending test message...")
        response = brain.generate(messages, config)
        
        if isinstance(response, str) and not response.startswith("NVIDIA Fehler"):
            print(f"  [OK] Response: {response[:100]}...")
            return True
        else:
            print(f"  [FAIL] Error in response: {response[:100]}")
            return False
            
    except Exception as e:
        print(f"  [FAIL] NVIDIA connection error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_context_files():
    """Test context files functionality."""
    print("\nTEST: Context Files")
    print("-" * 40)
    
    try:
        from memory.context_files import get_context_files_manager
        
        manager = get_context_files_manager()
        
        soul = manager.get_soul_context()
        print(f"  [INFO] Soul content length: {len(soul)} chars")
        
        user = manager.get_user_context()
        print(f"  [INFO] User content length: {len(user)} chars")
        
        prefs = manager.get_preferences_context()
        print(f"  [INFO] Preferences content length: {len(prefs)} chars")
        
        manager.update_user({"learning": "Test learning entry"})
        print(f"  [OK] User update successful")
        
        return True
        
    except Exception as e:
        print(f"  [FAIL] Context files error: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_integration_tests():
    """Run all integration tests."""
    tests = [
        ("NVIDIA Connection", test_nvidia_connection),
        ("Context Files", test_context_files),
        ("Full Conversation", test_full_conversation),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n[ERROR] Unexpected error in {name}: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("INTEGRATION TEST RESULTS")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  [{status}] {name}")
    
    print()
    print(f"Total: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    return passed == total


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)
