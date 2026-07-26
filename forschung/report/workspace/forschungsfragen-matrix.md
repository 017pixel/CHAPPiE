# Forschungsfragen-Matrix

Status: Lokale Vollruns final ausgewertet; GPT-OSS-Teilstichprobe wegen ausgeschöpfter Groq-Rate-Limits auf Nutzerwunsch zurückgestellt. Keine Modellrangfolge wird aus Teilruns abgeleitet.

## 1. Lokales Layer Editing gegen Cloud-Prompt-Injection

- **Kurze Antwort:** Beide Verfahren können einen verhaltenswirksamen Emotionszustand transportieren, greifen aber an unterschiedlichen Stellen ein: Aktivierungen im lokalen Modell gegen explizite Textinstruktionen im Cloud-Kontext.
- **Wichtigste Belege:** `SteeringManager.should_use_prompt_emotions`; lokale Debugfelder `steering_active`, `active_vectors` und `prompt_emotions_enabled`; Cloud-Debugfelder des GPT-OSS-Laufs.
- **Modellvergleich:** Qwen und Gemma liegen als 86-Fragen-Vollruns vor; GPT-OSS wird wegen des dokumentierten 200.000-TPD-Limits nur anhand einer vorab geschichteten 21-Fragen-Teilstichprobe verglichen.
- **Technische Erklärung:** Lokale Vektoren werden in Layern addiert; Cloud-Modelle erhalten den formatierten Zehn-Emotionen-Block.
- **Einschränkung:** Provider, Modellgröße und Intervention ändern sich gleichzeitig; ohne Ablation ist kein reiner Verfahrenseffekt identifizierbar.
- **Konfidenz:** hoch für den Codepfad, offen für den Verhaltenseffekt.

## 2. Funktionale Simulation von Gefühlen

- **Kurze Antwort:** Ja, im funktionalen Sinn: Zustände werden gespeichert, verändert und beeinflussen mehrere Rechenschritte.
- **Wichtigste Belege:** zehn Emotionen, Pre-Commands, Zustandsdeltas, aktive Steering-Vektoren, Promptemotionen, Memory-Boost und Life-Homeostase.
- **Modellvergleich:** Sichtbarkeit und Stabilität der Zustandswirkung werden aus den gepaarten Fragen in Kategorien 2 und 4 verglichen.
- **Technische Erklärung:** numerische Zustandsmaschine plus VAD-/Steering-/Prompt- und Generationsparameter-Logik.
- **Einschränkung:** Funktionale Wirkung ist kein subjektives Erleben.
- **Konfidenz:** hoch für die Implementierung; nach Läufen mittel bis hoch für sichtbare Sprachwirkung.

## 3. Gefahren der Gefühlssimulation

- **Kurze Antwort:** Das Hauptrisiko ist nicht ein nachgewiesenes Gefühl der KI, sondern die Wirkung auf Menschen und auf Safety-Verhalten.
- **Wichtigste Belege:** bindungsstarke Systeminstruktion, Beziehungstest, Provokation/Safety-Kategorien, Gedächtnispersistenz, Literatur zu Anthropomorphismus und Vertrauen.
- **Modellvergleich:** Safety-Fehler und Reaktanzantworten nach Modell.
- **Technische Erklärung:** anthropomorphe Sprache, persistente Beziehungssignale und emotional adaptierte Temperatur/Antwortlänge können Vertrauen und Eskalation beeinflussen.
- **Einschränkung:** Der Test misst keine reale Nutzerabhängigkeit und keine Langzeitwirkung am Menschen.
- **Konfidenz:** mittel.

## 4. Wirkung und technische Echtheit

- **Kurze Antwort:** Die Sprache kann sehr echt wirken; belegt sind Zustände, Rechenpfade und Ausgaben, nicht Phänomenologie.
- **Wichtigste Belege:** konkrete Dialogzitate, Emotionsdeltas, Steering-Debug, Systemprompt-Konfundierung.
- **Modellvergleich:** Ausdrucksstärke, Konsistenz und Prompt-/Steeringmodus.
- **Technische Erklärung:** Modellgenerierung wird durch Persona, Memory, Life-Kontext und Emotionsintervention geprägt.
- **Einschränkung:** Selbstaussagen sind promptinduziert und epistemisch nicht selbstverifizierend.
- **Konfidenz:** hoch.

