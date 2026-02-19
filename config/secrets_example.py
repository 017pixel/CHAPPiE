"""
CHAPiE - API Keys & Modell-Konfiguration (TEMPLATE)
===================================================
Kopiere diese Datei nach 'secrets.py' und trage dort deine Keys ein.
Die 'secrets.py' wird von Git ignoriert.
"""

# ═══════════════════════════════════════════════════════════════════
# 🔑 API SCHLÜSSEL
# ═══════════════════════════════════════════════════════════════════

# Groq Cloud API Key (Hole dir einen unter: https://console.groq.com/keys)
GROQ_API_KEY = "DEIN_GROQ_KEY_HIER"

# Cerebras Cloud API Key (Hole dir einen unter: https://cloud.cerebras.ai)
CEREBRAS_API_KEY = "DEIN_CEREBRAS_KEY_HIER"


# 🤖 MODELL AUSWAHL & PROVIDER
# ===========================

# Welches Backend soll verwendet werden? ("ollama", "groq", "cerebras")
LLM_PROVIDER = "groq"

# --- Ollama Configuration ---
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "llama3:8b"
EMOTION_ANALYSIS_MODEL = "qwen2.5:1.5b"

# --- Groq Configuration ---
GROQ_MODEL = "llama-3.3-70b-versatile"

# --- Cerebras Configuration ---
CEREBRAS_MODEL = "llama-3.3-70b"


# 🧠 MEMORY EINSTELLUNGEN
# ======================
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
MEMORY_TOP_K = 5
CHROMA_COLLECTION = "chapie_memory"


# ⚙️ GENERATION PARAMETER
# ======================
MAX_TOKENS = 2048
TEMPERATURE = 0.7
STREAM = True


# 🔎 SMART QUERY EXTRACTION
# =========================
ENABLE_QUERY_EXTRACTION = True
QUERY_EXTRACTION_GROQ_MODEL = "llama-3.1-8b-instant"
QUERY_EXTRACTION_OLLAMA_MODEL = "qwen2.5:1.5b"


# 🐛 DEBUG / COT
# ==============
DEBUG = True
CHAIN_OF_THOUGHT = True
