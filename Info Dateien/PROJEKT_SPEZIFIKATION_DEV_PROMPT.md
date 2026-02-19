- DATEINAME: PROJEKT_SPEZIFIKATION_DEV_PROMPT.txt
- DATUM: 08. Januar 2026
- PROJEKT: "Projekt Name TBD" (Arbeitstitel: Chappie-Proto)

### ANWEISUNG AN DIE KI ###
Du bist ein erfahrener Senior Python Backend Developer und AI Architect.
Ich möchte, dass du mich Schritt für Schritt bei der Entwicklung einer KI-Anwendung begleitest.
Lies dir die folgende Spezifikation genau durch. Sie ist der Master-Plan für das gesamte Projekt.

---

1. PROJEKTÜBERSICHT
Wir bauen einen KI-Agenten, der "lebendig" wirkt. Das Kernkonzept ist ein "episodisches Gedächtnis".
Anders als normale Chatbots, soll sich dieses System an vergangene Interaktionen erinnern und sein Verhalten basierend auf Feedback anpassen ("Lernen wie ein Kind").

2. HARDWARE & UMGEBUNG (WICHTIG)
Das System muss auf zwei verschiedenen Umgebungen laufen können. Der Code muss flexibel sein.

A) Entwicklungsumgebung (Aktueller Status):
- PC mit NVIDIA RTX 3060 (12GB VRAM), 16GB RAM.
- Limitierung: Große Modelle (20b/70b/120b) laufen hier NICHT oder zu langsam lokal.
- Lösung: Für die Entwicklung nutzen wir lokal kleine Modelle (Llama-3-8b via Ollama) ODER die Cloud API (Groq), um Geschwindigkeit zu simulieren.

B) Produktionsumgebung (Zukunft):
- Eigene Server-Infrastruktur.
- Ziel: Hier werden später Open Source Modelle wie GPT-OSS-20b oder GPT-OSS-120b laufen.

3. TECH STACK & ANFORDERUNGEN
- Sprache: Python 3.11+
- Interface: Terminal / CLI (Command Line Interface). Sauberer Output.
- Datenbank: ChromaDB (lokale Vektor-Datenbank).
- LLM Backend: Modularer Aufbau! Ich muss per Config wechseln können zwischen:
  1. Local (Ollama API / Llama-cpp)
  2. Cloud (Groq API)

4. ARCHITEKTUR-PLAN

Modul A: "Das Gedächtnis" (Memory)
- Wir nutzen ChromaDB.
- Embedding Modell: Muss lokal laufen, auch auf der RTX 3060.
- Modell-Empfehlung: "all-MiniLM-L6-v2" (klein, schnell, effizient für Tests).
- Funktion: Jeder User-Input und jede KI-Antwort wird als Vektor gespeichert.
- Retrieval: Vor der Antwort sucht das System die Top-X relevantesten Erinnerungen.

Modul B: "Das Gehirn" (Brain)
- Erstelle eine abstrakte Klasse, damit wir das Modell später tauschen können (von 8b auf 120b), ohne den ganzen Code neu zu schreiben.
- Streaming: Der Text soll im Terminal "fliessen" (Token für Token), nicht am Stück erscheinen.

Modul C: Der Loop (Main)
- 1. User Input empfangen.
- 2. Suche in Memory (RAG - Retrieval Augmented Generation).
- 3. Baue Prompt: System-Instruktion + Erinnerungen + User Input.
- 4. Generiere Antwort.
- 5. Speichere Input & Antwort im Memory.

5. ENTWICKLUNGS-PHASEN (DEINE AUFGABE)

PHASE 1: Setup
Erstelle die Ordnerstruktur, die `requirements.txt` und eine `config.py`, die API-Keys und Modelleinstellungen verwaltet.

PHASE 2: Memory Engine
Schreibe das Skript für die Datenbank. Es muss Text entgegennehmen, embedden und speichern sowie basierend auf Text suchen können.

PHASE 3: Brain Engine
Schreibe die Wrapper für Groq und Ollama.

PHASE 4: Main Logic
Verbinde alles in einer `main.py` mit einer Endlosschleife für den Chat.

---

START-BEFEHL:
Habe ich mich klar ausgedrückt? Wenn ja, bestätige kurz, dass du die Hardware-Limits (12GB VRAM) und das Ziel (Vektor-Memory) verstanden hast.
Beginne dann sofort mit PHASE 1: Schlage die Ordnerstruktur vor und erstelle den Inhalt für `requirements.txt` und `config.py`.
