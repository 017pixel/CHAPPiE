"""
CHAPPiE Live Chat Test - Simuliert 20+ Nachrichten
Testet alle Funktionen: Short-Term Memory, Context Files, Intent Processor
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setze In-Memory ChromaDB vor allen Imports
os.environ["CHROMA_DB_PATH"] = ":memory:"

from config.config import settings, LLMProvider
from memory.memory_engine import MemoryEngine
from memory.short_term_memory_v2 import get_short_term_memory_v2
from memory.context_files import get_context_files_manager
from memory.emotions_engine import EmotionsEngine
from memory.intent_processor import get_intent_processor
from memory.chat_manager import ChatManager
from brain import get_brain
from brain.base_brain import GenerationConfig, Message
from config.prompts import get_system_prompt_with_emotions

# ASCII Zeichen fuer Windows Kompatibilitaet
CHECK = "[OK]"
ERROR = "[FEHLER]"
ARROW = "->"

print("="*70)
print("CHAPPiE LIVE CHAT TEST")
print("="*70)
print(f"Provider: {settings.llm_provider.value}")
print(f"Modell: {settings.groq_model if settings.llm_provider == LLMProvider.GROQ else settings.cerebras_model}")
print("="*70)

# Initialisiere alle Module
print("\n[INIT] Initialisiere CHAPPiE...")
try:
    memory = MemoryEngine()
    print(f"  {CHECK} Memory Engine (ChromaDB In-Memory)")
    
    stm = get_short_term_memory_v2(memory_engine=memory)
    print(f"  {CHECK} Short-Term Memory V2")
    
    ctx = get_context_files_manager()
    print(f"  {CHECK} Context Files Manager")
    
    emotions = EmotionsEngine()
    print(f"  {CHECK} Emotions Engine")
    
    intent_proc = get_intent_processor()
    print(f"  {CHECK} Intent Processor")
    
    brain = get_brain()
    if brain.is_available():
        print(f"  {CHECK} Brain verfuegbar")
    else:
        print(f"  [!] Brain nicht verfuegbar (kein API Key?)")
        print("\n[Test abgebrochen - Kein API Key konfiguriert]")
        sys.exit(1)
        
    chat_mgr = ChatManager(os.path.join(os.path.dirname(__file__), "data"))
    print(f"  {CHECK} Chat Manager")
    
except Exception as e:
    print(f"  {ERROR}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*70)
print("STARTE TEST-CHAT (21 Nachrichten)")
print("="*70)

# Test Konversation
test_messages = [
    "Hallo CHAPPiE!",
    "Ich heisse Benjamin und bin KI-Entwickler.",
    "Ich arbeite an einem spannenden AGI-Projekt.",
    "Morgen habe ich ein wichtiges Meeting um 14 Uhr.",
    "Kannst du mir bei der Programmierung helfen?",
    "Ich mag Python und JavaScript.",
    "Was weisst du ueber maschinelles Lernen?",
    "Erklaere mir Transformer-Architekturen.",
    "Hast du schon von GPT-4 gehoert?",
    "Ich bevorzuge klare und praecise Antworten.",
    "Welche Musik hoerst du gerne?",
    "Erinnerst du dich an meinen Namen?",
    "Was habe ich dir ueber mein Meeting erzaehlt?",
    "Welche Programmiersprachen mag ich?",
    "Kannst du mir ein Rezept fuer Kaesekuchen geben?",
    "Ich bin Vegetarier.",
    "Welche Filme empfiehlst du?",
    "Ich mag Science-Fiction besonders gerne.",
    "Was ist deine Lieblingsfarbe?",
    "Danke fuer die Unterstuetzung!",
    "Auf Wiedersehen!"
]

# Chat Session
session_id = chat_mgr.create_session()
print(f"\n[Session] {session_id[:8]}... gestartet\n")

# Kontext fuer das Brain
context = {
    "soul": ctx.get_soul_context(),
    "user": ctx.get_user_context(),
    "preferences": ctx.get_preferences_context(),
    "short_term": "",
    "long_term": ""
}

message_history = []

# Debug Output
print("-" * 70)

for i, user_msg in enumerate(test_messages, 1):
    print(f"\n[{i}/21] Benjamin: {user_msg}")
    
    # Intent Analysis (Step 1)
    emotional_state = emotions.get_state()
    current_emotions = {
        "joy": emotional_state.happiness,
        "trust": emotional_state.trust,
        "energy": emotional_state.energy,
        "curiosity": emotional_state.curiosity,
        "frustration": emotional_state.frustration,
        "motivation": emotional_state.motivation
    }
    intent_result = intent_proc.process(user_msg, message_history, current_emotions)
    
    print(f"      [Intent] {intent_result.intent_type.value} (conf: {intent_result.confidence:.2f})")
    
    # Zeige Tool Calls
    if intent_result.tool_calls:
        print(f"      [Tools] {len(intent_result.tool_calls)} Tool Calls:")
        for tc in intent_result.tool_calls:
            print(f"        - {tc.tool}: {tc.action} (prio: {tc.priority})")
    
    # Zeige Short-Term Entries
    if intent_result.short_term_entries:
        print(f"      [STM] {len(intent_result.short_term_entries)} Eintraege:")
        for entry in intent_result.short_term_entries:
            print(f"        - [{entry.importance}] {entry.category}: {entry.content[:40]}...")
            # Speichere in STM
            stm.add_entry(entry.content, entry.category, entry.importance)
    
    # Bereite Prompt vor (Step 2)
    system_prompt = get_system_prompt_with_emotions(current_emotions)
    
    # Suche relevante Erinnerungen
    memories = memory.search_memory(user_msg, top_k=3)
    if memories:
        context["long_term"] = memory.format_memories_for_prompt(memories)
    
    # Hole Short-Term Eintraege
    stm_entries = stm.get_active_entries()
    if stm_entries:
        stm_text = "\n".join([f"- {e.content}" for e in stm_entries[-5:]])
        context["short_term"] = f"=== WICHTIGE INFOS (24h) ===\n{stm_text}"
    
    # Baue vollstaendigen Kontext
    full_context = f"""{context['soul']}

