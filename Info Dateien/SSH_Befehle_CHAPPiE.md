# 🚀 CHAPPiE Server Guide: Maximum Autonomy
*"Set and Forget" - Anleitung für den 24/7 Betrieb auf Ubuntu*

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
| [📝 Service Template](#-service-template) | Systemd-Service Konfiguration |

## 🛠 0. Setup & Updates
Bevor du startest, sichere dir immer den neuesten Stand.

```bash
# 1. Verbinden
ssh bbecker@100.105.94.71

# 2. In Projektordner
cd ~/CHAPPiE

# 3. Update & Environment
git pull
source venv/bin/activate
pip install -r requirements.txt
```

---

## 🚀 1. Training Starten (Service - Empfohlen)
Die robusteste Methode für 24/7 Betrieb. Der Service startet automatisch neu, falls der Server rebootet oder der Prozess crasht.

### Installation & Start
Wir nutzen das `deploy_training.sh` Skript, um alles einzurichten:

```bash
# 1. Service installieren (nur einmalig nötig oder nach Änderungen an der .service Datei)
./deploy_training.sh install-service

# 2. Service starten
./deploy_training.sh service-start

# 3. Status prüfen
./deploy_training.sh service-status
```

### Logs ansehen
```bash
# Live Logs
journalctl -u chappie-training.service -f

# Oder über unser Skript (liest die Log-Datei)
./deploy_training.sh tail
```

---

## 🖥 2. Manuelles Starten (nohup)
Falls du keinen Systemd-Service nutzen willst.

**Wichtig:** Nutze `training_daemon.py` (NICHT `training_loop.py` - das hat keinen Einstiegspunkt!)

```bash
# A: Standard-Start (Setzt vorheriges Training fort mit training_config.json)
nohup python3 Chappies_Trainingspartner/training_daemon.py > training.log 2>&1 &

# B: NEUES Training starten (interaktiv - fragt Konfiguration ab)
python3 Chappies_Trainingspartner/training_daemon.py --neu
```

**Erklärung:**
- `nohup`: Verhindert Beenden beim Logout
- `training_daemon.py`: Hat den eigentlichen main() Einstiegspunkt
- `> training.log`: Speichert alle Ausgaben in diese Datei
- `2>&1`: Leitet auch Fehler in die Datei um
- `&`: Startet den Prozess im Hintergrund

---

## 📊 3. Monitoring & Logs
Überwache den Prozess im Hintergrund und analysiere Logs.

### 🔍 Prozess-Monitoring
```bash
# Prüfen, ob das Training läuft (bei Service)
systemctl status chappie-training.service

# Manuell prüfen
ps aux | grep training_daemon
```

### 📝 Log-Analyse
```bash
# Über das Helper-Script
./deploy_training.sh tail

# Manuell
tail -f training_daemon.log
```

---

## 🛑 4. Training Stoppen
Um den Prozess zu beenden:

```bash
# A: Wenn als Service gestartet (Empfohlen)
./deploy_training.sh service-stop

# B: Wenn manuell gestartet
pkill -f training_daemon.py
```

---

## 🏥 5. Server Health Check
Allgemeine Server-Überwachung.

```bash
# CPU & RAM Auslastung (Bunt & Interaktiv)
htop

# Speicherplatz prüfen
df -h

# Wie groß ist die ChromaDB Datenbank?
du -sh data/*
```


---

## 📂 6. Daten-Management & Backups
Sichere das Gehirn deines KI-Partners.

```bash
# Backup der Datenbank erstellen (Zeitstempel im Namen)
tar -czf backup_chappie_$(date +%F).tar.gz data/

# Backup auf deinen PC ziehen (Befehl auf WINDOWS ausführen!)
scp bbecker@100.105.94.71:~/CHAPPiE/backup_chappie_*.tar.gz .
```

---

## 🔄 Training Neustarten (Neue Anweisungen / Reset)

Wenn du das Training komplett neu starten willst (z.B. neue Trainer-Persona, neuer Fokus), gehe so vor:

### 1. Service Stoppen
```bash
sudo systemctl stop chappie-training.service
```

### 2. Neuen Fokus setzen (2 Methoden)

**Methode A: Konfiguration per Befehl überschreiben (Schnell)**
Dies löscht automatisch den alten Status und speichert die neue Config.
```bash
python3 Chappies_Trainingspartner/training_daemon.py --fokus "Menschlichkeit & Eigener Wille" --persona "Ein Mentor, der Chappie beibringt, Nein zu sagen und Gefühle zu zeigen" --start "Chappie, hör auf mich bedienen zu wollen. Wer bist du wirklich?"
```

**Methode B: Konfiguration via Git Update (Sauber)**
Wenn du die `training_config.json` lokal am PC bearbeitet und gepusht hast:
```bash
# 1. Neueste Config laden
git pull

# 2. Alten Speicherstand löschen (WICHTIG für frischen Start!)
rm training_state.json
```

### 3. Service wieder starten
Damit läuft das Training mit den neuen Anweisungen weiter im Hintergrund.
```bash
sudo systemctl start chappie-training.service
```

### 4. Prüfen
```bash
./deploy_training.sh tail
```

---

## 📝 Service Template (`/etc/systemd/system/chappie-training.service`)
Dies ist die Konfiguration, die von `./deploy_training.sh install-service` installiert wird.
**WICHTIG:** `ExecStart` muss auf `training_daemon.py` zeigen!

```ini
[Unit]
Description=CHAPPiE Autonomous Training Service
After=network.target

[Service]
# User unter dem es laufen soll
User=bbecker
Group=bbecker

# Pfad zum Projekt
WorkingDirectory=/home/bbecker/CHAPPiE

# Environment Variablen laden
Environment="PATH=/home/bbecker/CHAPPiE/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"

# Start-Befehl (Direkt den Daemon starten - NICHT training_loop!)
ExecStart=/home/bbecker/CHAPPiE/venv/bin/python3 -m Chappies_Trainingspartner.training_daemon

# Restart bei Crash (Wichtig für Autonomie!)
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
