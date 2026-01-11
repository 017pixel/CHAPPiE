"""
CHAPiE - Memory Engine
======================
Episodisches Gedaechtnis mit ChromaDB Vektordatenbank.

Funktionen:
- add_memory(): Speichert Text als Vektor
- search_memory(): Findet relevante Erinnerungen
- get_recent_memories(): Holt die neuesten Eintraege
- clear_memory(): Loescht alle Erinnerungen
"""

import uuid
from datetime import datetime
from typing import Optional, Any
from dataclasses import dataclass

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from config.config import settings, CHROMA_DB_DIR
from brain.base_brain import GenerationConfig, Message
from config.prompts import format_query_extraction_prompt


@dataclass
class Memory:
    """Repraesentiert eine einzelne Erinnerung."""
    id: str
    content: str
    role: str  # "user" oder "assistant"
    timestamp: str
    mem_type: str = "interaction"  # "interaction" oder "summary"
    relevance_score: float = 0.0


class MemoryEngine:
    """
    Episodisches Gedaechtnis fuer CHAPiE.
    
    Nutzt ChromaDB fuer Vektorspeicherung und
    Sentence-Transformers fuer Embeddings.
    """
    
    def __init__(self):
        """Initialisiert die Memory Engine."""
        print("Initialisiere Memory Engine...")
        
        # Embedding-Modell laden (laeuft lokal)
        print(f"   Lade Embedding-Modell: {settings.embedding_model}")
        self.embedder = SentenceTransformer(settings.embedding_model)
        
        # ChromaDB Client initialisieren (in-memory für Stabilität)
        print(f"   Verbinde mit ChromaDB (in-memory)")
        self.client = chromadb.Client(
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        
        # Collection erstellen oder laden
        self.collection = self.client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"description": "CHAPiE episodic memory"}
        )
        
        memory_count = self.collection.count()
        print(f"   Memory Engine bereit! ({memory_count} Erinnerungen geladen)")
    
    def add_memory(self, content: str, role: str = "user", mem_type: str = "interaction") -> str:
        """
        Speichert eine neue Erinnerung.
        
        Args:
            content: Der zu speichernde Text
            role: "user" oder "assistant"
        
        Returns:
            Die ID der gespeicherten Erinnerung
        """
        # Generiere eindeutige ID
        memory_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Erstelle Embedding
        embedding = self.embedder.encode(content).tolist()
        
        # Speichere in ChromaDB
        self.collection.add(
            ids=[memory_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[{
                "role": role,
                "timestamp": timestamp,
                "type": mem_type
            }]
        )
        
        if settings.debug:
            print(f"   Memory gespeichert: [{role}] {content[:50]}...")

        return memory_id

    def extract_search_query(self, user_input: str) -> str:
        """
        Extrahiert optimierte Suchbegriffe aus dem User-Input.

        Nutzt Dual-Strategy:
        1. Priority: Groq API (llama-3.1-8b-instant)
        2. Fallback: Ollama (llama3.2:1b)
        3. Silent Fallback: Originaler User-Input bei komplettem Fehler

        Args:
            user_input: Der originale User-Input

        Returns:
            Optimierter Such-Query oder Original-Input bei Fehler
        """
        if not settings.enable_query_extraction:
            return user_input

        if not user_input or not user_input.strip():
            return user_input

        prompt = format_query_extraction_prompt(user_input)
        gen_config = GenerationConfig(
            max_tokens=100,
            temperature=0.3,
            stream=False
        )

        messages = [Message(role="user", content=prompt)]

        # Priority A: Groq API
        try:
            from brain.groq_brain import GroqBrain
            groq_brain = GroqBrain(model=settings.query_extraction_groq_model)

            if groq_brain.is_available():
                result = groq_brain.generate(messages, config=gen_config)

                if isinstance(result, str) and result.strip():
                    extracted = result.strip()
                    if settings.debug:
                        print(f"   Query Extraction (Groq): '{user_input}' -> '{extracted}'")
                    return extracted
        except Exception as e:
            if settings.debug:
                print(f"   Groq Query Extraction fehlgeschlagen: {e}")

        # Priority B: Ollama Fallback
        try:
            from brain.ollama_brain import OllamaBrain
            ollama_brain = OllamaBrain(
                model=settings.query_extraction_ollama_model,
                host=settings.ollama_host
            )

            if ollama_brain.is_available():
                result = ollama_brain.generate(messages, config=gen_config)

                if isinstance(result, str) and result.strip():
                    extracted = result.strip()
                    if settings.debug:
                        print(f"   Query Extraction (Ollama): '{user_input}' -> '{extracted}'")
                    return extracted
        except Exception as e:
            if settings.debug:
                print(f"   Ollama Query Extraction fehlgeschlagen: {e}")

        # Silent Fallback: Originaler User-Input
        if settings.debug:
            print(f"   Query Extraction fehlgeschlagen - nutze Original-Input")
        return user_input

    def search_memory(self, query: str, top_k: Optional[int] = None) -> list[Memory]:
        """
        Sucht nach relevanten Erinnerungen.

        Args:
            query: Suchanfrage
            top_k: Anzahl der Ergebnisse (default: aus settings)

        Returns:
            Liste von Memory-Objekten, sortiert nach Relevanz
        """
        if top_k is None:
            top_k = settings.memory_top_k

        # Pruefe ob Erinnerungen vorhanden
        if self.collection.count() == 0:
            return []

        # Smart Query Extraction: Optimiere den Query vor der Vektorisierung
        optimized_query = self.extract_search_query(query)

        # Erstelle Query-Embedding
        query_embedding = self.embedder.encode(optimized_query).tolist()
        
        # Suche in ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self.collection.count())
        )
        
        # Konvertiere zu Memory-Objekten
        memories = []
        if results and results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                # ChromaDB gibt Cosine Distance zurück (0-2), nicht Ähnlichkeit
                # 0 = identisch, 1 = orthogonal, 2 = gegensätzlich
                distance = results["distances"][0][i] if results["distances"] else 0
                relevance = max(0, 1 - distance / 2)  # Konvertiere zu 0-1 Relevanz
                
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                
                memory = Memory(
                    id=results["ids"][0][i],
                    content=doc,
                    role=metadata.get("role", "unknown"),
                    timestamp=metadata.get("timestamp", ""),
                    mem_type=metadata.get("type", "interaction"),
                    relevance_score=relevance
                )
                memories.append(memory)
        
        return memories
    
    def get_recent_memories(self, limit: int = 10) -> list[Memory]:
        """
        Holt die neuesten Erinnerungen.
        
        Args:
            limit: Maximale Anzahl
        
        Returns:
            Liste von Memory-Objekten
        """
        if self.collection.count() == 0:
            return []
        
        # Hole alle Erinnerungen
        results = self.collection.get(
            limit=limit,
            include=["documents", "metadatas"]
        )
        
        memories = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"]):
                metadata = results["metadatas"][i] if results["metadatas"] else {}
                
                # Sicherstellen, dass metadata ein Dict ist
                if not isinstance(metadata, dict):
                    metadata = {}
                
                memory = Memory(
                    id=results["ids"][i] if i < len(results["ids"]) else str(uuid.uuid4()),
                    content=doc if isinstance(doc, str) else str(doc),
                    role=metadata.get("role", "unknown"),
                    timestamp=metadata.get("timestamp", ""),
                    mem_type=metadata.get("type", "interaction")
                )
                memories.append(memory)
        
        # Sortiere nach Timestamp (neueste zuerst)
        memories.sort(key=lambda m: m.timestamp, reverse=True)
        
        return memories[:limit]
    
    def delete_memories(self, ids: list[str]):
        """
        Loescht Erinnerungen anhand ihrer IDs.
        
        Args:
            ids: Liste der zu loeschenden IDs
        """
        if not ids:
            return
            
        self.collection.delete(ids=ids)
        if settings.debug:
            print(f"   {len(ids)} Erinnerungen geloescht.")

    def clear_memory(self) -> int:
        """
        Loescht alle Erinnerungen.
        
        Returns:
            Anzahl der geloeschten Erinnerungen
        """
        count = self.collection.count()
        
        # Collection loeschen und neu erstellen
        self.client.delete_collection(settings.chroma_collection_name)
        self.collection = self.client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"description": "CHAPiE episodic memory"}
        )
        
        print(f"   {count} Erinnerungen geloescht")
        return count
    
    def get_memory_count(self) -> int:
        """Gibt die Anzahl der gespeicherten Erinnerungen zurueck."""
        return self.collection.count()

    def reset_all_memories(self) -> str:
        """
        Loescht ALLE Erinnerungen aus CHAPiE's Gedächtnis.

        WARNING: Diese Aktion ist irreversibel! Alle persönlichen
        Informationen, Gesprächsverläufe und Kontext werden permanent
        gelöscht.

        Returns:
            Bestätigungsnachricht
        """
        count = self.get_memory_count()

        if count == 0:
            return "ℹ️  Gedächtnis ist bereits leer."

        print()
        print("═══════════════════════════════════════════════════════════════════")
        print("⚠️  WARNUNG - GESAMTES GEDÄCHTNIS LÖSCHEN")
        print("═══════════════════════════════════════════════════════════════════")
        print(f"Es werden {count} Erinnerungen permanent gelöscht!")
        print("CHAPiE wird sich nach dem Löschen an nichts mehr erinnern.")
        print()
        print("Drücke ENTER zum Bestätigen oder STRG+C zum Abbrechen...")
        print("═══════════════════════════════════════════════════════════════════")

        try:
            input()
        except KeyboardInterrupt:
            print("\n❌ Abgebrochen - Gedächtnis wurde nicht gelöscht.")
            return "Abgebrochen"

        # Collection löschen und neu erstellen
        self.client.delete_collection(settings.chroma_collection_name)
        self.collection = self.client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"description": "CHAPiE episodic memory"}
        )

        print(f"✅ {count} Erinnerungen wurden gelöscht.")
        print("═══════════════════════════════════════════════════════════════════")
        print()

        return f"✅ Gedächtnis erfolgreich zurückgesetzt ({count} Erinnerungen gelöscht)"
    
    def format_memories_for_prompt(self, memories: list[Memory]) -> str:
        """
        Formatiert Erinnerungen fuer den LLM-Prompt.
        
        Args:
            memories: Liste von Memory-Objekten
        
        Returns:
            Formatierter String fuer den Prompt
        """
        if not memories:
            return "Keine relevanten Erinnerungen gefunden."
        
        lines = ["=== RELEVANTE ERINNERUNGEN ==="]
        for i, mem in enumerate(memories, 1):
            role_label = "USER" if mem.role == "user" else "CHAPIE"
            score_percent = int(mem.relevance_score * 100)
            lines.append(f"\n[{i}] {role_label} (Relevanz: {score_percent}%)")
            lines.append(f"    {mem.content}")
        
        return "\n".join(lines)

    def consolidate_memories(self, brain: Any) -> str:
        """
        Fuehrt die Memory-Consolidation (Traum-Phase) durch.
        
        Holt alle Erinnerungen, laesst das LLM eine Zusammenfassung erstellen,
        speichert die Zusammenfassung und loescht die alten Erinnerungen.
        
        Args:
            brain: Brain-Instanz fuer die Generierung
        
        Returns:
            Zusammenfassungstext
        """
        from config.prompts import format_dream_prompt
        
        # Alle Erinnerungen holen
        all_memories = self.get_recent_memories(limit=1000)
        
        if not all_memories:
            return "Keine Erinnerungen zum Konsolidieren vorhanden."
        
        # Debug: Pruefen ob alle Memories korrekt sind
        for mem in all_memories:
            if not hasattr(mem, 'role'):
                return f"Fehler: Memory-Objekt hat kein 'role' Attribut: {mem}"
        
        # Konversation fuer den Traum-Prompt formatieren
        conversation_lines = []
        for mem in all_memories:
            role_label = "User" if mem.role == "user" else "CHAPiE"
            conversation_lines.append(f"{role_label}: {mem.content}")
        
        conversation_text = "\n".join(conversation_lines)
        
        # Traum-Prompt erstellen
        dream_prompt = format_dream_prompt(conversation_text)
        
        try:
            # Zusammenfassung generieren
            gen_config = GenerationConfig(
                max_tokens=500,
                temperature=0.3,
                stream=False,
            )
            summary = brain.generate([Message(role="user", content=dream_prompt)], config=gen_config)
            
            # Sicherstellen, dass summary ein String ist
            if not isinstance(summary, str):
                summary = str(summary)
            
            # Zusammenfassung speichern
            self.add_memory(summary, role="assistant", mem_type="summary")
            
            # Alte Erinnerungen loeschen (nur interaction-Typ)
            old_ids = [mem.id for mem in all_memories if mem.mem_type == "interaction"]
            if old_ids:
                self.delete_memories(old_ids)
            
            return f"💤 Traum-Phase abgeschlossen. {len(old_ids)} Erinnerungen konsolidiert.\n\nZusammenfassung:\n{summary}"
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return f"Fehler bei der Memory-Consolidation: {str(e)}\n\nDetails:\n{error_details}"


