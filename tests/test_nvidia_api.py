"""
CHAPPiE NVIDIA API Test
======================
Quick test for NVIDIA API connection.

Run with: python tests/test_nvidia_api.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("NVIDIA API Connection Test")
print("=" * 60)

def test_nvidia_api():
    print("\nTesting NVIDIA NIM API...")
    
    try:
        from brain.nvidia_brain import NVIDIABrain
        from brain.base_brain import Message, GenerationConfig
        
        brain = NVIDIABrain()
        print(f"  Model: {brain.model}")
        print(f"  API Key: {'SET' if brain.api_key else 'NOT SET'}")
        
        if not brain.api_key:
            print("  [FAIL] No API key configured!")
            return False
        
        print("\n  Sending test message to NVIDIA...")
        
        messages = [
            Message(role="system", content="Du bist CHAPPiE. Antworte kurz."),
            Message(role="user", content="Sag Hallo.")
        ]
        
        config = GenerationConfig(
            max_tokens=50,
            temperature=0.7,
            stream=False
        )
        
        response = brain.generate(messages, config)
        
        if isinstance(response, str):
            if response.startswith("NVIDIA Fehler"):
                print(f"  [FAIL] {response}")
                return False
            else:
                print(f"  [OK] Response: {response[:100]}")
                return True
        else:
            print(f"  [OK] Got response generator")
            text = "".join(list(response))
            print(f"  [OK] Response: {text[:100]}")
            return True
            
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sensory_cortex_with_api():
    print("\nTesting Sensory Cortex Agent with NVIDIA API...")
    
    try:
        from brain.agents.sensory_cortex import SensoryCortexAgent
        
        agent = SensoryCortexAgent()
        print(f"  Agent: {agent.name}")
        
        input_data = {
            "user_input": "Hallo, wie geht es dir?",
            "history": []
        }
        
        print("  Processing...")
        result = agent.process(input_data)
        
        if result.success:
            print(f"  [OK] Success!")
            print(f"  Input type: {result.data.get('input_type', 'unknown')}")
            print(f"  Urgency: {result.data.get('urgency', 'unknown')}")
            print(f"  Time: {result.processing_time_ms:.0f}ms")
            return True
        else:
            print(f"  [FAIL] {result.error}")
            return False
            
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\nTest 1: Direct API Call")
    test1 = test_nvidia_api()
    
    print("\n" + "-" * 40)
    print("\nTest 2: Sensory Cortex Agent")
    test2 = test_sensory_cortex_with_api()
    
    print("\n" + "=" * 60)
    print(f"Results: {sum([test1, test2])}/2 passed")
    print("=" * 60)
    
    sys.exit(0 if all([test1, test2]) else 1)
