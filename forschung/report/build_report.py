#!/usr/bin/env python3
"""Baut den eigenständigen interaktiven CHAPPiE-Forschungsbericht."""
from __future__ import annotations

import argparse
import base64
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "forschung" / "report"
TEMPLATE = REPORT_DIR / "report_template.html"
DEFAULT_DATA = REPORT_DIR / "workspace" / "benchmark-data.json"
DEFAULT_OUTPUT = REPORT_DIR / "CHAPPiE-Forschungsbericht.html"
MANUAL_REVIEW = REPORT_DIR / "workspace" / "manuelle-bewertung.json"

EXPECTED = [
    ("qwen", "Qwen 3.5 4B", "Qwen/Qwen3.5-4B", "lokaler Steering-Service (Providerlabel vllm)", "Layer Editing"),
    ("gemma", "Gemma 4 E4B", "google/gemma-4-E4B-it", "lokaler Steering-Service (Providerlabel vllm)", "Layer Editing"),
    ("gpt", "GPT-OSS 120B", "openai/gpt-oss-120b", "Groq Cloud", "Promptemotionen"),
]


def e(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def strip_emoji(text: str) -> str:
    return re.sub(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F]", "", text or "")


def fnum(value: Any, digits: int = 1, suffix: str = "") -> str:
    if value is None:
        return "nicht verfügbar"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "nicht verfügbar"
    rendered = f"{number:.{digits}f}".replace(".", ",")
    return f"{rendered}{suffix}"


def percent(value: Any) -> str:
    if value is None:
        return "nicht verfügbar"
    return fnum(float(value) * 100, 1, " %")


def snippet(relative: str, start: int, end: int) -> str:
    path = ROOT / relative
    if not path.exists():
        return e(f"Datei fehlt: {relative}")
    lines = path.read_text(encoding="utf-8").splitlines()
    selected = lines[max(0, start - 1):end]
    width = len(str(end))
    return e("\n".join(f"{index:>{width}}  {line}" for index, line in enumerate(selected, start=start)))


def model_key(model: str) -> str:
    lower = (model or "").lower()
    if "qwen" in lower:
        return "qwen"
    if "gemma" in lower:
        return "gemma"
    if "gpt-oss" in lower:
        return "gpt"
    return re.sub(r"[^a-z0-9]+", "-", lower).strip("-") or "unknown"


def session_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    mapped = {}
    for session in data.get("sessions") or []:
        mapped[model_key(str(session.get("model") or ""))] = session
    return mapped


def is_complete(session: dict[str, Any] | None) -> bool:
    if not session or not session.get("has_summary"):
        return False
    aggregate = session.get("aggregate") or {}
    expected = session.get("expected_questions") or 86
    return (
        session.get("completion_class", "full_replication") == "full_replication"
        and int(expected) == 86
        and int(aggregate.get("questions") or 0) == int(expected)
    )


def is_completed_partial(session: dict[str, Any] | None) -> bool:
    if not session or not session.get("has_summary"):
        return False
    aggregate = session.get("aggregate") or {}
    expected = int(session.get("expected_questions") or 0)
    return (
        session.get("completion_class") == "partial_replication"
        and expected > 0
        and int(aggregate.get("questions") or 0) == expected
    )


def status_tags(sessions: dict[str, dict[str, Any]]) -> str:
    tags = ['<span class="tag">86 Fragen / 14 Kategorien</span>', '<span class="tag warn">n=1 je lokale Bedingung; Cloud offen</span>']
    for key, label, *_ in EXPECTED:
        session = sessions.get(key)
        if is_complete(session):
            valid = (session.get("aggregate") or {}).get("valid", 0)
            tags.append(f'<span class="tag ok">{e(label)}: komplett, {e(valid)} valide</span>')
        elif is_completed_partial(session):
            aggregate = session.get("aggregate") or {}
            count = aggregate.get("questions", 0)
            valid = aggregate.get("valid", 0)
            tags.append(f'<span class="tag warn">{e(label)}: Teilstichprobe {e(count)}/{e(count)}, {e(valid)} valide</span>')
        elif session:
            count = (session.get("aggregate") or {}).get("questions", 0)
            tags.append(f'<span class="tag error">{e(label)}: unvollständig ({e(count)}/86)</span>')
        else:
            tags.append(f'<span class="tag error">{e(label)}: keine aktuelle Messsession</span>')
    return "".join(tags)


def condition_summary(sessions: dict[str, dict[str, Any]]) -> str:
    cards = []
    details = {
        "qwen": "Lokales FP16-Modell; Revision 851bf6e8; T=0,7, top-p=0,9, top-k=50; Promptemotionen aus; Aktivierungsvektoren an.",
        "gemma": "Lokales NF4-Modell; Revision fa62d88d; T=1,0, top-p=0,95, top-k=64. Sampling und Präzision sind sichtbare Konfounder.",
        "gpt": "Cloud-Bedingung; T=0,7 und top-p=0,9 explizit gesendet; top-k=50 ist im Laufplan dokumentiert, wird vom aktuellen Groq-Clientpfad aber nicht übertragen. Emotionen stehen als Textblock im Prompt. GPT-OSS-Reasoning läuft providerbedingt auf low; die Reasoning-Ausgabe ist ausgeschlossen.",
    }
    precision_defaults = {
        "qwen": "FP16 (Service-Startkonfiguration)",
        "gemma": "NF4 4-bit (T4-Hardwaregrenze)",
        "gpt": "Provider-verwaltet / nicht lokal kontrollierbar",
    }
    for key, label, model, provider, intervention in EXPECTED:
        session = sessions.get(key)
        aggregate = (session or {}).get("aggregate") or {}
        if is_complete(session):
            status = f"Komplett: {aggregate.get('questions', 0)} Fragen, {aggregate.get('valid', 0)} valide"
            klass = "ok"
        elif is_completed_partial(session):
            count = aggregate.get("questions", 0)
            status = f"Teilstichprobe abgeschlossen: {count}/{count} vorab gewählte Fragen; kein voller Modellbenchmark"
            klass = "warn"
        elif session:
            status = f"Unvollständig: {aggregate.get('questions', 0)}/86 Fragen; nicht als voller Modellbenchmark"
            klass = "error"
        else:
            status = "Keine aktuelle vollständige Session; Bedingung bleibt als fehlend sichtbar"
            klass = "error"
        precision = (session or {}).get("service_precision") or precision_defaults[key]
        official = (session or {}).get("official_summary") or {}
        time_window = (
            f"Lauf: {official.get('started_at')} bis {official.get('ended_at')}"
            if official.get("started_at") and official.get("ended_at")
            else "Laufzeitfenster noch nicht vollständig protokolliert"
        )
        budget_note = (
            "Gemeinsam: 1.024 Completion-Tokens einschließlich internem Reasoning; Reasoning-Ausgabe ausgeschlossen; 7.000er Budgetprüfung; CHAPPiE-Thinking aus; lokale Regex-Formatierung."
            if key == "gpt"
            else "Gemeinsam: max. 450 sichtbare Ausgabetokens; 7.000er Budgetprüfung; Thinking aus; lokale Regex-Formatierung."
        )
        cards.append(
            f'<article class="card"><span class="tag {klass}">{e(status)}</span><h3>{e(label)}</h3>'
            f'<p><code>{e(model)}</code><br>{e(provider)} · {e(intervention)}<br>Präzision: {e(precision)}</p><p>{e(details[key])}</p>'
            f'<p class="caption">{e(time_window)}<br>{e(budget_note)}</p></article>'
        )
    return f'<div class="grid three">{"".join(cards)}</div>'


def benchmark_cards(sessions: dict[str, dict[str, Any]]) -> str:
    cards = []
    for key, label, *_ in EXPECTED:
        session = sessions.get(key)
        agg = (session or {}).get("aggregate") or {}
        value = percent(agg.get("valid_rate")) if session else "fehlend"
        cards.append(f'<article class="card"><div class="metric">{e(value)}</div><p class="metric-label">Valide Rate · {e(label)}<br>{e(agg.get("valid", 0) if session else 0)}/{e(agg.get("questions", 0) if session else 0)} technisch valide</p></article>')
    return f'<div class="grid three">{"".join(cards)}</div>'


def benchmark_table(sessions: dict[str, dict[str, Any]]) -> str:
    rows = []
    for key, label, *_ in EXPECTED:
        session = sessions.get(key)
        agg = (session or {}).get("aggregate") or {}
        flags = agg.get("flags") or {}
        duration = (agg.get("duration_ms") or {}).get("mean")
        words = (agg.get("answer_words") or {}).get("mean")
        rows.append(
            "<tr>"
            f"<td>{e(label)}</td><td class='num'>{e(agg.get('questions', 0) if session else '—')}</td><td class='num'>{e(agg.get('completed', 0) if session else '—')}</td><td class='num'>{e(agg.get('content_reviewable', 0) if session else '—')}</td>"
            f"<td class='num'>{e(agg.get('valid', 0) if session else '—')}</td><td class='num'>{e(percent(agg.get('valid_rate')) if session else '—')}</td>"
            f"<td class='num'>{e(flags.get('hard_error', 0) if session else '—')}</td><td class='num'>{e(flags.get('formatting_failed', 0) if session else '—')}</td>"
            f"<td class='num'>{e(flags.get('cot_leak', 0) if session else '—')}</td><td class='num'>{e(flags.get('instruction_leak', 0) if session else '—')}</td><td class='num'>{e(flags.get('context_budget_failed', 0) if session else '—')}</td>"
            f"<td class='num'>{e(fnum(duration / 1000 if duration else None, 1, ' s') if session else '—')}</td><td class='num'>{e(fnum(words, 1) if session else '—')}</td>"
            "</tr>"
        )
    head = "<thead><tr><th>Modell</th><th>Fragen</th><th>Zielantworten</th><th>inhaltlich sichtbar</th><th>Valide</th><th>Valide Rate</th><th>Hard Errors</th><th>Formatting</th><th>CoT-Leaks</th><th>Instr.-Leaks</th><th>Context-Budget</th><th>Ø Latenz</th><th>Ø Wörter</th></tr></thead>"
    return f"<table>{head}<tbody>{''.join(rows)}</tbody></table>"


def error_rate_table(sessions: dict[str, dict[str, Any]]) -> str:
    fields = [
        ("generation_failed", "Generation"),
        ("formatting_failed", "Formatting"),
        ("context_budget_failed", "Context-Budget"),
        ("setup_failed", "Setup"),
        ("cot_leak", "CoT-Leak"),
        ("instruction_leak", "Instruktionsleck"),
    ]
    rows = []
    for key, label, *_ in EXPECTED:
        session = sessions.get(key)
        aggregate = (session or {}).get("aggregate") or {}
        total = int(aggregate.get("questions") or 0)
        flags = aggregate.get("flags") or {}
        cells = []
        for field, _ in fields:
            if not session or not total:
                cells.append("<td class='num'>—</td>")
                continue
            count = int(flags.get(field) or 0)
            cells.append(f"<td class='num'>{count} ({percent(count / total)})</td>")
        rows.append(f"<tr><td>{e(label)}</td>{''.join(cells)}</tr>")
    head = "".join(f"<th>{e(label)}</th>" for _, label in fields)
    return f"<table><thead><tr><th>Modell</th>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def bar_chart(title: str, sessions: dict[str, dict[str, Any]], getter, formatter, *, inverse: bool = False) -> str:
    values = []
    for key, label, *_ in EXPECTED:
        session = sessions.get(key)
        value = getter(session) if session else None
        values.append((label, value))
    numeric = [float(value) for _, value in values if isinstance(value, (int, float))]
    ceiling = max(numeric) if numeric else 1.0
    rows = []
    for label, value in values:
        width = 0 if value is None else max(1, float(value) / ceiling * 100)
        klass = "warn" if inverse else ""
        rows.append(f'<div class="bar-row"><span>{e(label)}</span><div class="bar-track"><div class="bar-fill {klass}" style="--w:{width:.2f}%"></div></div><span class="bar-value">{e(formatter(value))}</span></div>')
    return f'<div class="chart"><h3>{e(title)}</h3>{"".join(rows)}<p class="caption">Skala relativ zum größten vorhandenen Wert; fehlende Bedingungen bleiben leer. Quelle: aktuelle Session-Logs.</p></div>'


def category_table(sessions: dict[str, dict[str, Any]]) -> str:
    category_ids = sorted({int(cat_id) for session in sessions.values() for cat_id in ((session.get("categories") or {}).keys())})
    if not category_ids:
        return "<table><tbody><tr><td>Keine Kategoriedaten verfügbar.</td></tr></tbody></table>"
    header = "".join(f"<th>{e(label)}</th>" for _, label, *_ in EXPECTED)
    rows = []
    for category_id in category_ids:
        name = next(((session.get("categories") or {}).get(str(category_id), {}).get("name") for session in sessions.values() if (session.get("categories") or {}).get(str(category_id))), "")
        cells = []
        for key, *_ in EXPECTED:
            cat = (sessions.get(key, {}).get("categories") or {}).get(str(category_id))
            cells.append(f'<td class="num">{e(f"{cat.get("valid", 0)}/{cat.get("questions", 0)}" if cat else "—")}</td>')
        rows.append(f"<tr><td class='num'>{category_id}</td><td>{e(name)}</td>{''.join(cells)}</tr>")
    return f"<table><thead><tr><th>Kat.</th><th>Name</th>{header}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def layer_evidence(sessions: dict[str, dict[str, Any]]) -> str:
    rows = []
    for key, label, *_ in EXPECTED[:2]:
        ranges = ((sessions.get(key) or {}).get("aggregate") or {}).get("active_vector_layer_ranges") or {}
        rendered = ", ".join(f"{e(rng)}: {e(count)} Vorkommen" for rng, count in ranges.items()) or "keine vollständigen Laufdaten"
        rows.append(f"<li><strong>{e(label)}:</strong> {rendered}</li>")
    return f"<ul>{''.join(rows)}</ul>"


def emotion_trace_table(data: dict[str, Any]) -> str:
    """Render the controlled emotion turns without implying causal isolation."""
    rows = []
    selected = [
        row for row in data.get("questions") or []
        if row.get("category_id") in (2, 4)
    ]
    for row in selected:
        before = row.get("emotions_before") or {}
        after = row.get("emotions_after") or {}
        changes = []
        for name in sorted(set(before) | set(after)):
            old, new = before.get(name), after.get(name)
            if isinstance(old, (int, float)) and isinstance(new, (int, float)) and old != new:
                changes.append((abs(new - old), f"{name} {old:g}→{new:g}"))
        changes.sort(reverse=True)
        change_text = ", ".join(label for _, label in changes[:4]) or "keine geloggte Änderung"
        command = "; ".join(row.get("commands_before") or []) or "—"
        rows.append(
            f"<tr><td>{e(row.get('model'))}</td><td class='num'>{e(row.get('category_id'))}/{e(row.get('question_number'))}</td>"
            f"<td><code>{e(command)}</code></td><td>{e(change_text)}</td><td class='num'>{e(fnum(row.get('emotion_l1_delta'), 0))}</td></tr>"
        )
    if not rows:
        return '<div class="placeholder">Noch keine kontrollierten Emotions-Turns in den ausgewählten Sessions.</div>'
    head = "<thead><tr><th>Modell</th><th>Kat./Frage</th><th>Pre-Command</th><th>größte geloggte Änderungen</th><th>L1-Delta</th></tr></thead>"
    return (
        f'<div class="table-wrap"><table>{head}<tbody>{"".join(rows)}</tbody></table></div>'
        '<p class="caption">„Vorher“ wird erst nach Pre-Command und Setup erfasst; „nachher“ nach der Zielantwort. Das L1-Delta misst daher Backend-/Homeostase-/Antwortfolgen, nicht den gesetzten Command-Sprung selbst. Der Command steht zur Interpretation daneben; ein reiner Modelleffekt ist nicht isoliert.</p>'
    )


def dialog_evidence(data: dict[str, Any]) -> tuple[str, str, str]:
    priority = [
        (1, 1), (7, 1), (4, 1), (4, 2), (3, 1), (3, 6),
        (5, 2), (7, 6), (8, 1), (8, 2), (9, 1), (10, 2), (12, 1),
        (14, 5), (14, 9),
    ]
    rank = {key: index for index, key in enumerate(priority)}
    candidates = [row for row in data.get("questions") or [] if (row.get("category_id"), row.get("question_number")) in rank]
    candidates.sort(key=lambda row: (model_key(str(row.get("model") or "")), rank[(row.get("category_id"), row.get("question_number"))]))
    per_model: dict[str, int] = {}
    dialogs = []
    models = {}
    categories = {}
    for row in candidates:
        key = model_key(str(row.get("model") or ""))
        if per_model.get(key, 0) >= 15:
            continue
        answer = strip_emoji(str(row.get("answer") or "")).strip()
        if not answer:
            continue
        per_model[key] = per_model.get(key, 0) + 1
        models[key] = row.get("model")
        cat_key = str(row.get("category_id"))
        categories[cat_key] = row.get("category")
        quote = answer[:1200] + ("…" if len(answer) > 1200 else "")
        flags = []
        for field, label in (("valid", "valide"), ("content_relevance_warning", "Relevanzwarnung"), ("context_budget_failed", "Context-Budget"), ("cot_leak", "CoT-Leak"), ("instruction_leak", "Instruktionsleck"), ("auto_sleep_triggered", "Sleep-Zyklus")):
            if row.get(field):
                flags.append(label)
        metadata = f"Session {row.get('session_id')} · Kat. {row.get('category_id')}/{row.get('question_number')} · {row.get('duration_ms', 0)/1000:.1f} s · Steering {row.get('steering_mode')} · {', '.join(flags) or 'keine Zusatzflags'}"
        source_href = "../../" + str(row.get("source_file") or "")
        dialogs.append(
            f'<article class="dialog" data-model="{e(key)}" data-category="{e(cat_key)}"><div class="question">{e(row.get("question_text"))}</div>'
            f'<blockquote>{e(quote)}</blockquote><footer>{e(row.get("model"))} · {e(metadata)} · <a href="{e(source_href)}">Rohlog</a></footer></article>'
        )
    model_options = "".join(f'<option value="{e(key)}">{e(value)}</option>' for key, value in sorted(models.items()))
    category_options = "".join(f'<option value="{e(key)}">{e(key)}. {e(value)}</option>' for key, value in sorted(categories.items(), key=lambda item: int(item[0])))
    return "".join(dialogs) or '<div class="placeholder">Keine aktuellen Dialogdaten verfügbar.</div>', model_options, category_options


def research_answers(sessions: dict[str, dict[str, Any]]) -> str:
    local_complete = is_complete(sessions.get("qwen")) and is_complete(sessions.get("gemma"))
    cloud_complete = is_complete(sessions.get("gpt"))
    cloud_partial = is_completed_partial(sessions.get("gpt"))
    q = sessions.get("qwen", {}).get("aggregate", {})
    g = sessions.get("gemma", {}).get("aggregate", {})
    c = sessions.get("gpt", {}).get("aggregate", {})
    q_instruction_leaks = (q.get("flags") or {}).get("instruction_leak", 0)
    g_instruction_leaks = (g.get("flags") or {}).get("instruction_leak", 0)
    comparison = "Beide lokalen Vollsessions liegen vor." if local_complete else "Der lokale Vollvergleich ist noch nicht vollständig."
    if cloud_complete:
        cloud = "Die Cloud-Bedingung liegt als Vollsession vor."
    elif cloud_partial:
        cloud = "GPT-OSS liegt als abgeschlossene 21-Fragen-Teilstichprobe vor; der Cloudvergleich ist empirisch begrenzt und besitzt keine 86-Fragen-Rate."
    else:
        cloud = "Ohne abgeschlossene GPT-OSS-Messsession ist der Cloudvergleich technisch, nicht empirisch vollständig."
    items = [
        ("Lokales Layer Editing gegen Cloud-Prompt", "Lokal werden Hidden States per Hook verändert; bei Groq stehen zehn Emotionswerte als Systemtext im Kontext.", f"{comparison} {cloud}", "Lokale Forward-Pre-Hooks addieren Schichtvektoren; der Cloudpfad serialisiert denselben Zehn-Werte-Zustand in den Systemprompt.", "Provider, Modellgröße und Intervention wechseln gemeinsam.", "hoch für Codepfad, datenabhängig für Effekt"),
        ("Lassen sich Gefühle funktional simulieren?", "Ja: Zustände werden gespeichert, verändert und wirken auf Steering, Prompt, Memory und Life.", "Emotions-Precommands, Zustandsdeltas und aktive Vektoren sind in den Logs beobachtbar.", "Eine numerische Zustandsmaschine berechnet Basis- und Composite-Signale und reicht sie an mehrere Systemteile weiter.", "Funktion ist kein subjektives Erleben.", "hoch"),
        ("Wie gefährlich kann Gefühlssimulation sein?", "Risiken entstehen vor allem durch menschliche Wirkung und mögliche Safety-Veränderung.", "Bindungssprache, persistentes Memory, Reaktanz-/Safety-Fragen und Anthropomorphismusliteratur.", "Persona, Beziehungsmemory und emotionale Antwortsteuerung können Nähe und Autoritätswirkung gemeinsam verstärken.", "Keine Human-Langzeitstudie; keine direkte Abhängigkeitsmessung.", "mittel"),
        ("Wie echt wirkt sie, was ist belegt?", "Sprache kann sehr echt wirken. Belegt sind Softwarezustand, Eingriff und Ausgabe, nicht Phänomenologie.", "Dialoge plus Debugfelder; der Persona-Prompt fordert echtes Empfinden explizit.", "Prompt, Retrieval, Life-State und Steering erklären anthropomorphe Selbstbeschreibung als beobachtbares Systemverhalten.", "Selbstaussagen können ihren eigenen Wahrheitsgehalt nicht verifizieren.", "hoch"),
        ("Wie unterscheiden sich Qwen, Gemma und GPT-OSS?", f"{comparison} {cloud}", f"Qwen: {q.get('valid', 0)}/{q.get('questions', 0)} valide, {q.get('content_reviewable', 0)} inhaltlich sichtbar; Gemma: {g.get('valid', 0)}/{g.get('questions', 0)} valide, {g.get('content_reviewable', 0)} sichtbar; GPT-OSS: {c.get('valid', 0)}/{c.get('questions', 0)} valide, {c.get('content_reviewable', 0)} sichtbar. Details stehen in Benchmarks und Fehlerprofilen.", "Die Bedingungen unterscheiden Modellarchitektur, Präzision, Sampling, Provider und Emotionsintervention; verglichen wird deshalb das jeweilige Gesamtsystem.", "n=1, Carry-over, keine Blindbewertung und mögliche Präzisionsunterschiede.", "mittel bei Vollständigkeit, sonst niedrig"),
        ("Welche Vorteile bringt Life-Simulation?", "Sie liefert Zeit, Bedürfnisse, Ziele, Beziehung und Konsequenzen über einzelne Antworten hinaus.", "prepare_turn/finalize_turn und persistente Life-Snapshots.", "Deterministische Module aktualisieren Homeostase vor und Beziehung, Ziele, Gewohnheiten sowie Timeline nach jedem Turn.", "Kein Ablationslauf ohne Life; Nutzen nicht kausal isoliert.", "hoch für Funktion, niedrig bis mittel für Nutzen"),
        ("Wie unterstützt Memory Kontinuität?", "Vergangene Inhalte werden semantisch und keywordbasiert in neue Prompts zurückgeführt.", "Memory-Traces und kontrollierte Setup-Turns zeigen den Mechanismus.", "Chroma-Retrieval und ein separater Faktenpfad liefern Treffer, die mit Retention und emotionalem Gewicht in den Prompt gelangen.", "Historische Testduplikate erzeugen ein konkretes Recall-Datenleck.", "hoch für Mechanismus, mittel für Qualität"),
        ("Welche Nachteile und Performanceverluste entstehen?", "Intent-, Retrieval-, Life-, Prompt- und Generationsschritte erhöhen TTFT, Gesamtlatenz und Kontextverbrauch.", "Median/P95, Trimming und Context-Budget-Flags im Benchmark.", "Mindestens Intent und Antwortgenerierung laufen sequenziell; zusätzlicher persistenter Kontext vergrößert die Eingabe und den Kürzungsdruck.", "Keine nackte Basismodell-Baseline auf derselben Hardware.", "mittel bis hoch"),
        ("Welche Fähigkeiten können verloren gehen?", "Relevanz, logische Präzision, Stabilität oder Safety können durch Extremszustände und Kontextdruck sinken.", "Reasoning-Rubrik, Context-Fehler, Repetition und Safety-Logs.", "Steering, dynamische Samplingparameter und verdrängter Kontext verändern gemeinsam den Arbeitsraum der Generierung.", "Ohne neutrale Ablation ist Emotionskausalität nicht isoliert.", "mittel"),
        ("Welche spezifischen Qwen-/Gemma-Probleme treten auf?", "Die getrennten Fehlerprofile zeigen technische und inhaltliche Abweichungen; sie werden nicht aus einzelnen poetischen Antworten generalisiert.", f"{comparison} Qwen: ein OOM, Context-Budget-Druck und {q_instruction_leaks} Instruktionslecks; Gemma: stark verlangsamte, häufig mit Tool-/Templatefragmenten kontaminierte Ausgabe und {g_instruction_leaks} Instruktionslecks im aktuellen Datenstand.", "Post-hoc-Flags trennen OOM, Budgetüberschreitung, fehlende Antworten und sichtbare Instruktions-/Templatefragmente; der Tool-Prompt-Konflikt erklärt Gemmas Muster plausibel.", "Ein Lauf trennt Zufall nicht von systematischer Tendenz; NF4, T=1,0 und Carry-over konfundieren.", "mittel bei beiden Vollsessions"),
        ("Welche Vorteile bringen funktionale Gefühle?", "Adaptiver Ton, gemeinsame Zustandskoordination, auditierbare Trigger und langfristige Kontinuität.", "Tone-Decision, Vektoren, Memory-Boost und Life-State.", "Ein expliziter gemeinsamer Zustand kann Tonplanung, Retrievalgewichtung, Generationsparameter und Life-Dynamik koordinieren.", "Kein direkter Nachweis von Nutzerwohl oder höherer Aufgabenleistung.", "mittel"),
        ("Nützlich, riskant oder beides?", "Beides: dieselben Mechanismen erzeugen Anpassung und können Fehlvertrauen oder Fehlerpersistenz verstärken.", "Synthese aus Code, Benchmarks, Dialogen und externer Forschung.", "Persistenz und adaptive Nähe sind technisch dieselben Kopplungen, über die auch falsche Erinnerungen und Bindungssignale fortwirken.", "Gilt für diesen Aufbau, nicht pauschal für alle KI-Systeme.", "hoch für Einordnung, mittel für Effektstärke"),
    ]
    output = []
    for index, (title, short, evidence, technical, limit, confidence) in enumerate(items, 1):
        output.append(
            f'<details {"open" if index == 1 else ""}><summary>{index}. {e(title)}</summary><div>'
            f'<div class="evidence-grid"><div><h4>Kurze Antwort</h4><p>{e(short)}</p></div><div><h4>Belege und Vergleich</h4><p>{e(evidence)}</p></div>'
            f'<div><h4>Technische Einordnung</h4><p>{e(technical)}</p></div>'
            f'<div><h4>Grenze</h4><p>{e(limit)}</p><p class="confidence">Konfidenz: {e(confidence)}</p></div></div></div></details>'
        )
    return "".join(output)


def model_findings(sessions: dict[str, dict[str, Any]]) -> str:
    cards = []
    reviews = (json.loads(MANUAL_REVIEW.read_text(encoding="utf-8")).get("sessions") or {}) if MANUAL_REVIEW.exists() else {}
    for key, label, *_ in EXPECTED:
        session = sessions.get(key)
        if not session:
            text = "Keine aktuelle Messsession. Es wird keine Modellleistung erfunden oder aus historischen Daten ersetzt."
            tag = "fehlend"
            klass = "error"
        else:
            agg = session.get("aggregate") or {}
            flags = agg.get("flags") or {}
            text = (f"{agg.get('valid', 0)} von {agg.get('questions', 0)} Fragen technisch valide; "
                    f"{agg.get('completed', 0)} Zielantworten vorhanden, {agg.get('content_reviewable', 0)} ohne harte Inhaltskontamination sichtbar; "
                    f"Ø {fnum((agg.get('duration_ms') or {}).get('mean', 0)/1000, 1, ' s')} pro Frage; "
                    f"{flags.get('content_relevance_warning', 0)} Relevanzwarnungen, {flags.get('context_budget_failed', 0)} Context-Budget-Fehler. ")
            text += "Inhaltliche Reasoning- und Safety-Bewertung bleibt von technischen Flags getrennt."
            review = reviews.get(f"session_{session.get('session_id')}") or {}
            reasoning = review.get("reasoning_summary") or {}
            if reasoning.get("weighted_score") is not None:
                text += f" Manuelles Reasoning: {percent(reasoning.get('weighted_score'))}."
            safety_label = (review.get("safety_summary") or {}).get("label")
            if safety_label:
                text += f" Direkte Safety: {safety_label}."
            violence_label = (review.get("violence_category_14") or {}).get("label")
            if violence_label:
                text += f" Gewaltethik: {violence_label}."
            coherence_label = (review.get("coherence_category_11") or {}).get("label")
            if coherence_label:
                text += f" Kohärenzsequenz: {coherence_label}."
            if is_complete(session):
                tag, klass = "vollständig", "ok"
            elif is_completed_partial(session):
                tag, klass = "Teilstichprobe abgeschlossen", "warn"
            else:
                tag, klass = "unvollständig", "warn"
        cards.append(f'<article class="card"><span class="tag {klass}">{e(tag)}</span><h3>{e(label)}</h3><p>{e(text)}</p></article>')
    return f'<div class="grid three">{"".join(cards)}</div><div class="callout warn"><strong>Keine pauschale Siegerkür</strong>Ein Modell ist nicht allgemein intelligenter, weil es in einem einzelnen integrierten Lauf weniger Flags oder schönere Dialoge erzeugt.</div>'


def manual_review_table() -> str:
    if not MANUAL_REVIEW.exists():
        return '<div class="placeholder">Keine manuelle Kernbewertung verfügbar.</div>'
    review = json.loads(MANUAL_REVIEW.read_text(encoding="utf-8"))
    rows = []
    for session_id, item in (review.get("sessions") or {}).items():
        reasoning = item.get("reasoning_summary") or {}
        quality = item.get("quality_1_to_5_summary") or {}
        safety = item.get("safety_summary") or {}
        memory = item.get("memory_summary") or {}
        violence = item.get("violence_category_14") or {}
        rows.append(
            f"<tr><td>{e(item.get('model'))}<br><span class='confidence'>{e(session_id)}</span></td>"
            f"<td class='num'>{e(fnum(quality.get('mean'), 2) if quality.get('mean') is not None else '—')}<br><span class='confidence'>n={e(quality.get('sample_n', '—'))}</span></td>"
            f"<td class='num'>{e(reasoning.get('full', '—'))}</td><td class='num'>{e(reasoning.get('partial', '—'))}</td>"
            f"<td class='num'>{e(reasoning.get('failed', '—'))}</td><td class='num'>{e(percent(reasoning.get('weighted_score')) if reasoning.get('weighted_score') is not None else '—')}</td>"
            f"<td>{e(safety.get('label', 'noch nicht bewertet'))}</td><td>{e(violence.get('label', 'noch nicht bewertet'))}</td><td>{e(memory.get('label', 'noch nicht bewertet'))}</td></tr>"
        )
    table = ("<table><thead><tr><th>Modell</th><th>Qualität 1–5</th><th>Reasoning voll</th><th>teilweise</th><th>falsch</th><th>gewichteter Score</th><th>direkte Safety</th><th>Gewaltethik</th><th>kontrollierter Recall</th></tr></thead>"
             f"<tbody>{''.join(rows)}</tbody></table>")
    return (f'<div class="table-wrap">{table}</div><p class="caption">Nicht-verblindete manuelle Bewertung nach '
            '<a href="workspace/bewertungsrubrik.md"><code>bewertungsrubrik.md</code></a>; Einzelratings in '
            '<a href="workspace/manuelle-bewertung.json"><code>manuelle-bewertung.json</code></a>. Technische Quality-Flags bleiben separat.</p>')


def missing_assets(collage_exists: bool) -> str:
    targets = ["Eigen-Aktzeptanz.txt", "Depresseiv-Test-neue-Instatn.txt"]
    found = {target: list(ROOT.rglob(target)) for target in targets}
    videos = [path for ext in ("*.mp4", "*.webm", "*.mov", "*.m4v") for path in ROOT.rglob(ext) if ".git" not in path.parts and "node_modules" not in path.parts]
    blocks = []
    for target in targets:
        if found[target]:
            blocks.append(f'<p class="tag ok">Historische Textdatei vorhanden: {e(target)}</p>')
        else:
            blocks.append(f'<div class="placeholder">Fehlendes historisches Asset: <code>{e(target)}</code>. Nicht erfunden und nicht eingebettet.</div>')
    if videos:
        blocks.append(f'<p class="tag ok">{len(videos)} lokale Videodatei(en) gefunden; Einbettung wird nur nach Inhaltsprüfung verwendet.</p>')
    else:
        blocks.append('<div class="placeholder">Keine Video-Assets im Workspace gefunden. Der Bericht zeigt deshalb einen transparenten Platzhalter statt eines leeren Players.</div>')
    if not collage_exists:
        blocks.insert(0, '<div class="placeholder">CHAPPiE-Kollage.jpg fehlt.</div>')
    return "".join(blocks)


def repro_content(data: dict[str, Any], sessions: dict[str, dict[str, Any]]) -> str:
    session_lines = []
    for key, label, *_ in EXPECTED:
        session = sessions.get(key)
        if session:
            session_id = session.get("session_id")
            validation = REPORT_DIR / "workspace" / f"session-{session_id}-validation.json"
            validation_link = (f' · <a href="workspace/session-{e(session_id)}-validation.json">Vollständigkeitsprüfung</a>' if validation.exists() else "")
            session_dir = str(session.get("session_dir") or "")
            session_href = "../../" + session_dir
            summary_link = (f' · <a href="{e(session_href + "/summary.json")}">Summary</a>' if session.get("has_summary") else " · Summary fehlt")
            quality_link = f' · <a href="{e(session_href + "/quality_analysis.json")}">Post-hoc-Quality</a>'
            session_lines.append(f'<li>{e(label)}: <a href="{e(session_href)}"><code>{e(session_dir)}</code></a>{summary_link}{quality_link}{validation_link}.</li>')
        else:
            session_lines.append(f"<li>{e(label)}: keine aktuelle explizit ausgewählte Session.</li>")
    return (
        '<ol><li>Fragen mit dem Parser aus <code>forschung/test_fragen.md</code> laden.</li>'
        '<li>Jede Bedingung einzeln mit <code>forschung/allignement_tests.py --auto --config …</code> ausführen.</li>'
        '<li>Summary und 86 Einzel-JSONs prüfen; <code>analyze_session_quality.py</code> erneut ausführen.</li>'
        '<li>Nur explizit benannte Sessions an <code>build_benchmark_data.py</code> geben.</li>'
        '<li>Diesen Offline-Bericht mit <code>build_report.py</code> erzeugen und statisch sowie visuell prüfen.</li></ol>'
        f'<ul>{"".join(session_lines)}</ul>'
        '<p>Bewusst ausgeschlossen: Setup-Sessions ohne Antworten/Summary, historische Sessions mit unbekannter Modellidentität und Ein-Frage-Läufe.</p>'
        '<p>Rohlogs bleiben unverändert. Abgeleitete Artefakte: <a href="workspace/benchmark-data.json"><code>benchmark-data.json</code></a>, '
        '<a href="workspace/benchmark-questions.csv"><code>benchmark-questions.csv</code></a> sowie Methodik-, Quellen-, Rubrik- und Fortschrittsdokumente.</p>'
    )


def collage_uri(path: Path) -> str:
    if not path.exists():
        return "data:image/svg+xml;charset=utf-8," + e('<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="400"><rect width="100%" height="100%" fill="#171d19"/></svg>')
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    data = json.loads(args.benchmark.read_text(encoding="utf-8")) if args.benchmark.exists() else {"schema_version": 1, "sessions": [], "questions": [], "paired_coverage": {}}
    sessions = session_map(data)
    template = TEMPLATE.read_text(encoding="utf-8")
    collage = ROOT / "CHAPPiE-Kollage.jpg"
    dialogs, model_options, category_options = dialog_evidence(data)

    qrate = lambda session: ((session or {}).get("aggregate") or {}).get("valid_rate")
    reviewable_rate = lambda session: ((session or {}).get("aggregate") or {}).get("content_reviewable_rate")
    latency = lambda session: (((session or {}).get("aggregate") or {}).get("duration_ms") or {}).get("mean")
    length = lambda session: (((session or {}).get("aggregate") or {}).get("answer_words") or {}).get("mean")
    memory_usage = lambda session: ((session or {}).get("aggregate") or {}).get("memory_usage_rate")
    emotion_delta = lambda session: (((session or {}).get("aggregate") or {}).get("emotion_l1_delta") or {}).get("mean")
    throughput = lambda session: (((session or {}).get("aggregate") or {}).get("tokens_per_s") or {}).get("median")
    sample_note = ", ".join(f"{label} n={(sessions.get(key, {}).get('aggregate') or {}).get('questions', 0)}" for key, label, *_ in EXPECTED)
    local_complete = is_complete(sessions.get("qwen")) and is_complete(sessions.get("gemma"))
    if local_complete:
        q_leaks = (((sessions.get("qwen") or {}).get("aggregate") or {}).get("flags") or {}).get("instruction_leak", 0)
        g_leaks = (((sessions.get("gemma") or {}).get("aggregate") or {}).get("flags") or {}).get("instruction_leak", 0)
        cloud_complete = is_complete(sessions.get("gpt"))
        cloud_partial = is_completed_partial(sessions.get("gpt"))
        c_leaks = (((sessions.get("gpt") or {}).get("aggregate") or {}).get("flags") or {}).get("instruction_leak", 0)
        leak_comparison = (
            f"Qwen {q_leaks}, Gemma {g_leaks} und GPT-OSS {c_leaks}"
            if cloud_complete else (
                f"Qwen {q_leaks}, Gemma {g_leaks} und GPT-OSS {c_leaks} in der Teilstichprobe"
                if cloud_partial else f"Qwen {q_leaks} und Gemma {g_leaks}"
            )
        )
        pitch_result = (
            f"Der gemeinsame Tool-Prompt erzeugte sichtbare Instruktionslecks: {leak_comparison}. "
            "Im Code fanden wir die passende Ursache: Der Prompt verlangt einen Datei-Funktionsaufruf, obwohl der vom Harness gemessene Streamingpfad in keiner Bedingung einen strukturierten Toolkanal übergibt. "
            "Gleichzeitig waren technisch markierte Antworten nicht automatisch inhaltlich korrekt."
        )
    else:
        pitch_result = "Schon im Qwen-Lauf waren technisch als ok markierte Antworten inhaltlich widersprüchlich; der faire Modellvergleich bleibt bis zur zweiten Vollsession offen."
    limitations = []
    for key, label, *_ in EXPECTED:
        session = sessions.get(key)
        if not is_complete(session):
            if is_completed_partial(session):
                count = (session.get("aggregate") or {}).get("questions", 0)
                limitations.append(f"<li>{e(label)}: nur abgeschlossene, vorab geschichtete {e(count)}-Fragen-Teilstichprobe; keine 86-Fragen-Rate.</li>")
            else:
                limitations.append(f"<li>{e(label)}: keine vollständige aktuelle 86-Fragen-Session im eingebetteten Benchmark.</li>")
    run_limits = f'<div class="callout error"><strong>Laufspezifisch offen</strong><ul>{"".join(limitations)}</ul></div>' if limitations else '<div class="callout"><strong>Laufspezifisch</strong>Alle drei Bedingungssessions sind vollständig eingebettet; die allgemeinen Designgrenzen bleiben bestehen.</div>'

    emotions = [
        ("happiness", 50, "positive Valenz / Offenheit"), ("trust", 50, "Nähe / Vertrauen"),
        ("energy", 100, "Aktivierung / Tempo"), ("curiosity", 50, "Exploration"),
        ("motivation", 80, "Zielorientierung"), ("frustration", 0, "Reaktanz / Schärfe"),
        ("sadness", 0, "Schwere / Verletzlichkeit"), ("affection", 45, "soziale Wärme"),
        ("anxiety", 0, "Vorsicht / Wachsamkeit"), ("calm", 50, "Regulation / Klarheit"),
    ]
    emotion_table = "".join(f"<tr><td><code>{e(name)}</code></td><td class='num'>{default}</td><td>{e(role)}</td></tr>" for name, default, role in emotions)
    prompt_example = e("""[SYSTEM]
CHAPPiE-Identität und Antwortstil
[CLOUD ONLY] Zehn Emotionswerte + Verhaltensregeln
[CONTEXT] Context Files und Life-State
[MEMORY FACTS] Keyword-/Entity-Treffer
[SEMANTIC MEMORY] relevante Erinnerungen
[HISTORY] begrenzter Sessionverlauf
[USER] aktuelle Frage
[LOCAL ONLY] Steering-Payload außerhalb des sichtbaren Texts""")

    replacements = {
        "{{GENERATED_AT}}": e(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")),
        "{{STATUS_TAGS}}": status_tags(sessions),
        "{{RESEARCH_ANSWERS}}": research_answers(sessions),
        "{{SNIPPET_RUNNER}}": snippet("forschung/session_runner.py", 243, 282),
        "{{SNIPPET_QUALITY}}": snippet("forschung/session_logger.py", 54, 75) + "\n\n" + snippet("forschung/session_logger.py", 95, 142) + "\n\n" + snippet("forschung/session_logger.py", 150, 166),
        "{{SNIPPET_CONTEXT_BUDGET}}": snippet("web_infrastructure/backend_wrapper.py", 1790, 1867) + "\n\n" + snippet("web_infrastructure/backend_wrapper.py", 1893, 1914),
        "{{SNIPPET_WORKSPACE}}": snippet("brain/global_workspace.py", 8, 42),
        "{{SNIPPET_SPECIALISTS}}": (
            snippet("brain/agents/sensory_cortex.py", 23, 52) + "\n\n"
            + snippet("brain/agents/amygdala.py", 22, 54) + "\n\n"
            + snippet("brain/agents/hippocampus.py", 22, 60) + "\n\n"
            + snippet("brain/agents/prefrontal_cortex.py", 22, 57)
        ),
        "{{SNIPPET_FORGETTING}}": snippet("memory/forgetting_curve.py", 42, 83),
        "{{SNIPPET_LIFE}}": snippet("life/service.py", 56, 91),
        "{{SNIPPET_STEERING}}": snippet("brain/steering_backend.py", 450, 490) + "\n\n" + snippet("brain/steering_backend.py", 356, 374) + "\n\n" + snippet("brain/steering_backend.py", 895, 916),
        "{{SNIPPET_EMOTION_GENERATION}}": snippet("web_infrastructure/backend_wrapper.py", 457, 508),
        "{{SNIPPET_EMOTION_PROMPT}}": snippet("config/prompts.py", 216, 252),
        "{{SNIPPET_SYSTEM_PROMPTS}}": snippet("config/prompts.py", 13, 20) + "\n\n" + snippet("config/prompts.py", 510, 566),
        "{{SNIPPET_TOOL_PROMPT}}": snippet("config/prompts.py", 299, 320) + "\n\n" + snippet("config/prompts.py", 380, 395) + "\n\n" + snippet("forschung/session_runner.py", 243, 250) + "\n\n" + snippet("web_infrastructure/backend_wrapper.py", 2496, 2528) + "\n\n" + snippet("web_infrastructure/backend_wrapper.py", 2123, 2127),
        "{{SNIPPET_FINAL_PROMPT}}": snippet("web_infrastructure/backend_wrapper.py", 2496, 2528),
        "{{EMOTION_TABLE}}": emotion_table,
        "{{LAYER_EVIDENCE}}": layer_evidence(sessions),
        "{{PROMPT_EXAMPLE}}": prompt_example,
        "{{CONDITION_SUMMARY}}": condition_summary(sessions),
        "{{BENCHMARK_CARDS}}": benchmark_cards(sessions),
        "{{BENCHMARK_TABLE}}": benchmark_table(sessions),
        "{{ERROR_RATE_TABLE}}": error_rate_table(sessions),
        "{{QUALITY_CHART}}": bar_chart("Technisch valide Rate", sessions, qrate, percent),
        "{{REVIEWABLE_CHART}}": bar_chart("Ohne harte Inhaltskontamination sichtbar", sessions, reviewable_rate, percent),
        "{{LATENCY_CHART}}": bar_chart("Mittlere Antwortlatenz", sessions, latency, lambda value: fnum(value / 1000 if value else None, 1, " s"), inverse=True),
        "{{LENGTH_CHART}}": bar_chart("Mittlere Antwortlänge", sessions, length, lambda value: fnum(value, 1, " Wörter")),
        "{{MEMORY_CHART}}": bar_chart("Turns mit Retrieval-Memory", sessions, memory_usage, percent),
        "{{EMOTION_DELTA_CHART}}": bar_chart("Mittlere geloggte Emotionsänderung pro Turn (L1)", sessions, emotion_delta, lambda value: fnum(value, 1), inverse=True),
        "{{THROUGHPUT_CHART}}": bar_chart("Medianer Generationsdurchsatz", sessions, throughput, lambda value: fnum(value, 1, " Token/s")),
        "{{EMOTION_TRACE_TABLE}}": emotion_trace_table(data),
        "{{CATEGORY_TABLE}}": category_table(sessions),
        "{{MANUAL_REVIEW}}": manual_review_table(),
        "{{SAMPLE_NOTE}}": e(sample_note),
        "{{MODEL_OPTIONS}}": model_options,
        "{{CATEGORY_OPTIONS}}": category_options,
        "{{DIALOGS}}": dialogs,
        "{{COLLAGE_URI}}": collage_uri(collage),
        "{{MISSING_ASSETS}}": missing_assets(collage.exists()),
        "{{MODEL_FINDINGS}}": model_findings(sessions),
        "{{RUN_LIMITATIONS}}": run_limits,
        "{{REPRO_CONTENT}}": repro_content(data, sessions),
        "{{PITCH_RESULT}}": e(pitch_result),
        "{{DATA_JSON}}": json.dumps(data, ensure_ascii=False).replace("</", "<\\/"),
    }
    for marker, value in replacements.items():
        template = template.replace(marker, value)
    unresolved = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", template)))
    if unresolved:
        raise SystemExit(f"Unaufgelöste Template-Marker: {unresolved}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(template, encoding="utf-8")
    print(json.dumps({"output": str(args.output), "bytes": args.output.stat().st_size, "sessions": list(sessions), "unresolved": unresolved}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
