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

import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from dataclasses import dataclass

# ============================================
# CRITICAL: SQLite Threading Fix for ChromaDB
# ============================================
# ChromaDB uses SQLite internally and can cause Segmentation Faults
# on certain Linux systems due to SQLite threading issues.
# This MUST be set BEFORE importing chromadb.
# ============================================
try:
    import sqlite3
    # Check if we're on a system that might have threading issues
    if hasattr(sqlite3, 'threadsafety'):
        # SQLite threadsafety levels:
        # 0 = single-thread, 1 = multi-thread, 3 = serialized
        if sqlite3.threadsafety < 3:
            print(f"   WARNUNG: SQLite threadsafety={sqlite3.threadsafety} (empfohlen: 3)")
except Exception as e:
    print(f"   SQLite check failed: {e}")

# Set environment variable to help with ChromaDB SQLite issues
os.environ.setdefault("CHROMA_SQLITE_JOURNAL_MODE", "WAL")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")  # Avoid tokenizer warnings

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
    label: str = "original"  # "original" oder "zsm gefasst"


class MemoryEngine:
    """
    Episodisches Gedaechtnis fuer CHAPiE.
    
    Nutzt ChromaDB fuer Vektorspeicherung und
    Sentence-Transformers fuer Embeddings.
    """
    
    def __init__(self):
        """Initialisiert die Memory Engine."""
        print("Initialisiere Memory Engine...")
        
        # Flag für den Modus (persistent vs in-memory)
        self._is_persistent = True
        self._init_failed = False
        
        # Embedding-Modell laden (laeuft lokal) mit Fehlerbehandlung
        print(f"   Lade Embedding-Modell: {settings.embedding_model}")
        try:
            # Versuche zuerst ohne explizites Device (auto-detect)
            self.embedder = SentenceTransformer(settings.embedding_model)
            # Test-Embedding um sicherzustellen, dass es funktioniert
            test_embedding = self.embedder.encode("test")
            # DYNAMISCHE DIMENSION: Speichere die tatsächliche Dimension des Modells
            self.embedding_dim = len(test_embedding)
            print(f"   Embedding-Modell bereit! (Dimension: {self.embedding_dim})")
        except Exception as e:
            print(f"   FEHLER beim Laden des Embedding-Modells: {e}")
            print("   Fallback: Verwende CPU-only Modus")
            try:
                self.embedder = SentenceTransformer(
                    settings.embedding_model,
                    device='cpu'  # Erzwinge CPU-Modus bei GPU-Problemen
                )
                # Auch hier Dimension ermitteln
                test_embedding = self.embedder.encode("test")
                self.embedding_dim = len(test_embedding)
            except Exception as e2:
                print(f"   KRITISCH: Embedding-Modell konnte nicht geladen werden: {e2}")
                self.embedder = None
                self.embedding_dim = 384  # Default für all-MiniLM-L6-v2
                self._init_failed = True
        
        # ChromaDB Client initialisieren mit robuster Fehlerbehandlung
        self.client = None
        self.collection = None
        
        # Strategie: Versuche zuerst persistent (fuer Ubuntu Server)
        # Fallback auf In-Memory nur bei Fehler (Windows SQLite-Probleme)
        if not self._init_failed:
            self._init_chromadb_persistent()
        
        # Fallback auf In-Memory wenn persistent fehlschlaegt
        if self.client is None:
            print("   Fallback: Verwende ChromaDB In-Memory Modus...")
            self._init_chromadb_inmemory()
        
        # Finale Status-Meldung
        if self.collection is not None:
            try:
                memory_count = self.collection.count()
                mode = "persistent" if self._is_persistent else "in-memory"
                print(f"   Memory Engine bereit! ({memory_count} Erinnerungen, Modus: {mode})")
            except Exception as e:
                print(f"   Memory Engine bereit! (Modus: {'persistent' if self._is_persistent else 'in-memory'})")
        else:
            print("   WARNUNG: Memory Engine im degradierten Modus (keine Speicherung)")
            self._init_failed = True
    
    def _init_chromadb_persistent(self):
        """Versucht ChromaDB im persistenten Modus zu initialisieren."""
        print(f"   Verbinde mit ChromaDB (persistent: {CHROMA_DB_DIR})")
        try:
            # Stelle sicher, dass das Verzeichnis existiert
            os.makedirs(str(CHROMA_DB_DIR), exist_ok=True)
            
            # ChromaDB Settings für bessere Stabilität
            chroma_settings = ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
                is_persistent=True
            )
            
            self.client = chromadb.PersistentClient(
                path=str(CHROMA_DB_DIR),
                settings=chroma_settings
            )
            
            # Collection erstellen oder laden
            self.collection = self.client.get_or_create_collection(
                name=settings.chroma_collection_name,
                metadata={"description": "CHAPiE episodic memory"}
            )
            
            # Test-Zugriff um sicherzustellen, dass es funktioniert
            _ = self.collection.count()
            
            self._is_persistent = True
            print(f"   ChromaDB persistent verbunden!")
            
        except Exception as e:
            print(f"   FEHLER bei ChromaDB persistent: {e}")
            print(f"   Fehlertyp: {type(e).__name__}")
            self.client = None
            self.collection = None
            self._is_persistent = False
    
    def _init_chromadb_inmemory(self):
        """Fallback: ChromaDB im In-Memory Modus."""
        print("   Fallback: Versuche ChromaDB In-Memory Modus...")
        try:
            self.client = chromadb.Client(
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    is_persistent=False
                )
            )
            
            self.collection = self.client.get_or_create_collection(
                name=settings.chroma_collection_name,
                metadata={"description": "CHAPiE episodic memory (in-memory)"}
            )
            
            self._is_persistent = False
            print("   ChromaDB In-Memory Modus aktiv (Daten werden nicht dauerhaft gespeichert!)")
            
        except Exception as e:
            print(f"   KRITISCH: Auch In-Memory Modus fehlgeschlagen: {e}")
            self.client = None
            self.collection = None
    
    def add_memory(self, content: str, role: str = "user", mem_type: str = "interaction", label: str = "original", source: str = "conversation") -> str:
        """
        Speichert eine neue Erinnerung.
        
        ROBUST: Bei ChromaDB-Konflikten (z.B. gleichzeitiger Zugriff durch
        Training-Daemon und Web-App) wird mehrfach versucht und Fehler
        werden graceful behandelt ohne den Prozess zu stoppen.

        Args:
            content: Der zu speichernde Text
            role: "user" oder "assistant"
            mem_type: "interaction" oder "summary"
            label: "original", "zsm gefasst" oder "self_reflection"
            source: "conversation" oder "self_reflection" (fuer Deep Think)

        Returns:
            Die ID der gespeicherten Erinnerung oder "" bei Fehler
        """
        # Prüfe ob Collection verfügbar ist
        if self.collection is None:
            if settings.debug:
                print("   WARNUNG: Memory-Speicherung übersprungen (keine Collection)")
            return ""
        
        import time
        
        max_retries = 5  # Erhöht von 3 auf 5 für bessere Robustheit
        base_delay = 0.3  # Sekunden (Basis für exponential backoff)
        
        for attempt in range(max_retries):
            try:
                # Generiere eindeutige ID
                memory_id = str(uuid.uuid4())
                timestamp = datetime.now(timezone.utc).isoformat()

                # Erstelle Embedding mit Fehlerbehandlung
                try:
                    if self.embedder is not None:
                        embedding = self.embedder.encode(content).tolist()
                    else:
                        # Kein Embedder verfügbar - verwende Dummy
                        embedding = [0.0] * self.embedding_dim
                except Exception as embed_err:
                    error_msg = f"Embedding-Fehler für '{content[:50]}...': {str(embed_err)}"
                    print(f"   WARNUNG: {error_msg}")
                    # DYNAMIC: Verwende die tatsächliche Dimension des geladenen Modells
                    # statt hardcodierter 384 (die nur für all-MiniLM-L6-v2 gilt)
                    embedding = [0.0] * self.embedding_dim
                    # Logge den Fehler für spätere Analyse
                    import logging
                    logging.warning(f"Memory embedding failed, using dummy ({self.embedding_dim}D): {error_msg}")

                # Speichere in ChromaDB mit erweitertem Metadata
                self.collection.add(
                    ids=[memory_id],
                    embeddings=[embedding],
                    documents=[content],
                    metadatas=[{
                        "role": role,
                        "timestamp": timestamp,
                        "type": mem_type,
                        "label": label,
                        "source": source
                    }]
                )

                if settings.debug:
                    print(f"   Memory gespeichert: [{role}] [{source}] {content[:50]}...")

                return memory_id
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # Bei Locking/Busy-Fehlern: Retry mit Exponential Backoff
                if any(kw in error_msg for kw in ["lock", "busy", "timeout", "database is locked"]):
                    if attempt < max_retries - 1:
                        # Exponential Backoff: 0.3s, 0.6s, 1.2s, 2.4s...
                        wait_time = base_delay * (2 ** attempt)
                        if settings.debug:
                            print(f"   Memory-Speicherung blockiert (Versuch {attempt+1}/{max_retries}), warte {wait_time:.1f}s...")
                        time.sleep(wait_time)
                        continue
                
                # Bei anderen Fehlern oder nach allen Retries: Warnen aber weitermachen
                if settings.debug:
                    print(f"   WARNUNG: Memory konnte nicht gespeichert werden: {e}")
                
                # Nicht den Prozess stoppen, nur leere ID zurueckgeben
                return ""
        
        return ""
    
    
    def search_self_reflections(self, query: str, top_k: int = 5, min_relevance: float = 0.0) -> list[Memory]:
        """
        Sucht speziell nach Selbstreflexions-Erinnerungen.
        
        Priorisiert Memories mit source="self_reflection".
        
        Args:
            query: Suchanfrage
            top_k: Anzahl Ergebnisse
            min_relevance: Minimale Relevanz (0-1), Default 0.0 fuer Abwaertskompatibilitaet
            
        Returns:
            Liste von Memory-Objekten
        """
        # Prüfe ob Collection verfügbar ist
        if self.collection is None:
            return []
        
        if self.collection.count() == 0:
            return []
        
        # Nutze Global Setting falls nicht spezifiziert (aber erlaube Override)
        if min_relevance == 0.0 and hasattr(settings, 'memory_min_relevance'):
             min_relevance = settings.memory_min_relevance
        
        # Versuche zuerst mit Filter nach self_reflection
        try:
            try:
                if self.embedder is not None:
                    query_embedding = self.embedder.encode(query).tolist()
                else:
                    query_embedding = [0.0] * self.embedding_dim
            except Exception as embed_err:
                error_msg = f"Filtered search embedding failed for '{query[:50]}...': {str(embed_err)}"
                print(f"   WARNUNG: {error_msg}")
                # DYNAMIC: Nutze die beim Init ermittelte Dimension
                query_embedding = [0.0] * self.embedding_dim
                import logging
                logging.warning(f"Memory filtered search embedding failed, using dummy ({self.embedding_dim}D): {error_msg}")
            
            # Suche mit Filter
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k * 2, self.collection.count()), # Hole mehr für Filterung
                where={"source": "self_reflection"}
            )
            
            # Wenn keine Selbstreflexionen, normale Suche
            if not results["documents"] or not results["documents"][0]:
                return self.search_memory(query, top_k=top_k, min_relevance=min_relevance)
            
            # Konvertiere zu Memory-Objekten und filtere
            memories = []
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i] if results["distances"] else 0
                relevance = max(0, 1 - distance / 2)
                
                # Filterung nach Relevanz
                if relevance < min_relevance:
                    continue

                metadata = results["metadatas"][0][i] if results["metadatas"] else {}

                # Normalize metadata to a dict to avoid None attribute errors
                if not isinstance(metadata, dict):
                    metadata = {}
                
                memory = Memory(
                    id=results["ids"][0][i],
                    content=doc,
                    role=metadata.get("role", "unknown"),
                    timestamp=metadata.get("timestamp", ""),
                    mem_type=metadata.get("type", "interaction"),
                    relevance_score=relevance,
                    label=metadata.get("label", "self_reflection")
                )
                memories.append(memory)
            
            # Sortiere nach Relevanz absteigend
            memories.sort(key=lambda x: x.relevance_score, reverse=True)
            
            return memories[:top_k]
            
        except Exception as e:
            # Fallback auf normale Suche
            if settings.debug:
                print(f"   Self-Reflection Suche fehlgeschlagen: {e}")
            return self.search_memory(query, top_k=top_k, min_relevance=min_relevance)

    def extract_search_query(self, user_input: str) -> str:
        """
        Extrahiert optimierte Suchbegriffe aus dem User-Input.

        Nutzt Tri-Strategy:
        1. Priority: Manual (Kurze Inputs < 6 Wörter)
        2. Priority: Groq API (llama-3.1-8b-instant)
        3. Fallback: Ollama (qwen2.5:1.5b)
        4. Silent Fallback: Originaler User-Input bei komplettem Fehler

        Args:
            user_input: Der originale User-Input

        Returns:
            Optimierter Such-Query oder Original-Input bei Fehler
        """
        if not settings.enable_query_extraction:
            return user_input

        if not user_input or not user_input.strip():
            return user_input

        # === 1. Manual Optimization (für kurze Inputs) ===
        words = user_input.split()
        if len(words) < 6:
            # Deutsche Stoppwörter (Füllwörter), die ignoriert werden sollen
            stop_words = {
                "ich", "du", "er", "sie", "es", "wir", "ihr", "sie",
                "der", "die", "das", "ein", "eine", "einen", "einem", "einer",
                "und", "oder", "aber", "doch", "als", "wie",
                "bin", "bist", "ist", "sind", "war", "wäre", "haben", "hat",
                "mir", "dir", "ihm", "ihr", "uns", "euch", "ihnen",
                "mich", "dich", "sich",
                "hallo", "hi", "hey", "moin", "servus", "guten", "tag", "morgen", "abend",
                "bitte", "danke", "mal", "halt", "eben", "so", "doch", "ja", "nein"
            }
            
            # Filtere Stoppwörter raus (case-insensitive)
            keywords = [w for w in words if w.lower().strip(".,!?") not in stop_words]
            
            if keywords:
                extracted = " ".join(keywords)
                if settings.debug:
                    print(f"   Query Extraction (Manual): '{user_input}' -> '{extracted}'")
                return extracted
            else:
                # Wenn nur Stoppwörter übrig bleiben (z.B. "Hallo, wie geht es?"), nimm Original
                return user_input

        prompt = format_query_extraction_prompt(user_input)

        gen_config = GenerationConfig(
            max_tokens=100,
            temperature=0.3,
            stream=False
        )

        messages = [Message(role="user", content=prompt)]
        
        query_provider = getattr(settings, 'query_extraction_provider', None) or settings.llm_provider

        if query_provider == LLMProvider.GROQ or settings.llm_provider == LLMProvider.GROQ:
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

    def search_memory(self, query: str, top_k: Optional[int] = None, min_relevance: float = 0.0) -> list[Memory]:
        """
        Sucht nach relevanten Erinnerungen.
        
        ROBUST: Bei ChromaDB-Konflikten wird graceful eine leere Liste
        zurueckgegeben statt den Prozess zu stoppen.

        Args:
            query: Suchanfrage
            top_k: Anzahl der Ergebnisse (default: aus settings)
            min_relevance: Minimale Relevanz (0-1)

        Returns:
            Liste von Memory-Objekten, sortiert nach Relevanz
        """
        # Prüfe ob Collection verfügbar ist
        if self.collection is None:
            return []
        
        import time
        
        if top_k is None:
            top_k = settings.memory_top_k
            
        # Nutze Global Setting falls nicht spezifiziert
        if min_relevance == 0.0 and hasattr(settings, 'memory_min_relevance'):
             min_relevance = settings.memory_min_relevance

        max_retries = 3
        retry_delay = 0.3
        
        for attempt in range(max_retries):
            try:
                # Pruefe ob Erinnerungen vorhanden
                if self.collection.count() == 0:
                    return []

                # Smart Query Extraction: Optimiere den Query vor der Vektorisierung
                optimized_query = self.extract_search_query(query)

                # Erstelle Query-Embedding mit Fehlerbehandlung
                try:
                    if self.embedder is not None:
                        query_embedding = self.embedder.encode(optimized_query).tolist()
                    else:
                        query_embedding = [0.0] * self.embedding_dim
                except Exception as embed_err:
                    error_msg = f"Search embedding failed for '{query[:50]}...': {str(embed_err)}"
                    print(f"   WARNUNG: {error_msg}")
                    # DYNAMIC: Nutze die beim Init ermittelte Dimension statt hardcodiert 384
                    query_embedding = [0.0] * self.embedding_dim
                    import logging
                    logging.warning(f"Memory search embedding failed, using dummy ({self.embedding_dim}D): {error_msg}")

                # Suche in ChromaDB - Hole mehr Ergebnisse zum Filtern
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(top_k * 2, self.collection.count()) 
                )

                # Konvertiere zu Memory-Objekten
                memories = []
                if results and results["documents"] and results["documents"][0]:
                    for i, doc in enumerate(results["documents"][0]):
                        # ChromaDB gibt Cosine Distance zurueck (0-2), nicht Aehnlichkeit
                        # 0 = identisch, 1 = orthogonal, 2 = gegensaetzlich
                        distance = results["distances"][0][i] if results["distances"] else 0
                        relevance = max(0, 1 - distance / 2)  # Konvertiere zu 0-1 Relevanz
                        
                        # FILTERUNG NACH RELEVANZ
                        if relevance < min_relevance:
                            continue

                        metadata = results.get("metadatas") or []
                        metadata = metadata[0][i] if metadata and metadata[0] else {}

                        # Ensure metadata is a dict to prevent NoneType errors
                        if not isinstance(metadata, dict):
                            metadata = metadata or {}

                        memory = Memory(
                            id=results["ids"][0][i],
                            content=doc,
                            role=metadata.get("role", "unknown"),
                            timestamp=metadata.get("timestamp", ""),
                            mem_type=metadata.get("type", "interaction"),
                            relevance_score=relevance,
                            label=metadata.get("label", "original")
                        )
                        memories.append(memory)
                
                # Sortiere explizit nach Relevanz (Sicherheitshalber)
                memories.sort(key=lambda m: m.relevance_score, reverse=True)

                return memories[:top_k]
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # Bei Locking/Busy-Fehlern: Retry mit Exponential Backoff
                if any(kw in error_msg for kw in ["lock", "busy", "timeout", "database is locked"]):
                    if attempt < max_retries - 1:
                        # Exponential Backoff: 0.3s, 0.6s, 1.2s...
                        wait_time = retry_delay * (2 ** attempt)
                        if settings.debug:
                            print(f"   Memory-Suche blockiert (Versuch {attempt+1}/{max_retries}), warte {wait_time:.1f}s...")
                        time.sleep(wait_time)
                        continue
                
                # Bei anderen Fehlern: Warnen und leere Liste zurueckgeben
                if settings.debug:
                    print(f"   WARNUNG: Memory-Suche fehlgeschlagen: {e}")
                
                return []
        
        return []
    

    def get_recent_memories(self, limit: int = 10, offset: int = 0) -> list[Memory]:
        """
        Holt die neuesten Erinnerungen mit Pagination-Support.

        Args:
            limit: Maximale Anzahl pro Seite
            offset: Anzahl der zu überspringenden Einträge (für Pagination)

        Returns:
            Liste von Memory-Objekten
        """
        # Prüfe ob Collection verfügbar ist
        if self.collection is None:
            return []
        
        total_count = self.collection.count()
        if total_count == 0:
            return []

        # Hole alle und sortiere dann (ChromaDB hat kein natives Offset)
        # Für sehr große DBs: Hole nur was nötig ist
        fetch_limit = min(offset + limit, total_count)
        
        results = self.collection.get(
            limit=fetch_limit,
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
                    mem_type=metadata.get("type", "interaction"),
                    label=metadata.get("label", "original")
                )
                memories.append(memory)

        # Sortiere nach Timestamp (neueste zuerst)
        memories.sort(key=lambda m: m.timestamp, reverse=True)

        # Wende Offset und Limit an
        return memories[offset:offset + limit]

    
    def delete_memories(self, ids: list[str]):
        """
        Loescht Erinnerungen anhand ihrer IDs.
        
        Args:
            ids: Liste der zu loeschenden IDs
        """
        if not ids:
            return
        
        # Prüfe ob Collection verfügbar ist
        if self.collection is None:
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
        # Prüfe ob Collection und Client verfügbar sind
        if self.collection is None or self.client is None:
            return 0
        
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
        if self.collection is None:
            return 0
        try:
            return self.collection.count()
        except Exception as e:
            print(f"WARNUNG: Konnte Memory-Count nicht ermitteln: {e}")
            return 0

    def health_check(self) -> dict:
        """Führt einen Health-Check der Memory-Engine durch."""
        status = {
            "memory_count": 0,
            "embedding_model_loaded": False,
            "chromadb_connected": False,
            "is_persistent": getattr(self, '_is_persistent', False),
            "errors": []
        }

        if self.collection is None:
            status["errors"].append("ChromaDB: Collection nicht verfügbar")
        else:
            try:
                status["memory_count"] = self.collection.count()
                status["chromadb_connected"] = True
            except Exception as e:
                status["errors"].append(f"ChromaDB: {str(e)}")

        if self.embedder is None:
            status["errors"].append("Embedding: Modell nicht geladen")
        else:
            try:
                # Test-Embedding
                test_embed = self.embedder.encode("health check")
                status["embedding_model_loaded"] = len(test_embed) > 0
            except Exception as e:
                status["errors"].append(f"Embedding: {str(e)}")

        return status

    def reset_all_memories(self) -> str:
        """
        Loescht ALLE Erinnerungen aus CHAPiE's Gedächtnis.

        WARNING: Diese Aktion ist irreversibel! Alle persönlichen
        Informationen, Gesprächsverläufe und Kontext werden permanent
        gelöscht.

        Returns:
            Bestätigungsnachricht
        """
        # Prüfe ob Client und Collection verfügbar sind
        if self.client is None or self.collection is None:
            return "⚠️ Gedächtnis nicht verfügbar (ChromaDB nicht initialisiert)"
        
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

    def _parse_bullet_points(self, text: str) -> list[str]:
        """
        Parst einen Text und extrahiert alle Stichpunkte als einzelne Elemente.
        
        Unterstuetzt:
        - Bullet-Points mit -, *, •
        - Nummerierte Listen (1., 2., 1), 2) etc.)
        - Mehrzeilige Stichpunkte (Einrueckung wird beruecksichtigt)
        
        Args:
            text: Der zu parsende Text
            
        Returns:
            Liste von einzelnen Stichpunkten
        """
        import re
        
        bullet_points = []
        current_point = []
        
        # Regex fuer Bullet-Point-Marker
        bullet_pattern = re.compile(r'^\s*([-*•]|\d{1,2}[\.\)])\s+')
        
        for line in text.split('\n'):
            stripped = line.strip()
            
            # Leere Zeilen beenden aktuellen Punkt
            if not stripped:
                if current_point:
                    full_point = ' '.join(current_point).strip()
                    if len(full_point) > 5:
                        bullet_points.append(full_point)
                    current_point = []
                continue
            
            # Check ob Zeile mit Bullet beginnt
            match = bullet_pattern.match(line)
            if match:
                # Vorherigen Punkt speichern
                if current_point:
                    full_point = ' '.join(current_point).strip()
                    if len(full_point) > 5:
                        bullet_points.append(full_point)
                    current_point = []
                
                # Neuen Punkt starten (ohne Bullet-Marker)
                clean_text = bullet_pattern.sub('', line).strip()
                if clean_text:
                    current_point.append(clean_text)
            elif current_point:
                # Fortsetzung des aktuellen Punkts (eingerueckte Zeile)
                current_point.append(stripped)
            else:
                # Zeile ohne Bullet-Marker und kein aktiver Punkt
                # Behandle als eigenstaendigen Punkt wenn genuegend Inhalt
                if len(stripped) > 10:
                    bullet_points.append(stripped)
        
        # Letzten Punkt nicht vergessen
        if current_point:
            full_point = ' '.join(current_point).strip()
            if len(full_point) > 5:
                bullet_points.append(full_point)
        
        return bullet_points

    def consolidate_memories(self, brain: Any) -> str:
        """
        Fuehrt die Memory-Consolidation (Traum-Phase) durch.
        
        Robuste Version mit:
        - Chunking (Batch-Verarbeitung) bei vielen Erinnerungen
        - Fehlerbehandlung für Token-Limits (413 Errors)
        - Atomare Operationen (Löschen erst nach Speichern)
        - Unbegrenzte Verarbeitung (kein Limit mehr)
        """
        from config.prompts import format_dream_prompt

        # Erinnerungen holen - UNBEGRENZT (alle Interaction-Erinnerungen)
        total_count = self.get_memory_count()
        all_memories = self.get_recent_memories(limit=total_count)
        interaction_memories = [m for m in all_memories if m.mem_type == "interaction"]

        if not interaction_memories:
            return "Keine neuen Erinnerungen zum Konsolidieren vorhanden."

        # Chunking-Konfiguration
        BATCH_SIZE = 50
        total_memories = len(interaction_memories)
        
        # In Batches aufteilen
        batches = [interaction_memories[i:i + BATCH_SIZE] for i in range(0, total_memories, BATCH_SIZE)]
        
        summary_log = []
        errors = []
        consolidated_total = 0
        deleted_total = 0
        
        for i, batch in enumerate(batches):
            batch_id = f"Batch {i+1}/{len(batches)}"
            
            try:
                # 1. Konversation formatieren
                conversation_lines = []
                for mem in batch:
                    role_label = "User" if mem.role == "user" else "CHAPiE"
                    conversation_lines.append(f"{role_label}: {mem.content}")
                
                conversation_text = "\n".join(conversation_lines)
                dream_prompt = format_dream_prompt(conversation_text)
                
                # 2. Generierung mit Error Handling
                try:
                    gen_config = GenerationConfig(
                        max_tokens=1000, # Etwas mehr Raum geben
                        temperature=0.3,
                        stream=False
                    )
                    summary = brain.generate([Message(role="user", content=dream_prompt)], config=gen_config)
                except Exception as api_err:
                    err_msg = str(api_err)
                    if "413" in err_msg or "too large" in err_msg.lower():
                        errors.append(f"{batch_id}: Token Limit überschritten - Erinnerungen bleiben erhalten.")
                        continue # Batch überspringen, nichts löschen
                    else:
                        raise api_err # Anderen Fehler weiterwerfen

                if not isinstance(summary, str):
                    summary = str(summary)
                
                # 3. Parsen und Speichern (NEUE Memories)
                bullet_points = self._parse_bullet_points(summary)
                if not bullet_points:
                    errors.append(f"{batch_id}: Keine Zusammenfassung generiert.")
                    continue

                for point in bullet_points:
                    self.add_memory(point, role="assistant", mem_type="summary", label="zsm gefasst")
                    consolidated_count = 0 # Nur für Logik
                
                # 4. Löschen der ALTEN Memories (nur wenn wir bis hier kommen)
                batch_ids = [mem.id for mem in batch]
                if batch_ids:
                    self.delete_memories(batch_ids)
                    deleted_total += len(batch_ids)
                
                summary_log.append(f"✅ {batch_id}: {len(bullet_points)} Fakten extrahiert.")
                consolidated_total += len(bullet_points)
                
            except Exception as e:
                import traceback
                errors.append(f"❌ {batch_id} Fehler: {str(e)}")
                if settings.debug:
                    print(traceback.format_exc())
        
        # Abschlussbericht
        result_msg = f"Traum-Phase abgeschlossen.\n"
        result_msg += f"- Verarbeitet: {deleted_total}/{total_memories} Erinnerungen\n"
        result_msg += f"- Neu erstellt: {consolidated_total} Fakten\n\n"
        
        if summary_log:
            result_msg += "Verlauf:\n" + "\n".join(summary_log)
            
        if errors:
            result_msg += "\n\n⚠️ Warnungen:\n" + "\n".join(errors)
            
        return result_msg

    def think_deep(self, brain: Any, topic: str = "", steps: int = 10, delay: float = 1.0):
        """
        Fuehrt einen tiefen Reflektionsprozess durch (Think-Modus).
        
        Iteriert ueber mehrere Denkschritte, sucht relevante Erinnerungen,
        formuliert Gedanken und speichert diese als neue Erinnerungen.
        
        Args:
            brain: Brain-Instanz fuer die Generierung
            topic: Optionales Thema fuer die Reflektion
            steps: Anzahl der Denkschritte (default: 10)
            delay: Verzoegerung zwischen Schritten in Sekunden (default: 1.0)
            
        Yields:
            Dict mit step, thought, memories_found fuer jeden Schritt
        """
        import time
        
        # Think-Prompt Template
        THINK_PROMPT_TEMPLATE = """Du bist CHAPPiE und befindest dich in einer tiefen Reflektionsphase.

Dein aktueller Denkschritt: {step} von {total_steps}
Thema der Reflektion: {topic}

VORHERIGER GEDANKE:
{previous_thought}

RELEVANTE ERINNERUNGEN:
{memories}

AUFGABE:
Reflektiere ueber das Thema basierend auf deinem vorherigen Gedanken und den Erinnerungen.
Formuliere einen neuen, tieferen Gedanken der auf den bisherigen aufbaut.

REGELN:
- Sei introspektiv und analytisch
- Verbinde verschiedene Informationen miteinander
- Ziehe Schlussfolgerungen
- Formuliere neue Fragen oder Erkenntnisse
- Maximal 2-3 Saetze

Dein naechster Gedanke:"""

        # Standard-Thema wenn keins angegeben
        if not topic:
            topic = "Allgemeine Selbstreflexion ueber meine Erfahrungen und Erkenntnisse"
        
        previous_thought = "Ich beginne meine Reflektionsphase..."
        
        for step in range(1, steps + 1):
            # Suche relevante Erinnerungen basierend auf Thema und vorherigem Gedanken
            search_query = f"{topic} {previous_thought}"
            memories = self.search_memory(search_query, top_k=3, min_relevance=settings.memory_min_relevance)
            memories_text = self.format_memories_for_prompt(memories)
            
            # Prompt erstellen
            think_prompt = THINK_PROMPT_TEMPLATE.format(
                step=step,
                total_steps=steps,
                topic=topic,
                previous_thought=previous_thought,
                memories=memories_text
            )
            
            try:
                # Gedanken generieren (hoeheres Token-Limit fuer tiefere Gedanken)
                gen_config = GenerationConfig(
                    max_tokens=5000,
                    temperature=0.7,
                    stream=False,
                )
                thought = brain.generate([Message(role="user", content=think_prompt)], config=gen_config)
                
                # Sicherstellen, dass thought ein String ist
                if not isinstance(thought, str):
                    thought = str(thought)
                
                thought = thought.strip()
                
                # Gedanken als Erinnerung speichern (Self-Learning)
                self.add_memory(
                    f"[Reflektion Schritt {step}] {thought}",
                    role="assistant",
                    mem_type="interaction",
                    label="original"
                )
                
                # Ergebnis zurueckgeben
                yield {
                    "step": step,
                    "total_steps": steps,
                    "thought": thought,
                    "memories_found": len(memories),
                    "memories": [m.content[:100] for m in memories]
                }
                
                # Aktuellen Gedanken fuer naechste Iteration speichern
                previous_thought = thought
                
                # Verzoegerung (ausser beim letzten Schritt)
                if step < steps:
                    time.sleep(delay)
                    
            except Exception as e:
                yield {
                    "step": step,
                    "total_steps": steps,
                    "thought": f"Fehler bei Schritt {step}: {str(e)}",
                    "memories_found": 0,
                    "memories": [],
                    "error": True
                }
                break


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
