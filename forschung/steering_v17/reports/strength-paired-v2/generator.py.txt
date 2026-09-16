"""Export reproducible sweep figures; missing ratings remain visibly missing."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from statistics import median

import numpy as np


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(run, metrics_path, output):
    if output.exists() and any(output.iterdir()):
        raise ValueError("Figure output already contains evidence; choose a new directory")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm, ListedColormap

    metrics = json.loads(metrics_path.read_text())
    generations = run / "generations.jsonl"
    if metrics.get("generations_sha256") != digest(generations):
        raise ValueError("Figure input generations differ from ranked evidence")
    rows = [json.loads(line) for line in generations.read_text().splitlines() if line.strip()]
    manifest = json.loads((run / "manifest.json").read_text())
    configured = manifest["configurations"]
    layers = sorted({layers[0] for layers, _ in configured if len(layers) == 1})
    strengths = sorted({strength for layers, strength in configured if len(layers) == 1})
    if not layers:
        raise ValueError("Heatmaps require single-layer configurations")
    emotion = np.full((len(layers), len(strengths)), np.nan)
    ratios = emotion.copy()
    paired = metrics.get("ranking_method", "").startswith("paired_")
    field = "emotion_change_vs_off" if paired else "emotion_expression"
    for row in metrics["ranking"]:
        if len(row["layers"]) == 1:
            emotion[layers.index(row["layers"][0]), strengths.index(row["strength"])] = row[field]
    latest = {(tuple(row["layers"]), row["strength"], row["case_id"], row.get("seed", row.get("request", {}).get("seed", 42))): row for row in rows}
    for layer in layers:
        for strength in strengths:
            values = []
            for row in latest.values():
                if row["layers"] != [layer] or row["strength"] != strength or "error" in row:
                    continue
                value = row["response"].get("chappie_steering", {}).get("layer_measurements", {}).get(str(layer), {}).get("intervention_rms_ratio")
                if isinstance(value, (float, int)) and np.isfinite(value):
                    values.append(value * 100)
            if values:
                ratios[layers.index(layer), strengths.index(strength)] = median(values)
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "svg.hashsalt": "chappie-v17-research", "axes.spines.top": False,
                         "axes.spines.right": False})

    def heatmap(matrix, stem, title, label, bounds, colors):
        fig, ax = plt.subplots(figsize=(8.4, max(3.8, len(layers) * .46)), layout="constrained")
        palette = ListedColormap(colors)
        palette.set_bad("#dedede")
        im = ax.imshow(np.ma.masked_invalid(matrix), cmap=palette,
                       norm=BoundaryNorm(bounds, palette.N), aspect="auto", interpolation="nearest")
        ax.set_xticks(range(len(strengths)), [f"{value:g}" for value in strengths])
        ax.set_yticks(range(len(layers)), [str(layer) for layer in layers])
        ax.set_xlabel("Rohe Stärke α")
        ax.set_ylabel("Decoder-Layer, nullbasiert")
        ax.set_title(title, loc="left", pad=15)
        for i in range(len(layers)):
            for j in range(len(strengths)):
                value = matrix[i, j]
                text = "n. b." if not np.isfinite(value) else f"{value:.2f}"
                ax.text(j, i, text, ha="center", va="center", fontsize=9, color="#111111",
                        bbox={"facecolor": "white", "alpha": .8, "edgecolor": "none", "pad": 1})
        fig.colorbar(im, ax=ax, label=label, shrink=.85)
        fig.text(.01, -.015, "Vorläufige Forschung. n. b. = nicht vollständig bewertet; keine Produktionsfreigabe.", fontsize=8)
        for extension in ("svg", "png"):
            fig.savefig(output / f"{stem}.{extension}", dpi=180, bbox_inches="tight",
                        metadata={"Date": None} if extension == "svg" else {})
        plt.close(fig)

    heatmap(emotion, "emotion-transfer", "Zusätzliche sichtbare Frustration gegenüber OFF" if paired else "Sichtbare Frustration, ohne gepaarten OFF-Abzug",
            "Differenz auf Skala 0 bis 1" if paired else "Mittlere Bewertung / 4",
            [-1, -.1, -.001, .001, .1, 1.0001] if paired else [0, .1, .25, .5, .75, 1.0001],
            ["#9c5143", "#d8aea0", "#f3eee5", "#b6c2a7", "#547247"] if paired else ["#f7f4ed", "#ddd3ba", "#b69a5d", "#826536", "#493b26"])
    maximum = max(1, float(np.nanmax(ratios))) if np.isfinite(ratios).any() else 1
    heatmap(ratios, "intervention-rms", "Physikalische Dosis im ersten Hook-Aufruf",
            "Median Intervention-RMS / Hidden-State-RMS (%)",
            np.linspace(0, maximum + .001, 6), ["#f7f4ed", "#ddd3ba", "#b69a5d", "#826536", "#493b26"])
    def serial(matrix):
        return [[float(value) if np.isfinite(value) else None for value in row] for row in matrix]
    data = {"layers": layers, "strengths": strengths, "emotion_field": field,
            "emotion": serial(emotion), "intervention_rms_ratio_percent_median": serial(ratios),
            "rms_scope": "first hook invocation per generation, median across cases/seeds"}
    (output / "plot_data.json").write_text(json.dumps(data, indent=2) + "\n")
    (output / "generator.py.txt").write_bytes(Path(__file__).read_bytes())
    evidence = {"generations_sha256": digest(generations), "metrics_sha256": digest(metrics_path),
                "run_manifest_sha256": digest(run / "manifest.json"), "generator_sha256": digest(Path(__file__)),
                "matplotlib_version": matplotlib.__version__, "production_acceptance": False,
                "files": {path.name: digest(path) for path in sorted(output.iterdir()) if path.is_file() and path.name != "plot_manifest.json"}}
    (output / "plot_manifest.json").write_text(json.dumps(evidence, indent=2) + "\n")
    return evidence


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.run, args.metrics, args.output), indent=2))
