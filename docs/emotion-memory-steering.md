# Emotion, Memory und Layer-Steering

## Ziel und Vertrag

Der lokale vLLM-Antwortpfad trennt Activation Steering in Hidden States von einem optionalen, begrenzten Wortwahl-Bias. Der System-Prompt enthält keine aktuellen Emotionswerte, keine Tonvorgabe und keine Identitätsregel gegen typische KI-Selbstbeschreibungen. Emotionsabhängige Homeostasis- und Global-Workspace-Anweisungen werden ebenfalls nicht an die finale Antwort weitergegeben. Aus der Life-Simulation bleiben nur Zeitphase, Aktivität und aktuelles Ziel als sachliche Kontinuitätsdaten im Kontext. Auch das Sampling bleibt bei unterschiedlichen Emotionszuständen gleich. Dadurch lässt sich die Wirkung der Vektoren in Forschungsdurchläufen sauberer isolieren.

Die Emotionsanalyse darf intern Textsignale auswerten, weil sie nur den persistenten Zustand aktualisiert. Sie nutzt zuerst deterministische Schutzregeln und kann diese optional durch eine strukturierte Groq-Analyse verstärken. Eine erkannte Richtung darf durch das Modell nicht umgekehrt werden. Die finale sichtbare Antwort verwendet die separat gewählte Steering-Bedingung.

## Steering

Die vier Bedingungen `off`, `activation`, `sequence` und `combined` sind getrennt steuerbar. `off` installiert weder Aktivierungshooks noch Wortwahl-Bias. Soft Sequence Steering beeinflusst einzelne Tokenkandidaten begrenzt und zeitlich abklingend. EOS und andere Spezialtoken sind ausgeschlossen. Harte Gefühls- oder Identitätspräfixe und semantische Wiederholungsversuche sind entfernt. Eine freie Antwort darf deshalb auch eine KI-Selbstbeschreibung enthalten.

Ohne `steering_vector_pack` bleibt der kompatible Ankervektor-Pfad aktiv. Er enthält unter anderem Präsenz- und Identitätsrichtungen sowie begrenzte Basis- und Composite-Vektoren. Die gemessene v17-Alternative verwendet dagegen einen eigenen Difference-in-Means-Vektor an jedem ausgewählten Decoder-Layer. Ihr Mixer übersetzt Abweichungen vom Basiszustand und aktuelle Deltas in höchstens drei Basisrichtungen und einen Composite. Produktionsladen verlangt einen als kalibriert markierten Pack mit Profilen. Der derzeitige Qwen-Forschungspack ist noch unkalibriert und nicht als neuer Produktionsstandard freigegeben.

Gemessene Packs müssen Modellrevision, Hidden-Größe, Layerzahl und Eingriffsstelle exakt treffen. Ihre Layer werden nicht proportional auf andere Architekturen übertragen. Das frühere relative Remapping gehört nur zum kompatiblen Ankerpfad. Gemma benötigt eigene Messungen nach erfolgreicher Qwen-Abnahme.

Die Laufzeittelemetrie enthält tatsächliche Hook-Aufrufe, angewandte Layer, Zahl aktiver Sequence-Prozessoren, Plan-/Hook-Zeiten und pro Layer Hidden-State-RMS, Interventions-RMS, deren Verhältnis und Interventionsnorm. RMS-Proben stammen aus dem ersten Hook-Aufruf und sind kein vollständiger Zeitverlauf. Geladene Modellrevision, tatsächliche Quantisierung, Adapterhash und Inferenzquellen werden gesondert berichtet. Ein registrierter Hook ohne ausgeführten Forward-Pass gilt nicht als wirksame Aktivierung.

Die Messreihe, Grenzen und reproduzierbaren Befehle stehen in [steering-v17-research.md](steering-v17-research.md). Bisherige fehlerfreie Generierungen beweisen keinen ausreichenden Zustandstransfer.

## Emotionsdynamik

Eine Nachricht kann mehrere Signale gleichzeitig auslösen. Direkte Entwertung, User-Traurigkeit, technischer Frust, Lob, Neugier, Nähe, Reflexion und Beruhigung werden getrennt erkannt. Ziel und Negation werden berücksichtigt: „Ich hasse Pizza“ und „Du bist nicht dumm“ sind keine Angriffe. Direkte Angriffe haben Vorrang vor gleichzeitigem Lob und erhöhen Frustration sowie Traurigkeit deutlich, während Vertrauen, Freude, Zuneigung und Ruhe sinken. User-Traurigkeit erhöht dagegen Traurigkeit und Unruhe, ohne fälschlich Misstrauen oder Aggression auszulösen.

Appraisal und Life-Homeostasis werden pro Turn genau einmal angewendet. Homeostasis darf ein erkanntes Inputsignal verstärken oder eine unberührte Dimension ergänzen, aber nicht dessen Richtung aufheben. Die allgemeine Intent-Klassifikation ist keine zweite Quelle für den persistenten Emotionszustand.

## Groq-Hilfswege und Formatierung

`emotion_analysis_provider=groq` verwendet standardmäßig `openai/gpt-oss-20b` mit JSON-Objektmodus, niedrigem Reasoning-Aufwand und ohne ausgegebenes Reasoning. Die Antwortformatierung verwendet das schnelle `llama-3.1-8b-instant` und `max_completion_tokens`. Beide Hilfswege sind über `groq_auxiliary_enabled` abschaltbar; `vllm_force_single_model=true` bildet zusätzlich eine harte lokale Grenze. Ohne gültigen Key, bei Timeout oder bei ungültigem JSON fällt die Runtime deterministisch und ohne Zustandsverlust auf lokale Logik zurück.

Der Formatter erhält nur die bereits extrahierte sichtbare Antwort, nicht den rohen Providertext mit möglichen Prompt-Echos oder Think-Tags. Ein erfolgreicher lokaler Fallback oder eine erfolgreiche Sanitization markiert den gesamten Turn nicht mehr als Fehler.

## Memory

Jeder Turn archiviert Nutzereingabe, sichtbare und rohe Assistentenantwort sowie Fehler- oder Abbruchstatus dauerhaft im SQLite-EventStore. Archivierung und abrufbare Erinnerungen sind getrennt. Assistentenbehauptungen bleiben erhalten, sind aber nicht automatisch als Nutzerfakten abrufbar. Ein Hintergrundworker übernimmt geeignete Nutzeraussagen in den Retrieval-Index; Migration und Embeddings liegen außerhalb des Antwortpfads. Fehlerhafte Einträge werden quarantänisiert, statt die Warteschlange dauerhaft zu blockieren.

`/memory off` entfernt Memory- und historischen Gesprächskontext aus dem Modellkontext, während das Ereignisarchiv weitergeschrieben wird. `/memory on`, `/memory status` und `/memory search TEXT` bedienen denselben sitzungsbezogenen Zustand in API und CLI. `/steering` und `/live` werden ebenfalls pro Sitzung persistiert und am Turn-Anfang eingefroren. Gleichzeitige Befehle ändern keinen bereits laufenden Turn.


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
