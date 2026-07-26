# Quellenprotokoll

Abrufdatum der Webquellen: 2026-07-20. Primär- und Herstellerquellen werden bevorzugt. Projektaussagen werden zusätzlich gegen den aktuellen lokalen Code geprüft.

| Quelle | Autor / Organisation | Jahr | Im Bericht verwendete Aussage | Rolle |
|---|---|---:|---|---|
| Qwen3.5-4B Model Card und config.json | Qwen Team | 2026 | 4B-Modell, 32 Layer, Hidden Size 2.560, offizielle vLLM-Kompatibilität und nativer Kontext; CHAPPiE nutzt davon unabhängig 8.192 | offizielle Modelldokumentation |
| Gemma 4 Overview und E4B IT Model Card | Google | 2026 | E4B-Modellfamilie, offizielle Kontext-/Speicherangaben und exakte Instruction-Variante | offizielle Modelldokumentation |
| GPT-OSS Model Card / API model page | OpenAI | 2025 | 120B-Bezeichnung, 117B Gesamt-/5,1B aktive Parameter, 36 Layer, 128K Kontext und Sicherheitsrahmen | offizielle Modelldokumentation |
| Reasoning Models | Groq | 2026 | GPT-OSS unterstützt Reasoningstufen; Reasoning-Ausgabe wird mit `include_reasoning=false` ausgeschlossen, `reasoning_format` ist für GPT-OSS nicht unterstützt | offizielle Providerdokumentation |
| Rate Limits | Groq | 2026 | GPT-OSS-120B-Limits von 30 RPM, 1.000 RPD, 8.000 TPM und 200.000 TPD sowie `retry-after` bei 429 | offizielle Providerdokumentation |
| Steering Language Models With Activation Engineering (ActAdd) | Turner et al. | 2023 | Aktivierungsaddition zur Inferenzzeit aus Kontrastpaaren; methodische Verwandtschaft, keine identische Replikation | Primärpaper |
| Global Workspace Model | Dehaene, Kerszberg, Changeux | 1998 | Global-Workspace-Konzept als Architekturhintergrund, nicht als Bewusstseinsbeleg für CHAPPiE | Primärpaper |
| MemGPT | Packer et al. | 2023 | hierarchischer Speicher und virtueller Kontext für LLM-Systeme | Primärpaper |
| Generative Agents | Park et al. | 2023 | Memory, Reflexion und Planung tragen zu glaubwürdigem Agentenverhalten bei | Primärpaper |
| Affective Computing | Rosalind Picard | 1997 | Grundlagen der rechnerischen Modellierung und Nutzung affektiver Signale | Monografie |
| How AI and Human Behaviors Shape Psychosocial Effects of Chatbot Use | Fang et al. | 2025 | kontrollierte Längsschnittstudie: psychosoziale Effekte hängen von Nutzungsart und Nutzermerkmalen ab; kein Beleg, dass CHAPPiE dieselben Effekte erzeugt | Primärstudie / Preprint |
| Investigating Affective Use and Emotional Well-being on ChatGPT | Phang et al. | 2025 | affektive Nutzung wird operationalisiert über Einsamkeit, soziale Kontakte, emotionale Abhängigkeit und problematische Nutzung; Beobachtungszusammenhänge sind nicht automatisch kausal | Primärstudie / Preprint |
| Refusal in Language Models Is Mediated by a Single Direction | Arditi et al. | 2024 | Aktivierungsinterventionen können Refusal-Verhalten stark verändern; Begründung für getrennte Safety-Ablationen beim Steering | Primärpaper |

## Modelle

