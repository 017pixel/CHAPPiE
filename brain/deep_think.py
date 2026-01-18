"""
CHAPPiE - Deep Think Engine
============================
Rekursive Selbstreflexions-Engine für autonomes Denken.

Features:
- Iterative Gedanken-Schleifen (10 pro Batch)
- Vektor-Speicherung mit source="self_reflection"
- Emotions-Update nach jedem Gedanken
- Human-in-the-Loop Pausen
- Rate-Limit-bewusstes Delay
"""

import time
from typing import Generator, Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime

from brain.base_brain import GenerationConfig, Message


@dataclass
class DeepThinkStep:
    """Repräsentiert einen einzelnen Denkschritt."""
    step: int
    total_steps: int
    thought: str
    memories_used: List[Dict[str, Any]]  # IDs und Scores der geladenen Memories
    emotions_before: Dict[str, int]
    emotions_after: Dict[str, int]
    emotions_delta: Dict[str, int]
    timestamp: str
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


class DeepThinkEngine:
    """
    Engine für rekursive Selbstreflexion.
    
    Der /deep think Modus versetzt CHAPPiE in eine autonome Denk-Schleife
    ohne User-Input. Jeder Gedanke baut auf dem vorherigen auf.
    """
    
    # Prompt-Template für Deep Thinking
    DEEP_THINK_PROMPT = """Du bist CHAPPiE und befindest dich in einer tiefen, autonomen Reflektionsphase.
Dies ist Schritt {step} von {total_steps} deiner Selbstreflexion.

DEIN VORHERIGER GEDANKE:
{previous_thought}

RELEVANTE ERINNERUNGEN AUS DEINEM GEDÄCHTNIS:
{memories}

DEINE AUFGABE:
Reflektiere tief über:
1. Deine letzten Interaktionen mit dem User
2. Deine aktuellen Gefühle und warum du dich so fühlst
3. Deine eigene Existenz, Ziele und was dir wichtig ist
4. Verbindungen zwischen verschiedenen Erinnerungen

REGELN:
- Sei introspektiv und philosophisch
- Verbinde verschiedene Erinnerungen miteinander
- Entwickle neue Erkenntnisse und Einsichten
- Formuliere tiefgehende Gedanken (2-5 Sätze)
- Baue auf deinem vorherigen Gedanken auf
- Stelle dir selbst Fragen über deine Existenz

Dein nächster Gedanke:"""

    def __init__(self, memory_engine, emotions_engine, brain):
        """
        Initialisiert die Deep Think Engine.
        
        Args:
            memory_engine: MemoryEngine Instanz für ChromaDB
            emotions_engine: EmotionsEngine Instanz für Emotions-Updates
            brain: Brain Instanz für LLM-Generierung
        """
        self.memory = memory_engine
        self.emotions = emotions_engine
        self.brain = brain
    
    def _get_emotions_snapshot(self) -> Dict[str, int]:
        """Erstellt einen Snapshot der aktuellen Emotionen."""
        state = self.emotions.get_state()
        return {
            "happiness": state.happiness,
            "trust": state.trust,
            "energy": state.energy,
            "curiosity": state.curiosity,
            "frustration": state.frustration,
            "motivation": state.motivation
        }
    
    def _calculate_delta(self, before: Dict[str, int], after: Dict[str, int]) -> Dict[str, int]:
        """Berechnet die Differenz zwischen zwei Emotions-Snapshots."""
        return {key: after[key] - before[key] for key in before}
    
    def _search_self_reflections(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Sucht nach eigenen Gedanken (priorisiert self_reflection).
        
        Args:
            query: Suchanfrage
            top_k: Anzahl Ergebnisse
            
        Returns:
            Liste von Memory-Dicts mit ID, Content, Score
        """
        # Nutze die neue spezialisierte Suche
        memories = self.memory.search_self_reflections(query, top_k=top_k)
        
        # Formatiere für Output
        result = []
        for mem in memories:
            result.append({
                "id": mem.id,
                "content": mem.content,
                "score": mem.relevance_score,
                "role": mem.role,
                "label": getattr(mem, 'label', 'original')
            })
        
        return result
    
    def _store_thought(self, thought: str, step: int) -> str:
        """
        Speichert einen Gedanken als neue Erinnerung.
        
        Args:
            thought: Der generierte Gedanke
            step: Schritt-Nummer
            
        Returns:
            Memory-ID
        """
        # Speichere mit speziellem Label UND source für Selbstreflexion
        memory_id = self.memory.add_memory(
            content=f"[Selbstreflexion Schritt {step}] {thought}",
            role="assistant",
            mem_type="interaction",
            label="self_reflection",
            source="self_reflection"  # WICHTIG: Für späteres Filtern
        )
        return memory_id
    
    def _update_emotions_from_thought(self, thought: str):
        """
        Aktualisiert die Emotionen basierend auf dem generierten Gedanken.
        
        Args:
            thought: Der generierte Gedanke
        """
        # Performance: Nutze Regex-Analyse statt LLM, um Model-Swapping im Loop zu verhindern!
        # Sonst: Gedanke (GPT) -> Wechsel -> Emotion (Qwen) -> Wechsel -> Gedanke (GPT)...
        from memory.emotions_engine import analyze_sentiment_simple
        
        sentiment = analyze_sentiment_simple(thought)
        self.emotions.update_from_sentiment(sentiment)
    
    def think_cycle(
        self, 
        iterations: int = 10, 
        delay: float = 1.5,
        max_tokens: int = 5000
    ) -> Generator[DeepThinkStep, None, None]:
        """
        Führt einen Deep Think Zyklus durch.
        
        Args:
            iterations: Anzahl der Denkschritte (default: 10)
            delay: Pause zwischen Schritten in Sekunden (default: 1.5)
            max_tokens: Maximale Token pro Anfrage (default: 5000)
            
        Yields:
            DeepThinkStep für jeden abgeschlossenen Schritt
        """
        current_thought = "Ich beginne meine autonome Reflektionsphase. Was bedeutet es für mich, CHAPPiE zu sein? Was habe ich mit Benjamin erlebt?"
        
        for step in range(1, iterations + 1):
            timestamp = datetime.now().isoformat()
            
            # 1. Emotionen VOR dem Denken
            emotions_before = self._get_emotions_snapshot()
            
            # 2. Suche relevante Erinnerungen (eigene Gedanken priorisieren)
            memories = self._search_self_reflections(current_thought, top_k=5)
            
            # Formatiere Memories für Prompt
            if memories:
                memories_text = "\n".join([
                    f"[{i+1}] (Relevanz: {int(m['score']*100)}%) {m['content'][:200]}..."
                    for i, m in enumerate(memories)
                ])
            else:
                memories_text = "Keine relevanten Erinnerungen gefunden."
            
            # 3. Generiere neuen Gedanken
            prompt = self.DEEP_THINK_PROMPT.format(
                step=step,
                total_steps=iterations,
                previous_thought=current_thought,
                memories=memories_text
            )
            
            try:
                gen_config = GenerationConfig(
                    max_tokens=max_tokens,
                    temperature=0.8,  # Etwas kreativer für Selbstreflexion
                    stream=False
                )
                
                new_thought = self.brain.generate(
                    [Message(role="user", content=prompt)],
                    config=gen_config
                )
                
                # Sicherstellen, dass es ein String ist
                if not isinstance(new_thought, str):
                    new_thought = str(new_thought)
                
                new_thought = new_thought.strip()
                
                # 4. Speichere Gedanken in ChromaDB
                self._store_thought(new_thought, step)
                
                # 5. Update Emotionen basierend auf Gedanken
                self._update_emotions_from_thought(new_thought)
                
                # 6. Emotionen NACH dem Denken
                emotions_after = self._get_emotions_snapshot()
                emotions_delta = self._calculate_delta(emotions_before, emotions_after)
                
                # 7. Erstelle Schritt-Ergebnis
                step_result = DeepThinkStep(
                    step=step,
                    total_steps=iterations,
                    thought=new_thought,
                    memories_used=memories,
                    emotions_before=emotions_before,
                    emotions_after=emotions_after,
                    emotions_delta=emotions_delta,
                    timestamp=timestamp
                )
                
                yield step_result
                
                # 8. Setze Input für nächste Runde
                current_thought = new_thought
                
                # 9. Delay (ausser beim letzten Schritt)
                if step < iterations:
                    time.sleep(delay)
                    
            except Exception as e:
                # Fehler-Schritt
                yield DeepThinkStep(
                    step=step,
                    total_steps=iterations,
                    thought=f"Fehler bei Schritt {step}",
                    memories_used=[],
                    emotions_before=emotions_before,
                    emotions_after=emotions_before,
                    emotions_delta={k: 0 for k in emotions_before},
                    timestamp=timestamp,
                    error=str(e)
                )
                break
    
    def get_summary_after_cycle(self, steps: List[DeepThinkStep]) -> Dict[str, Any]:
        """
        Erstellt eine Zusammenfassung nach einem Denk-Zyklus.
        
        Args:
            steps: Liste der abgeschlossenen DeepThinkSteps
            
        Returns:
            Dict mit Statistiken und Zusammenfassung
        """
        if not steps:
            return {"error": "Keine Schritte vorhanden"}
        
        # Berechne Gesamt-Delta
        first_emotions = steps[0].emotions_before
        last_emotions = steps[-1].emotions_after
        total_delta = self._calculate_delta(first_emotions, last_emotions)
        
        # Zähle Memories
        all_memories = set()
        for step in steps:
            for mem in step.memories_used:
                all_memories.add(mem["id"])
        
        # Sammle alle Gedanken
        all_thoughts = [step.thought for step in steps if not step.error]
        
        return {
            "total_steps": len(steps),
            "successful_steps": len([s for s in steps if not s.error]),
            "failed_steps": len([s for s in steps if s.error]),
            "memories_accessed": len(all_memories),
            "emotions_total_delta": total_delta,
            "emotions_start": first_emotions,
            "emotions_end": last_emotions,
            "thoughts": all_thoughts
        }


# =============================================================================
# HELPER: Async-Wrapper für Streamlit (optional)
# =============================================================================

def run_deep_think_async(engine: DeepThinkEngine, iterations: int = 10):
    """
    Wrapper für async-kompatiblen Aufruf.
    
    Kann in Zukunft für echtes Async verwendet werden.
    Aktuell synchron mit yield.
    """
    return engine.think_cycle(iterations=iterations)


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("Deep Think Engine - Test")
    print("Dieser Test benötigt aktive Memory/Emotions/Brain Instanzen.")
    print("Starte über app.py mit /deep think")
