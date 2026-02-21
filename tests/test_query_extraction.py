"""
Test Query Extraction for different input lengths.
"""

import sys
sys.path.insert(0, ".")

from config.config import settings
from memory.memory_engine import MemoryEngine

def test_query_extraction():
    print("=" * 60)
    print("Query Extraction Test")
    print("=" * 60)
    print(f"Provider: {settings.llm_provider.value}")
    print(f"Memory Top-K: {settings.memory_top_k}")
    print(f"Query Extraction Model: {settings.get_query_extraction_model()}")
    print("=" * 60)
    
    memory = MemoryEngine()
    
    test_cases = [
        ("Short Input (3 words)", "Hallo wie gehts"),
        ("Medium Input (10 words)", "Ich moechte gerne etwas ueber Python Programmierung lernen"),
        ("Long Input (5 sentences)", """
            Ich habe heute ein sehr spannendes Gespräch mit Benjamin geführt.
            Wir haben über die Verbesserung der CHAPPiE KI-Architektur gesprochen.
            Dabei ging es besonders um das neue Agent-Gehirn-System mit den verschiedenen Agenten.
            Der Benutzer möchte, dass die Query Extraction auch bei langen Inputs funktioniert.
            Wir haben beschlossen, die geladenen Memories auf 15 zu erhöhen und alle Provider zu unterstützen.
        """),
        ("Very Long Input (500+ chars)", """
            Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. 
            Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. 
            Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. 
            Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
            CHAPPiE ist ein fortschrittliches KI-System mit einem inspirierten Gehirn-Architektur-Design.
            Das System nutzt verschiedene Agenten wie Sensory Cortex, Amygdala, Hippocampus, Prefrontal Cortex, Basal Ganglia und Neocortex.
            Diese Agenten arbeiten zusammen, um eine menschenähnliche kognitive Verarbeitung zu ermöglichen.
        """),
    ]
    
    for name, input_text in test_cases:
        print(f"\n--- {name} ---")
        print(f"Input ({len(input_text)} chars, {len(input_text.split())} words):")
        print(f"  '{input_text[:100]}{'...' if len(input_text) > 100 else ''}'")
        
        result = memory.extract_search_query(input_text)
        
        print(f"Extracted Query ({len(result)} chars):")
        print(f"  '{result}'")
        
        if result and result.strip():
            print("OK - Query extracted")
        else:
            print("FAIL - Empty query")
    
    print("\n" + "=" * 60)
    print("Memory Search Test")
    print("=" * 60)
    
    search_queries = [
        "Python Programmierung",
        "Agent Gehirn System CHAPPiE",
        "Benjamin CHAPPiE Architektur",
    ]
    
    for query in search_queries:
        print(f"\nSearching for: '{query}'")
        memories = memory.search_memory(query, top_k=settings.memory_top_k)
        print(f"Found: {len(memories)} memories")
        for i, m in enumerate(memories[:3]):
            print(f"  {i+1}. {m.content[:60]}... (relevance: {m.relevance_score:.2f})")
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)

if __name__ == "__main__":
    test_query_extraction()
