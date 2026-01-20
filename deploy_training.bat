@echo off
REM CHAPiE Training Deployment Script (Windows)
REM Startet/stoppt/überwacht den Training-Daemon auf dem Server

set SERVER_USER=bbecker
set SERVER_HOST=100.105.94.71
set PROJECT_PATH=/home/bbecker/CHAPiE

if "%1"=="" goto usage
if "%1"=="start" goto start
if "%1"=="stop" goto stop
if "%1"=="status" goto status
if "%1"=="tail" goto tail
goto usage

:start
echo [GREEN]Verbinde mit Server...[/GREEN]

REM 1. Updates holen und Dependencies installieren (nicht-interaktiv)
echo [YELLOW]Hole Updates von GitHub...[/YELLOW]
ssh %SERVER_USER%@%SERVER_HOST% "cd %PROJECT_PATH% && git pull && source venv/bin/activate && pip install -r requirements.txt"

REM 2. Setup-Wizard starten (INTERAKTIV - fragt nach Persona/Focus)
echo [YELLOW]Starte Setup-Wizard...[/YELLOW]
ssh -t %SERVER_USER%@%SERVER_HOST% "cd %PROJECT_PATH% && source venv/bin/activate && python Chappies_Trainingspartner/setup_training.py"

REM 3. Daemon im Hintergrund starten
echo [GREEN]Starte Training-Daemon im Hintergrund...[/GREEN]
ssh %SERVER_USER%@%SERVER_HOST% "cd %PROJECT_PATH% && source venv/bin/activate && nohup python Chappies_Trainingspartner/training_daemon.py ^> training_daemon.log 2^>^&1 ^&"

echo [GREEN]Daemon erfolgreich gestartet![/GREEN]
echo Logs ansehen: deploy_training.bat tail
goto end

:stop
echo [YELLOW]Stoppe Training-Daemon...[/YELLOW]
ssh %SERVER_USER%@%SERVER_HOST% "pkill -f training_daemon.py"
echo [GREEN]Daemon gestoppt[/GREEN]
goto end

:status
echo [YELLOW]Pruefe Status des Training-Daemons...[/YELLOW]
ssh %SERVER_USER%@%SERVER_HOST% "ps aux | grep training_daemon.py | grep -v grep && echo RUNNING || echo STOPPED"
echo [YELLOW]Letzte Logs:[/YELLOW]
ssh %SERVER_USER%@%SERVER_HOST% "tail -20 %PROJECT_PATH%/training_daemon.log"
goto end

:tail
echo [YELLOW]Live-Logs vom Server (Ctrl+C zum Beenden):[/YELLOW]
ssh %SERVER_USER%@%SERVER_HOST% "tail -f %PROJECT_PATH%/training_daemon.log"
goto end

:usage
echo Usage: %0 {start^|stop^|status^|tail}
exit /b 1

:end