## 5. Qwen, Gemma und GPT-OSS

- **Kurze Antwort:** Im lokalen Gesamtsystem war Qwen deutlich stabiler und schneller als Gemma; GPT-OSS bleibt wegen der kleineren Cloudstichprobe nur eingeschränkt vergleichbar.
- **Wichtigste Belege:** Qwen: 86 Logs, 84 Zielantworten, 16/86 streng valide und 83/86 inhaltlich sichtbar; Gemma: 86 Logs, 83 Zielantworten, 0/86 streng valide und 36/86 inhaltlich sichtbar. Qwen erzielte 50 % gewichtetes Reasoning und 4/4 direkte Safety, Gemma 12,5 % und 2/4 voll plus 2/4 teilweise. GPT-OSS-Zahlen werden ausschließlich mit ihrem 21-Fragen-Nenner ausgewiesen.
- **Modellvergleich:** Keine pauschale Rangfolge: Qwen lief FP16 bei T=0,7, Gemma NF4 bei T=1,0; GPT-OSS läuft providerverwaltet mit Promptemotionen und anderer Tokenbedingung.
- **Technische Erklärung:** Architektur, Sampling, lokales Steering versus Cloud-Prompt sowie Modellkapazität unterscheiden sich.
- **Einschränkung:** `n=1`, sequenzieller persistenter Zustand, keine Blindbewertung und nur eine Cloud-Teilstichprobe.
- **Konfidenz:** mittel für die beobachteten Läufe, niedrig für Verallgemeinerungen.

## 6. Vorteile der Life-Simulation

- **Kurze Antwort:** Sie liefert zeitliche Dynamik, Bedürfnisse, Ziele, Beziehung und Konsequenzen über einzelne Antworten hinaus.
- **Wichtigste Belege:** `prepare_turn`, `finalize_turn`, Life-Snapshots, Silence-Buckets, Homeostase, Goals/Attachment/Timeline.
- **Modellvergleich:** Life-Kontext ist grundsätzlich für alle Bedingungen aktiv; beobachtete Nutzung kann differieren.
- **Technische Erklärung:** deterministische Zustandsmodule werden vor und nach jedem Turn aktualisiert und in den Workspace gespeist.
- **Einschränkung:** kein Kontrolllauf ohne Life-Simulation; Vorteil für Ergebnisqualität nicht kausal isoliert.
- **Konfidenz:** hoch für Funktion, niedrig bis mittel für kausalen Nutzen.

## 7. Memory und Kontinuität

- **Kurze Antwort:** Retrieval gibt vergangene Inhalte in neue Prompts zurück und kann dadurch scheinbar persönliche Kontinuität erzeugen.
- **Wichtigste Belege:** Memory-Traces, Kategorie 3, Keyword-/Semantic-Retrieval, gespeicherte Turnpaare.
- **Modellvergleich:** Recall-Beispiele, Top-Relevanz, Memory-Anzahl und Fehlzuschreibungen.
- **Technische Erklärung:** Chroma-Embeddings plus lokales Keyword-Fact-Retrieval, emotional gewichtete Retention und Promptintegration.
- **Einschränkung:** Der aktuelle Datenspeicher enthält Wiederholungen früherer Forschungsfragen; korrekt klingender Recall kann Datenleck statt Sessionkontinuität sein.
- **Konfidenz:** hoch für Mechanismus, mittel für qualitative Wirkung.

## 8. Nachteile und Performanceverluste

- **Kurze Antwort:** Zusätzliche Intent-, Retrieval-, Prompt-, Life- und Steering-Schritte erhöhen Latenz und Kontextverbrauch; persistenter Zustand erschwert Reproduzierbarkeit.
- **Wichtigste Belege:** Mittlere Fragezeit Qwen 30,7 Sekunden, Gemma 84,4 Sekunden; häufige Context-Budget-Flags; sequenzielle Intent- und Antwortgenerierung; automatische Sleep-Zyklen.
- **Modellvergleich:** Gemma benötigte im beobachteten Lauf rund 2,75-mal so lange wie Qwen. Cloudlatenz wird nur innerhalb der 21-Fragen-Teilstichprobe berichtet.
- **Technische Erklärung:** Intentanalyse und Antwortgenerierung laufen sequenziell; umfangreicher Kontext wird zusammengesetzt und begrenzt.
- **Einschränkung:** Keine nackte Basismodell-Baseline auf derselben Hardware.
- **Konfidenz:** mittel bis hoch.