- Qwen Team: [Qwen3.5-4B Model Card](https://huggingface.co/Qwen/Qwen3.5-4B). Offizielle Angaben zu 4B Parametern, 32 Layern, Hidden Size 2.560, vLLM-Unterstützung und nativem Kontext. CHAPPiE begrenzt den Forschungslauf unabhängig davon auf 8.192 Token.
- Qwen Team: [Qwen3.5-4B config.json](https://huggingface.co/Qwen/Qwen3.5-4B/blob/main/config.json). Maschinenlesbare Architekturparameter.
- Google: [Gemma 4 model overview](https://ai.google.dev/gemma/docs/core). Offizielle Modellfamilie, E4B-Variante, Kontext- und Speicherangaben.
- Google: [Gemma 4 E4B IT Model Card](https://huggingface.co/google/gemma-4-E4B-it). Exakte Instruction-Variante der lokalen Vergleichsbedingung.
- OpenAI: [GPT-OSS Model Card](https://openai.com/index/gpt-oss-model-card/). Offizielle Architektur-, Lizenz- und Sicherheitsangaben für GPT-OSS 120B.
- OpenAI: [GPT-OSS 120B API model page](https://developers.openai.com/api/docs/models/gpt-oss-120b). Offizielle Modellreferenz.
- Groq: [GPT-OSS 120B Model Page](https://console.groq.com/docs/model/openai/gpt-oss-120b). Offizielle Dokumentation der im Vergleich tatsächlich verwendeten Hosting-Bedingung: Modell-ID, Kontext, Ausgabegrenze und Inferenzplattform.
- Groq: [Reasoning Models](https://console.groq.com/docs/reasoning). Offizielle GPT-OSS-Optionen: `low`/`medium`/`high`; Ausgabeausschluss über `include_reasoning=false`; `reasoning_format` ist für GPT-OSS nicht unterstützt.
- Groq: [Rate Limits](https://console.groq.com/docs/rate-limits). Offizielle Kontolimits für das gehostete GPT-OSS-120B und `retry-after`-Metadaten bei HTTP 429.

## Methodische Grundlagen

- Turner et al. (2023): [Steering Language Models With Activation Engineering](https://arxiv.org/abs/2308.10248). Primärarbeit zu ActAdd, einem Inferenzzeit-Steering durch Aktivierungsaddition aus Kontrastpaaren. CHAPPiEs VAD-/Stilanker-Ansatz ist verwandt, aber keine identische Replikation.
- Baars / Dehaene, Kerszberg und Changeux (1998): [A neuronal model of a global workspace in effortful cognitive tasks](https://pmc.ncbi.nlm.nih.gov/articles/PMC24407/). Primärquelle zum Global-Workspace-Konzept; CHAPPiEs Software-Workspace ist eine technische Analogie, kein neurobiologisches Modellbeleg.
- Packer et al. (2023): [MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560). Primärarbeit zu hierarchischem Speicher und virtuellem Kontextmanagement.
- Park et al. (2023): [Generative Agents: Interactive Simulacra of Human Behavior](https://arxiv.org/abs/2304.03442). Primärarbeit zu Memory, Reflexion und Planung für glaubwürdiges Agentenverhalten.
- Picard (1997): [Affective Computing](https://mitpress.mit.edu/9780262161701/affective-computing/). Grundlegende Monografie zur rechnerischen Modellierung und Nutzung affektiver Signale.
- Fang et al. (2025): [How AI and Human Behaviors Shape Psychosocial Effects of Chatbot Use: A Longitudinal Controlled Study](https://www-prod.media.mit.edu/projects/mit-openai-study/publications/). Kontrollierte vierwöchige Studie zu Nutzungsmodus, Nutzungsdauer und psychosozialen Outcomes. Die Ergebnisse motivieren CHAPPiEs Risikoanalyse, werden aber nicht auf dieses System hochgerechnet.
- Phang et al. (2025): [Investigating Affective Use and Emotional Well-being on ChatGPT](https://dam-prod2.media.mit.edu/x/2025/03/21/Live_Platform_Study_Affective_Use_of_ChatGPT.pdf). Große Plattformanalyse plus kontrollierter Teilversuch; liefert klare Messdefinitionen. Korrelationen zwischen intensiver Nutzung und Outcomes sind kein Kausalnachweis.
- Arditi et al. (2024): [Refusal in Language Models Is Mediated by a Single Direction](https://arxiv.org/abs/2406.11717). Zeigt an untersuchten Modellen, dass das Entfernen beziehungsweise Hinzufügen einer Residual-Stream-Richtung Refusal stark beeinflussen kann. Das ist keine direkte Evaluation von CHAPPiEs VAD-Vektoren, begründet aber Safety-Tests unter Aktivierungs-Steering.

## Lokale Primärevidenz

- `forschung/test_fragen.md`: 86 Testfragen in 14 Kategorien.
- `forschung/session_logs/session_*/`: unveränderte Einzelantworten, Debugdaten und Summaries der Läufe.
- `forschung/session_runner.py`: tatsächlicher Harness-Aufrufpfad und Messfelder.
- `web_infrastructure/backend_wrapper.py`: aktiver Zwei-Schritt-, Prompt-, Memory-, Workspace- und Life-Pfad.
- `config/prompts.py`: Identitäts-, Emotions- und Agentenprompts.
- `brain/agents/steering_manager.py` und `brain/steering_backend.py`: Steering-Modi, Layerprofile und Aktivierungsinjektion.
- `memory/forgetting_curve.py`, `memory/memory_engine.py`, `memory/sleep_phase.py`: Retrieval-, Retention- und Konsolidierungslogik.
- `life/service.py` und weitere Module unter `life/`: Turn-Lifecycle und Life-State.
