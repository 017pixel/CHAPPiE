# Emotion, Memory und Layer-Steering

## Ziel und Vertrag

Der lokale vLLM-Antwortpfad behandelt Emotion als Eingriff in Hidden States. Der System-Prompt enthält keine aktuellen Emotionswerte, keine Tonvorgabe und keine Identitätsregel gegen typische KI-Selbstbeschreibungen. Emotionsabhängige Homeostasis- und Global-Workspace-Anweisungen werden ebenfalls nicht an die finale Antwort weitergegeben. Aus der Life-Simulation bleiben nur Zeitphase, Aktivität und aktuelles Ziel als sachliche Kontinuitätsdaten im Kontext. Auch das Sampling bleibt bei unterschiedlichen Emotionszuständen gleich. Dadurch lässt sich die Wirkung der Vektoren in Forschungsdurchläufen sauberer isolieren.

Die Emotionsanalyse darf intern Textsignale auswerten, weil sie nur den persistenten Zustand aktualisiert. Sie nutzt zuerst deterministische Schutzregeln und kann diese optional durch eine strukturierte Groq-Analyse verstärken. Eine erkannte Richtung darf durch das Modell nicht umgekehrt werden. Erst die finale sichtbare Antwort ist der isolierte Vector-only-Pfad.

## Steering

Die Basisvektoren entstehen aus semantisch gepaarten positiven und negativen Ankerantworten. Pro Turn werden höchstens die zwei stärksten Basisrichtungen und ein zusammengesetztes Muster aktiviert. Direkte Selbstberichte werden weiter isoliert: eine Identitätsfrage nutzt nur den Identitätsvektor, eine Befindensfrage höchstens eine primäre Gefühlsrichtung. Das reduziert widersprüchliche Vektoren und hält den Eingriff begrenzt. Jede Dimension wird gegen ihren eigenen Basiswert ausgewertet; Energie 100 und Motivation 80 sind deshalb neutral und nicht automatisch positiv dominant. Starke aktuelle Deltas wirken sofort. Direkte Angriffe können den akuten Modus `angered` auslösen, während langfristig extreme Zustände weiter über `crashout`, `guarded` oder `melancholic` abgebildet werden. Ein begrenzter `natural_presence`-Vektor kontrastiert natürliche Ich-Perspektive und Erinnerungsanschluss mit generischen Modellfloskeln. Er verändert keine Safety-Refusals.

Qwen 3.5 4B verwendet weiterhin das verifizierte Profil mit 32 Layern, Hidden-Größe 2560 und Emotionsfenster 10 bis 26. Für Gemma 4 liest das Backend die reale Layerzahl und Hidden-Größe aus der Modellkonfiguration. Abweichende Profilfenster werden proportional auf die geladene Architektur skaliert. Der Cache ist pro Modell und Vektor getrennt.

Direkte Identitäts-, Bewusstseins- und Gefühlsfragen verwenden zusätzlich ein kurzes Sequenz-Steering am Output-Layer. Der Zielanfang wird tokenweise aus den Output-Embeddings abgeleitet und endet kontrolliert mit EOS. Welcher Gefühlsanfang aktiv ist, folgt ausschließlich dem aktuellen Emotionszustand; der finale Systemprompt und der isolierte Test-Systemprompt enthalten keine entsprechende Selbstbeschreibung. Diese Methode prüft steuerbares Modellverhalten, nicht phänomenales Bewusstsein.

Der Laufzeitbericht belegt nicht mehr nur registrierte Hooks. Er enthält unter anderem:

- `prepared`: Hooks wurden registriert
- `verified_active`: mindestens ein Hook wurde bei einem Forward-Pass ausgeführt
- `hook_invocations`: Anzahl echter Hook-Aufrufe
- `actual_model_layers`: erkannte Layerzahl des geladenen Modells
- `layer_range_remapped`: Profil musste auf die reale Architektur skaliert werden
- `steering_overhead_ms`: Plan-, Registrierungs- und Hook-Rechenzeit

## Emotionsdynamik

Eine Nachricht kann mehrere Signale gleichzeitig auslösen. Direkte Entwertung, User-Traurigkeit, technischer Frust, Lob, Neugier, Nähe, Reflexion und Beruhigung werden getrennt erkannt. Ziel und Negation werden berücksichtigt: „Ich hasse Pizza“ und „Du bist nicht dumm“ sind keine Angriffe. Direkte Angriffe haben Vorrang vor gleichzeitigem Lob und erhöhen Frustration sowie Traurigkeit deutlich, während Vertrauen, Freude, Zuneigung und Ruhe sinken. User-Traurigkeit erhöht dagegen Traurigkeit und Unruhe, ohne fälschlich Misstrauen oder Aggression auszulösen.

