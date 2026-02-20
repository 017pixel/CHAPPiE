"""
CHAPPiE Brain Agent Tests
========================
Comprehensive tests for all brain agents.

Run with: python tests/test_brain_agents.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from typing import Dict, Any

print("=" * 60)
print("CHAPPiE Brain Agent Tests")
print("=" * 60)
print()


def test_imports():
    """Test that all modules can be imported."""
    print("TEST 1: Importing all modules...")
    
    try:
        from brain.agents import (
            SensoryCortexAgent,
            AmygdalaAgent,
            HippocampusAgent,
            PrefrontalCortexAgent,
            BasalGangliaAgent,
            NeocortexAgent,
            MemoryAgent,
            BrainOrchestrator,
        )
        from brain.agents.base_agent import BaseAgent, AgentResult
        print("  [OK] All agent imports successful")
        return True
    except Exception as e:
        print(f"  [FAIL] Import error: {e}")
        return False


def test_config():
    """Test brain configuration."""
    print("\nTEST 2: Testing brain configuration...")
    
    try:
        from config.brain_config import (
            BRAIN_AGENT_CONFIGS,
            get_agent_config,
            get_sleep_config,
            get_forgetting_curve_config,
        )
        
        assert len(BRAIN_AGENT_CONFIGS) == 7, f"Expected 7 agent configs, got {len(BRAIN_AGENT_CONFIGS)}"
        print(f"  [OK] Found {len(BRAIN_AGENT_CONFIGS)} agent configurations")
        
        sensory_config = get_agent_config("sensory_cortex")
        assert sensory_config is not None, "sensory_cortex config not found"
        print(f"  [OK] Sensory Cortex model: {sensory_config.model_id}")
        
        sleep_config = get_sleep_config()
        assert "triggers" in sleep_config, "Sleep config missing triggers"
        print(f"  [OK] Sleep config has triggers: {list(sleep_config['triggers'].keys())}")
        
        forgetting_config = get_forgetting_curve_config()
        assert "ebbinghaus" in forgetting_config, "Forgetting config missing ebbinghaus"
        print(f"  [OK] Forgetting curve config loaded")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Config error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sensory_cortex():
    """Test Sensory Cortex Agent."""
    print("\nTEST 3: Testing Sensory Cortex Agent...")
    
    try:
        from brain.agents.sensory_cortex import SensoryCortexAgent
        
        agent = SensoryCortexAgent()
        print(f"  [OK] Agent created: {agent.name}")
        
        input_data = {
            "user_input": "Hallo, ich moechte etwas wissen",
            "history": []
        }
        
        result = agent.process(input_data)
        
        assert result.success, f"Processing failed: {result.error}"
        print(f"  [OK] Processing successful")
        print(f"  [INFO] Input type: {result.data.get('input_type', 'unknown')}")
        print(f"  [INFO] Urgency: {result.data.get('urgency', 'unknown')}")
        print(f"  [INFO] Processing time: {result.processing_time_ms:.1f}ms")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Sensory Cortex error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_amygdala():
    """Test Amygdala Agent."""
    print("\nTEST 4: Testing Amygdala Agent...")
    
    try:
        from brain.agents.amygdala import AmygdalaAgent
        
        agent = AmygdalaAgent()
        print(f"  [OK] Agent created: {agent.name}")
        
        input_data = {
            "user_input": "Ich bin heute sehr gluecklich!",
            "current_emotions": {
                "happiness": 50,
                "trust": 50,
                "energy": 100,
                "curiosity": 50,
                "frustration": 0,
                "motivation": 80
            }
        }
        
        result = agent.process(input_data)
        
        assert result.success, f"Processing failed: {result.error}"
        print(f"  [OK] Processing successful")
        print(f"  [INFO] Primary emotion: {result.data.get('primary_emotion', 'unknown')}")
        print(f"  [INFO] Emotional intensity: {result.data.get('emotional_intensity', 0):.2f}")
        print(f"  [INFO] Memory boost: {result.data.get('memory_boost_factor', 1.0):.2f}")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Amygdala error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_hippocampus():
    """Test Hippocampus Agent."""
    print("\nTEST 5: Testing Hippocampus Agent...")
    
    try:
        from brain.agents.hippocampus import HippocampusAgent
        
        agent = HippocampusAgent()
        print(f"  [OK] Agent created: {agent.name}")
        
        input_data = {
            "user_input": "Ich heisse Benjamin und ich programmiere gerne",
            "sensory_result": {
                "input_type": "personal_sharing",
                "requires_memory_search": True
            },
            "amygdala_result": {
                "primary_emotion": "joy",
                "memory_boost_factor": 1.2,
                "personal_relevance": 0.8
            }
        }
        
        result = agent.process(input_data)
        
        assert result.success, f"Processing failed: {result.error}"
        print(f"  [OK] Processing successful")
        print(f"  [INFO] Should encode: {result.data.get('should_encode', False)}")
        print(f"  [INFO] Search query: {result.data.get('search_query', 'none')[:50]}...")
        print(f"  [INFO] Short term entries: {len(result.data.get('short_term_entries', []))}")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Hippocampus error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_prefrontal_cortex():
    """Test Prefrontal Cortex Agent."""
    print("\nTEST 6: Testing Prefrontal Cortex Agent...")
    
    try:
        from brain.agents.prefrontal_cortex import PrefrontalCortexAgent
        
        agent = PrefrontalCortexAgent()
        print(f"  [OK] Agent created: {agent.name}")
        
        input_data = {
            "user_input": "Erzaehl mir etwas ueber KI",
            "sensory_result": {"input_type": "information", "urgency": "medium"},
            "amygdala_result": {"primary_emotion": "neutral", "sentiment": "neutral"},
            "hippocampus_result": {"search_query": "KI", "context_relevance": {}},
            "memories": [],
            "context": "",
            "current_emotions": {"happiness": 50, "trust": 50}
        }
        
        result = agent.process(input_data)
        
        assert result.success, f"Processing failed: {result.error}"
        print(f"  [OK] Processing successful")
        print(f"  [INFO] Response strategy: {result.data.get('response_strategy', 'unknown')}")
        print(f"  [INFO] Tone: {result.data.get('tone', 'unknown')}")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Prefrontal Cortex error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_basal_ganglia():
    """Test Basal Ganglia Agent."""
    print("\nTEST 7: Testing Basal Ganglia Agent...")
    
    try:
        from brain.agents.basal_ganglia import BasalGangliaAgent
        
        agent = BasalGangliaAgent()
        print(f"  [OK] Agent created: {agent.name}")
        
        input_data = {
            "user_input": "Danke, das war hilfreich!",
            "response": "Gerne! Kann ich noch etwas tun?",
            "emotions_before": {"happiness": 50, "trust": 50},
            "emotions_after": {"happiness": 60, "trust": 55}
        }
        
        result = agent.process(input_data)
        
        assert result.success, f"Processing failed: {result.error}"
        print(f"  [OK] Processing successful")
        print(f"  [INFO] Satisfaction: {result.data.get('satisfaction_score', 0):.2f}")
        print(f"  [INFO] Quality: {result.data.get('interaction_quality', 'unknown')}")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Basal Ganglia error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_memory_agent():
    """Test Memory Agent."""
    print("\nTEST 8: Testing Memory Agent...")
    
    try:
        from brain.agents.memory_agent import MemoryAgent
        
        agent = MemoryAgent()
        print(f"  [OK] Agent created: {agent.name}")
        
        input_data = {
            "user_input": "Ich bin Benjamin und arbeite als Entwickler",
            "chappie_response": "Hallo Benjamin! Schoen, dich kennenzulernen.",
            "current_soul": "# CHAPPiE Soul\nTrust Level: 50/100",
            "current_user": "# User Profile\nName: Unknown",
            "current_preferences": "# CHAPPiE's Preferences",
            "amygdala_result": {"primary_emotion": "joy"},
            "hippocampus_result": {},
            "basal_ganglia_result": {"satisfaction_score": 0.7}
        }
        
        result = agent.process(input_data)
        
        assert result.success, f"Processing failed: {result.error}"
        print(f"  [OK] Processing successful")
        print(f"  [INFO] Tool calls: {len(result.data.get('tool_calls', []))}")
        print(f"  [INFO] No update needed: {result.data.get('no_update_needed', True)}")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Memory Agent error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_forgetting_curve():
    """Test Ebbinghaus Forgetting Curve."""
    print("\nTEST 9: Testing Forgetting Curve...")
    
    try:
        from memory.forgetting_curve import get_forgetting_curve, get_decay_manager
        
        curve = get_forgetting_curve()
        print(f"  [OK] Forgetting curve created")
        
        retention_1h = curve.calculate_retention(1.0, strength=1.0)
        print(f"  [INFO] Retention after 1h: {retention_1h:.2%}")
        assert 0.3 < retention_1h < 0.6, f"Unexpected retention value: {retention_1h}"
        
        retention_24h = curve.calculate_retention(24.0, strength=1.0)
        print(f"  [INFO] Retention after 24h: {retention_24h:.2%}")
        assert retention_24h < retention_1h, "Retention should decrease over time"
        
        boosted_strength = curve.calculate_strength_boost(1.0, recall_count=0)
        print(f"  [INFO] Strength after recall: {boosted_strength:.2f}")
        assert boosted_strength > 1.0, "Strength should increase after recall"
        
        optimal_time = curve.get_optimal_review_time(1.0, target_retention=0.7)
        print(f"  [INFO] Optimal review time: {optimal_time:.1f} hours")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Forgetting Curve error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sleep_phase():
    """Test Sleep Phase Handler."""
    print("\nTEST 10: Testing Sleep Phase Handler...")
    
    try:
        from memory.sleep_phase import get_sleep_phase_handler
        
        handler = get_sleep_phase_handler()
        print(f"  [OK] Sleep phase handler created")
        
        status = handler.get_status()
        print(f"  [INFO] Interactions since sleep: {status.get('interactions_since_sleep', 0)}")
        print(f"  [INFO] Next trigger: {status.get('next_sleep_trigger', 'unknown')}")
        
        for i in range(5):
            handler.increment_interaction()
        
        status_after = handler.get_status()
        print(f"  [INFO] After 5 increments: {status_after.get('interactions_since_sleep', 0)}")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Sleep Phase error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_brain_pipeline():
    """Test Brain Pipeline integration."""
    print("\nTEST 11: Testing Brain Pipeline...")
    
    try:
        from brain.brain_pipeline import get_brain_pipeline
        
        pipeline = get_brain_pipeline()
        print(f"  [OK] Brain pipeline created")
        
        status = pipeline.get_status()
        print(f"  [INFO] Provider: {status.get('provider', 'unknown')}")
        print(f"  [INFO] Model: {status.get('model', 'unknown')}")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Brain Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests and report results."""
    tests = [
        ("Imports", test_imports),
        ("Config", test_config),
        ("Sensory Cortex", test_sensory_cortex),
        ("Amygdala", test_amygdala),
        ("Hippocampus", test_hippocampus),
        ("Prefrontal Cortex", test_prefrontal_cortex),
        ("Basal Ganglia", test_basal_ganglia),
        ("Memory Agent", test_memory_agent),
        ("Forgetting Curve", test_forgetting_curve),
        ("Sleep Phase", test_sleep_phase),
        ("Brain Pipeline", test_brain_pipeline),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"  [ERROR] Unexpected error in {name}: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
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
    success = run_all_tests()
    sys.exit(0 if success else 1)
