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
# Optionen: "ollama" (lokal), "groq" (cloud), "cerebras" (cloud high-speed)
LLM_PROVIDER = "cerebras"


# --- Ollama (Lokal) ---
# Hauptmodell für Unterhaltungen
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "llama3:70b"

# Modell für Gehirnzusammenfassungen / Sleep Modus
EMOTION_ANALYSIS_MODEL = "qwen2.5:1.5b"


# --- Groq (Cloud) ---
GROQ_MODEL = "moonshotai/kimi-k2-instruct-0905"


# --- Cerebras (Cloud - High Speed) ---
# Hole dir einen API Key von: https://cloud.cerebras.ai
CEREBRAS_API_KEY = ""

# Verfügbare Modelle: llama-3.3-70b, llama-3.1-8b, qwen-3-32b
CEREBRAS_MODEL = "llama-3.3-70b"


# ═══════════════════════════════════════════════════════════════════
# 🧠 MEMORY EINSTELLUNGEN
# ═══════════════════════════════════════════════════════════════════

# Embedding-Modell für die Vektordatenbank
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Wie viele Erinnerungen sollen bei jeder Anfrage abgerufen werden?
MEMORY_TOP_K = 5

# Name der ChromaDB Collection
CHROMA_COLLECTION = "chapie_memory"


# ═══════════════════════════════════════════════════════════════════
# ⚙️ GENERATION PARAMETER
# ═══════════════════════════════════════════════════════════════════

# Maximale Anzahl Tokens pro Antwort
MAX_TOKENS = 2048

# Kreativität (0.0 = deterministic, 1.0 = sehr kreativ)
# Für DeepSeek R1 ist etwas niedriger oft besser
TEMPERATURE = 0.6

# Token-Streaming aktivieren
STREAM = True


# ═══════════════════════════════════════════════════════════════════
# 🔍 SMART QUERY EXTRACTION
# ═══════════════════════════════════════════════════════════════════

ENABLE_QUERY_EXTRACTION = False
QUERY_EXTRACTION_GROQ_MODEL = "llama-3.1-8b-instant"
QUERY_EXTRACTION_OLLAMA_MODEL = "qwen2.5:1.5b"


# ═══════════════════════════════════════════════════════════════════
# 🐛 DEBUG
# ═══════════════════════════════════════════════════════════════════

DEBUG = True
CHAIN_OF_THOUGHT = True