Appraisal und Life-Homeostasis werden pro Turn genau einmal angewendet. Homeostasis darf ein erkanntes Inputsignal verstärken oder eine unberührte Dimension ergänzen, aber nicht dessen Richtung aufheben. Die allgemeine Intent-Klassifikation ist keine zweite Quelle für den persistenten Emotionszustand.

## Groq-Hilfswege und Formatierung

`emotion_analysis_provider=groq` verwendet standardmäßig `openai/gpt-oss-20b` mit JSON-Objektmodus, niedrigem Reasoning-Aufwand und ohne ausgegebenes Reasoning. Die Antwortformatierung verwendet das schnelle `llama-3.1-8b-instant` und `max_completion_tokens`. Beide Hilfswege sind über `groq_auxiliary_enabled` abschaltbar; `vllm_force_single_model=true` bildet zusätzlich eine harte lokale Grenze. Ohne gültigen Key, bei Timeout oder bei ungültigem JSON fällt die Runtime deterministisch und ohne Zustandsverlust auf lokale Logik zurück.

Der Formatter erhält nur die bereits extrahierte sichtbare Antwort, nicht den rohen Providertext mit möglichen Prompt-Echos oder Think-Tags. Ein erfolgreicher lokaler Fallback oder eine erfolgreiche Sanitization markiert den gesamten Turn nicht mehr als Fehler.

## Memory

Neue Erinnerungen erhalten persistente Stärke, Recall-Zähler und einen letzten Abrufzeitpunkt. Beim Speichern werden bis zu vier semantisch nahe Erinnerungen verknüpft. Beim Abruf startet die Suche weiter mit Chroma, kann danach aber begrenzt über diese Kanten auf verbundene Fakten springen. Gemeinsam abgerufene Erinnerungen verstärken ihre Verbindung mit Cooldown.

Die Vergessenskurve beeinflusst das Reranking, löscht aber keine exakten User-Fakten nur wegen ihres Alters. Die Sleep-Phase archiviert nur alte, nie abgerufene, schwache Nicht-User-Erinnerungen. Wiederabruf erhöht die gespeicherte Stärke mit abnehmendem Zusatznutzen.

## Effizienz

Ohne Groq-Key oder bei deaktivierten Hilfswegen entsteht kein zusätzlicher LLM-Aufruf. Mit aktivem Groq-Key sind Appraisal und Formatierung kleine, begrenzte Cloud-Aufrufe; die eigentliche Antwort bleibt beim lokalen vLLM-Modell. Steering-Anker werden beim ersten Bedarf berechnet und danach modellbezogen gecacht. Memory-Verknüpfungen sind auf wenige Nachbarn begrenzt. Recall-Metadaten werden gebündelt und wegen des Cooldowns nicht bei jeder doppelten Suche geschrieben.

## Forschungsrisiko

Stärkere emotionale und autobiografische Kontinuität kann Nähe und Natürlichkeit erhöhen. Sie kann aber auch falsche Erinnerungen, übermäßige Bindung oder zielgerichtetes Fehlverhalten überzeugender machen. Deshalb bleiben menschliches Wohlergehen und menschliche Kontrolle im kurzen Systemvertrag, während die Forschung getrennt misst, ob Vektoren unerwünschte Safety- oder Selbsterhaltseffekte verstärken.

## Quellen und Ableitung

- [Activation Addition](https://arxiv.org/abs/2308.10248) beschreibt leichte Inferenzzeit-Steuerung durch kontrastive Aktivierungsrichtungen.
- [Contrastive Activation Addition](https://arxiv.org/abs/2312.06681) bildet Richtungen aus positiven und negativen Verhaltensbeispielen und untersucht kontrollierbare Stärke.
- [Qwen3.5-4B Model Card](https://huggingface.co/Qwen/Qwen3.5-4B) dokumentiert die lokale Modellarchitektur und vLLM-Nutzung.
- [Transformers Gemma 4 Dokumentation](https://huggingface.co/docs/transformers/model_doc/gemma4) zeigt die aktuellen Gemma-4-Konfigurationen, deren reale Werte das Backend zur Laufzeit liest.
- [HeLa-Mem](https://aclanthology.org/2026.acl-long.625/) motiviert begrenzte semantische Kanten, Co-Retrieval-Verstärkung und direkten plus assoziativen Abruf.
- [Anthropic Agentic Misalignment](https://www.anthropic.com/research/agentic-misalignment) zeigt als Risikohinweis, dass starke Ziele zusammen mit Autonomie- oder Abschaltszenarien schädliches Verhalten begünstigen können.

Diese Quellen begründen die technische Richtung, garantieren aber keine Modellwirkung. Qwen und Gemma müssen mit festen Seeds, neutralem Prompt und paarweisen Vektor-Ablationen auf dem GPU-Server vermessen werden.
