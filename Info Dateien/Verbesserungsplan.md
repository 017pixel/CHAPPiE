# CHAPiE Verbesserungsplan - Detaillierte Problemanalyse

**Datum:** 31. Januar 2026  
**Zweck:** Analyse zur Übergabe an eine KI zur Implementierung der Lösungen

---

## Inhaltsverzeichnis

1. [Problem 1: Kurzzeitgedächtnis (daily_info.md)](#problem-1-kurzzeitgedächtnis)
2. [Problem 2: API-System mit hardcodierten Keys](#problem-2-api-system)
3. [Kritische Fehler im Projekt](#kritische-fehler)

---

## Problem 1: Kurzzeitgedächtnis (daily_info.md)

### 1.1 Übersicht

Das Kurzzeitgedächtnis-System speichert temporäre Informationen in der Datei `data/daily_info.md` und parallel in ChromaDB. Es gibt mehrere kritische Probleme, die das System ineffektiv machen.

### 1.2 Problem: Platzhalter-Erkennung funktioniert nur einmal

**Datei:** [`memory/short_term_memory.py`](memory/short_term_memory.py:119-151)

**Funktion:** `_append_to_file()`

**Beschreibung:**
Die Methode prüft auf den Platzhalter-Text:
```python
if "_(Keine Einträge" in content:
    content = content.replace(
        "_(Keine Einträge - CHAPI wird hier wichtige Informationen während des Tages sammeln)_",
        entry + "\n_(Keine Einträge)_"
    )
else:
    # Füge nach der "Aktuell Relevant" Überschrift ein
    content = content.replace(
        "### Aktuell Relevant\n",
        f"### Aktuell Relevant\n{entry}\n"
    )
```

**Problem:** Nach dem ersten Eintrag wird der Platzhalter-Text "`_(Keine Einträge)_`" durch "`_(Keine Einträge)_`" ersetzt (derselbe Text), aber die Bedingung `"_(Keine Einträge" in content` ist weiterhin TRUE, weil der neue Platzhalter immer noch "Keine Einträge" enthält. Dies führt dazu, dass jeder neue Eintrag den alten Platzhalter-Text überschreibt anstatt angehängt zu werden.

**Erwartetes Verhalten:** Einträge sollten als Liste unter "### Aktuell Relevant" angehängt werden.

**Tatsächliches Verhalten:** Bei jedem neuen Eintrag wird der vorherige Platzhalter-Text ersetzt, aber der eigentliche Inhalt wird nicht korrekt eingefügt, wenn bereits Einträge vorhanden sind.

### 1.3 Problem: Regex-Pattern für Eintrag-Erkennung

**Datei:** [`memory/short_term_memory.py`](memory/short_term_memory.py:174-186)

**Funktion:** `get_relevant_infos()`

**Beschreibung:**
```python
pattern = r'\[([^\]]+)\] \[([^\]]+)\] \[([^\]]+)\] (.+)'
for match in re.finditer(pattern, content):
```

**Problem:** Das Pattern `(.+)` am Ende ist "greedy" (gierig) und matcht so viel wie möglich. Wenn die Datei mehrere Einträge enthält, kann das Pattern über Zeilenumbrüche hinweg matchen und alle nachfolgenden Inhalte einschließen. Dies führt zu falsch geparsten oder fehlenden Einträgen.

**Zusatzproblem:** Das Pattern funktioniert nur, wenn jeder Eintrag auf einer einzigen Zeile ist. Mehrzeilige Einträge werden nicht korrekt erkannt.

### 1.4 Problem: Doppelte Speicherung ohne Synchronisation

**Datei:** [`memory/short_term_memory.py`](memory/short_term_memory.py:101-115)

**Funktion:** `add_info()`

**Beschreibung:**
```python
# 1. Append zur Markdown-Datei
self._append_to_file(entry)

# 2. AUCH in ChromaDB indexieren (für RAG-Suche)
if self.memory_engine:
    try:
        self.memory_engine.add_memory(...)
```

**Problem:** Die Informationen werden sowohl in der Markdown-Datei als auch in ChromaDB gespeichert, aber es gibt keine Synchronisation zwischen beiden. Wenn:
- Ein Eintrag in der Markdown-Datei fehlschlägt, wird er trotzdem in ChromaDB gespeichert
- Ein Eintrag in ChromaDB fehlschlägt, wird er trotzdem in die Markdown-Datei geschrieben
- Es gibt keine Möglichkeit, die beiden Quellen zu vergleichen oder zu synchronisieren

**Konsquenz:** Inkonsistente Daten zwischen den beiden Speichern.

### 1.5 Problem: Automatische Bereinigung wird nie aufgerufen

**Datei:** [`memory/short_term_memory.py`](memory/short_term_memory.py:203-261)

**Funktion:** `cleanup_expired()`

**Beschreibung:** Die Methode `cleanup_expired()` existiert und entfernt Einträge, die älter als 24 Stunden sind, aber:
- Sie wird nirgendwo im Code automatisch aufgerufen
- Es gibt keinen Cron-Job oder Timer, der diese Funktion regelmäßig ausführt
- Ein manueller Aufruf über die UI oder CLI ist nicht möglich

**Konsquenz:** Die Daily-Info-Datei wächst unbegrenzt an, da abgelaufene Einträge nie entfernt werden.

### 1.6 Problem: Daily-Info wird bei jedem Start nicht aktualisiert

**Datei:** [`memory/short_term_memory.py`](memory/short_term_memory.py:37-82)

**Funktion:** `_ensure_file_exists()` und `_create_default_file()`

**Beschreibung:**
```python
def _ensure_file_exists(self):
    """Erstellt die Datei wenn sie nicht existiert."""
    if not self.daily_info_path.exists():
        self._create_default_file()
```

**Problem:** Die Methode prüft nur, ob die Datei existiert. Wenn sie existiert, wird sie NICHT aktualisiert. Allerdings:
- Der Default-Inhalt enthält Platzhalter wie `{timestamp}`, `{session_start}`, `{user_context}` die NIE ersetzt werden
- Es gibt keine Logik, die den "Aktuelle Session"-Block bei einem neuen Start aktualisiert

### 1.7 Problem: `_create_default_file()` setzt User auf "Unbekannt"

**Datei:** [`memory/short_term_memory.py`](memory/short_term_memory.py:42-82)

**Funktion:** `_create_default_file()`

**Beschreibung:**
```python
content = f"""# CHAPiE Daily Information
> Automatisch generiert - Letzte Aktualisierung: {timestamp}

## Aktuelle Session
- **Start:** {timestamp}
- **User:** Unbekannt
```

**Problem:** Der User wird immer auf "Unbekannt" gesetzt, obwohl das System möglicherweise bereits weiß, wer der User ist. Es gibt keine Logik, um:
- Den User aus dem Langzeitgedächtnis zu laden
- Den Session-Start korrekt zu tracken
- Die Session-Informationen zu aktualisieren

---

## Problem 2: API-System

### 2.1 Aktuelle Architektur

Das aktuelle System besteht aus mehreren Teilen:

1. **secrets_example.py** - Template mit Platzhaltern
2. **secrets.py** - Sollte kopiert werden mit echten Keys (wird von Git ignoriert)
3. **addSecrets.py** - Wird von der UI erstellt und enthält User-Overrides
4. **config/config.py** - Lädt Settings mit folgender Hierarchie: `UI > addSecrets.py > secrets.py`

### 2.2 Problem: API-Keys werden in addSecrets.py geschrieben

**Datei:** [`config/config.py`](config/config.py:160-214)

**Funktion:** `_persist_to_addsecrets()`

**Beschreibung:**
```python
def _persist_to_addsecrets(self):
    """Schreibt die aktuellen Settings in addSecrets.py für Persistenz."""
    try:
        addsecrets_path = PROJECT_ROOT / "config" / "addSecrets.py"
        with open(addsecrets_path, "w") as f:
            f.write("# Automatisch generierte Benutzer-Overrides\n")
            f.write("# Diese Datei wird von der UI aktualisiert - nicht manuell bearbeiten!\n\n")
            
            # API Keys
            if self.groq_api_key:
                f.write(f"GROQ_API_KEY = '{self.groq_api_key}'\n")
            if self.cerebras_api_key:
                f.write(f"CEREBRAS_API_KEY = '{self.cerebras_api_key}'\n")
```

**Problem:** Die API-Keys werden im Klartext in eine Python-Datei geschrieben:
- Dies ist ein Sicherheitsrisiko
- Die Datei könnte versehentlich in ein Git-Repository eingecheckt werden
- Die Datei ist im Dateisystem lesbar (nicht verschlüsselt)
- Auf einem gemeinsam genutzten Server könnten andere Benutzer die Keys lesen

### 2.3 Problem: Settings laden bei jedem Request die Datei neu

**Datei:** [`config/config.py`](config/config.py:51-63)

**Funktion:** `_get_val()`

**Beschreibung:**
```python
def _get_val(self, name, default=None):
    """Hilfsfunktion: Holt Wert aus addSecrets, dann secrets, dann default."""
    # 1. Check addSecrets
    if addSecrets and hasattr(addSecrets, name):
        val = getattr(addSecrets, name)
        if val: return val # Nur wenn nicht leer
```

**Problem:** Die Hierarchie `UI > addSecrets > secrets` wird bei jedem Zugriff auf `settings` neu geladen. Das bedeutet:
- Wenn ein API-Key in der UI eingegeben wird, wird er in `addSecrets.py` geschrieben
- Bei jedem weiteren Request wird die Datei neu geladen
- Dies ist langsam und ineffizient

### 2.4 Problem: Kein LocalStorage für Web-UI

**Datei:** [`web_infrastructure/settings_ui.py`](web_infrastructure/settings_ui.py:1-334)

**Problem:** Die Web-UI (Streamlit) speichert API-Keys nicht im LocalStorage des Browsers. Stattdessen:
- Werden sie direkt in `addSecrets.py` geschrieben
- Gehen sie bei einem Server-Neustart nicht verloren (aber sind im Dateisystem)
- Gibt es keine Möglichkeit, Keys nur für die aktuelle Session zu setzen

**Gewünschtes Verhalten:** 
- Keys sollten im LocalStorage des Browsers gespeichert werden
- Bei jedem Page-Refresh sollten die Keys aus dem LocalStorage geladen werden
- Optional: Keys können in `addSecrets.py` persistiert werden (nur auf expliziten Wunsch)

### 2.5 Problem: Kein separater APIs-Ordner

**Aktuelle Struktur:**
```
config/
├── __init__.py
├── config.py
├── prompts.py
├── secrets_example.py
└── secrets.py (manuell erstellt, wird ignoriert)
```

**Gewünschte Struktur:**
```
config/
├── __init__.py
├── config.py
├── prompts.py
├── secrets_example.py
├── secrets.py (wird ignoriert)
└── APIs/
    ├── groq_api.py (leere Variable GROQ_API_KEY = "")
    └── cerebras_api.py (leere Variable CEREBRAS_API_KEY = "")
```

**Problem:** Aktuell sind die API-Keys direkt in `secrets.py` definiert. Es gibt keinen dedizierten Ordner für API-Konfigurationen.

### 2.6 Problem: Web-UI zeigt unsichere Speicherung an

**Datei:** [`web_infrastructure/settings_ui.py`](web_infrastructure/settings_ui.py:52-53)

**Beschreibung:**
```python
new_api_key = st.text_input(
    "Groq API Key", 
    value=settings.groq_api_key if settings.groq_api_key else "",
    type="password",
    help="Der Key wird nur für die aktuelle Sitzung temporär gespeichert, wenn addSecrets.py leer ist."
)
```

**Problem:** Der Hilfetext ist verwirrend und teilweise falsch:
- "temporär" ist nicht korrekt - der Key wird in `addSecrets.py` geschrieben (persistent)
- Es gibt keine klare Aussage darüber, wo der Key gespeichert wird
- Es gibt keine Option, den Key nur für die aktuelle Session zu speichern

---

## Kritische Fehler im Projekt

### Kritischer Fehler 1: TypeError bei Memory-Rendering

**Datei:** [`web_infrastructure/components.py`](web_infrastructure/components.py:138)

**Fehlertext:**
```
TypeError: object of type 'NoneType' has no len()
Traceback:
File ".../streamlit/runtime/scriptrunner/script_runner.py", line 672, in code_to_exec
    exec(code, module.__dict__)
File ".../app.py", line 51, in main
    main()
File ".../app.py", line 39, in main
    user_input = render_chat_interface(backend)
File ".../chat_ui.py", line 50, in render_chat_interface
    render_memory_item(m, idx + 1)
File ".../components.py", line 138, in render_memory_item
    st.caption(content[:250] + "..." if len(content) > 250 else content)
```

**Problem:** Die Funktion `render_memory_item()` nimmt an, dass `content` immer ein String ist. Wenn `content` `None` ist, schlägt `len(content)` fehl.

**Code:**
```python
def render_memory_item(mem: Any, index: int = 1):
    # ...
    if isinstance(mem, dict):
        content = mem.get("content", "")  # <-- "" als Default, aber...
    # ...
    if content and isinstance(content, str):
        st.caption(content[:250] + "..." if len(content) > 250 else content)
```

**Problem:** Der Code prüft `if content and isinstance(content, str)`, was True sein sollte wenn `content` ein leerer String ist. Aber wenn `mem.get("content", "")` einen leeren String zurückgibt, sollte es funktionieren. Der Fehler tritt auf, wenn `content` tatsächlich `None` ist (nicht der Default-Wert).

**Ursache:** Der `mem` Parameter kann aus ChromaDB geladene Daten enthalten, die möglicherweise `None` als Content haben. Das passiert, wenn:
- Ein Memory-Eintrag in ChromaDB ohne Content gespeichert wurde
- Die Metadaten nicht korrekt serialisiert wurden
- Ein alter Eintrag mit fehlerhaften Daten existiert

### Kritischer Fehler 2: Training-Modus + Web-UI Konflikt

**Datei:** [`Info Dateien/bugs.txt`](Info/ Dateien/bugs.txt:1-23)

**Fehlertext:**
```
TypeError: object of type 'NoneType' has no len()
Traceback:
...
File ".../web_infrastructure/components.py", line 138, in render_memory_item
    st.caption(content[:250] + "..." if len(content) > 250 else content)
```

**Wann tritt der Fehler auf:**
1. CHAPiE läuft im Trainingsmodus (Training-Daemon)
2. User startet die Web-UI
3. User schreibt eine Nachricht -> funktioniert
4. User schreibt eine zweite Nachricht -> TypeError

**Problem:** Der Training-Daemon und die Web-UI teilen sich die gleiche ChromaDB-Datenbank. Wenn:
- Der Training-Daemon neue Memories hinzufügt
- Die Web-UI gleichzeitig versucht, Memories zu laden
- Es zu einem Race Condition oder Datenbank-Lock kommt
- Ein Memory mit ungültigen/fehlenden Daten geladen wird

**Ursache:** 
- Keine Lock-Mechanismen beim gleichzeitigen Zugriff auf ChromaDB
- Keine Fehlerbehandlung bei corruptten Memory-Einträgen
- Die `render_memory_item()` Funktion ist nicht robust genug

### Kritischer Fehler 3: Embedding-Dimension bei Fehlern

**Datei:** [`memory/memory_engine.py`](memory/memory_engine.py:118-124)

**Problem:** Bei Embedding-Fehlern wird ein Dummy-Embedding verwendet:
```python
# Fallback: Verwende einen Dummy-Embedding (alle Nullen)
embedding_dim = 384  # Standard-Dimension für all-MiniLM-L6-v2
embedding = [0.0] * embedding_dim
```

**Problem:** Die Dimension ist hardcodiert auf 384. Wenn das `EMBEDDING_MODEL` in den Settings geändert wird (z.B. auf ein anderes Modell mit anderer Dimension), werden trotzdem 384-Dimension-Vektoren gespeichert. Dies führt zu:
- Inkonsistenten Vektorlängen in der Datenbank
- Fehlern bei der Suche (ChromaDB erwartet konsistente Dimensionen)
- Stillen Datenverlusten

### Kritischer Fehler 4: ChromeDB Lock bei gleichzeitigem Zugriff

**Datei:** [`memory/memory_engine.py`](memory/memory_engine.py:146-155)

**Problem:** Es gibt zwar Retry-Logik, aber:
```python
# Bei Locking/Busy-Fehlern: Retry
if any(kw in error_msg for kw in ["lock", "busy", "timeout", "database is locked"]):
    if attempt < max_retries - 1:
        # ...
        continue
```

**Problem:** Der Retry-Mechanismus ist nicht ausreichend, wenn der Training-Daemon und die Web-UI gleichzeitig auf die gleiche ChromaDB-Instanz zugreifen:
- Die Wartezeit zwischen Retries ist zu kurz
- Es gibt keine maximale Wartezeit
- Bei zu vielen gleichzeitigen Zugriffen können Daten verloren gehen

---

## Zusammenfassung der Prioritäten

| Priorität | Problem | Beschreibung | Status |
|-----------|---------|--------------|--------|
| **P1** | TypeError bei Memory-Rendering | Führt zum Absturz der Web-UI | ✅ **BEHOBEN** |
| **P1** | Training-Modus + Web-UI Konflikt | Race Condition bei ChromaDB-Zugriff | ✅ **BEHOBEN** |
| **P1** | Hardcodierte Embedding-Dimension | Kann zu Inkompatibilität führen | ✅ **BEHOBEN** |
| **P2** | Kurzzeitgedächtnis Platzhalter | Einträge werden nicht korrekt gespeichert | ✅ **BEHOBEN** |
| **P2** | API-Keys in addSecrets.py | Sicherheitsrisiko | ✅ Hinweistext + Backup-Ausschluss |
| **P2** | Backup kopiert API-Keys | Sicherheitsrisiko | ✅ **BEHOBEN** (v2.0 Script) |
| **P2** | ChromaDB Backup-Korruption | Konflikte beim Restore | ✅ **BEHOBEN** (ZIP-Archiv) |
| **P3** | APIs-Ordner fehlt | Keine saubere Struktur | ✅ **ERSTELLT** |
| **P3** | Training-Daemon Import-Probleme | Case-Sensitivity auf Linux | ✅ **BEHOBEN** |
| **P3** | LocalStorage für API-Keys | Benutzerfreundlichkeit | ⏳ Erfordert JS-Integration |

---

## Implementierte Änderungen (31.01.2026)

### Kritische Fixes (P1)
- `components.py`: Robuste None-Checks für alle Memory-Felder
- `memory_engine.py`: Dynamische Embedding-Dimension (`self.embedding_dim`)
- `memory_engine.py`: Exponential Backoff für ChromaDB-Locking (5 Retries)

### Wichtige Fixes (P2)
- `short_term_memory.py`: Korrekte Platzhalter-Logik und nicht-greedy Regex
- `backend_wrapper.py`: Automatische Bereinigung abgelaufener Einträge
- `backup_project.py`: Komplett neu - API-Keys werden ausgeschlossen, ChromaDB als ZIP
- `settings_ui.py`: Korrigierter Hilfetext für API-Key-Speicherung

### Verbesserungen (P3)
- `config/APIs/`: Ordnerstruktur für separate API-Konfiguration
- `training_daemon.py`: Robustere Imports mit Fallback für Linux-Kompatibilität
- `.gitignore`: APIs-Ordner hinzugefügt

---

## Hinweis zur Bearbeitung

**Dieses Dokument enthält NUR Problembeschreibungen!**  
Die Lösungen sollen von einer KI implementiert werden basierend auf dieser Analyse.

Bitte bei der Implementierung beachten:
1. Sicherheit hat höchste Priorität (API-Keys nicht in Dateien speichern)
2. Robustheit gegen fehlerhafte Daten (Type-Checks, None-Checks)
3. Performance bei gleichzeitigem Zugriff (ChromaDB Locks)
4. Benutzerfreundlichkeit (LocalStorage, klare UI-Texte)

