#!/bin/bash
# CHAPPiE Autonomy Script - läuft nach SSH-Trennung weiter

LOG_FILE="/home/bbecker/CHAPPiE/autonomy.log"
cd /home/bbecker/CHAPPiE

echo "[$(date)] Autonomy Script gestartet" >> $LOG_FILE

# Warte bis pip install fertig ist
while pgrep -f "pip install" > /dev/null; do
    echo "[$(date)] Installation noch aktiv..." >> $LOG_FILE
    sleep 60
done

echo "[$(date)] Python Pakete installiert" >> $LOG_FILE

# Prüfe vllm Ollama Integration
echo "[$(date)] Prüfe vllm Integration..." >> $LOG_FILE
python3 -c "import vllm; print('vllm OK')" >> $LOG_FILE 2>&1

# Teste Brain-Import
echo "[$(date)] Teste Brain-Imports..." >> $LOG_FILE
python3 -c "from brain.vllm_brain import VLLMBrain; print('VLLM Brain OK')" >> $LOG_FILE 2>&1
python3 -c "from memory.emotions_engine import EmotionsEngine; print('Emotions Engine OK')" >> $LOG_FILE 2>&1

echo "[$(date)] Alle Checks abgeschlossen" >> $LOG_FILE
echo "[$(date)] CHAPPiE bereit für Start" >> $LOG_FILE
