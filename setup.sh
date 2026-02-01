#!/bin/bash
# CHAPPiE Auto-Setup Script für AI Agents
# Dieses Script richtet CHAPPiE automatisch ein

set -e  # Stop bei Fehlern

echo "[START] CHAPPiE Auto-Setup wird gestartet..."
echo ""

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Prüfe ob Python 3.11+ installiert ist
echo -e "${BLUE}[CHECK] Prüfe Python Version...${NC}"
python_version=$(python3 --version 2>&1 || python --version 2>&1)
echo "Gefunden: $python_version"

# Repository klonen oder aktualisieren
if [ -d "CHAPPiE" ]; then
    echo -e "${YELLOW}[DIR] CHAPPiE Verzeichnis existiert bereits. Aktualisiere...${NC}"
    cd CHAPPiE
    git pull
else
    echo -e "${BLUE}[DOWNLOAD] Klone Repository...${NC}"
    git clone https://github.com/017pixel/CHAPPiE.git
    cd CHAPPiE
fi

# Virtual Environment erstellen
echo -e "${BLUE}[PYTHON] Erstelle Virtual Environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv || python -m venv venv
fi

# Virtual Environment aktivieren
echo -e "${BLUE}[RUN] Aktiviere Virtual Environment...${NC}"
source venv/bin/activate

# Dependencies installieren
echo -e "${BLUE}[INSTALL] Installiere Dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# Prüfe ob Ollama installiert ist
echo -e "${BLUE}[SEARCH] Prüfe Ollama...${NC}"
if command -v ollama &> /dev/null; then
    echo -e "${GREEN}[OK] Ollama ist installiert${NC}"
    
    # Intent Processor Modell herunterladen
    echo -e "${BLUE}[AI] Lade Intent Processor Modell (qwen2.5:7b)...${NC}"
    ollama pull qwen2.5:7b || echo -e "${YELLOW}[WARN]  Konnte qwen2.5:7b nicht laden. Überspringe...${NC}"
else
    echo -e "${YELLOW}[WARN]  Ollama nicht gefunden. Lokale Modelle nicht verfügbar.${NC}"
    echo -e "${YELLOW}   Installiere Ollama von: https://ollama.com${NC}"
fi

# Konfigurationsdatei erstellen
echo -e "${BLUE}[CONFIG] Richte Konfiguration ein...${NC}"
if [ ! -f "config/secrets.py" ]; then
    if [ -f "config/secrets_example.py" ]; then
        cp config/secrets_example.py config/secrets.py
        echo -e "${GREEN}[OK] secrets.py erstellt${NC}"
        echo -e "${YELLOW}[WARN]  WICHTIG: Bearbeite config/secrets.py und trage deine API Keys ein!${NC}"
    else
        echo -e "${YELLOW}[WARN]  secrets_example.py nicht gefunden${NC}"
    fi
else
    echo -e "${GREEN}[OK] secrets.py existiert bereits${NC}"
fi

# Daten-Verzeichnis erstellen
echo -e "${BLUE}[DIR] Erstelle Daten-Verzeichnisse...${NC}"
mkdir -p data/chroma_db

echo ""
echo -e "${GREEN}[DONE] Setup abgeschlossen!${NC}"
echo ""
echo -e "${BLUE}[START] CHAPPiE kann jetzt gestartet werden:${NC}"
echo ""
echo "  Web UI:    streamlit run app.py"
echo "  CLI:       python main.py"
echo "  Training:  python -m Chappies_Trainingspartner.training_daemon --neu"
echo ""
echo -e "${YELLOW}[TIP] Tipp: Bearbeite config/secrets.py um API Keys einzutragen!${NC}"
echo ""

# Frage ob CHAPPiE sofort gestartet werden soll
read -p "Möchtest du CHAPPiE jetzt im Web-Modus starten? (j/N): " start_now

if [[ $start_now =~ ^[Jj]$ ]]; then
    echo -e "${GREEN}[WEB] Starte CHAPPiE Web UI...${NC}"
    streamlit run app.py
else
    echo -e "${BLUE}[BYE] Setup abgeschlossen. Bis bald!${NC}"
fi
