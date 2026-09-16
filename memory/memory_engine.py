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
import uuid
import re
import json
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional, Any
from pathlib import Path
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

from config.config import (
    DEFAULT_CHROMA_COLLECTION,
    LEGACY_CHROMA_COLLECTION,
    settings,
    CHROMA_DB_DIR,
    LLMProvider,
    get_memory_association_config,
    get_forgetting_curve_config,
)
from memory.forgetting_curve import get_forgetting_curve
from brain import get_brain
from brain.base_brain import GenerationConfig, Message
from brain.response_parser import looks_like_model_error
from config.prompts import format_query_extraction_prompt, THINK_PROMPT_TEMPLATE, scrub_internal_identifiers  # from config/prompts.py


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
    match_type: str = ""
    matched_terms: str = ""
    source: str = "unknown"
    strength: float = 1.0
    recall_count: int = 0
    last_recall_time: str = ""
    retention: float = 1.0
    association_score: float = 0.0


class MemoryEngine:
    """
    Episodisches Gedaechtnis fuer CHAPiE.
    
    Nutzt ChromaDB fuer Vektorspeicherung und
    Sentence-Transformers fuer Embeddings.
    """
    
    def __init__(self, persist_directory: Optional[Path] = None, collection_name: Optional[str] = None):
        """Initialisiert die Memory Engine."""
        self.persist_directory = Path(persist_directory or settings.chroma_persist_directory or CHROMA_DB_DIR)
        requested_collection = str(collection_name or settings.chroma_collection_name or "").strip()
        if requested_collection == LEGACY_CHROMA_COLLECTION:
            print(
                f"   Alte Chroma-Sammlung '{LEGACY_CHROMA_COLLECTION}' erkannt; "
                f"verwende sichere Sammlung '{DEFAULT_CHROMA_COLLECTION}'."
            )
            requested_collection = DEFAULT_CHROMA_COLLECTION
        self.collection_name = requested_collection or DEFAULT_CHROMA_COLLECTION
        self._operation_lock = threading.RLock()
        self._lock_path = self.persist_directory / ".chappie-memory.lock"
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
                memory_count = self._collection_count()
                mode = "persistent" if self._is_persistent else "in-memory"
                print(f"   Memory Engine bereit! ({memory_count} Erinnerungen, Modus: {mode})")
            except Exception:
                print(f"   Memory Engine bereit! (Modus: {'persistent' if self._is_persistent else 'in-memory'})")
        else:
            print("   WARNUNG: Memory Engine im degradierten Modus (keine Speicherung)")
            self._init_failed = True

    @staticmethod
    def _is_memory_contaminated(content, role="assistant", source="", label=""):
        from memory.retrieval_quality import is_memory_contaminated
        return is_memory_contaminated(content, role=role, source=source, label=label)

    @contextmanager
    def _storage_lock(self):
        """Serialisiert Chroma-Zugriffe auch zwischen API und Daemons.

        ChromaDBs SQLite-/HNSW-Persistenz ist nicht sicher gegen parallele
        Initialisierung und Schreibzugriffe aus mehreren Prozessen. Ein
        recoverable Lockfile verhindert dabei sowohl Datenrennen als auch die
        nativen Segfaults, die zuvor beim gleichzeitigen Oeffnen auftraten.
        """
        operation_lock = getattr(self, "_operation_lock", None)
        if operation_lock is None:
            # Lightweight test doubles and embedding-only callers may build
            # MemoryEngine through __new__ without production init state.
            yield
            return

        with operation_lock:
            if not getattr(self, "_is_persistent", False):
                yield
                return

            self.persist_directory.mkdir(parents=True, exist_ok=True)
            try:
                import fcntl
            except ImportError:  # pragma: no cover - Windows-Fallback
                yield
                return

            with self._lock_path.open("a+", encoding="utf-8") as lock_file:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _collection_count(self) -> int:
        if self.collection is None:
            return 0
        with self._storage_lock():
            return int(self.collection.count())

    def _collection_get(self, **kwargs: Any) -> dict:
        if self.collection is None:
            return {"ids": [], "documents": [], "metadatas": []}
        with self._storage_lock():
            return self.collection.get(**kwargs)

    def _collection_query(self, **kwargs: Any) -> dict:
        if self.collection is None:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
        with self._storage_lock():
            return self.collection.query(**kwargs)

    def _collection_add(self, **kwargs: Any) -> None:
        if self.collection is None:
            return
        with self._storage_lock():
            self.collection.add(**kwargs)

    def _collection_update(self, **kwargs: Any) -> None:
        if self.collection is None or not hasattr(self.collection, "update"):
            return
        with self._storage_lock():
            self.collection.update(**kwargs)

    def _collection_delete(self, **kwargs: Any) -> None:
        if self.collection is None:
            return
        with self._storage_lock():
            self.collection.delete(**kwargs)

    @staticmethod
    def _parse_associations(raw: Any) -> dict[str, float]:
        if isinstance(raw, dict):
            source = raw
        elif isinstance(raw, str) and raw.strip():
            try:
                source = json.loads(raw)
            except (TypeError, ValueError, json.JSONDecodeError):
                source = {}
        else:
            source = {}
        parsed: dict[str, float] = {}
        for memory_id, weight in source.items():
            try:
                numeric = max(0.0, min(1.0, float(weight)))
            except (TypeError, ValueError):
                continue
            if str(memory_id).strip() and numeric > 0:
                parsed[str(memory_id)] = numeric
        return parsed

    @staticmethod
    def _dump_associations(associations: dict[str, float], limit: int) -> str:
        ranked = sorted(associations.items(), key=lambda item: item[1], reverse=True)[: max(0, int(limit))]
        return json.dumps({memory_id: round(weight, 4) for memory_id, weight in ranked}, separators=(",", ":"))

    @staticmethod
    def _metadata_float(metadata: dict[str, Any], key: str, default: float) -> float:
        try:
            return float(metadata.get(key, default))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _metadata_int(metadata: dict[str, Any], key: str, default: int) -> int:
        try:
            return int(metadata.get(key, default))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _hours_since(timestamp: Any) -> float:
        if not timestamp:
            return 24.0
        try:
            parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return max(0.0, (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds() / 3600.0)
        except (TypeError, ValueError):
            return 24.0

    def _memory_retention(self, metadata: dict[str, Any]) -> float:
        strength = self._metadata_float(metadata, "strength", 1.0)
        reference_time = metadata.get("last_recall_time") or metadata.get("timestamp")
        return get_forgetting_curve().calculate_retention(
            self._hours_since(reference_time),
            strength,
        )

    def _retention_adjusted_score(self, semantic_score: float, metadata: dict[str, Any]) -> tuple[float, float]:
        config = get_forgetting_curve_config()
        weight = max(0.0, min(0.5, float(config["memory_strength"]["retrieval_retention_weight"])))
        retention = self._memory_retention(metadata)
        score = float(semantic_score) * ((1.0 - weight) + weight * retention)
        # First-person facts from the user remain slightly stronger evidence
        # than model-written summaries with the same semantic similarity.
        if str(metadata.get("role", "")).casefold() == "user":
            score += 0.025
        return max(0.0, min(1.0, score)), retention

    def _load_associated_memories(
        self,
        direct_memories: list[Memory],
        metadata_by_id: dict[str, dict[str, Any]],
    ) -> list[Memory]:
        config = get_memory_association_config()
        if not config.get("enabled") or not direct_memories:
            return []
        direct_ids = {memory.id for memory in direct_memories}
        spread_candidates: dict[str, tuple[float, float]] = {}
        seed_count = max(1, int(config["retrieval_seed_count"]))
        for seed in direct_memories[:seed_count]:
            links = self._parse_associations(metadata_by_id.get(seed.id, {}).get("associations"))
            for associated_id, edge_weight in links.items():
                if associated_id in direct_ids:
                    continue
                previous = spread_candidates.get(associated_id, (0.0, 0.0))
                activation = seed.relevance_score * edge_weight
                if activation > previous[0] * previous[1]:
                    spread_candidates[associated_id] = (seed.relevance_score, edge_weight)

        ranked_ids = sorted(
            spread_candidates,
            key=lambda memory_id: spread_candidates[memory_id][0] * spread_candidates[memory_id][1],
            reverse=True,
        )[: max(0, int(config["retrieval_max_associations"]))]
        if not ranked_ids:
            return []

        raw = self._collection_get(ids=ranked_ids, include=["documents", "metadatas"])
        ids = raw.get("ids") or []
        documents = raw.get("documents") or []
        metadatas = raw.get("metadatas") or []
        spread_weight = max(0.0, min(0.5, float(config["retrieval_spread_weight"])))
        memories: list[Memory] = []
        for index, memory_id in enumerate(ids):
            metadata = dict(metadatas[index]) if index < len(metadatas) and isinstance(metadatas[index], dict) else {}
            content = str(documents[index] if index < len(documents) else "")
            if self._is_memory_contaminated(
                content,
                role=metadata.get("role", "unknown"),
                source=metadata.get("source", ""),
                label=metadata.get("label", ""),
            ):
                continue
            seed_score, edge_weight = spread_candidates.get(str(memory_id), (0.0, 0.0))
            spread_score = seed_score * (1.0 - spread_weight) + edge_weight * spread_weight
            score, retention = self._retention_adjusted_score(spread_score, metadata)
            metadata_by_id[str(memory_id)] = metadata
            memories.append(Memory(
                id=str(memory_id),
                content=content,
                role=metadata.get("role", "unknown"),
                timestamp=metadata.get("timestamp", ""),
                mem_type=metadata.get("type", "interaction"),
                relevance_score=score,
                label=metadata.get("label", "original"),
                match_type="Association",
                source=metadata.get("source", "unknown"),
                strength=self._metadata_float(metadata, "strength", 1.0),
                recall_count=self._metadata_int(metadata, "recall_count", 0),
                last_recall_time=str(metadata.get("last_recall_time", "")),
                retention=retention,
                association_score=edge_weight,
            ))
        return memories

    def _find_associations_for_embedding(self, embedding: list[float]) -> dict[str, float]:
        config = get_memory_association_config()
        if not config.get("enabled") or not embedding or self.collection is None:
            return {}
        count = self._collection_count()
        if count <= 0:
            return {}
        max_links = max(1, int(config["max_links_per_memory"]))
        raw = self._collection_query(
            query_embeddings=[embedding],
            n_results=min(count, max_links * 3),
        )
        ids = (raw.get("ids") or [[]])[0]
        documents = (raw.get("documents") or [[]])[0]
        metadatas = (raw.get("metadatas") or [[]])[0]
        distances = (raw.get("distances") or [[]])[0]
        candidates: dict[str, float] = {}
        for index, memory_id in enumerate(ids):
            metadata = metadatas[index] if index < len(metadatas) and isinstance(metadatas[index], dict) else {}
            content = documents[index] if index < len(documents) else ""
            if self._is_memory_contaminated(
                str(content or ""),
                role=metadata.get("role", "unknown"),
                source=metadata.get("source", ""),
                label=metadata.get("label", ""),
            ):
                continue
            distance = distances[index] if index < len(distances) else 1.0
            similarity = max(0.0, min(1.0, 1.0 - float(distance)))
            if similarity >= float(config["min_cosine_similarity"]):
                candidates[str(memory_id)] = similarity
        return dict(sorted(candidates.items(), key=lambda item: item[1], reverse=True)[:max_links])

    def _add_reciprocal_associations(self, memory_id: str, associations: dict[str, float]) -> None:
        if not associations:
            return
        config = get_memory_association_config()
        try:
            raw = self._collection_get(ids=list(associations), include=["metadatas"])
            ids = raw.get("ids") or []
            metadatas = raw.get("metadatas") or []
            updates = []
            update_ids = []
            for index, neighbor_id in enumerate(ids):
                metadata = dict(metadatas[index]) if index < len(metadatas) and isinstance(metadatas[index], dict) else {}
                links = self._parse_associations(metadata.get("associations"))
                links[memory_id] = max(links.get(memory_id, 0.0), float(associations.get(str(neighbor_id), 0.0)))
                metadata["associations"] = self._dump_associations(links, int(config["max_links_per_memory"]))
                metadata["memory_schema_version"] = int(config["schema_version"])
                update_ids.append(str(neighbor_id))
                updates.append(metadata)
            if update_ids:
                self._collection_update(ids=update_ids, metadatas=updates)
        except Exception as exc:
            if settings.debug:
                print(f"   Memory-Verknuepfung konnte nicht gespiegelt werden: {exc}")

    def _reinforce_retrieved_memories(
        self,
        memories: list[Memory],
        metadata_by_id: dict[str, dict[str, Any]],
    ) -> None:
        """Persistiert Recall-Staerke und kleine Co-Retrieval-Kanten gebuendelt."""
        config = get_memory_association_config()
        if not config.get("enabled") or not memories:
            return
        selected = [memory for memory in memories if memory.id][: int(config["max_links_per_memory"])]
        now = datetime.now(timezone.utc)
        curve = get_forgetting_curve()
        update_ids: list[str] = []
        updates: list[dict[str, Any]] = []

        for memory in selected:
            metadata = dict(metadata_by_id.get(memory.id, {}))
            strength = self._metadata_float(metadata, "strength", memory.strength)
            recall_count = self._metadata_int(metadata, "recall_count", memory.recall_count)
            last_recall = metadata.get("last_recall_time")
            cooldown_elapsed = self._hours_since(last_recall) * 60.0 >= float(config["recall_cooldown_minutes"])
            changed = metadata.get("memory_schema_version") != int(config["schema_version"])
            if cooldown_elapsed:
                strength = curve.calculate_strength_boost(strength, recall_count)
                recall_count += 1
                metadata["last_recall_time"] = now.isoformat()
                changed = True

            links = self._parse_associations(metadata.get("associations"))
            if cooldown_elapsed:
                for other in selected:
                    if other.id == memory.id:
                        continue
                    links[other.id] = min(
                        1.0,
                        links.get(other.id, 0.0) + float(config["co_retrieval_boost"]),
                    )
            if not changed:
                continue
            metadata.update({
                "strength": round(strength, 4),
                "recall_count": recall_count,
                "associations": self._dump_associations(links, int(config["max_links_per_memory"])),
                "memory_schema_version": int(config["schema_version"]),
            })
            update_ids.append(memory.id)
            updates.append(metadata)

        if update_ids:
            try:
                self._collection_update(ids=update_ids, metadatas=updates)
            except Exception as exc:
                if settings.debug:
                    print(f"   Memory-Recall konnte nicht verstaerkt werden: {exc}")
    
    def _init_chromadb_persistent(self):
        """Versucht ChromaDB im persistenten Modus zu initialisieren."""
        print(f"   Verbinde mit ChromaDB (persistent: {self.persist_directory})")
        try:
            with self._storage_lock():
                # Stelle sicher, dass das Verzeichnis existiert
                os.makedirs(str(self.persist_directory), exist_ok=True)

                chroma_settings = ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                    is_persistent=True
                )

                self.client = chromadb.PersistentClient(
                    path=str(self.persist_directory),
                    settings=chroma_settings
                )

                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine", "description": "CHAPiE episodic memory"}
                )

                # Test-Zugriff um sicherzustellen, dass es funktioniert
                _ = self.collection.count()

                self._is_persistent = True
            print("   ChromaDB persistent verbunden!")
            
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
                name=self.collection_name,
                metadata={"hnsw:space": "cosine", "description": "CHAPiE episodic memory (in-memory)"}
            )
            
            self._is_persistent = False
            print("   ChromaDB In-Memory Modus aktiv (Daten werden nicht dauerhaft gespeichert!)")
            
        except Exception as e:
            print(f"   KRITISCH: Auch In-Memory Modus fehlgeschlagen: {e}")
            self.client = None
            self.collection = None
    
    def add_memory_batch(self, records: list[dict[str, Any]]) -> list[str]:
        """Idempotent, single-embedding batch for the durable promotion worker.

        Errors propagate so the event outbox retries later. No dummy embeddings
        or generated assistant assertions are promoted as conversation facts.
        """
        if not records:
            return []
        if self.collection is None or self.embedder is None:
            raise RuntimeError("Retrieval index or embedder unavailable")
        accepted = [record for record in records if not self._is_memory_contaminated(
            record["content"], role=record.get("role", "user"),
            source=record.get("source", "conversation"), label=record.get("label", "original"),
        )]
        if len(accepted) != len(records):
            raise ValueError("Ineligible record in retrieval promotion batch")
        embeddings = self.embedder.encode([record["content"] for record in records]).tolist()
        if len(embeddings) != len(records):
            raise RuntimeError("Embedding batch size mismatch")
        association_config = get_memory_association_config()
        initial_strength = float(get_forgetting_curve_config()["memory_strength"]["initial"])
        now = datetime.now(timezone.utc).isoformat()
        metadata = []
        for record in records:
            metadata.append({
                "role": record.get("role", "user"), "timestamp": record.get("timestamp", now),
                "type": record.get("type", "interaction"), "label": record.get("label", "original"),
                "source": record.get("source", "conversation"), "strength": initial_strength,
                "recall_count": 0, "last_recall_time": now, "associations": "{}",
                "memory_schema_version": int(association_config["schema_version"]),
                "event_id": record.get("event_id", ""), "session_id": record.get("session_id", ""),
                "retrieval_eligible": True,
            })
        ids = [str(record["id"]) for record in records]
        with self._storage_lock():
            self.collection.upsert(ids=ids, embeddings=embeddings,
                                   documents=[record["content"] for record in records], metadatas=metadata)
        return ids

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

        if role == "assistant" and self._is_memory_contaminated(content, role=role, source=source, label=label):
            if settings.debug:
                print("   HINWEIS: Unzuverlaessige Assistant-Ausgabe nicht als Erinnerung gespeichert")
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

                try:
                    associations = self._find_associations_for_embedding(embedding)
                except Exception as association_error:
                    associations = {}
                    if settings.debug:
                        print(f"   Memory-Verknuepfung uebersprungen: {association_error}")

                association_config = get_memory_association_config()
                forgetting_config = get_forgetting_curve_config()
                initial_strength = float(forgetting_config["memory_strength"]["initial"])

                # Speichere in ChromaDB mit erweitertem Metadata
                self._collection_add(
                    ids=[memory_id],
                    embeddings=[embedding],
                    documents=[content],
                    metadatas=[{
                        "role": role,
                        "timestamp": timestamp,
                        "type": mem_type,
                        "label": label,
                        "source": source,
                        "strength": initial_strength,
                        "recall_count": 0,
                        "last_recall_time": timestamp,
                        "associations": self._dump_associations(
                            associations,
                            int(association_config["max_links_per_memory"]),
                        ),
                        "memory_schema_version": int(association_config["schema_version"]),
                    }]
                )
                self._add_reciprocal_associations(memory_id, associations)

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
        
        if self._collection_count() == 0:
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
            results = self._collection_query(
                query_embeddings=[query_embedding],
                n_results=min(top_k * 2, self._collection_count()), # Hole mehr für Filterung
                where={"source": "self_reflection"}
            )
            
            # Wenn keine Selbstreflexionen, normale Suche
            if not results["documents"] or not results["documents"][0]:
                return self.search_memory(query, top_k=top_k, min_relevance=min_relevance)
            
            # Konvertiere zu Memory-Objekten und filtere
            memories = []
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i] if results["distances"] else 0
                # Chroma's cosine distance is 1 - cosine similarity (not a
                # 0..2 percentage scale). The old division by two made
                # unrelated vectors look relevant and polluted recall.
                relevance = max(0.0, min(1.0, 1.0 - float(distance)))
                
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
                    label=metadata.get("label", "self_reflection"),
                    source=metadata.get("source", "unknown"),
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

    @staticmethod
    def _normalize_german_text(text: str) -> str:
        if not text:
            return ""
        replacements = str.maketrans({
            "ä": "ae",
            "ö": "oe",
            "ü": "ue",
            "ß": "ss",
            "Ä": "ae",
            "Ö": "oe",
            "Ü": "ue",
        })
        return text.translate(replacements).lower()

    @staticmethod
    def _default_stop_words() -> set[str]:
        return {
            "ich", "du", "er", "sie", "es", "wir", "ihr", "uns", "euch", "ihnen",
            "der", "die", "das", "den", "dem", "des", "ein", "eine", "einen", "einem", "einer",
            "und", "oder", "aber", "doch", "weil", "dass", "wenn", "als", "wie", "sowie", "alle",
            "bin", "bist", "ist", "sind", "war", "waren", "waere", "sein", "haben", "hat", "hatte",
            "mich", "dich", "sich", "mir", "dir", "ihm", "ihr",
            "nicht", "auch", "noch", "schon", "nur", "sehr", "mehr", "ganz", "wirklich",
            "fuer", "auf", "an", "in", "im", "am", "bei", "nach", "vor", "mit", "ohne", "ueber", "unter",
            "was", "wer", "wen", "wem", "welche", "welcher", "welchem", "dieser", "diese", "diesem",
            "koennen", "kann", "muessen", "muss", "sollen", "soll", "wollen", "will", "duerfen", "darf",
            "koennte", "wuerde", "sollte", "moechte", "werde", "wurde", "worden",
            "hallo", "hi", "hey", "moin", "servus", "guten", "tag", "morgen", "abend", "bitte", "danke",
            "mal", "halt", "eben", "ja", "nein", "ok", "okay",
        }

    def _tokenize_for_keywords(self, text: str) -> list[str]:
        normalized = self._normalize_german_text(text)
        return re.findall(r"[a-z0-9]{3,}", normalized)

    @staticmethod
    def _clean_query_output(raw_query: str) -> str:
        if not raw_query:
            return ""
        cleaned = str(raw_query).replace("\n", " ").replace("\r", " ").strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = cleaned.strip(" ,.;:|")
        # Detektiere Verweigerungen / Fehlausgaben
        refusal_patterns = [
            "ich kann nicht", "ich kann diese", "als ki", "ich darf",
            "entschuldigung", "tut mir leid", "i cannot", "i'm sorry",
        ]
        if any(p in cleaned.lower() for p in refusal_patterns):
            return ""
        if cleaned.startswith("{") and cleaned.endswith("}"):
            return ""
        return cleaned[:280]

    def _build_keyword_query(self, text: str, max_terms: int = 15) -> str:
        stop_words = self._default_stop_words()
        tokens = self._tokenize_for_keywords(text)
        if not tokens:
            return ""

        first_position: dict[str, int] = {}
        frequency: dict[str, int] = {}
        for idx, token in enumerate(tokens):
            if token in stop_words:
                continue
            if token not in first_position:
                first_position[token] = idx
            frequency[token] = frequency.get(token, 0) + 1

        if not frequency:
            return ""

        ranked = sorted(
            frequency.keys(),
            key=lambda token: (
                -frequency[token],
                -(len(token)),
                first_position[token],
            ),
        )
        return " ".join(ranked[: max(1, int(max_terms))])

    @staticmethod
    def _keyword_weak_words() -> set[str]:
        return {
            "name", "projekt", "projekte", "fehler", "problem", "probleme", "sache", "sachen",
            "info", "infos", "erinnerung", "erinnerungen", "daten", "frage", "antwort",
            "user", "chappie", "chat", "gespraech", "gespraeche", "heute", "gestern",
        }

    @staticmethod
    def _keyword_strong_words() -> set[str]:
        return {
            "bruder", "schwester", "mutter", "vater", "eltern", "familie", "freund", "freundin",
            "wohnort", "adresse", "geburtstag", "alter", "job", "beruf", "schule", "klasse",
            "heisse", "heisst", "heiße", "heißt", "genannt", "nenne", "nennst",
            "lieblings", "lieblingsfarbe", "lieblingsessen", "deadline", "termin",
        }

    def _normalize_keyword_list(self, values: Optional[list[str] | tuple[str, ...] | set[str] | str], max_terms: int = 20) -> list[str]:
        if not values:
            return []
        if isinstance(values, str):
            raw_items = re.split(r"[,;|\n]+|\s{2,}", values)
        else:
            raw_items = [str(item) for item in values]

        normalized: list[str] = []
        seen: set[str] = set()
        stop_words = self._default_stop_words()
        for item in raw_items:
            for token in self._tokenize_for_keywords(item):
                if token in seen or token in stop_words:
                    continue
                seen.add(token)
                normalized.append(token)
                if len(normalized) >= max_terms:
                    return normalized
        return normalized

    def _normalize_entity_list(
        self,
        values: Optional[list[str] | tuple[str, ...] | set[str] | str],
        max_terms: int = 12,
    ) -> list[str]:
        """Keep robust entity phrases/IDs intact and discard grammar noise."""
        if not values:
            return []
        raw_items = re.split(r"[,;|\n]+", values) if isinstance(values, str) else [str(item) for item in values]
        stop_words = self._default_stop_words()
        normalized: list[str] = []
        seen: set[str] = set()
        for raw_item in raw_items:
            item = re.sub(r"\s+", " ", self._normalize_german_text(raw_item)).strip(" .,:;!?()[]{}\"")
            meaningful = [token for token in self._tokenize_for_keywords(item) if token not in stop_words]
            if not meaningful:
                continue
            # Preserve explicit identifiers (e.g. ORBIT-741) and multi-word
            # names as a phrase. A sentence fragment is not promoted to Exact.
            identifier = re.fullmatch(r"[a-z0-9]+(?:[-_./][a-z0-9]+)+", item)
            if identifier:
                candidate = item
            elif len(meaningful) == 1:
                candidate = meaningful[0]
            elif len(meaningful) <= 4 and len(item.split()) <= 4:
                candidate = " ".join(meaningful)
            else:
                continue
            if candidate in seen:
                continue
            seen.add(candidate)
            normalized.append(candidate)
            if len(normalized) >= max_terms:
                break
        return normalized

    @staticmethod
    def _timestamp_score(timestamp: str) -> float:
        if not timestamp:
            return 0.0
        try:
            parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            age_seconds = max(0.0, (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds())
        except (TypeError, ValueError):
            return 0.0
        age_days = age_seconds / 86400
        if age_days <= 7:
            return 0.15
        if age_days <= 30:
            return 0.10
        if age_days <= 365:
            return 0.04
        return 0.0

    def _keyword_match_score(
        self,
        content: str,
        keywords: list[str],
        entities: list[str],
        timestamp: str = "",
    ) -> tuple[float, str, list[str]]:
        normalized_content = self._normalize_german_text(content or "")
        content_tokens = set(re.findall(r"[a-z0-9]{3,}", normalized_content))
        weak_words = self._keyword_weak_words()
        strong_words = self._keyword_strong_words()

        score = 0.0
        matched: list[str] = []
        has_non_weak_match = False
        match_type = "Keyword"

        for entity in entities:
            if not entity:
                continue
            if entity in normalized_content:
                score += 1.0
                has_non_weak_match = True
                match_type = "Exact"
                matched.append(entity)

        for keyword in keywords:
            if not keyword:
                continue
            is_match = keyword in content_tokens or keyword in normalized_content
            if not is_match:
                continue
            matched.append(keyword)
            if keyword in weak_words:
                score += 0.03
                continue
            has_non_weak_match = True
            if keyword in strong_words or len(keyword) >= 8 or any(char.isdigit() for char in keyword):
                score += 0.35
            else:
                score += 0.15

        if not matched or not has_non_weak_match:
            return 0.0, "", []

        unique_matches = []
        seen = set()
        for term in matched:
            if term in seen:
                continue
            seen.add(term)
            unique_matches.append(term)

        if match_type != "Exact" and len([term for term in unique_matches if term not in weak_words]) >= 2:
            match_type = "Entity" if entities else "Keyword"

        score += self._timestamp_score(timestamp)
        return min(1.0, round(score, 3)), match_type, unique_matches[:8]

    def search_memory_keywords(
        self,
        query: str,
        keywords: Optional[list[str]] = None,
        entities: Optional[list[str]] = None,
        top_k: int = 5,
        min_score: float = 0.25,
        exclude_ids: Optional[set[str]] = None,
    ) -> list[Memory]:
        """Lokale Keyword-/Entity-Suche fuer exakte Fakten ohne zusaetzlichen LLM-Call."""
        if self.collection is None:
            return []

        exclude_ids = exclude_ids or set()
        keyword_terms = self._normalize_keyword_list(keywords, max_terms=20)
        entity_terms = self._normalize_entity_list(entities, max_terms=12)
        if not keyword_terms and not entity_terms:
            keyword_terms = self._normalize_keyword_list(self._build_keyword_query(query or "", max_terms=12), max_terms=12)
        if not keyword_terms and not entity_terms:
            return []

        try:
            if self._collection_count() == 0:
                return []
            raw = self._collection_get(include=["documents", "metadatas"])
        except Exception as e:
            if settings.debug:
                print(f"   Keyword-RAG Suche fehlgeschlagen: {e}")
            return []

        documents = raw.get("documents") or []
        ids = raw.get("ids") or []
        metadatas = raw.get("metadatas") or []
        memories: list[Memory] = []
        metadata_by_id: dict[str, dict[str, Any]] = {}

        for idx, content in enumerate(documents):
            metadata = metadatas[idx] if idx < len(metadatas) and isinstance(metadatas[idx], dict) else {}
            role = metadata.get("role", "unknown")
            if self._is_memory_contaminated(
                str(content or ""),
                role=role,
                source=metadata.get("source", ""),
                label=metadata.get("label", ""),
            ):
                continue
            memory_id = str(ids[idx]) if idx < len(ids) else ""
            if memory_id and memory_id in exclude_ids:
                continue
            timestamp = metadata.get("timestamp", "")
            score, match_type, matched_terms = self._keyword_match_score(
                str(content or ""),
                keyword_terms,
                entity_terms,
                timestamp=timestamp,
            )
            if score < min_score:
                continue
            memories.append(
                Memory(
                    id=memory_id,
                    content=str(content or ""),
                    role=metadata.get("role", "unknown"),
                    timestamp=timestamp,
                    mem_type=metadata.get("type", "interaction"),
                    relevance_score=score,
                    label=f"keyword_{match_type.lower()}",
                    match_type=match_type,
                    matched_terms=", ".join(matched_terms),
                    source=metadata.get("source", "unknown"),
                    strength=self._metadata_float(metadata, "strength", 1.0),
                    recall_count=self._metadata_int(metadata, "recall_count", 0),
                    last_recall_time=str(metadata.get("last_recall_time", "")),
                    retention=self._memory_retention(metadata),
                )
            )
            metadata_by_id[memory_id] = metadata

        # At equal keyword relevance, explicit USER statements are stronger
        # autobiographical evidence than generated assistant summaries.
        memories.sort(
            key=lambda m: (
                m.relevance_score,
                str(m.role or "").casefold() == "user",
                self._timestamp_score(m.timestamp),
            ),
            reverse=True,
        )
        selected = memories[: max(1, int(top_k))]
        self._reinforce_retrieved_memories(selected, metadata_by_id)
        return selected

    def extract_search_query(self, user_input: str) -> str:
        """
        Extrahiert optimierte Suchbegriffe aus dem User-Input.

        Nutzt Multi-Provider Strategy:
        1. Manual (Kurze Inputs < 10 Woerter)
        2. LLM Extraction mit aktivem Provider (Groq/Ollama)
        3. Fallback: Zusammenfassung der ersten 200 Zeichen

        Args:
            user_input: Der originale User-Input

        Returns:
            Optimierter Such-Query oder gekuerzter Input bei Fehler
        """
        if not settings.enable_query_extraction:
            return user_input

        if not user_input or not user_input.strip():
            return user_input

        words = user_input.split()
        
        if len(words) < int(getattr(settings, "query_extraction_min_words_for_llm", 7)):
            extracted = self._build_keyword_query(user_input, max_terms=10)
            if extracted:
                if settings.debug:
                    print(f"   Query Extraction (Manual): '{user_input}' -> '{extracted}'")
                return extracted
            else:
                return user_input

        truncated_input = user_input[:1500] if len(user_input) > 1500 else user_input
        
        prompt = format_query_extraction_prompt(truncated_input)

        gen_config = GenerationConfig(
            max_tokens=100,
            temperature=0.3,
            stream=False,
            enable_thinking=False,
        )

        messages = [Message(role="user", content=prompt)]
        
        # Query extraction is part of the single local chat route. It must
        # never introduce a cloud or secondary-provider request.
        effective_provider = LLMProvider.VLLM
        model = settings.resolve_vllm_runtime_model(settings.vllm_model)

        if settings.debug:
            print(f"   Query Extraction: Provider={effective_provider.value}, Model={model}")

        try:
            brain = self._get_brain_for_provider(effective_provider, model)
            if brain:
                result = brain.generate(messages, config=gen_config)
                if not looks_like_model_error(result):
                    extracted = self._clean_query_output(result)
                    if settings.debug:
                        print(f"   Query Extraction ({effective_provider.value}): '{extracted[:100]}...'")
                    if extracted:
                        return extracted
                elif settings.debug:
                    print(f"   Query Extraction ({effective_provider.value}): LLM returned error or empty: {result[:100] if result else 'None'}")
        except Exception as e:
            if settings.debug:
                print(f"   Query Extraction ({effective_provider.value}) fehlgeschlagen: {e}")

        keywords_fallback = self._extract_keywords_simple(user_input)
        if keywords_fallback:
            if settings.debug:
                print(f"   Query Extraction (Fallback Keywords): '{keywords_fallback[:100]}...'")
            return keywords_fallback

        truncated_fallback = " ".join(words[:20])
        if settings.debug:
            print(f"   Query Extraction (Fallback Truncate): '{truncated_fallback}'")
        return truncated_fallback

    def _get_brain_for_provider(self, provider, model: str):
        """Holt die passende Brain-Instanz fuer einen Provider."""
        try:
            return get_brain(provider=provider, model=model)
        except Exception as e:
            if settings.debug:
                print(f"   Brain init failed for {provider}: {e}")
        return None

    def _extract_keywords_simple(self, text: str) -> str:
        """Extrahiert einfach Schluesselwoerter ohne LLM."""
        return self._build_keyword_query(text, max_terms=15)

    def search_memory(
        self,
        query: str,
        top_k: Optional[int] = None,
        min_relevance: float = 0.0,
        optimize_query: bool = True,
    ) -> list[Memory]:
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
        if self.collection is None:
            return []
        
        if not query or not query.strip():
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
                if self._collection_count() == 0:
                    return []

                # Smart Query Extraction: Optimiere den Query vor der Vektorisierung.
                optimized_query = self.extract_search_query(query) if optimize_query else query

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
                results = self._collection_query(
                    query_embeddings=[query_embedding],
                    n_results=min(top_k * 2, self._collection_count())
                )

                # Konvertiere zu Memory-Objekten
                memories = []
                metadata_by_id: dict[str, dict[str, Any]] = {}
                if results and results["documents"] and results["documents"][0]:
                    for i, doc in enumerate(results["documents"][0]):
                        metadata = results.get("metadatas") or []
                        metadata = metadata[0][i] if metadata and metadata[0] else {}
                        if not isinstance(metadata, dict):
                            metadata = metadata or {}
                        if self._is_memory_contaminated(
                            str(doc or ""),
                            role=metadata.get("role", "unknown"),
                            source=metadata.get("source", ""),
                            label=metadata.get("label", ""),
                        ):
                            continue
                        # Chroma's cosine distance is 1 - cosine similarity.
                        distance = results["distances"][0][i] if results["distances"] else 0
                        semantic_relevance = max(0.0, min(1.0, 1.0 - float(distance)))
                        relevance, retention = self._retention_adjusted_score(semantic_relevance, metadata)
                        
                        # FILTERUNG NACH RELEVANZ
                        if relevance < min_relevance:
                            continue

                        memory = Memory(
                            id=results["ids"][0][i],
                            content=doc,
                            role=metadata.get("role", "unknown"),
                            timestamp=metadata.get("timestamp", ""),
                            mem_type=metadata.get("type", "interaction"),
                            relevance_score=relevance,
                            label=metadata.get("label", "original"),
                            source=metadata.get("source", "unknown"),
                            strength=self._metadata_float(metadata, "strength", 1.0),
                            recall_count=self._metadata_int(metadata, "recall_count", 0),
                            last_recall_time=str(metadata.get("last_recall_time", "")),
                            retention=retention,
                        )
                        memories.append(memory)
                        metadata_by_id[memory.id] = metadata

                memories.sort(key=lambda m: m.relevance_score, reverse=True)
                memories.extend(self._load_associated_memories(memories, metadata_by_id))

                # Deduplicate direct and spread paths, keeping the stronger
                # score, then persist recall and co-retrieval strengthening.
                deduplicated: dict[str, Memory] = {}
                for memory in memories:
                    previous = deduplicated.get(memory.id)
                    if previous is None or memory.relevance_score > previous.relevance_score:
                        deduplicated[memory.id] = memory
                memories = list(deduplicated.values())
                memories.sort(key=lambda m: m.relevance_score, reverse=True)
                selected = memories[:top_k]
                self._reinforce_retrieved_memories(selected, metadata_by_id)
                return selected
                
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
    

    def get_recent_memories(self, limit: int = 10, offset: int = 0, mem_type_filter: str = None, label_filter: str = None) -> list[Memory]:
        """
        Holt die neuesten Erinnerungen mit Pagination-Support.

        WICHTIG: ChromaDB gibt Einträge in Insertion-Order zurück (älteste zuerst).
        Daher müssen wir ALLE Einträge laden, sortieren und dann offset/limit anwenden.

        Args:
            limit: Maximale Anzahl pro Seite
            offset: Anzahl der zu überspringenden Einträge (für Pagination)
            mem_type_filter: Optionaler Filter nach mem_type ("interaction" oder "summary")
            label_filter: Optionaler Filter nach label ("original" oder "zsm gefasst")

        Returns:
            Liste von Memory-Objekten (neueste zuerst)
        """
        if self.collection is None:
            return []
        
        total_count = self._collection_count()
        if total_count == 0:
            return []

        results = self._collection_get(
            include=["documents", "metadatas"]
        )

        memories = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"]):
                metadata = results["metadatas"][i] if results["metadatas"] else {}

                if not isinstance(metadata, dict):
                    metadata = {}

                mem_type = metadata.get("type", "interaction")
                label = metadata.get("label", "original")
                
                if mem_type_filter and mem_type != mem_type_filter:
                    continue
                if label_filter and label != label_filter:
                    continue

                if self._is_memory_contaminated(
                    str(doc or ""),
                    role=metadata.get("role", "unknown"),
                    source=metadata.get("source", ""),
                    label=metadata.get("label", ""),
                ):
                    continue

                memory = Memory(
                    id=results["ids"][i] if i < len(results["ids"]) else str(uuid.uuid4()),
                    content=doc if isinstance(doc, str) else str(doc),
                    role=metadata.get("role", "unknown"),
                    timestamp=metadata.get("timestamp", ""),
                    mem_type=mem_type,
                    label=label,
                    source=metadata.get("source", "unknown"),
                    strength=self._metadata_float(metadata, "strength", 1.0),
                    recall_count=self._metadata_int(metadata, "recall_count", 0),
                    last_recall_time=str(metadata.get("last_recall_time", "")),
                    retention=self._memory_retention(metadata),
                )
                memories.append(memory)

        memories.sort(key=lambda m: m.timestamp, reverse=True)

        return memories[offset:offset + limit]
    
    def get_filtered_memory_count(self, mem_type_filter: str = None, label_filter: str = None) -> int:
        """
        Gibt die Anzahl der Erinnerungen nach Filter-Kriterien zurück.

        Args:
            mem_type_filter: Optionaler Filter nach mem_type ("interaction" oder "summary")
            label_filter: Optionaler Filter nach label ("original" oder "zsm gefasst")

        Returns:
            Anzahl der gefilterten Erinnerungen
        """
        if self.collection is None:
            return 0
        
        total_count = self._collection_count()
        if total_count == 0:
            return 0

        if not mem_type_filter and not label_filter:
            return total_count

        results = self._collection_get(
            include=["metadatas"]
        )

        count = 0
        if results and results["metadatas"]:
            for metadata in results["metadatas"]:
                if not isinstance(metadata, dict):
                    continue
                    
                mem_type = metadata.get("type", "interaction")
                label = metadata.get("label", "original")
                
                if mem_type_filter and mem_type != mem_type_filter:
                    continue
                if label_filter and label != label_filter:
                    continue
                
                count += 1

        return count

    def get_usable_memory_count(self, mem_type_filter: str = None, label_filter: str = None) -> int:
        """Gibt nur prompt-sichere, nicht kontaminierte Erinnerungen zurueck."""
        if self.collection is None:
            return 0
        try:
            results = self._collection_get(include=["documents", "metadatas"])
        except Exception:
            return 0

        documents = results.get("documents") or []
        metadatas = results.get("metadatas") or []
        count = 0
        for index, document in enumerate(documents):
            metadata = metadatas[index] if index < len(metadatas) and isinstance(metadatas[index], dict) else {}
            if mem_type_filter and metadata.get("type", "interaction") != mem_type_filter:
                continue
            if label_filter and metadata.get("label", "original") != label_filter:
                continue
            if not self._is_memory_contaminated(
                str(document or ""),
                role=metadata.get("role", "unknown"),
                source=metadata.get("source", ""),
                label=metadata.get("label", ""),
            ):
                count += 1
        return count

    
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
            
        self._collection_delete(ids=ids)
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
        
        count = self._collection_count()
        
        # Collection loeschen und neu erstellen. Die Distanzmetrik muss beim
        # Recreate erhalten bleiben, sonst unterscheiden sich neue und alte
        # Retrieval-Ergebnisse nach einem /clear.
        with self._storage_lock():
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine", "description": "CHAPiE episodic memory"}
            )
        
        print(f"   {count} Erinnerungen geloescht")
        return count
    
    def get_memory_count(self) -> int:
        """Gibt die Anzahl der gespeicherten Erinnerungen zurueck."""
        if self.collection is None:
            return 0
        try:
            return self._collection_count()
        except Exception as e:
            print(f"WARNUNG: Konnte Memory-Count nicht ermitteln: {e}")
            return 0

    def health_check(self) -> dict:
        """Führt einen Health-Check der Memory-Engine durch."""
        status = {
            "backend": "chromadb" if self.collection is not None else "unavailable",
            "collection": self.collection_name,
            "memory_count": 0,
            "usable_memory_count": 0,
            "quarantined_memory_count": 0,
            "embedding_model_loaded": False,
            "chromadb_connected": False,
            "is_persistent": getattr(self, '_is_persistent', False),
            "errors": []
        }

        if self.collection is None:
            status["errors"].append("ChromaDB: Collection nicht verfügbar")
        else:
            try:
                status["memory_count"] = self._collection_count()
                status["usable_memory_count"] = self.get_usable_memory_count()
                status["quarantined_memory_count"] = max(
                    0,
                    status["memory_count"] - status["usable_memory_count"],
                )
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
        with self._storage_lock():
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine", "description": "CHAPiE episodic memory"}
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
        
        lines = [
            "=== RELEVANTE ERINNERUNGEN (QUELLENKONTEXT) ===",
            "Nutze einen Treffer nur, wenn er die aktuelle Frage direkt beantwortet. Zitiere keine Erinnerung als sicher, wenn Quelle oder Bezug unklar ist.",
            "Bei einer konkreten Recall-Frage haben passende, aktuelle USER-Fakten Vorrang vor Persona und freien Schlussfolgerungen.",
        ]
        for i, mem in enumerate(memories, 1):
            if self._is_memory_contaminated(mem.content, role=mem.role, source=mem.source, label=mem.label):
                continue
            role_label = "USER" if mem.role == "user" else "CHAPPiE"
            score_percent = int(mem.relevance_score * 100)
            date = (mem.timestamp or "")[:10] or "ohne Datum"
            lines.append(f"\n[{i} | ID {mem.id[:8]} | Quelle {mem.source} | {date}] {role_label} (Relevanz: {score_percent}%)")
            lines.append(f"    {scrub_internal_identifiers(mem.content)}")

        return "\n".join(lines) if len(lines) > 3 else "Keine relevanten Erinnerungen gefunden."

    def format_keyword_memories_for_prompt(self, memories: list[Memory], max_chars: int = 1200) -> str:
        """Formatiert lokale Keyword-RAG Treffer als kleinen Faktenblock fuer den finalen Prompt."""
        if not memories:
            return ""

        lines = [
            "=== KEYWORD-RAG FAKTEN / EXAKTE TREFFER ===",
            "Diese belegten Treffer haben bei konkreten Fakten, Namen, Orten, Projekten und frueheren Aussagen Vorrang vor Persona und Vermutungen.",
            "Bei Widerspruechen neuere und exaktere USER-Treffer bevorzugen. Wenn kein Treffer direkt passt, sage das statt eine Erinnerung zu erfinden.",
        ]
        for memory in memories:
            if self._is_memory_contaminated(
                memory.content,
                role=memory.role,
                source=memory.source,
                label=memory.label,
            ):
                continue
            role_label = "USER" if memory.role == "user" else "CHAPPiE"
            match_type = memory.match_type or "Keyword"
            score_percent = int(min(1.0, max(0.0, memory.relevance_score)) * 100)
            date = (memory.timestamp or "")[:10] or "ohne Datum"
            terms = f" | Treffer: {memory.matched_terms}" if memory.matched_terms else ""
            content = scrub_internal_identifiers(re.sub(r"\s+", " ", memory.content).strip()[:220])
            candidate = f"\n[{match_type} | ID {memory.id[:8]} | Quelle {memory.source} | Score {score_percent}% | {date} | {role_label}{terms}]\n\"{content}\""
            if len("\n".join(lines)) + len(candidate) > max_chars:
                break
            lines.append(candidate)

        return "\n".join(lines) if len(lines) > 3 else ""

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
        from config.prompts import format_dream_prompt  # from config/prompts.py

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
        result_msg = "Traum-Phase abgeschlossen.\n"
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
