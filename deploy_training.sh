#!/bin/bash
# CHAPPiE Training, API und Frontend Deployment Script

SERVER_USER="bbecker"
SERVER_HOST="100.105.94.71"
PROJECT_PATH="/home/bbecker/CHAPPiE"

function colors() {
    GREEN='\033[0;32m'
    RED='\033[0;31m'
    YELLOW='\033[1;33m'
    CYAN='\033[0;36m'
    NC='\033[0m'
}

colors

IS_LOCAL=false
if [[ "$(hostname)" == "benjaminsserver2" ]] || [[ "$HOSTNAME" == "benjaminsserver2" ]]; then
    IS_LOCAL=true
fi

check_connection() {
    if [ "$IS_LOCAL" = true ]; then
        return 0
    fi
    echo -e "${CYAN}Pruefe Verbindung zu $SERVER_HOST...${NC}"
    if ! ssh -q -o BatchMode=yes -o ConnectTimeout=5 "$SERVER_USER@$SERVER_HOST" exit; then
        echo -e "${RED}Keine Verbindung zum Server moeglich.${NC}"
        exit 1
    fi
}

run_cmd() {
    local cmd=$1
    if [ "$IS_LOCAL" = true ]; then
        bash -c "$cmd"
    else
        ssh -t "$SERVER_USER@$SERVER_HOST" "$cmd"
    fi
}

case "$1" in
    install-service)
        check_connection
        echo -e "${YELLOW}Installiere Systemd Services...${NC}"

        if [ "$IS_LOCAL" = true ]; then
            sudo cp chappie-training.service chappie-vllm.service chappie-web.service chappie-frontend.service /etc/systemd/system/
        else
            scp chappie-training.service chappie-vllm.service chappie-web.service chappie-frontend.service "$SERVER_USER@$SERVER_HOST:$PROJECT_PATH/"
            ssh -t "$SERVER_USER@$SERVER_HOST" "sudo cp $PROJECT_PATH/chappie-training.service $PROJECT_PATH/chappie-vllm.service $PROJECT_PATH/chappie-web.service $PROJECT_PATH/chappie-frontend.service /etc/systemd/system/"
        fi

        run_cmd "sudo systemctl daemon-reload && sudo systemctl enable chappie-vllm.service chappie-training.service chappie-web.service chappie-frontend.service"

        echo -e "${GREEN}Services installiert und enabled.${NC}"
        echo -e "${YELLOW}Starte mit: ./deploy_training.sh service-start${NC}"
        ;;

    service-start)
        check_connection
        echo -e "${GREEN}Starte CHAPPiE Services via Systemd...${NC}"
        run_cmd "sudo systemctl start chappie-vllm.service chappie-training.service chappie-web.service chappie-frontend.service"
        echo -e "${GREEN}Start-Befehl gesendet.${NC}"
        ;;

    service-stop)
        check_connection
        echo -e "${YELLOW}Stoppe CHAPPiE Services...${NC}"
        run_cmd "sudo systemctl stop chappie-frontend.service chappie-web.service chappie-training.service chappie-vllm.service"
        echo -e "${GREEN}Stop-Befehl gesendet.${NC}"
        ;;

    service-restart)
        check_connection
        echo -e "${YELLOW}Starte CHAPPiE Services neu...${NC}"
        run_cmd "sudo systemctl restart chappie-vllm.service chappie-training.service chappie-web.service chappie-frontend.service"
        echo -e "${GREEN}Restart-Befehl gesendet.${NC}"
        ;;

    service-status)
        check_connection
        echo -e "${YELLOW}Pruefe Systemd Service Status...${NC}"
        run_cmd "sudo systemctl status chappie-vllm.service chappie-training.service chappie-web.service chappie-frontend.service"
        ;;

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
        echo -e "${YELLOW}Live-Logs von der App-API (Ctrl+C zum Beenden):${NC}"
        run_cmd "sudo journalctl -u chappie-web.service -f"
        ;;

    tail-frontend)
        check_connection
        echo -e "${YELLOW}Live-Logs vom Frontend (Ctrl+C zum Beenden):${NC}"
        run_cmd "sudo journalctl -u chappie-frontend.service -f"
        ;;

    tail-vllm)
        check_connection
        echo -e "${YELLOW}Live-Logs vom vLLM-Service (Ctrl+C zum Beenden):${NC}"
        run_cmd "sudo journalctl -u chappie-vllm.service -f"
        ;;

    start-manual)
        check_connection
        echo -e "${YELLOW}Starte Training-Daemon manuell (nohup)...${NC}"
        ssh "$SERVER_USER@$SERVER_HOST" "cd $PROJECT_PATH && source venv/bin/activate && nohup python3 -m Chappies_Trainingspartner.training_daemon > training_daemon.log 2>&1 &"
        echo -e "${GREEN}Daemon manuell gestartet${NC}"
        ;;

    stop-manual)
        check_connection
        echo -e "${YELLOW}Stoppe manuellen Training-Daemon...${NC}"
        ssh "$SERVER_USER@$SERVER_HOST" "pkill -f 'Chappies_Trainingspartner.training_daemon|training_daemon.py'"
        echo -e "${GREEN}Prozess gekillt${NC}"
        ;;

    update)
        check_connection
        echo -e "${CYAN}Aktualisiere Server-Code, Python und Frontend...${NC}"
        ssh "$SERVER_USER@$SERVER_HOST" "cd $PROJECT_PATH && git pull && source venv/bin/activate && pip install -r requirements.txt && cd frontend && npm install && npm run build"
        echo -e "${GREEN}Update abgeschlossen. Bitte Services neustarten.${NC}"
        ;;

    *)
        echo "CHAPPiE Deployment Manager"
        echo "Usage: $0 {COMMAND}"
        echo ""
        echo "Service Commands:"
        echo "  install-service  - Installiert vLLM-, Training-, API- und Frontend-Service"
        echo "  service-start    - Startet vLLM, Training, API und Frontend"
        echo "  service-stop     - Stoppt Frontend, API, Training und vLLM"
        echo "  service-restart  - Startet alles neu"
        echo "  service-status   - Zeigt Status aller Services"
        echo ""
        echo "Monitoring:"
        echo "  tail             - Live-Logs vom Training"
        echo "  tail-web         - Live-Logs von der App-API"
        echo "  tail-frontend    - Live-Logs vom Frontend"
        echo "  tail-vllm        - Live-Logs vom vLLM-Service"
        echo ""
        echo "Maintenance:"
        echo "  update           - Git Pull, Pip Install und Frontend Build auf dem Server"
        exit 1
        ;;
esac