# === Test-Funktion ===
if __name__ == "__main__":
    from rich.console import Console
    from rich.panel import Panel
    
    console = Console()
    console.print(Panel("Memory Engine Test", style="bold blue"))
    
    # Engine initialisieren
    engine = MemoryEngine()
    
    # Test: Erinnerungen hinzufuegen
    console.print("\n[cyan]1. Fuege Test-Erinnerungen hinzu...[/cyan]")
    engine.add_memory("Ich heisse Benjamin und programmiere gerne.", role="user")
    engine.add_memory("Schoen dich kennenzulernen, Benjamin! Was programmierst du am liebsten?", role="assistant")
    engine.add_memory("Ich arbeite gerade an einem KI-Projekt namens CHAPiE.", role="user")
    engine.add_memory("Das klingt spannend! CHAPiE - ein KI-Agent mit Gedaechtnis.", role="assistant")
    
    console.print(f"   {engine.get_memory_count()} Erinnerungen gespeichert")
    
    # Test: Suche
    console.print("\n[cyan]2. Suche nach 'KI Projekt'...[/cyan]")
    results = engine.search_memory("KI Projekt", top_k=3)
    for mem in results:
        console.print(f"   [{mem.role}] {mem.content[:60]}... (Score: {mem.relevance_score:.2f})")
    
    # Test: Formatierung
    console.print("\n[cyan]3. Formatierte Ausgabe:[/cyan]")
    formatted = engine.format_memories_for_prompt(results)
    console.print(formatted)
    
    console.print("\n[green]Memory Engine Test erfolgreich![/green]")
