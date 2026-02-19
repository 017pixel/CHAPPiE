"""
Repetition Tracker
==================
Tracking und Bewertung von Antwort-Vielfalt im Training.
Nutzt Embeddings fuer semantische Aehnlichkeitsberechnung.
"""

from typing import List, Dict, Set, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
import re
import logging

log = logging.getLogger(__name__)


@dataclass
class ResponseEntry:
    """Speichert eine Antwort mit Metadaten."""
    content: str
    role: str
    timestamp: datetime
    keywords: Set[str] = field(default_factory=set)
    embedding: List[float] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)


class RepetitionTracker:
    """
    Tracking und Bewertung von Antwort-Vielfalt.
    
    Features:
    - Embedding-basierte Aehnlichkeitsberechnung
    - Keyword-Extraktion
    - Themen-Tracking
    - Belohnung/Bestrafung fuer Trainer-Prompt
    """
    
    def __init__(self, window_size: int = 30, similarity_threshold: float = 0.7):
        self.window_size = window_size
        self.similarity_threshold = similarity_threshold
        
        self.response_history: deque[ResponseEntry] = deque(maxlen=window_size)
        self.all_keywords: Set[str] = set()
        self.all_topics: List[str] = []
        
        self._embedder = None
        
        self.stats = {
            "total_responses": 0,
            "repetitive_count": 0,
            "novel_count": 0,
            "avg_novelty_score": 0.0,
            "unique_keywords": 0,
            "unique_topics": 0,
        }
        
        self._novelty_scores: List[float] = []
    
    def _get_embedder(self):
        """Lazy Loading des Embedders."""
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedder = SentenceTransformer('all-MiniLM-L6-v2')
                log.info("RepetitionTracker: Embedder geladen")
            except Exception as e:
                log.warning(f"RepetitionTracker: Konnte Embedder nicht laden: {e}")
                return None
        return self._embedder
    
    def add_response(self, content: str, role: str) -> float:
        """
        Fuegt neue Antwort hinzu und gibt Novelty-Score zurueck.
        
        Args:
            content: Die Antwort
            role: "chappie" oder "trainer"
            
        Returns:
            novelty_score: 0.0 (repetitiv) bis 1.0 (komplett neu)
        """
        keywords = self._extract_keywords(content)
        embedding = self._get_embedding(content)
        topics = self._extract_topics(content)
        
        novelty_score = self._calculate_novelty(content, embedding, keywords)
        
        entry = ResponseEntry(
            content=content,
            role=role,
            timestamp=datetime.now(),
            keywords=keywords,
            embedding=embedding,
            topics=topics
        )
        
        self.response_history.append(entry)
        self.all_keywords.update(keywords)
        self.all_topics.extend(topics)
        
        self.stats["total_responses"] += 1
        if novelty_score < 0.4:
            self.stats["repetitive_count"] += 1
        else:
            self.stats["novel_count"] += 1
        
        self._novelty_scores.append(novelty_score)
        if self._novelty_scores:
            self.stats["avg_novelty_score"] = sum(self._novelty_scores) / len(self._novelty_scores)
        
        self.stats["unique_keywords"] = len(self.all_keywords)
        self.stats["unique_topics"] = len(set(self.all_topics))
        
        return novelty_score
    
    def _extract_keywords(self, text: str) -> Set[str]:
        """Extrahiert relevante deutsche/englische Keywords."""
        stop_words = {
            "der", "die", "das", "ein", "eine", "und", "oder", "aber",
            "ich", "du", "wir", "ihr", "sie", "es", "ist", "sind",
            "war", "waren", "haben", "hat", "hatte", "werden", "wird",
            "kann", "kannst", "nicht", "auch", "nur", "schon", "noch",
            "wenn", "dann", "aber", "doch", "mal", "ja", "nein",
            "the", "a", "an", "and", "or", "but", "is", "are", "was", "were",
            "have", "has", "had", "will", "would", "could", "should",
            "i", "you", "we", "they", "it", "this", "that", "to", "of",
            "in", "on", "for", "with", "as", "at", "by", "from",
            "ganz", "sehr", "mehr", "viel", "wenig", "immer", "wirklich",
            "natuerlich", "natürlich", "vielleicht", "wahrscheinlich",
            "denke", "meine", "glaube", "sagen", "sagte", "gesagt",
            "chappie", "trainer", "ok", "okay", "hmm", "oh", "ah",
        }
        
        words = re.findall(r'\b[a-zA-ZäöüÄÖÜß]{4,}\b', text.lower())
        keywords = {w for w in words if w not in stop_words}
        
        return keywords
    
    def _get_embedding(self, text: str) -> List[float]:
        """Berechnet Embedding fuer den Text."""
        try:
            embedder = self._get_embedder()
            if embedder is None:
                return []
            embedding = embedder.encode(text, convert_to_list=True)
            return embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)
        except Exception as e:
            log.debug(f"Embedding Fehler: {e}")
            return []
    
    def _calculate_novelty(
        self, 
        content: str, 
        embedding: List[float], 
        keywords: Set[str]
    ) -> float:
        """
        Berechnet Novelty-Score basierend auf:
        1. Embedding-Aehnlichkeit (semantisch)
        2. Keyword-Overlap (lexikalisch)
        3. Themen-Neuheit
        """
        if not self.response_history:
            return 1.0
        
        scores = []
        
        if embedding:
            embedding_score = self._embedding_novelty(embedding)
            scores.append(("embedding", embedding_score, 0.5))
        
        keyword_score = self._keyword_novelty(keywords)
        scores.append(("keyword", keyword_score, 0.3))
        
        topic_score = self._topic_novelty(content)
        scores.append(("topic", topic_score, 0.2))
        
        total_weight = sum(s[2] for s in scores)
        weighted_score = sum(s[1] * s[2] for s in scores) / total_weight
        
        return weighted_score
    
    def _embedding_novelty(self, new_embedding: List[float]) -> float:
        """Berechnet durchschnittliche Aehnlichkeit zu vorherigen Antworten."""
        try:
            import numpy as np
        except ImportError:
            return 0.5
        
        if not self.response_history:
            return 1.0
        
        new_emb = np.array(new_embedding)
        similarities = []
        
        for entry in list(self.response_history)[-10:]:
            if entry.embedding:
                old_emb = np.array(entry.embedding)
                norm_new = np.linalg.norm(new_emb)
                norm_old = np.linalg.norm(old_emb)
                if norm_new > 0 and norm_old > 0:
                    similarity = np.dot(new_emb, old_emb) / (norm_new * norm_old)
                    similarities.append(similarity)
        
        if not similarities:
            return 1.0
        
        avg_similarity = float(np.mean(similarities))
        novelty = 1.0 - avg_similarity
        return max(0.0, min(1.0, novelty))
    
    def _keyword_novelty(self, new_keywords: Set[str]) -> float:
        """Berechnet Keyword-Neuheit."""
        if not new_keywords:
            return 0.5
        if not self.all_keywords:
            return 1.0
        
        recent_keywords = set()
        for entry in list(self.response_history)[-5:]:
            recent_keywords.update(entry.keywords)
        
        if not recent_keywords:
            return 1.0
        
        overlap = new_keywords & recent_keywords
        overlap_ratio = len(overlap) / len(new_keywords) if new_keywords else 0
        
        novelty = 1.0 - overlap_ratio
        return max(0.0, min(1.0, novelty))
    
    def _extract_topics(self, content: str) -> List[str]:
        """Extrahiert Themen aus dem Inhalt."""
        topic_indicators = [
            "philosophie", "wissenschaft", "technologie", "kunst",
            "geschichte", "psychologie", "physik", "mathematik",
            "sprache", "kultur", "natur", "gesellschaft",
            "philosophy", "science", "technology", "art", "history",
            "emotion", "gefuehl", "gefühl", "liebe", "hass",
            "zukunft", "vergangenheit", "gegenwart",
            "future", "past", "present",
            "bewusstsein", "consciousness", "ki", "ai", "machine learning",
            "ethik", "ethics", "moral", "recht", "law",
            "musik", "music", "film", "buch", "buch",
            "sport", "reise", "travel", "essen", "food",
        ]
        
        content_lower = content.lower()
        found_topics = [t for t in topic_indicators if t in content_lower]
        
        return found_topics
    
    def _topic_novelty(self, content: str) -> float:
        """Prueft ob neue Themen angesprochen werden."""
        found_topics = self._extract_topics(content)
        
        if not found_topics:
            return 0.5
        
        recent_topics = []
        for entry in list(self.response_history)[-5:]:
            recent_topics.extend(entry.topics)
        
        if not recent_topics:
            return 1.0
        
        new_topics = [t for t in found_topics if t not in recent_topics]
        
        if new_topics:
            return 1.0
        return 0.3
    
    def get_diversity_feedback(self) -> str:
        """
        Generiert Feedback fuer den Trainer-Prompt.
        
        Returns:
            Konkrete Handlungsanweisung fuer den Trainer
        """
        recent = list(self.response_history)[-5:]
        
        if not recent:
            return "Du startest ein neues Gespraech. Sei kreativ und bring frische Themen ein!"
        
        recent_keywords = set()
        for entry in recent:
            recent_keywords.update(entry.keywords)
        
        if len(recent_keywords) < 5:
            return "Das Gespraech ist noch kurz. Fuehre es natuerlich fort und entdecke neue Themen."
        
        suggested_topics = self._suggest_new_topics()
        
        if self.stats["avg_novelty_score"] < 0.4:
            return (
                f"WARNUNG: Ihr dreht euch im Kreis! "
                f"Wechsle JETZT zu einem NEUEN Thema: {suggested_topics[0] if suggested_topics else 'etwas voellig Neues'}. "
                f"Sei kreativ und ueberraschend!"
            )
        elif self.stats["avg_novelty_score"] < 0.6:
            return (
                f"Das Gespraech wird etwas repetitiv. "
                f"Bringe einen neuen Aspekt ein oder wechsle das Thema. "
                f"Vorschlag: {suggested_topics[0] if suggested_topics else 'neue Perspektive'}"
            )
        else:
            return "Das Gespraech ist vielfaeltig. Fuehre es natuerlich fort und bleibe neugierig!"
    
    def _suggest_new_topics(self) -> List[str]:
        """Schlaegt neue Themen vor basierend auf noch nicht behandelten Themen."""
        all_possible_topics = [
            "Philosophie und Ethik - tiefe Fragen ueber das Leben",
            "Wissenschaft und Forschung - neueste Entdeckungen",
            "Technologie und Innovation - die Zukunft der Technik",
            "Kunst und Kreativitaet - schoepferische Ausdrucksformen",
            "Geschichte und Kultur - interessante Ereignisse der Vergangenheit",
            "Psychologie und menschliches Verhalten - wie Menschen denken",
            "Natur und Umwelt - die Welt um uns herum",
            "Sprache und Kommunikation - wie wir uns verstaendigen",
            "Mathematik und Logik - rationale Problemlösung",
            "Gesellschaft und Politik - aktuelle Themen",
            "Persoenliche Erfahrungen - teile eine Geschichte",
            "Hypothetische Szenarien - was waere wenn?",
            "Zukunftsvisionen - wie wird die Welt in 100 Jahren?",
            "Raumfahrt und Universum - die Erforschung des Kosmos",
            "Musik und Kunst - kreative Ausdrucksformen",
        ]
        
        new_topics = []
        for topic in all_possible_topics:
            topic_lower = topic.lower()
            if not any(t in topic_lower for t in self.all_topics):
                new_topics.append(topic)
        
        return new_topics[:3]
    
    def get_stats_report(self) -> str:
        """Generiert einen Statistik-Bericht."""
        total = self.stats["total_responses"]
        if total == 0:
            return "Noch keine Antworten analysiert."
        
        rep_pct = self.stats["repetitive_count"] / total * 100
        nov_pct = self.stats["novel_count"] / total * 100
        avg_novelty = self.stats["avg_novelty_score"] * 100
        
        return f"""Vielfalt-Statistik:
  Gesamt Antworten: {total}
  Repetitiv (< 40% Novelty): {self.stats["repetitive_count"]} ({rep_pct:.1f}%)
  Neu (> 40% Novelty): {self.stats["novel_count"]} ({nov_pct:.1f}%)
  Durchschnittliche Novelty: {avg_novelty:.1f}%
  Einzigartige Keywords: {self.stats["unique_keywords"]}
  Themen behandelt: {self.stats["unique_topics"]}"""
    
    def reset(self):
        """Setzt den Tracker zurueck."""
        self.response_history.clear()
        self.all_keywords.clear()
        self.all_topics.clear()
        self._novelty_scores.clear()
        self.stats = {
            "total_responses": 0,
            "repetitive_count": 0,
            "novel_count": 0,
            "avg_novelty_score": 0.0,
            "unique_keywords": 0,
            "unique_topics": 0,
        }
