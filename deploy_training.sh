#!/bin/bash
# CHAPiE Training Deployment Script
# Startet/stoppt/überwacht den Training-Daemon auf dem Server

SERVER_USER="bbecker"
SERVER_HOST="100.105.94.71"
PROJECT_PATH="/home/bbecker/CHAPiE"

function colors() {
    GREEN='\033[0;32m'
    RED='\033[0;31m'
    YELLOW='\033[1;33m'
    NC='\033[0m' # No Color
}

colors

case "$1" in
    start)
        echo -e "${GREEN}Verbinde mit Server und starte Training-Daemon...${NC}"
        ssh "$SERVER_USER@$SERVER_HOST" "cd $PROJECT_PATH && source venv/bin/activate && nohup python Chappies_Trainingspartner/training_daemon.py > training_daemon.log 2>&1 &"
        echo -e "${GREEN}✅ Daemon gestartet auf dem Server${NC}"
        echo -e "${YELLOW}Logs ansehen: ./deploy_training.sh tail${NC}"
        ;;

    stop)
        echo -e "${YELLOW}Stoppe Training-Daemon...${NC}"
        ssh "$SERVER_USER@$SERVER_HOST" "pkill -f training_daemon.py"
        echo -e "${GREEN}✅ Daemon gestoppt${NC}"
        ;;

    status)
        echo -e "${YELLOW}Prüfe Status des Training-Daemons...${NC}"
        ssh "$SERVER_USER@$SERVER_HOST" "ps aux | grep training_daemon.py | grep -v grep && echo -e '${GREEN}✅ RUNNING${NC}' || echo -e '${RED}❌ STOPPED${NC}'"
        echo -e "${YELLOW}=== Letzte Logs ===${NC}"
        ssh "$SERVER_USER@$SERVER_HOST" "tail -20 $PROJECT_PATH/training_daemon.log"
        ;;

    tail)
        echo -e "${YELLOW}Live-Logs vom Server (Ctrl+C zum Beenden):${NC}"
        ssh "$SERVER_USER@$SERVER_HOST" "tail -f $PROJECT_PATH/training_daemon.log"
        ;;

    *)
        echo "Usage: $0 {start|stop|status|tail}"
        exit 1
        ;;
esac