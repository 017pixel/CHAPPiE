# CHAPPiE mit einem Coding-Agenten einrichten

Kopiere den folgenden Prompt vollständig in den Coding-Agenten deiner Wahl. Der Agent soll auf dem Linux-Rechner laufen, auf dem CHAPPiE später gestartet wird.

```text
Richte CHAPPiE auf diesem Linux-Rechner vollständig ein und prüfe die Installation. Arbeite bis zu einem nachgewiesenen lokalen Startzustand. Frage mich nur nach Zugangsdaten oder einer Entscheidung, die du nicht aus dem System ermitteln kannst.

Repository:
https://github.com/017pixel/CHAPPiE.git

Zielzustand:
- Das Repository ist lokal vorhanden und aktuell.
- Python 3.11 oder neuer und Node.js 22.12 oder neuer sind verfügbar.
- Eine virtuelle Umgebung `venv` existiert.
- `requirements.txt` ist vollständig installiert.
- Die Frontend-Abhängigkeiten sind mit `npm ci --legacy-peer-deps` installiert und `npm run build` besteht.
- Das lokale Hauptmodell ist heruntergeladen.
- `CHAPPIE_CONFIG.json` enthält eine passende lokale vLLM-/Steering-Konfiguration.
- Der Groq API-Key bleibt optional. Ohne Key muss CHAPPiE lokal funktionieren.
- Steering-Service und App-API bestehen ihre Health-Checks.
- Ein modellfreier Pflicht-Testlauf ist grün.

Vorgehen:
1. Prüfe Betriebssystem, freien Speicher, Python-, Node-, npm- und Git-Version. Verändere keine laufenden Dienste und keine bestehende Preview-Umgebung.
2. Klone das Repository, falls es noch nicht vorhanden ist. Wenn es vorhanden ist, prüfe zuerst `git status`. Überschreibe keine lokalen Änderungen. Führe nur bei sauberem Arbeitsbaum einen Fast-Forward-Pull aus.
3. Lies `AGENTS.md`, `README.md`, `docs/vLLM-Setup.md` und `docs/local-models.md`.
4. Verwende standardmäßig `Qwen/Qwen3.5-4B`. Frage mich nur dann nach der Modellauswahl, wenn ich Gemma ausdrücklich erwähnt habe. Die unterstützte Alternative ist `google/gemma-4-E4B-it`.
5. Starte den vorhandenen Setup-Wizard aus dem Repository:
   `python3 scripts/setup_wizard.py`
   Übernimm die vorgeschlagenen Defaults. Gib einen Groq API-Key nur ein, wenn ich ihn bereitstelle. Erfinde keinen Key und schreibe keine Secrets in getrackte Dateien.
6. Für Gemma muss zuerst der Zugang zu `google/gemma-4-E4B-it` auf Hugging Face akzeptiert sein. Frage nach einem Read-Token, falls kein gespeicherter Hugging-Face-Login vorhanden ist. Übergib ihn über `HF_TOKEN`; speichere ihn nicht in Projektdateien.
7. Falls du nicht interaktiv arbeitest, verwende:
   `python3 scripts/setup_wizard.py --non-interactive --model qwen`
   Für Gemma verwende `--model gemma`. `GROQ_API_KEY` und `HF_TOKEN` dürfen nur als Umgebungsvariablen gesetzt werden.
8. Wenn der Wizard fehlschlägt, lies die vollständige Fehlermeldung. Behebe die Ursache am System oder in der lokalen Installation und starte den fehlgeschlagenen Schritt erneut. Umgehe keine Versions-, Build- oder Testprüfung.
9. Starte danach in getrennten, von dir verwalteten Prozessen:
   `venv/bin/python -m brain.steering_api_server`
   `venv/bin/python app.py`
   Warte beim ersten Modellstart geduldig auf Download, Laden und Anchor-Kalibrierung.
10. Prüfe:
    `curl --fail http://127.0.0.1:8000/health`
    `curl --fail http://127.0.0.1:8010/health`
    Der Steering-Service muss das ausgewählte Modell und `restart_status: ready` melden.
11. Führe aus:
    `venv/bin/python tests/test_setup_wizard.py`
    `venv/bin/python tests/test_root_config.py`
    `venv/bin/python tests/test_gemma4_integration.py`
    `venv/bin/python tests/test_runtime_architecture.py`
    `venv/bin/python tests/test_vector_only_emotion_path.py`
    `cd frontend && npm run build`
12. Beende nur die von dir gestarteten Testprozesse. Lass bestehende Nutzerprozesse, Ports, tmux-Sitzungen und Services unverändert.

Fehlerregeln:
- Kein NVIDIA-Treiber oder keine CUDA-GPU: Melde, dass CPU-Betrieb technisch möglich, für interaktive Nutzung aber sehr langsam ist. Behaupte keinen erfolgreichen GPU-Start.
- Zu wenig Speicher: Senke zuerst `local_models.steering_context_length`. Wechsle nicht ungefragt auf ein anderes Modell.
- Gemma meldet 401 oder 403: Prüfe Modellfreigabe und `HF_TOKEN`.
- Port 8000 oder 8010 ist belegt: Ermittle den Prozess. Stoppe ihn nur, wenn du ihn in diesem Auftrag selbst gestartet hast. Sonst frage mich.
- Ein vorhandenes `CHAPPIE_CONFIG.json` wird vom Wizard gesichert und zusammengeführt. Lösche es nicht.
- Ein leerer Groq-Key ist gültig. Lokale Antwortgenerierung und Steering dürfen davon nicht abhängen.

Abschlussbericht:
Nenne das installierte Modell, Python- und Node-Version, die beiden Health-Ergebnisse, bestandene Tests und jeden verbleibenden Systemgrenzwert. Zeige niemals Tokens oder API-Keys. Erstelle keinen Commit und pushe nichts.
```

## Nicht interaktive Kurzform

Ein Agent kann Qwen mit den Standardwerten so installieren:

```bash
git clone https://github.com/017pixel/CHAPPiE.git
cd CHAPPiE
python3 scripts/setup_wizard.py --non-interactive --model qwen
```

Der Befehl lädt mehrere Gigabyte Modell- und Python-Daten. Gemma braucht vorab einen freigeschalteten Hugging-Face-Zugang.
