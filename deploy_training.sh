#!/bin/bash
# CHAPiE Training Deployment Script
# Startet/stoppt/überwacht den Training-Daemon auf dem Server

SERVER_USER="bbecker"
SERVER_HOST="100.105.94.71"
PROJECT_PATH="/home/bbecker/CHAPPiE"

function colors() {
    GREEN='\033[0;32m'
    RED='\033[0;31m'
    YELLOW='\033[1;33m'
    NC='\033[0m' # No Color
}

colors

case "$1" in
    start)
        echo -e "${GREEN}Verbinde mit Server und starte Training-Daemon (nohup)...${NC}"
        ssh "$SERVER_USER@$SERVER_HOST" "cd $PROJECT_PATH && source venv/bin/activate && nohup python Chappies_Trainingspartner/training_daemon.py > training_daemon.log 2>&1 &"
        echo -e "${GREEN}✅ Daemon gestartet auf dem Server${NC}"
        echo -e "${YELLOW}Logs ansehen: ./deploy_training.sh tail${NC}"
        ;;

    stop)
        echo -e "${YELLOW}Stoppe Training-Daemon (nohup)...${NC}"
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

    # === SYSTEMD SERVICE COMMANDS ===
    install-service)
        echo -e "${YELLOW}Installiere Systemd Service auf dem Server...${NC}"
        # 1. Service Datei kopieren
        echo "Kopiere Service-Datei..."
        scp chappie-training.service "$SERVER_USER@$SERVER_HOST:$PROJECT_PATH/"
        
        # 2. Service installieren und aktivieren
        echo "Richte Service ein (sudo wird benötigt)..."
        ssh -t "$SERVER_USER@$SERVER_HOST" "sudo cp $PROJECT_PATH/chappie-training.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable chappie-training.service"
        
        echo -e "${GREEN}✅ Service installiert und enabled.${NC}"
        echo -e "${YELLOW}Starte mit: ./deploy_training.sh service-start${NC}"
        ;;

    service-start)
        echo -e "${GREEN}Starte CHAPPiE via Systemd...${NC}"
        ssh -t "$SERVER_USER@$SERVER_HOST" "sudo systemctl start chappie-training.service"
        echo -e "${GREEN}✅ Start-Befehl gesendet.${NC}"
        ;;

    service-stop)
        echo -e "${YELLOW}Stoppe CHAPPiE Service...${NC}"
        ssh -t "$SERVER_USER@$SERVER_HOST" "sudo systemctl stop chappie-training.service"
        echo -e "${GREEN}✅ Stop-Befehl gesendet.${NC}"
        ;;

    service-status)
        echo -e "${YELLOW}Prüfe Systemd Service Status...${NC}"
        ssh -t "$SERVER_USER@$SERVER_HOST" "sudo systemctl status chappie-training.service"
        ;;
        
    *)
        echo "Usage: $0 {start|stop|status|tail|install-service|service-start|service-stop|service-status}"
        exit 1
        ;;
esac