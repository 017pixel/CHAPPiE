"""Render full terminal diagnostics at narrow and desktop widths."""
import io
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rich.console import Console, Group
from rich.table import Table
from cli.report import emotion_panel, timing_panel, steering_panel, runtime_panel, responsive_report
from config.emotions import EMOTION_ORDER

def main():
    result = {"session_id": "test-session", "model": "Qwen/Qwen3.5-4B", "provider": "vllm",
              "runtime_settings": {"memory_enabled": False, "steering_enabled": True, "steering_mode": "activation", "live_enabled": False},
              "emotions": {name: 50 for name in EMOTION_ORDER},
              "emotions_before": {name: 40 for name in EMOTION_ORDER},
              "emotions_delta": {"frustration": {"applied_delta": 10, "reason": "Anhaltende Frustration"}},
              "emotion_steering": {"active_vectors": [{"name": "frustration", "strength": .2, "source": "acute_delta", "layer_range": [15, 19]}]},
              "steering_runtime": {"ablation_mode": "activation", "hook_count": 2, "sequence_processor_count": 0},
              "timing": {"intent_ms": 123, "generation_ms": 4567, "generation_ttft_ms": None, "total_ms": 5000}}
    for width in (60, 80, 119, 120, 160):
        left = [runtime_panel(result), timing_panel(result)]
        right = [steering_panel(result), emotion_panel(result)]
        report = responsive_report(left, right, width)
        assert isinstance(report, Group if width < 120 else Table)
        output = io.StringIO()
        console = Console(file=output, width=width, color_system=None)
        console.print(report)
        text = output.getvalue()
        assert all(len(line) <= width for line in text.splitlines())
        for name in EMOTION_ORDER:
            assert name in text
        assert "123.0 ms" in text and "4567.0 ms" in text
        assert "nicht gemessen" in text
    print("Two-column report: widths 60, 80, 119, 120, 160 passed")
if __name__ == "__main__":
    main()
