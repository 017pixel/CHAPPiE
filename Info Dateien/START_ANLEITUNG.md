# 🚀 CHAPiE Start-Anleitung

Folge diesen Schritten, um CHAPiE über das Terminal (Windows PowerShell oder CMD) zu starten.

## 1. Terminal öffnen
Drücke `Win + R`, gib `powershell` ein und drücke Enter. Oder suche "PowerShell" im Startmenü.

## 2. In den Projekt-Ordner wechseln
Kopiere diesen Befehl und füge ihn ein:
```powershell
cd "c:\Users\Benja\OneDrive\Desktop\CHAPiE"
```

## 3. Virtual Environment aktivieren
Damit die installierten Pakete genutzt werden können:
```powershell
.\venv\Scripts\activate
```
*(Du erkennst, dass es geklappt hat, wenn vor deiner Zeile nun `(venv)` steht.)*

## 4. CHAPiE starten
```powershell
python main.py
```

.\venv\Scripts\activate

---

streamlit run app.py

## 💡 Ein-Zeilen-Befehl (Schnellstart)
Wenn du dich bereits im Ordner befindest, kannst du auch einfach das hier eingeben:
```powershell
.\venv\Scripts\activate; python main.py
```

## ⚠️ Wichtige Voraussetzungen
1. **Ollama:** Stelle sicher, dass die Ollama-App im Hintergrund läuft (unten rechts in der Taskleiste).
2. **API-Key:** Falls du Groq nutzt, muss der Key in `config/secrets.py` eingetragen sein.
3. **Modelle:** Für die lokale Nutzung muss das Modell geladen sein (`ollama pull llama3:8b`).

---

Viel Spaß beim Chatten! 🤖

gedächtniss löschen:
python -c "from memory.memory_engine import MemoryEngine; engine = MemoryEngine(); engine.reset_all_memories()"