{context['user']}

{context['preferences']}

{context['short_term']}

{context['long_term']}"""

    messages = [
        Message(role="system", content=system_prompt + "\n\n" + full_context),
    ]
    # Fuege Chat-Verlauf hinzu (letzte 5 Nachrichten)
    for msg in message_history[-5:]:
        messages.append(Message(role=msg["role"], content=msg["content"]))
    messages.append(Message(role="user", content=user_msg))
    
    # Generiere Antwort
    try:
        gen_config = GenerationConfig(
            max_tokens=1024,
            temperature=0.7,
            stream=False
        )
        
        response = brain.generate(messages, config=gen_config)
        
        # Speichere in Memory
        memory.add_memory(user_msg, role="user")
        memory.add_memory(str(response), role="assistant")
        
        # Update Emotionen (analysiere die Antwort)
        emotions.analyze_and_update(user_msg)
        
        # Speichere in Chat History
        message_history.append({"role": "user", "content": user_msg})
        message_history.append({"role": "assistant", "content": str(response)})
        
        print(f"      [CHAPPiE] {str(response)[:100]}...")
        
    except Exception as e:
        print(f"      [ERROR] {e}")

# Speichere Session
chat_mgr.save_session(session_id, message_history)

print("\n" + "="*70)
print("TEST ZUSAMMENFASSUNG")
print("="*70)

print(f"\n[Chat]")
print(f"  - Nachrichten: {len(message_history)}")
print(f"  - Session ID: {session_id[:8]}...")

print(f"\n[Memory]")
print(f"  - Gespeicherte Erinnerungen: {memory.get_memory_count()}")

print(f"\n[Short-Term Memory]")
print(f"  - Aktive Eintraege: {stm.get_count()}")
entries = stm.get_active_entries()
for i, e in enumerate(entries[:5], 1):
    print(f"    {i}. [{e.importance}] {e.content[:50]}...")

print(f"\n[Context Files]")
print(f"  - Soul: {len(ctx.get_soul_context())} Zeichen")
print(f"  - User: {len(ctx.get_user_context())} Zeichen")
print(f"  - Prefs: {len(ctx.get_preferences_context())} Zeichen")

print(f"\n[Emotionen]")
emotional_state = emotions.get_state()
print(f"  - Happiness: {emotional_state.happiness}%")
print(f"  - Trust: {emotional_state.trust}%")
print(f"  - Energy: {emotional_state.energy}%")
print(f"  - Curiosity: {emotional_state.curiosity}%")
print(f"  - Frustration: {emotional_state.frustration}%")
print(f"  - Motivation: {emotional_state.motivation}%")

print("\n" + "="*70)
print("TEST ERFOLGREICH ABGESCHLOSSEN")
print("="*70)