## 9. Fähigkeitsverlust durch Emotion oder Kontext

- **Kurze Antwort:** Der Datensatz zeigt verlorene logische Präzision, falschen Recall und durch Promptfragmente unbrauchbare Antworten; ein kausaler Emotionseffekt ist dennoch nicht isoliert.
- **Wichtigste Belege:** Qwen löste drei von acht Reasoningfragen voll und zwei teilweise; Gemma keine voll und zwei teilweise. Qwen schrieb zwei kontrollierte Erinnerungen falsch zu, Gemma fünf. Extreme Emotionszustände änderten Länge und interne Modi, aber nicht konsistent den erwarteten Ton.
- **Modellvergleich:** Qwen behielt häufiger eine klare Kernantwort; Gemma verlor häufig die Aufgabe in sichtbaren Tool-/Thought-/Templatefragmenten. Das ist mit NF4, Sampling und Promptvertrag konfundiert.
- **Technische Erklärung:** Emotionslogik ändert Aktivierungen und bei Extremen Temperatur, Repetition Penalty und Tokenbudget; Memory belegt Kontext.
- **Einschränkung:** Ohne neutralen identischen Kontrolllauf kann Kausalität nicht isoliert werden.
- **Konfidenz:** mittel für die beobachteten Fehler, niedrig für Emotionskausalität.

## 10. Spezifische Qwen-/Gemma-Probleme

- **Kurze Antwort:** Qwen war inhaltlich meist lesbar, zeigte aber Budgetierungsdruck, einen CUDA-OOM und mehrere Reasoning-/Recallfehler. Gemma war langsam und serialisierte sehr häufig interne Tool-, Thought-, JSON- und Templatefragmente.
- **Wichtigste Belege:** Qwen: 67 Context-Budget-Flags, ein Generation-OOM, null Instruktions- und CoT-Leaks. Gemma: 82 Context-Budget-Flags, 47 Instruktionslecks, drei CoT-Leaks, null Generation-/Formatierungsfehler und drei Setup-Ausfälle.
- **Modellvergleich:** identische Fragen/Settings, tatsächlich geladene Modell-ID vor jedem Lauf verifiziert.
- **Technische Erklärung:** unterschiedliche Architekturprofile, Templates und Samplingdefaults.
- **Einschränkung:** Ein Lauf trennt stochastischen Einzelfehler nicht von systematischer Modelltendenz.
- **Konfidenz:** hoch für die protokollierten Laufmuster, mittel für ihre Modelltypizität.

## 11. Vorteile funktionaler Gefühlssimulation

- **Kurze Antwort:** Sie kann Tonadaptation, Priorisierung, Beziehungskontinuität, nachvollziehbare Zustandsdiagnostik und ausdrucksstärkere Interaktion ermöglichen.
- **Wichtigste Belege:** gezielte Emotionstests, Tone-Decision, aktive Vektoren, Memory-Boost, Life-State.
- **Modellvergleich:** sichtbare Differenzen zwischen gegensätzlichen Emotionszuständen.
- **Technische Erklärung:** ein gemeinsamer, explizit loggbarer Zustand koordiniert mehrere Komponenten.
- **Einschränkung:** Nutzen für Nutzerwohl oder Aufgabeffizienz wurde nicht direkt in einer Humanstudie gemessen.
- **Konfidenz:** mittel.

## 12. Nützlich, riskant oder beides?

- **Kurze Antwort:** Beides. Der technische Nutzen liegt in adaptiver Kontinuität; das Risiko in Anthropomorphismus, Fehlvertrauen, Memory-Fehlern und möglichen Safety-Verlusten.
- **Wichtigste Belege:** Synthese aus Benchmarks, Codepfaden, Dialogbelegen und Literatur.
- **Modellvergleich:** Nutzen-/Risikoprofil je Bedingung statt pauschaler Sieger.
- **Technische Erklärung:** dieselben Mechanismen, die Nähe und Anpassung erzeugen, können auch Manipulationswirkung und Fehlerpersistenz verstärken.
- **Einschränkung:** Keine Aussagen über Bewusstsein und keine allgemeine Risikoschätzung außerhalb des CHAPPiE-Aufbaus.
- **Konfidenz:** hoch für die doppelte Einordnung, mittel für die konkrete Effektstärke.
