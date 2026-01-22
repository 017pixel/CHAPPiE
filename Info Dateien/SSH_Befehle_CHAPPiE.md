# 🚀 CHAPPiE Server Guide: Maximum Autonomy
*"Set and Forget" - Anleitung für den 24/7 Betrieb auf Ubuntu*

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

## 🚀 1. Training Starten (nohup - Empfohlen)
Die einfachste Methode: Starten und Logout möglich.

**Wichtig:** Nutze den neuen Modul-Aufruf (`python -m ...`), damit alle Imports funktionieren!

```bash
# A: Standard-Start (Nutzt settings.json / training_config.json)
nohup python3 -m Chappies_Trainingspartner.training_loop > training.log 2>&1 &

# B: Mit vorherigem Setup (Wizard kurz starten, dann abbrechen und nohup nutzen)
# 1. python3 -m Chappies_Trainingspartner.setup_training
# 2. Konfigurieren & Speichern
# 3. STRG+C
# 4. nohup python3 -m Chappies_Trainingspartner.training_loop > training.log 2>&1 &
```

**Erklärung:**
- `nohup`: Verhindert Beenden beim Logout
- `-m ...`: Startet das Modul korrekt (wichtig für Imports!)
- `> training.log`: Speichert alle Ausgaben in diese Datei
- `2>&1`: Leitet auch Fehler in die Datei um
- `&`: Startet den Prozess im Hintergrund

---

## 🖥 2. Alternative: "Screen" (für Interaktion)
Falls du zwischendurch in die Konsole schauen willst.
1. `screen -S chappie`
2. `python3 -m Chappies_Trainingspartner.training_loop`
3. `STRG+A`, dann `D` zum Verlassen.

---

## 🤖 3. Alternative: Systemd Service
Für automatischen Start beim Booten (siehe `chappie-training.service`).

---

---

## 📊 4. Monitoring (Wichtig bei nohup!)
Überwache den Prozess im Hintergrund.

```bash
# Live-Logs verfolgen (Drücke STRG+C zum Verlassen)
tail -f training.log

# Prüfen, ob der Prozess noch läuft
ps aux | grep training_loop
```

## 🛑 5. Training Stoppen
Um den Prozess zu beenden:

```bash
pkill -f training_loop
```

---

## 🏥 6. Server Health Check
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

## 📂 7. Daten-Management & Backups
Sichere das Gehirn deines KI-Partners.

```bash
# Backup der Datenbank erstellen (Zeitstempel im Namen)
tar -czf backup_chappie_$(date +%F).tar.gz data/

# Backup auf deinen PC ziehen (Befehl auf WINDOWS ausführen!)
scp bbecker@100.105.94.71:~/CHAPPiE/backup_chappie_*.tar.gz .
```

---

## 📝 Service Template (`/etc/systemd/system/chappie-training.service`)
Falls du den Service nutzen willst, hier ist die Vorlage. Passe `User` und `WorkingDirectory` an!

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

# Start-Befehl (Direkt den Loop starten, ohne Wizard)
ExecStart=/home/bbecker/CHAPPiE/venv/bin/python3 -m Chappies_Trainingspartner.training_loop

# Restart bei Crash (Wichtig für Autonomie!)
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
