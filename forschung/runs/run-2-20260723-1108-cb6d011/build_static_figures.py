#!/usr/bin/env python3
"""Generate offline SVG figures from current CHAPPiE code-derived data."""

from __future__ import annotations

import html
import json
import math
from pathlib import Path

from config.emotions import EMOTION_DEFINITIONS
from memory.forgetting_curve import EbbinghausForgettingCurve


RUN_DIR = Path(__file__).resolve().parent
OUT = RUN_DIR / "figures"
OUT.mkdir(parents=True, exist_ok=True)

BG = "#1e1e1e"
GRID = "#343434"
TEXT = "#eeeeee"
MUTED = "#a8a8a8"
SAGE = "#8fae96"
INFO = "#718ca8"
WARN = "#b59a5c"


def svg_shell(title: str, desc: str, width: int, height: int, body: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc" viewBox="0 0 {width} {height}">
  <title id="title">{html.escape(title)}</title>
  <desc id="desc">{html.escape(desc)}</desc>
  <rect width="{width}" height="{height}" fill="{BG}" rx="8"/>
  <style>
    text {{ font-family: Inter, system-ui, sans-serif; fill: {TEXT}; }}
    .muted {{ fill: {MUTED}; font-size: 12px; }}
    .label {{ fill: {MUTED}; font-size: 11px; }}
  </style>
  {body}
</svg>
"""


def build_forgetting() -> dict:
    curve = EbbinghausForgettingCurve()
    times = [0, 20 / 60, 1, 3, 9, 24, 48, 72, 144, 336, 744]
    strengths = [1.0, 2.0, 4.0]
    data = {
        "source": "memory/forgetting_curve.py",
        "kind": "implemented_code_model_not_observed_agent_memory",
        "series": {
            str(strength): [
                {"hours": hour, "retention": curve.calculate_retention(hour, strength)}
                for hour in times
            ]
            for strength in strengths
        },
    }
    (OUT / "forgetting-curve.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    width, height = 820, 390
    left, top, plot_w, plot_h = 68, 44, 704, 270
    max_log = math.log10(745)
    def x(hour: float) -> float:
        return left + math.log10(hour + 1) / max_log * plot_w
    def y(retention: float) -> float:
        return top + (1 - retention) * plot_h
    grid = []
    for value in (0, .25, .5, .75, 1):
        yy = y(value)
        grid.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{left+plot_w}" y2="{yy:.1f}" stroke="{GRID}"/>')
        grid.append(f'<text class="label" x="{left-12}" y="{yy+4:.1f}" text-anchor="end">{int(value*100)}%</text>')
    for hour, label in ((0, "0"), (1, "1 h"), (24, "1 d"), (144, "6 d"), (744, "31 d")):
        xx = x(hour)
        grid.append(f'<line x1="{xx:.1f}" y1="{top}" x2="{xx:.1f}" y2="{top+plot_h}" stroke="{GRID}"/>')
        grid.append(f'<text class="label" x="{xx:.1f}" y="{top+plot_h+22}" text-anchor="middle">{label}</text>')
    colors = {1.0: SAGE, 2.0: INFO, 4.0: WARN}
    paths = []
    for index, strength in enumerate(strengths):
        points = " ".join(
            f"{x(item['hours']):.1f},{y(item['retention']):.1f}"
            for item in data["series"][str(strength)]
        )
        paths.append(f'<polyline points="{points}" fill="none" stroke="{colors[strength]}" stroke-width="2.5"/>')
        paths.append(f'<text class="muted" x="{left+12+index*170}" y="356" fill="{colors[strength]}">Stärke {strength:g}</text>')
    body = (
        f'<text x="{left}" y="26" font-size="16" font-weight="600">Implementierte Vergessenskurve</text>'
        + "".join(grid + paths)
        + f'<text class="label" x="{left+plot_w}" y="378" text-anchor="end">Quelle: memory/forgetting_curve.py · keine Run-Messung</text>'
    )
    (OUT / "forgetting-curve.svg").write_text(
        svg_shell(
            "Implementierte CHAPPiE-Vergessenskurve",
            "Retention über logarithmische Zeit für drei Memory-Stärken. Code-Modell, keine beobachtete Agentenerinnerung.",
            width,
            height,
            body,
        ),
        encoding="utf-8",
    )
    return data


def build_vad() -> dict:
    data = {
        "source": "config/emotions.py",
        "kind": "configured_synthetic_vad_map",
        "emotions": [
            {
                "key": item["key"],
                "label": item["label_de"],
                **item["vad"],
                "default": item["default"],
                "max_alpha": item["max_alpha"],
            }
            for item in EMOTION_DEFINITIONS
        ],
    }
    (OUT / "emotion-vad.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    width, height = 720, 500
    left, top, size = 82, 58, 360
    def px(value: float) -> float:
        return left + (value + 1) / 2 * size
    def py(value: float) -> float:
        return top + (1 - (value + 1) / 2) * size
    body = [
        f'<text x="{left}" y="28" font-size="16" font-weight="600">Konfigurierte VAD-Landkarte</text>',
        f'<rect x="{left}" y="{top}" width="{size}" height="{size}" fill="none" stroke="{GRID}"/>',
        f'<line x1="{px(0)}" y1="{top}" x2="{px(0)}" y2="{top+size}" stroke="{GRID}"/>',
        f'<line x1="{left}" y1="{py(0)}" x2="{left+size}" y2="{py(0)}" stroke="{GRID}"/>',
        f'<text class="label" x="{left+size/2}" y="{top+size+32}" text-anchor="middle">Valenz −1 … +1</text>',
        f'<text class="label" transform="translate(28 {top+size/2}) rotate(-90)" text-anchor="middle">Arousal −1 … +1</text>',
    ]
    legend_y = 74
    for index, item in enumerate(data["emotions"]):
        xx, yy = px(item["valence"]), py(item["arousal"])
        radius = 4 + float(item["max_alpha"]) * 5
        body.append(f'<circle cx="{xx:.1f}" cy="{yy:.1f}" r="{radius:.1f}" fill="{SAGE}" opacity=".82"><title>{html.escape(item["label"])} · Dominanz {item["dominance"]:+.2f}</title></circle>')
        body.append(f'<text class="label" x="{xx+9:.1f}" y="{yy+4:.1f}">{html.escape(item["label"])}</text>')
        body.append(f'<text class="muted" x="500" y="{legend_y+index*32}">{html.escape(item["label"])}</text>')
        body.append(f'<text class="label" x="640" y="{legend_y+index*32}" text-anchor="end">D {item["dominance"]:+.2f}</text>')
    body.append(f'<text class="label" x="{width-28}" y="{height-18}" text-anchor="end">Quelle: config/emotions.py · synthetische Konfiguration</text>')
    (OUT / "emotion-vad.svg").write_text(
        svg_shell(
            "Konfigurierte VAD-Landkarte",
            "Zehn CHAPPiE-Emotionen auf Valenz und Arousal; Dominanz in der Legende. Synthetische Konfiguration.",
            width,
            height,
            "".join(body),
        ),
        encoding="utf-8",
    )
    return data


def build_architecture() -> None:
    width, height = 940, 250
    labels = [
        ("Input", "API / SSE"),
        ("State", "Intent · Emotion · Life"),
        ("Memory", "semantisch + Keyword"),
        ("Modell", "Prompt oder Layer"),
        ("Safety", "Parser · Sanitizer"),
        ("Antwort", "gepuffert sichtbar"),
    ]
    body = [f'<text x="42" y="30" font-size="16" font-weight="600">Tatsächlich gemessener Web-Streamingpfad</text>']
    x = 42
    for index, (title, note) in enumerate(labels):
        body.append(f'<rect x="{x}" y="78" width="130" height="82" rx="6" fill="#232323" stroke="{GRID}"/>')
        body.append(f'<text x="{x+14}" y="107" font-size="14" font-weight="600">{title}</text>')
        body.append(f'<text class="label" x="{x+14}" y="132">{note}</text>')
        if index < len(labels) - 1:
            body.append(f'<line x1="{x+130}" y1="119" x2="{x+150}" y2="119" stroke="{SAGE}" stroke-width="2"/>')
            body.append(f'<path d="M{x+145} 114 L{x+150} 119 L{x+145} 124" fill="none" stroke="{SAGE}" stroke-width="2"/>')
        x += 150
    body.append(f'<text class="muted" x="42" y="205">BrainPipeline ist konzeptionell/alternativ; aktuelle Session-Logs messen backend_wrapper.process_stream.</text>')
    body.append(f'<text class="label" x="898" y="230" text-anchor="end">Quelle: api/routers/chat.py · web_infrastructure/backend_wrapper.py</text>')
    (OUT / "architecture-flow.svg").write_text(
        svg_shell(
            "Gemessener CHAPPiE-Webpfad",
            "Input fließt über State, Memory, Modell und Safety-Puffer zur sichtbaren Antwort.",
            width,
            height,
            "".join(body),
        ),
        encoding="utf-8",
    )


def build_layers() -> None:
    width, height = 820, 250
    profiles = [
        ("Qwen 3.5 4B", 32, (10, 26), SAGE),
        ("Gemma 4 E4B", 42, (12, 30), INFO),
    ]
    body = [f'<text x="56" y="30" font-size="16" font-weight="600">Nominale Modellprofile</text>']
    for row, (label, total, bounds, color) in enumerate(profiles):
        y = 82 + row * 72
        x0, w = 190, 560
        body.append(f'<text class="muted" x="56" y="{y+18}">{label}</text>')
        body.append(f'<rect x="{x0}" y="{y}" width="{w}" height="24" rx="4" fill="#2a2a2a"/>')
        start = x0 + bounds[0] / total * w
        active_w = (bounds[1] - bounds[0]) / total * w
        body.append(f'<rect x="{start:.1f}" y="{y}" width="{active_w:.1f}" height="24" rx="4" fill="{color}" opacity=".76"/>')
        body.append(f'<text class="label" x="{x0}" y="{y+44}">L0</text>')
        body.append(f'<text class="label" x="{x0+w}" y="{y+44}" text-anchor="end">L{total-1}</text>')
        body.append(f'<text x="{start+active_w/2:.1f}" y="{y+17}" text-anchor="middle" font-size="11">L{bounds[0]}–{bounds[1]}</text>')
    body.append(f'<text class="label" x="764" y="230" text-anchor="end">Session 33 zeigt tatsächliche Gemma-Vektoren bis L40 → separates Issue</text>')
    (OUT / "layer-profiles.svg").write_text(
        svg_shell(
            "Nominale Layerprofile von Qwen und Gemma",
            "Qwen nominal L10 bis 26, Gemma nominal L12 bis 30. Tatsächliche Run-2-Payloads werden separat geprüft.",
            width,
            height,
            "".join(body),
        ),
        encoding="utf-8",
    )


def main() -> None:
    build_forgetting()
    build_vad()
    build_architecture()
    build_layers()
    print("SVG-Figuren erzeugt:", ", ".join(path.name for path in sorted(OUT.glob("*.svg"))))


if __name__ == "__main__":
    main()
