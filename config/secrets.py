"""
CHAPiE - API Keys & Modell-Konfiguration
=========================================
Hier trägst du deine API-Schlüssel und Modellnamen ein.

"""

# ═══════════════════════════════════════════════════════════════════
# 🔑 API SCHLÜSSEL
# ═══════════════════════════════════════════════════════════════════

# Groq Cloud API Key
# Hole dir einen kostenlosen Key von: https://console.groq.com/keys
GROQ_API_KEY = "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"


# ═══════════════════════════════════════════════════════════════════
# 🤖 MODELL AUSWAHL
# ═══════════════════════════════════════════════════════════════════

# Welches Backend soll verwendet werden?
# Optionen: "ollama" (lokal) oder "groq" (cloud)
LLM_PROVIDER = "groq"


# --- Ollama (Lokal) ---
# Stelle sicher, dass Ollama läuft und das Modell installiert ist!
# Installation: ollama pull llama3:8b
# Für Emotions-Analyse (schnell): ollama pull qwen2.5:1.5b
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "llama3:8b"
EMOTION_ANALYSIS_MODEL = "qwen2.5:1.5b"


# --- Groq (Cloud) ---
# Schnelle Cloud-API, benötigt GROQ_API_KEY oben
# Verfügbare Modelle: https://console.groq.com/docs/models
GROQ_MODEL = "moonshotai/kimi-k2-instruct-0905"

#moonshotai/kimi-k2-instruct-0905
#openai/gpt-oss-120b

# ═══════════════════════════════════════════════════════════════════
# 🧠 MEMORY EINSTELLUNGEN
# ═══════════════════════════════════════════════════════════════════

# Embedding-Modell für die Vektordatenbank
# Läuft lokal, braucht ca. 500MB VRAM
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Wie viele Erinnerungen sollen bei jeder Anfrage abgerufen werden?
MEMORY_TOP_K = 5

# Name der ChromaDB Collection
CHROMA_COLLECTION = "chapie_memory"


# ═══════════════════════════════════════════════════════════════════
# ⚙️ GENERATION PARAMETER
# ═══════════════════════════════════════════════════════════════════

# Maximale Anzahl Tokens pro Antwort
MAX_TOKENS = 1024

# Kreativität (0.0 = deterministic, 1.0 = sehr kreativ)
TEMPERATURE = 0.7

# Token-Streaming aktivieren (Text fließt Wort für Wort)
STREAM = True


# ═══════════════════════════════════════════════════════════════════
# � SMART QUERY EXTRACTION (RAG OPTIMIERUNG)
# ═══════════════════════════════════════════════════════════════════

# Smart Query Extraction aktivieren?
# True = User-Input wird vor der Vektor-Suche durch LLM optimiert
# False = User-Input wird direkt vektorisiert (alte Methode)
ENABLE_QUERY_EXTRACTION = False

# --- Groq (Cloud) für Query Extraction ---
# Schnelles Modell für Keyword-Extraktion
QUERY_EXTRACTION_GROQ_MODEL = "llama-3.1-8b-instant"

# --- Ollama (Local Fallback) ---
# Kleines Modell für Offline-Fallback
QUERY_EXTRACTION_OLLAMA_MODEL = "llama3.2:1b"


# ═══════════════════════════════════════════════════════════════════
# �� DEBUG
# ═══════════════════════════════════════════════════════════════════

# Debug-Modus für zusätzliche Ausgaben
DEBUG = True

# Innerer Monolog (Chain of Thought) aktivieren?
# True = Erst denken, dann antworten (besser, aber langsamer)
# False = Sofort antworten (schneller)
CHAIN_OF_THOUGHT = True

