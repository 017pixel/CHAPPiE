#!/bin/bash
# CHAPiE Training & Web Deployment Script
# Startet/stoppt/überwacht Training-Daemon und Web-UI auf dem Server

SERVER_USER="bbecker"
SERVER_HOST="100.105.94.71"
PROJECT_PATH="/home/bbecker/CHAPPiE"
VENV_PATH="$PROJECT_PATH/venv"

function colors() {
    GREEN='\033[0;32m'
    RED='\033[0;31m'
    YELLOW='\033[1;33m'
    CYAN='\033[0;36m'
    NC='\033[0m' # No Color
}

colors

# Prüfen ob wir lokal auf dem Server sind
IS_LOCAL=false
if [[ "$(hostname)" == "benjaminsserver2" ]] || [[ "$HOSTNAME" == "benjaminsserver2" ]]; then
    IS_LOCAL=true
fi

check_connection() {
    if [ "$IS_LOCAL" = true ]; then
        return 0
    fi
    echo -e "${CYAN}Prüfe Verbindung zu $SERVER_HOST...${NC}"
    if ! ssh -q -o BatchMode=yes -o ConnectTimeout=5 "$SERVER_USER@$SERVER_HOST" exit; then
        echo -e "${RED}❌ Keine Verbindung zum Server möglich!${NC}"
        exit 1
    fi
}

# Helper für Befehlsausführung (Lokal vs. Remote)
run_cmd() {
    local cmd=$1
    if [ "$IS_LOCAL" = true ]; then
        bash -c "$cmd"
    else
        ssh -t "$SERVER_USER@$SERVER_HOST" "$cmd"
    fi
}

case "$1" in
    # === SYSTEMD SERVICE COMMANDS (EMPFOHLEN) ===
    install-service)
        check_connection
        echo -e "${YELLOW}Installiere Systemd Services...${NC}"
        
        if [ "$IS_LOCAL" = true ]; then
            sudo cp chappie-training.service chappie-web.service /etc/systemd/system/
        else
            scp chappie-training.service chappie-web.service "$SERVER_USER@$SERVER_HOST:$PROJECT_PATH/"
            ssh -t "$SERVER_USER@$SERVER_HOST" "sudo cp $PROJECT_PATH/chappie-training.service $PROJECT_PATH/chappie-web.service /etc/systemd/system/"
        fi
        
        run_cmd "sudo systemctl daemon-reload && sudo systemctl enable chappie-training.service chappie-web.service"
        
        echo -e "${GREEN}✅ Services installiert und enabled.${NC}"
        echo -e "${YELLOW}Starte mit: ./deploy_training.sh service-start${NC}"
        ;;

    service-start)
        check_connection
        echo -e "${GREEN}Starte CHAPPiE Services via Systemd...${NC}"
        run_cmd "sudo systemctl start chappie-training.service chappie-web.service"
        echo -e "${GREEN}✅ Start-Befehl gesendet.${NC}"
        ;;

    service-stop)
        check_connection
        echo -e "${YELLOW}Stoppe CHAPPiE Services...${NC}"
        run_cmd "sudo systemctl stop chappie-training.service chappie-web.service"
        echo -e "${GREEN}✅ Stop-Befehl gesendet.${NC}"
        ;;

    service-restart)
        check_connection
        echo -e "${YELLOW}Starte CHAPPiE Services neu...${NC}"
        run_cmd "sudo systemctl restart chappie-training.service chappie-web.service"
        echo -e "${GREEN}✅ Restart-Befehl gesendet.${NC}"
        ;;

    service-status)
        check_connection
        echo -e "${YELLOW}Prüfe Systemd Service Status...${NC}"
        run_cmd "sudo systemctl status chappie-training.service chappie-web.service"
        ;;
        
    # === LOGGING ===
    tail)
        check_connection
        echo -e "${YELLOW}Live-Logs vom Training (Ctrl+C zum Beenden):${NC}"
        if [ "$IS_LOCAL" = true ]; then
            tail -f "$PROJECT_PATH/training_daemon.log"
        else
            ssh "$SERVER_USER@$SERVER_HOST" "tail -f $PROJECT_PATH/training_daemon.log"
        fi
        ;;

    tail-web)
        check_connection
        echo -e "${YELLOW}Live-Logs vom Web-UI (Ctrl+C zum Beenden):${NC}"
        run_cmd "sudo journalctl -u chappie-web.service -f"
        ;;

    # === MANUAL COMMANDS (LEGACY) ===
    start-manual)
        check_connection
        echo -e "${YELLOW}Starte Training-Daemon manuell (nohup)...${NC}"
        ssh "$SERVER_USER@$SERVER_HOST" "cd $PROJECT_PATH && source venv/bin/activate && nohup python3 Chappies_Trainingspartner/training_daemon.py > training_daemon.log 2>&1 &"
        echo -e "${GREEN}✅ Daemon manuell gestartet${NC}"
        ;;

    stop-manual)
        check_connection
        echo -e "${YELLOW}Stoppe manuellen Training-Daemon...${NC}"
        ssh "$SERVER_USER@$SERVER_HOST" "pkill -f training_daemon.py"
        echo -e "${GREEN}✅ Prozess gekillt${NC}"
        ;;
    
    # === REMOTE UPDATES ===
    update)
        check_connection
        echo -e "${CYAN}Aktualisiere Server-Code & Dependencies...${NC}"
        ssh "$SERVER_USER@$SERVER_HOST" "cd $PROJECT_PATH && git pull && source venv/bin/activate && pip install -r requirements.txt"
        echo -e "${GREEN}✅ Update abgeschlossen. Bitte Services neustarten.${NC}"
        ;;

    *)
        echo "CHAPPiE Deployment Manager"
        echo "Usage: $0 {COMMAND}"
        echo ""
        echo "Service Commands (Empfohlen):"
        echo "  install-service  - Installiert systemd Services auf dem Server"
        echo "  service-start    - Startet Training & Web-UI"
        echo "  service-stop     - Stoppt Training & Web-UI"
        echo "  service-restart  - Startet alles neu (z.B. nach Config-Änderung)"
        echo "  service-status   - Zeigt Status aller Services"
        echo ""
        echo "Monitoring:"
        echo "  tail             - Live-Logs vom Training"
        echo "  tail-web         - Live-Logs vom Web-UI"
        echo ""
        echo "Maintenance:"
        echo "  update           - Git Pull & Pip Install auf dem Server"
        exit 1
        ;;
esac