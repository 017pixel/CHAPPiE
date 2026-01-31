# 🚀 CHAPPiE Server Guide: Maximum Autonomy
*"Set and Forget" - Anleitung für den 24/7 Betrieb auf Ubuntu*

**Aktualisiert: 31.01.2026**

---

## 📋 Inhaltsverzeichnis

| Abschnitt | Beschreibung |
|-----------|-------------|
| [🛠 0. Setup & Updates](#-0-setup--updates) | Projekt aktualisieren und Environment einrichten |
| [🚀 1. Training Starten (Service - Empfohlen)](#-1-training-starten-service---empfohlen) | Robuster 24/7 Betrieb über Systemd |
| [🖥 2. Manuelles Starten (nohup)](#-2-manuelles-starten-nohup) | Alternative Startmethode |
| [📊 3. Monitoring & Logs](#-3-monitoring--logs) | Prozesse überwachen und Logs analysieren |
| [🛑 4. Training Stoppen](#-4-training-stoppen) | Das Training beenden |
| [🏥 5. Server Health Check](#-5-server-health-check) | System-Überwachung und Diagnose |
| [📂 6. Daten-Management](#-6-daten-management--backups) | Backups und Datenverwaltung |
| [🌐 7. Web-UI Starten](#-7-web-ui-starten) | Streamlit-App für Browser-Zugriff |
| [🆘 8. Troubleshooting](#-8-troubleshooting--common-issues) | Lösungen für häufige Probleme |
| [📝 Service Templates](#-service-templates) | Systemd-Service Konfigurationen |

---

## 🛠 0. Setup & Updates

### Erstmalige Einrichtung
```bash
# 1. Verbinden
ssh bbecker@100.105.94.71

# 2. Projekt klonen (falls noch nicht vorhanden)
cd ~
git clone https://github.com/DEIN_USER/CHAPPiE.git

# 3. Virtual Environment erstellen
cd ~/CHAPPiE
python3 -m venv venv

# 4. Aktivieren & Dependencies installieren
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Updates holen
```bash
# In Projektordner wechseln & Environment aktivieren
cd ~/CHAPPiE && source venv/bin/activate

# Updates ziehen
git pull

# Dependencies aktualisieren (falls requirements.txt geändert)
pip install -r requirements.txt --upgrade
```

---

## 🚀 1. Training Starten (Service - Empfohlen)

Die robusteste Methode für 24/7 Betrieb. Der Service startet automatisch neu bei Reboot oder Crash.

### Schnellstart (Service)
```bash
# 1. Service installieren (einmalig oder nach Änderungen)
./deploy_training.sh install-service

# 2. Service starten
./deploy_training.sh service-start

# 3. Status prüfen
./deploy_training.sh service-status
```

### Alternative: Direkte systemctl Befehle
```bash
# Service starten
sudo systemctl start chappie-training.service

# Service stoppen
sudo systemctl stop chappie-training.service

# Status prüfen
sudo systemctl status chappie-training.service

# Autostart aktivieren (startet nach Reboot automatisch)
sudo systemctl enable chappie-training.service
```

---

## 🖥 2. Manuelles Starten (nohup)

Falls du keinen Systemd-Service nutzen willst oder schnell testen möchtest.

### Standard-Start (Setzt vorheriges Training fort)
```bash
cd ~/CHAPPiE && source venv/bin/activate

# Mit nohup im Hintergrund starten
nohup python3 Chappies_Trainingspartner/training_daemon.py > training.log 2>&1 &

# PID merken für später
echo $! > training.pid
echo "Training gestartet mit PID: $(cat training.pid)"
```

### NEUES Training starten (interaktiv)
```bash
cd ~/CHAPPiE && source venv/bin/activate

# Interaktiver Modus (fragt Konfiguration ab)
python3 Chappies_Trainingspartner/training_daemon.py --neu
```

### NEUES Training mit direkten Parametern
```bash
cd ~/CHAPPiE && source venv/bin/activate

# Fokus, Persona und Start-Prompt direkt angeben
nohup python3 Chappies_Trainingspartner/training_daemon.py \
    --fokus "Philosophie & Ethik" \
    --persona "Ein neugieriger Student" \
    --start "Hallo Chappie, erkläre mir die Welt!" \
    > training.log 2>&1 &
```

**Erklärung der Parameter:**
| Parameter | Bedeutung |
|-----------|-----------|
| `nohup` | Verhindert Beenden beim Logout |
| `> training.log` | Speichert Ausgaben in Logdatei |
| `2>&1` | Leitet Fehler auch in die Datei |
| `&` | Startet im Hintergrund |

---

## 📊 3. Monitoring & Logs

### Prozess-Status prüfen
```bash
# Bei Service-Betrieb
sudo systemctl status chappie-training.service

# Bei nohup-Betrieb
ps aux | grep training_daemon | grep -v grep

# Alternativ: Prüfe ob PID noch läuft
if [ -f training.pid ]; then 
    ps -p $(cat training.pid) && echo "Training läuft" || echo "Training gestoppt"
fi
```

### Logs ansehen
```bash
# Service-Logs (Live-Modus mit -f)
sudo journalctl -u chappie-training.service -f

# Nur letzte 100 Zeilen
sudo journalctl -u chappie-training.service -n 100

# Manuelle Log-Datei (bei nohup)
tail -f training_daemon.log

# Letzte 50 Zeilen ohne Follow
tail -n 50 training_daemon.log
```

### Speicherverbrauch prüfen
```bash
# Interaktiv (Beenden mit 'q')
htop

# Einmaliger Snapshot
free -h

# Prozess-spezifisch
ps aux | grep python3 | grep -v grep
```

---

## 🛑 4. Training Stoppen

### Service stoppen
```bash
# Empfohlen: Über deploy-Script
./deploy_training.sh service-stop

# Alternativ: Direkt
sudo systemctl stop chappie-training.service
```

### Manuellen Prozess stoppen
```bash
# Sanftes Beenden (gibt dem Prozess Zeit um Daten zu speichern)
pkill -SIGTERM -f training_daemon.py

# Falls das nicht funktioniert: Force Kill
pkill -9 -f training_daemon.py

# Mit PID-Datei
if [ -f training.pid ]; then kill $(cat training.pid); rm training.pid; fi
```

---

## 🏥 5. Server Health Check

### Schneller Gesundheitscheck
```bash
# Einzeiler: Zeigt CPU, RAM, Disk auf einmal
echo "=== CPU & RAM ===" && free -h && echo "" && echo "=== DISK ===" && df -h / && echo "" && echo "=== CHAPPiE Prozesse ===" && ps aux | grep -E "(training|streamlit)" | grep -v grep
```

### Detaillierte Checks
```bash
# CPU & RAM Auslastung (interaktiv)
htop

# Speicherplatz
df -h

# ChromaDB Größe
du -sh ~/CHAPPiE/data/

# Einzelne Ordnergrößen
du -sh ~/CHAPPiE/data/*
```

### Netzwerk-Check
```bash
# Prüfe ob Streamlit-Port offen ist
netstat -tlnp | grep 8501

# Oder mit ss (moderner)
ss -tlnp | grep 8501
```

---

## 📂 6. Daten-Management & Backups

### Backup erstellen
```bash
cd ~/CHAPPiE

# Komplettes Backup mit Datum
tar -czf ~/backups/chappie_$(date +%Y%m%d_%H%M%S).tar.gz \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.log' \
    .

# Nur Datenbank + Config
tar -czf ~/backups/chappie_data_$(date +%Y%m%d).tar.gz \
    data/ \
    training_config.json \
    training_state.json
```

### Backup auf lokalen PC ziehen
Führe diese Befehle **auf deinem Windows-PC** aus (PowerShell):
```powershell
# Backup-Ordner anlegen
mkdir C:\CHAPPiE_Backups -ErrorAction SilentlyContinue

# Neuestes Backup holen
scp bbecker@100.105.94.71:~/backups/chappie_*.tar.gz C:\CHAPPiE_Backups\
```

### ChromaDB defragmentieren (bei großen Datenbanken)
```bash
cd ~/CHAPPiE && source venv/bin/activate

# Python-Skript für Kompaktierung
python3 -c "
from memory.memory_engine import MemoryEngine
engine = MemoryEngine()
print(f'Memories: {engine.get_memory_count()}')
print('Fertig!')
"
```

---

## 🌐 7. Web-UI Starten

### Als Service (Empfohlen für 24/7)
```bash
# Service installieren
sudo cp chappie-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable chappie-web.service
sudo systemctl start chappie-web.service
```

### Manuell mit nohup
```bash
cd ~/CHAPPiE && source venv/bin/activate

# Auf allen Interfaces erreichbar (für Remote-Zugriff)
nohup streamlit run app.py --server.address 0.0.0.0 --server.port 8501 > web.log 2>&1 &

# Nur lokal
nohup streamlit run app.py > web.log 2>&1 &
```

### Zugriff im Browser
```
http://100.105.94.71:8501
```

---

## 🆘 8. Troubleshooting (Common Issues)

### 🚫 "Permission denied" bei .sh Skripten
```bash
chmod +x deploy_training.sh
chmod +x *.sh
```

### 🔄 "git pull" schlägt fehl wegen lokaler Änderungen
```bash
# Option A: Lokale Änderungen verwerfen
git checkout -- .
git pull

# Option B: Änderungen stashen (aufheben)
git stash
git pull
git stash pop  # Änderungen wieder anwenden
```

### 🐍 "ModuleNotFoundError" 
```bash
# Sicherstellen dass venv aktiv ist
source ~/CHAPPiE/venv/bin/activate

# Dependencies neu installieren
pip install -r requirements.txt --force-reinstall
```

### 💾 "No space left on device"
```bash
# Große Log-Dateien finden
find ~ -name "*.log" -size +100M

# Alte Logs löschen
rm -f ~/CHAPPiE/*.log

# __pycache__ aufräumen
find ~/CHAPPiE -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
```

### 🔒 ChromaDB Lock-Fehler
Falls "database is locked" auftritt:
```bash
# Alle Python-Prozesse stoppen
pkill -9 -f python3

# Lock-Datei entfernen (falls vorhanden)
rm -f ~/CHAPPiE/data/chroma_db/*.lock

# Neu starten
./deploy_training.sh service-start
```

### 💥 Segmentation Fault bei ChromaDB
Falls "Segmentation fault (core dumped)" beim Start auftritt:
```bash
# 1. Alle Prozesse stoppen
sudo systemctl stop chappie-web.service
sudo pkill -9 -f streamlit
sudo pkill -9 -f python3

# 2. ChromaDB-Datenbank zurücksetzen (ACHTUNG: Löscht alle Erinnerungen!)
rm -rf ~/CHAPPiE/data/chroma_db/*

# 3. Service-Datei aktualisieren (mit neuen Umgebungsvariablen)
sudo cp ~/CHAPPiE/chappie-web.service /etc/systemd/system/
sudo systemctl daemon-reload

# 4. Neu starten
sudo systemctl start chappie-web.service
sudo systemctl status chappie-web.service
```

**Alternative: Ohne Datenverlust**
```bash
# Umgebungsvariablen setzen und manuell testen
export CHROMA_SQLITE_JOURNAL_MODE=WAL
export TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=1

cd ~/CHAPPiE && source venv/bin/activate
streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true
```

### 📊 Training produziert keine Ausgabe
```bash
# Prüfe ob Log-Datei wächst
ls -la ~/CHAPPiE/training_daemon.log

# Letzte Zeilen prüfen
tail -20 ~/CHAPPiE/training_daemon.log

# Prüfe auf Fehler
grep -i "error\|exception\|failed" ~/CHAPPiE/training_daemon.log | tail -20
```

---

## 📝 Service Templates

### Training Service (`/etc/systemd/system/chappie-training.service`)
```ini
[Unit]
Description=CHAPPiE Autonomous Training Service
After=network.target

[Service]
User=bbecker
Group=bbecker
WorkingDirectory=/home/bbecker/CHAPPiE

# Python-Umgebung
Environment="PATH=/home/bbecker/CHAPPiE/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"
Environment="PYTHONIOENCODING=utf-8"

# Start-Befehl (WICHTIG: Pfad mit Slash, nicht mit Punkt!)
ExecStart=/home/bbecker/CHAPPiE/venv/bin/python3 Chappies_Trainingspartner/training_daemon.py

# Restart-Policy
Restart=always
RestartSec=10

# Logging
StandardOutput=append:/home/bbecker/CHAPPiE/training_daemon.log
StandardError=append:/home/bbecker/CHAPPiE/training_daemon.log

[Install]
WantedBy=multi-user.target
```

### Web-UI Service (`/etc/systemd/system/chappie-web.service`)
```ini
[Unit]
Description=CHAPPiE Web Interface (Streamlit)
After=network.target

[Service]
User=bbecker
Group=bbecker
WorkingDirectory=/home/bbecker/CHAPPiE

Environment="PATH=/home/bbecker/CHAPPiE/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"

ExecStart=/home/bbecker/CHAPPiE/venv/bin/streamlit run app.py --server.address 0.0.0.0 --server.port 8501

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Service-Installation (Einmalig)
```bash
# Training-Service
sudo cp chappie-training.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable chappie-training.service

# Web-Service
sudo cp chappie-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable chappie-web.service

# Beide starten
sudo systemctl start chappie-training.service
sudo systemctl start chappie-web.service
```

---

## 🎯 Quick Reference (Spickzettel)

| Aktion | Befehl |
|--------|--------|
| **Training starten** | `./deploy_training.sh service-start` |
| **Training stoppen** | `./deploy_training.sh service-stop` |
| **Training Status** | `sudo systemctl status chappie-training` |
| **Logs ansehen** | `sudo journalctl -u chappie-training -f` |
| **Web-UI starten** | `sudo systemctl start chappie-web` |
| **Backup erstellen** | `tar -czf backup_$(date +%F).tar.gz data/` |
| **Health Check** | `htop` oder `free -h && df -h` |
| **Updates holen** | `cd ~/CHAPPiE && git pull` |
