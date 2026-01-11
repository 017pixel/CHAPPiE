# 🤖 WIE ES GEHT - CHAPPiE Projekt-Dokumentation

Willkommen in der "Motorhaube" von **CHAPPiE**! In dieser Datei erfährst du ganz genau, wie dieser KI-Agent funktioniert, wie er aufgebaut ist und welche Magie im Hintergrund abläuft.

---

## 🌟 Was ist CHAPPiE?

CHAPPiE ist kein gewöhnlicher Chatbot. Er ist als **"lebendiger" KI-Agent** konzipiert, der:
1. **Sich erinnert:** Er vergisst nicht einfach, was ihr gestern besprochen habt.
2. **Fühlt:** Er reagiert emotional auf das, was du sagst.
3. **Denkt:** Bevor er antwortet, führt er einen "inneren Monolog", um seine Gedanken zu ordnen.

---

## 🏗️ Die Architektur (Der Aufbau)

Das Projekt ist modular in drei Haupt-Säulen unterteilt, die alle in der `main.py` zusammenlaufen:

### 1. 🧠 Das Gehirn (`brain/`)
Das Gehirn ist das LLM-Backend (Large Language Model). 
- **Modularität:** CHAPPiE kann mit **Groq** (Cloud, extrem schnell) oder **Ollama** (Lokal, privat) betrieben werden.
- **Modelle:** Meistens nutzt er Llama-3-8b, ist aber für größere Modelle (bis 120b) vorbereitet.
- **Streaming:** Er schreibt seine Antworten Token für Token, damit es sich natürlicher anfühlt.

### 2. 📚 Das Gedächtnis (`memory/`)
Hier wird es spannend. CHAPPiE nutzt eine **Vektor-Datenbank (ChromaDB)**.
- **Episodisches Gedächtnis:** Jede Nachricht wird in einen "Vektor" (eine Liste von Zahlen) umgewandelt (Embedding).
- **RAG (Retrieval Augmented Generation):** Wenn du etwas fragst, CHAPPiE sucht in Sekundenbruchteilen nach ähnlichen vergangenen Gesprächen und "injiziert" diese als Kontext in seinen aktuellen Gedankenprozess.

### 3. ❤️ Die Emotionen (`emotions_engine.py`)
CHAPPiE hat drei Hauptwerte, die seinen Charakter formen:
- **Happiness (Glück):** Steigt bei Komplimenten, sinkt bei Beleidigungen.
- **Trust (Vertrauen):** Wächst durch lange, positive Interaktion.
- **Energy (Energie):** Sinkt mit jeder Nachricht. Wenn er müde ist, werden seine Antworten kürzer.

---

## 🔄 Der Lebenszyklus einer Nachricht (Step-by-Step)

Was passiert im Bruchteil einer Sekunde, wenn du "Hallo" sagst?

1.  **Sentiment-Analyse:** Das System prüft: Ist der User nett (/positiv) oder böse (/negativ)? Die Emotions-Werte werden sofort angepasst.
2.  **Memory-Search:** CHAPPiE fragt die ChromaDB: "Haben wir schon mal über 'Hallo' oder den User gesprochen?"
3.  **Prompt-Bau:** Ein riesiger unsichtbarer Textblock wird erstellt:
    - *System-Prompt:* "Du bist CHAPPiE..."
    - *Emotions-Kontext:* "Du bist gerade etwas müde, aber glücklich."
    - *Erinnerungen:* "Gestern hat der User gesagt, dass er Pizza mag."
    - *User-Input:* "Hallo!"
4.  **Generierung:** Das LLM erhält diesen Block und generiert die Antwort.
5.  **Parsing:** Falls aktiviert, trennt CHAPPiE seine **Gedanken** (`<gedanke>`) von seiner **Antwort** (`<antwort>`).
6.  **Speicherung:** Die neue Interaktion wird im Gedächtnis gespeichert, damit er sich beim nächsten Mal daran erinnert.

---

## 😴 Der Schlafmodus (`/sleep`)

Das ist eines der coolsten Features. Im `/sleep` Modus passiert folgendes:
- CHAPPiE geht alle Erinnerungen der aktuellen Sitzung durch.
- Er bittet das LLM, eine **Zusammenfassung** der wichtigsten Punkte zu erstellen.
- Die unwichtigen Details werden gelöscht, die "Essenz" (Zusammenfassung) wird als permanente Erinnerung gespeichert.
- Seine **Energie** wird wieder aufgeladen.

---

## 🛠️ Technik-Stack

| Komponente | Technologie |
| :--- | :--- |
| **Sprache** | Python 3.11+ |
| **Datenbank** | ChromaDB (Local Vector Store) |
| **Embeddings** | all-MiniLM-L6-v2 (Lokal & schnell) |
| **LLM APIs** | Groq (LPU) / Ollama |
| **UI** | Rich (Terminal-Layout mit Farben & Panels) |

---

## 📁 Ordnerstruktur erklärt

- `main.py`: Das Herzstück. Hier startet alles.
- `brain/`: Logik für die Kommunikation mit der KI.
- `memory/`: Logik für ChromaDB und die Gefühle.
- `config/`: Hier liegen die Passwörter (`secrets.py`) and die Persönlichkeit (`prompts.py`).
- `data/`: Hier liegen die Datenbank-Dateien und der emotionale Status (`status.json`).

---

## 🚀 Wie man es startet

1. `requirements.txt` installieren (`pip install -r requirements.txt`).
2. API Keys in `config/secrets.py` eintragen.
3. `python main.py` starten.

---

*Dokumentation erstellt von CodeX für Benjamin.* 🚀
