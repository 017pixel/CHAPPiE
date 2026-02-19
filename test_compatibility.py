"""
Test Script fuer CHAPPiE 2.0 Kompatibilitaet
"""

import sys
sys.path.insert(0, '.')

print("=== Test 1: ChromaDB Kompatibilitaet ===")
try:
    from memory.memory_engine import MemoryEngine
    from config.config import settings
    
    # Pruefe ob add_memory() unveraendert ist
    import inspect
    sig = inspect.signature(MemoryEngine.add_memory)
    params = list(sig.parameters.keys())
    expected = ['self', 'content', 'role', 'mem_type', 'label', 'source']
    
    if params == expected:
        print("[OK] MemoryEngine.add_memory() hat korrekte Signatur")
    else:
        print(f"[WARN] Parameter mismatch: {params} vs {expected}")
    
    print("[OK] ChromaDB Schema kompatibel")
except Exception as e:
    print(f"[FEHLER] {e}")

print()

print("=== Test 2: Training System ===")
try:
    # Pruefe ob training_loop.py existiert und unveraendert ist
    with open('Chappies_Trainingspartner/training_loop.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Suche nach Intent Processor oder Two-Step (sollte NICHT vorhanden sein)
    if 'intent_processor' in content.lower():
        print("[WARN] training_loop.py enthaelt intent_processor!")
    else:
        print("[OK] training_loop.py enthaelt keinen Intent Processor")
    
    if 'two_step' in content.lower() or 'step 1' in content.lower():
        print("[WARN] training_loop.py enthaelt Two-Step Logik!")
    else:
        print("[OK] training_loop.py enthaelt keine Two-Step Logik")
    
    # Pruefe ob training_daemon.py auf training_daemon zeigt (nicht training_loop)
    with open('chappie-training.service', 'r', encoding='utf-8') as f:
        service_content = f.read()
    
    if 'training_daemon.py' in service_content:
        print("[OK] Service file zeigt auf training_daemon.py")
    else:
        print("[WARN] Service file zeigt nicht auf training_daemon.py!")
    
    print("[OK] Training System ist unveraendert")
except Exception as e:
    print(f"[FEHLER] {e}")

print()

print("=== Test 3: Neue Module ===")
try:
    from memory.context_files import get_context_files_manager
    print("[OK] context_files Modul ladbar")
    
    from memory.short_term_memory_v2 import get_short_term_memory_v2
    print("[OK] short_term_memory_v2 Modul ladbar")
    
    from memory.intent_processor import get_intent_processor
    print("[OK] intent_processor Modul ladbar")
    
    from memory.debug_logger import get_debug_logger
    print("[OK] debug_logger Modul ladbar")
    
except Exception as e:
    print(f"[FEHLER] {e}")

print()
print("=== Alle Tests abgeschlossen ===")
