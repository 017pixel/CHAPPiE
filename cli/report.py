"""Responsive Rich report composition using measured turn metadata."""
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from config.emotions import EMOTION_ORDER
from config.config import CLI_INTERACTION_CONFIG

TIMING_LABELS = (
    ("intent_ms", "Intent"), ("emotion_appraisal_ms", "Emotion"),
    ("memory_retrieval_ms", "Memory retrieval"), ("memory_context_build_ms", "Memory context"),
    ("steering_plan_ms", "Steering"), ("generation_ttft_ms", "TTFT"),
    ("generation_ms", "Generation"), ("formatting_ms", "Formatting"),
    ("persistence_ms", "Persist"), ("background_jobs_scheduled_ms", "Background scheduling"),
    ("total_ms", "Total"),
)

def timing_panel(result):
    timing = result.get("timing", {})
    aliases = {"generation_ttft_ms": "ttft_ms", "generation_ms": "total_gen_ms"}
    table = Table.grid(padding=(0, 1), expand=True)
    table.add_column(ratio=2)
    table.add_column(justify="right", ratio=1)
    for key, label in TIMING_LABELS:
        value = timing.get(key, timing.get(aliases.get(key, "")))
        if key == "total_ms" and value is None:
            value = result.get("processing_time_ms")
        table.add_row(label, f"{value:.1f} ms" if isinstance(value, (float, int)) else "nicht gemessen")
    # V18: finale Tokenizer-Tokens und echte Laengenbegrenzung sichtbar.
    answer_tokens = timing.get("answer_tokens")
    if isinstance(answer_tokens, (int, float)):
        table.add_row("Final Tokens", f"a:{int(answer_tokens)}tk")
    finish = timing.get("finish_reason", result.get("finish_reason", ""))
    if finish:
        table.add_row("Finish", str(finish))
    return Panel(table, title="Timing (Final)", border_style="blue")

def emotion_panel(result):
    after, before = result.get("emotions", {}), result.get("emotions_before", {})
    if not after:
        return None
    steering = result.get("emotion_steering", {})
    vectors = {item.get("name"): item for item in steering.get("active_vectors", []) if isinstance(item, dict)}
    transitions = result.get("emotions_delta", {})
    table = Table(box=box.SIMPLE, expand=True, padding=(0, 1))
    for label in ("Emotion", "Wert", "Delta", "Alpha", "Quelle", "Grund"):
        table.add_column(label, overflow="fold", min_width=11 if label == "Emotion" else None,
                         no_wrap=label == "Emotion")
    for name in EMOTION_ORDER:
        value = after.get(name)
        if value is None:
            continue
        transition = transitions.get(name, {})
        transition = transition if isinstance(transition, dict) else {"applied_delta": transition}
        delta = transition.get("applied_delta", value - before.get(name, value))
        vector = vectors.get(name, {})
        alpha = vector.get("strength", vector.get("alpha"))
        direction = -1 if vector.get("direction") == "negative" else 1
        table.add_row(name, str(value), f"{delta:+g}",
                      f"{direction * alpha:+.2f}" if isinstance(alpha, (int, float)) else "",
                      Text(str(vector.get("source", ""))), Text(str(transition.get("reason", ""))))
    return Panel(table, title="Emotionen", border_style="yellow")

def steering_panel(result):
    planned = result.get("emotion_steering", {})
    actual = result.get("steering_runtime", {}) or {}
    runtime = result.get("runtime_settings", {})
    if not planned and not actual and not runtime:
        return None
    mode = actual.get("ablation_mode", planned.get("ablation_mode", runtime.get("steering_mode", "unbekannt")))
    if runtime.get("steering_enabled") is False:
        mode = "off"
    dominant = planned.get("dominant_vector", "neutral")
    dominant_strength = planned.get("dominant_strength", 0.0)
    lines = [f"Mode: {mode}",
             f"Activation hooks: {actual.get('registered_hooks', actual.get('hook_count', 'nicht gemessen'))}",
             f"Sequence processors: {actual.get('sequence_processor_count', 'nicht gemessen')}",
             f"Dominant: {dominant} ({dominant_strength:.2f})"]
    fmt_source = result.get("formatting_source", "")
    fmt_model = result.get("formatting_model", "")
    fmt_reason = result.get("formatting_reason", result.get("formatting_skip_reason", ""))
    if fmt_source or fmt_model or fmt_reason:
        lines.append(f"Format: {fmt_source} {fmt_model} Grund: {fmt_reason}".strip())
    for vector in planned.get("active_vectors", []):
        lines.append(f"{vector.get('name', '?')}: alpha {vector.get('alpha', vector.get('strength', '?'))}; Layer {vector.get('layer_range', vector.get('layers', '?'))}")
    for sequence in planned.get("sequence_specs", []):
        lines.append(f"Sequence {sequence.get('concept', '?')}: Fenster {sequence.get('start_token', 0)} bis {sequence.get('end_token', '?')}, Bias {sequence.get('max_logit_bias', '?')}")
    for layer, measured in (actual.get("layer_measurements", {}) or {}).items():
        lines.append(f"Layer {layer}: RMS-Verhältnis {measured.get('intervention_rms_ratio', '?')}")
    return Panel(Text("\n".join(lines)), title="Steering Report", border_style="red")

def runtime_panel(result):
    state = result.get("runtime_settings", {})
    text = f"Session: {result.get('session_id', '?')}\n{result.get('provider', '?')}/{result.get('model', '?')}"
    if state:
        text += f"\nMemory: {'an' if state.get('memory_enabled') else 'aus'}; Live: {'an' if state.get('live_enabled') else 'aus'}"
    return Panel(Text(text), title="Turn / Runtime", border_style="blue")

def responsive_report(left, right, width):
    left = [panel for panel in left if panel is not None]
    right = [panel for panel in right if panel is not None]
    if width < CLI_INTERACTION_CONFIG["two_column_min_width"]:
        return Group(*left, *right)
    table = Table.grid(expand=True, padding=(0, 1))
    table.add_column(ratio=1)
    table.add_column(ratio=1)
    table.add_row(Group(*left), Group(*right))
    return table
