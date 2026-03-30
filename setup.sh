#!/bin/bash
# CHAPPiE Auto-Setup Script fuer AI Agents

set -e

echo "[START] CHAPPiE Auto-Setup wird gestartet..."
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}[CHECK] Pruefe Python Version...${NC}"
python_version=$(python3 --version 2>&1 || python --version 2>&1)
echo "Gefunden: $python_version"

if [ -d "CHAPPiE" ]; then
    echo -e "${YELLOW}[DIR] CHAPPiE Verzeichnis existiert bereits. Aktualisiere...${NC}"
    cd CHAPPiE
    git pull
else
    echo -e "${BLUE}[DOWNLOAD] Klone Repository...${NC}"
    git clone https://github.com/017pixel/CHAPPiE.git
    cd CHAPPiE
fi

echo -e "${BLUE}[PYTHON] Erstelle Virtual Environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv || python -m venv venv
fi

echo -e "${BLUE}[RUN] Aktiviere Virtual Environment...${NC}"
source venv/bin/activate

echo -e "${BLUE}[INSTALL] Installiere Python-Dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

if command -v npm >/dev/null 2>&1; then
    echo -e "${BLUE}[INSTALL] Installiere Frontend-Dependencies...${NC}"
    (
        cd frontend
        npm install
    )
else
    echo -e "${YELLOW}[WARN] npm nicht gefunden. Frontend-Dependencies werden uebersprungen.${NC}"
fi

echo -e "${BLUE}[SEARCH] Pruefe Ollama...${NC}"
if command -v ollama >/dev/null 2>&1; then
    echo -e "${GREEN}[OK] Ollama ist installiert${NC}"
    echo -e "${BLUE}[AI] Lade Intent Processor Modell (qwen2.5:7b)...${NC}"
    ollama pull qwen2.5:7b || echo -e "${YELLOW}[WARN] Konnte qwen2.5:7b nicht laden. Ueberspringe...${NC}"
else
    echo -e "${YELLOW}[WARN] Ollama nicht gefunden. Lokale Modelle nicht verfuegbar.${NC}"
    echo -e "${YELLOW}Installiere Ollama von: https://ollama.com${NC}"
fi

echo -e "${BLUE}[CONFIG] Richte Konfiguration ein...${NC}"
if [ ! -f "config/secrets.py" ]; then
    if [ -f "config/secrets_example.py" ]; then
        cp config/secrets_example.py config/secrets.py
        echo -e "${GREEN}[OK] secrets.py erstellt${NC}"
        echo -e "${YELLOW}[WARN] Bearbeite config/secrets.py und trage deine API Keys ein.${NC}"
    else
        echo -e "${YELLOW}[WARN] secrets_example.py nicht gefunden${NC}"
    fi
else
    echo -e "${GREEN}[OK] secrets.py existiert bereits${NC}"
fi

echo -e "${BLUE}[DIR] Erstelle Daten-Verzeichnisse...${NC}"
mkdir -p data/chroma_db

echo ""
echo -e "${GREEN}[DONE] Setup abgeschlossen!${NC}"
echo ""
echo -e "${BLUE}[START] CHAPPiE kann jetzt gestartet werden:${NC}"
echo ""
echo "  API:       uvicorn api.main:app --reload --port 8010"
echo "  Frontend:  cd frontend && npm run dev"
echo "  CLI:       python main.py"
echo "  Training:  python -m Chappies_Trainingspartner.training_daemon --neu"
echo ""
echo -e "${YELLOW}[TIP] Fuer Produktivbetrieb zuerst den lokalen Steering-Endpoint und danach API plus Frontend starten.${NC}"
echo ""

read -p "Moeechtest du die App-API jetzt starten? (j/N): " start_now

if [[ $start_now =~ ^[Jj]$ ]]; then
    echo -e "${GREEN}[API] Starte CHAPPiE App-API...${NC}"
    python -m uvicorn api.main:app --host 127.0.0.1 --port 8010 --reload
else
    echo -e "${BLUE}[BYE] Setup abgeschlossen. Bis bald!${NC}"
fi
