"""Tests for CLI v6.0 display helpers: panels, rendrers, data formatters."""

import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

import importlib

from unittest.mock import MagicMock

for mod in (
    "chromadb", "chromadb.config", "requests", "openai",
    "brain.nvidia_brain", "brain.steering_api_server",
    "brain.steering_backend", "brain.deep_think",
    "brain.global_workspace", "brain.action_response",
    "brain.response_parser", "brain.agents",
    "life", "memory", "memory.memory_engine",
    "memory.emotions_engine", "memory.sleep_phase",
    "memory.forgetting_curve", "memory.context_files",
    "memory.chat_manager", "memory.short_term_memory",
    "memory.short_term_memory_v2", "memory.personality_manager",
    "memory.function_registry", "memory.intent_processor",
    "memory.debug_logger", "sentence_transformers",
):
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()
sys.modules["ollama"] = MagicMock()


def _get_module():
    sys.modules.pop("chappie_brain_cli", None)
    return importlib.import_module("chappie_brain_cli")


# ── bar helper ───────────────────────────────────────────────────

def test_bar_full():
    m = _get_module()
    assert m._bar(100, 100, 20) == "\u2588" * 20


def test_bar_empty():
    m = _get_module()
    assert m._bar(0, 100, 20) == "\u2591" * 20


def test_bar_mid():
    m = _get_module()
    result = m._bar(30, 100, 10)
    assert result.count("\u2588") == 3
    assert result.count("\u2591") == 7


def test_bar_over_max():
    m = _get_module()
    result = m._bar(150, 100, 10)
    assert result == "\u2588" * 15


# ── emoji color ──────────────────────────────────────────────────

def test_emo_color_green_boundary():
    m = _get_module()
    assert m._emo_color(60) == "green"


def test_emo_color_yellow_boundary():
    m = _get_module()
    assert m._emo_color(30) == "yellow"


def test_emo_color_red():
    m = _get_module()
    assert m._emo_color(5) == "red"


# ── emoji delta ──────────────────────────────────────────────────

def test_emoji_delta_increase():
    m = _get_module()
    assert m._emoji_delta(20, 50) == "↑+30"


def test_emoji_delta_decrease():
    m = _get_module()
    assert m._emoji_delta(80, 30) == "↓-50"


def test_emoji_delta_unchanged():
    m = _get_module()
    assert m._emoji_delta(50, 50) == " →"


# ── remote_meta_to_result ────────────────────────────────────────

def test_remote_meta_to_result_maps_core_fields():
    m = _get_module()
    metadata = {
        "content": "Hallo",
        "formatted_cot": "CoT text",
        "formatted_answer": "Answer text",
        "intent_type": "casual_chat",
        "intent_confidence": 0.85,
        "selected_tools": ["tool_a"],
        "emotions": {"happiness": 66},
        "emotions_before": {"happiness": 63},
        "emotion_steering": {"dominant_vector": "curiosity"},
        "processing_time_ms": 1234,
        "provider": "vllm",
        "model": "qwen",
    }
    result = m.CHAPPiEBrainCLI._remote_meta_to_result(metadata)
    assert result["response_text"] == "Hallo"
    assert result["formatted_cot"] == "CoT text"
    assert result["formatted_answer"] == "Answer text"
    assert result["intent_type"] == "casual_chat"
    assert result["intent_confidence"] == 0.85
    assert result["selected_tools"] == ["tool_a"]
    assert result["emotions"] == {"happiness": 66}
    assert result["emotions_before"] == {"happiness": 63}
    assert result["emotion_steering"]["dominant_vector"] == "curiosity"
    assert result["processing_time_ms"] == 1234
    assert result["provider"] == "vllm"
    assert result["model"] == "qwen"


def test_remote_meta_to_result_defaults():
    m = _get_module()
    result = m.CHAPPiEBrainCLI._remote_meta_to_result({})
    assert result["response_text"] == ""
    assert result["formatted_cot"] == ""
    assert result["intent_type"] == "?"
    assert result["emotions"] == {}
    assert result["selected_tools"] == []
    assert result["processing_time_ms"] == 0


# ── panel emotions ───────────────────────────────────────────────

def _rich_only():
    m = _get_module()
    if not m.HAS_RICH:
        return None
    return m


def test_panel_emotions_shows_deltas():
    m = _rich_only()
    if m is None:
        return
    result = {
        "emotions_before": {"happiness": 50, "trust": 40, "energy": 70},
        "emotions": {"happiness": 55, "trust": 38, "energy": 70},
    }
    panel = m.CHAPPiEBrainCLI._panel_emotions(result)
    assert panel is not None


def test_panel_emotions_none_when_empty():
    m = _get_module()
    assert m.CHAPPiEBrainCLI._panel_emotions({}) is None


# ── panel tools ──────────────────────────────────────────────────

def test_panel_tools_none_when_no_tools():
    m = _get_module()
    assert m.CHAPPiEBrainCLI._panel_tools({}) is None


def test_panel_tools_shows_selected():
    m = _rich_only()
    if m is None:
        return
    result = {
        "available_tools": ["a", "b", "c", "d"],
        "selected_tools": ["a", "b"],
        "unused_tools": ["c", "d"],
        "tool_calls_executed": 2,
    }
    panel = m.CHAPPiEBrainCLI._panel_tools(result)
    assert panel is not None


# ── panel timing ─────────────────────────────────────────────────

def test_panel_timing_with_data():
    m = _rich_only()
    if m is None:
        return
    result = {
        "timing": {"ttft_ms": 100, "total_gen_ms": 500, "total_tokens": 50},
        "processing_time_ms": 800,
    }
    panel = m.CHAPPiEBrainCLI._panel_timing(result)
    assert panel is not None


def test_panel_timing_fallback():
    m = _rich_only()
    if m is None:
        return
    result = {"processing_time_ms": 900}
    panel = m.CHAPPiEBrainCLI._panel_timing(result)
    assert panel is not None


# ── panel steering ───────────────────────────────────────────────

def test_panel_steering_with_vectors():
    m = _rich_only()
    if m is None:
        return
    result = {
        "emotion_steering": {
            "steering_active": True,
            "dominant_vector": "curiosity",
            "dominant_strength": 0.72,
            "active_vectors": [
                {"name": "curiosity", "alpha": 0.5},
                {"name": "energy", "alpha": 0.3},
            ],
        },
        "prompt_emotion_mode": "local_layer_only",
    }
    panel = m.CHAPPiEBrainCLI._panel_steering(result)
    assert panel is not None


def test_panel_steering_none_when_empty():
    m = _get_module()
    assert m.CHAPPiEBrainCLI._panel_steering({}) is None


# ── panel tone ───────────────────────────────────────────────────

def test_panel_tone_displays():
    m = _rich_only()
    if m is None:
        return
    result = {
        "tone_decision": {
            "tone": "warm_open",
            "tone_reason": "Hohes Vertrauen",
            "tone_drivers": [{"signal": "happiness", "value": 75}],
        },
    }
    panel = m.CHAPPiEBrainCLI._panel_tone(result)
    assert panel is not None


def test_panel_tone_none():
    m = _get_module()
    assert m.CHAPPiEBrainCLI._panel_tone({}) is None


# ── panel workspace ──────────────────────────────────────────────

def test_panel_workspace_shows_focus():
    m = _rich_only()
    if m is None:
        return
    result = {
        "global_workspace": {
            "dominant_focus": {"label": "stability", "source": "life", "salience": 0.9},
            "attention_mode": "protective",
            "broadcast": "focus broadcast",
            "workspace_items": [{"source": "e", "label": "engaged", "salience": 0.95}],
        },
    }
    panel = m.CHAPPiEBrainCLI._panel_workspace(result)
    assert panel is not None


def test_panel_workspace_none():
    m = _get_module()
    assert m.CHAPPiEBrainCLI._panel_workspace({}) is None


# ── panel budget ─────────────────────────────────────────────────

def test_panel_budget_trimmed():
    m = _rich_only()
    if m is None:
        return
    result = {
        "context_budget": {
            "estimated_tokens": 5000,
            "was_trimmed": True,
            "original_tokens": 8000,
            "trimmed_tokens": 5000,
            "removed_messages": 3,
        },
    }
    panel = m.CHAPPiEBrainCLI._panel_budget(result)
    assert panel is not None


# ── panel causal ─────────────────────────────────────────────────

def test_panel_causal_shows_phases():
    m = _rich_only()
    if m is None:
        return
    result = {
        "causal_trace": [
            {"phase": "Input", "driver": "Intent casual_chat"},
            {"phase": "Memory", "driver": "Query hi"},
            {"phase": "Emotion", "driver": "happiness:+3"},
        ],
    }
    panel = m.CHAPPiEBrainCLI._panel_causal(result)
    assert panel is not None


def test_panel_causal_none():
    m = _get_module()
    assert m.CHAPPiEBrainCLI._panel_causal({}) is None


# ── panel consolidation ──────────────────────────────────────────

def test_panel_consolidation_stats():
    m = _rich_only()
    if m is None:
        return
    result = {
        "memory_consolidation": {
            "ltm_loaded": 10,
            "stm_loaded": 5,
            "ltm_consolidated": 8,
            "stm_consolidated": 3,
            "duplicates_merged": 2,
            "critical_events": 1,
        },
    }
    panel = m.CHAPPiEBrainCLI._panel_consolidation(result)
    assert panel is not None


def test_panel_consolidation_none():
    m = _get_module()
    assert m.CHAPPiEBrainCLI._panel_consolidation({}) is None


# ── panel debug ──────────────────────────────────────────────────

def test_panel_debug_shows_entries():
    m = _rich_only()
    if m is None:
        return
    result = {
        "debug_entries": [
            {"category": "TURN", "message": "Neuer Turn gestartet"},
            {"category": "STEP1", "message": "Intent Analysis"},
            {"category": "EMOTION", "message": "happiness +3"},
        ],
    }
    panel = m.CHAPPiEBrainCLI._panel_debug(result)
    assert panel is not None


def test_panel_debug_none():
    m = _get_module()
    assert m.CHAPPiEBrainCLI._panel_debug({}) is None


# ── render spinner structure ─────────────────────────────────────

def test_render_spinner_produces_panel():
    m = _get_module()
    if not m.HAS_RICH:
        print("SKIP: rich not installed")
        return
    panel = m.CHAPPiEBrainCLI._render_spinner(1.5)
    from rich.panel import Panel
    assert isinstance(panel, Panel)


def test_render_step1_done_produces_panel():
    m = _get_module()
    if not m.HAS_RICH:
        print("SKIP: rich not installed")
        return
    panel = m.CHAPPiEBrainCLI._render_step1_done("Intent-Analyse abgeschlossen")
    from rich.panel import Panel
    assert isinstance(panel, Panel)


def test_render_streaming_empty():
    m = _get_module()
    if not m.HAS_RICH:
        print("SKIP: rich not installed")
        return
    collected = {"reasoning": "", "answer": ""}
    rendered = m.CHAPPiEBrainCLI._render_streaming(collected, 0, 0.0, 0.0)
    from rich.panel import Panel
    assert isinstance(rendered, Panel)


def test_render_streaming_with_content():
    m = _get_module()
    if not m.HAS_RICH:
        print("SKIP: rich not installed")
        return
    collected = {"reasoning": "reasoning text", "answer": "hello world"}
    rendered = m.CHAPPiEBrainCLI._render_streaming(collected, 42, 12.5, 3.3)
    assert rendered is not None


# ── panel intent json ────────────────────────────────────────────

def test_panel_intent_json():
    m = _rich_only()
    if m is None:
        return
    result = {"intent_raw_json": {"intent_analysis": {"primary_intent": "casual_chat", "confidence": 0.9}}}
    panel = m.CHAPPiEBrainCLI._panel_intent_json(result)
    assert panel is not None


def test_panel_intent_json_none():
    m = _get_module()
    assert m.CHAPPiEBrainCLI._panel_intent_json({}) is None


# ── panel memory ─────────────────────────────────────────────────

def test_panel_memory_with_trace():
    m = _rich_only()
    if m is None:
        return
    result = {
        "memory_trace": {
            "merged": {
                "query": "test",
                "memories_found": 10,
                "top_relevance": 0.85,
                "preview": [
                    {"role": "assistant", "label": "original", "relevance": 0.85, "content_preview": "..."}
                ],
            },
        },
    }
    panel = m.CHAPPiEBrainCLI._panel_memory(result)
    assert panel is not None


def test_panel_memory_none():
    m = _get_module()
    assert m.CHAPPiEBrainCLI._panel_memory({}) is None


if __name__ == "__main__":
    test_bar_full()
    test_bar_empty()
    test_bar_mid()
    test_bar_over_max()
    test_emo_color_green_boundary()
    test_emo_color_yellow_boundary()
    test_emo_color_red()
    test_emoji_delta_increase()
    test_emoji_delta_decrease()
    test_emoji_delta_unchanged()
    test_remote_meta_to_result_maps_core_fields()
    test_remote_meta_to_result_defaults()
    test_panel_emotions_shows_deltas()
    test_panel_emotions_none_when_empty()
    test_panel_tools_none_when_no_tools()
    test_panel_tools_shows_selected()
    test_panel_timing_with_data()
    test_panel_timing_fallback()
    test_panel_steering_with_vectors()
    test_panel_steering_none_when_empty()
    test_panel_tone_displays()
    test_panel_tone_none()
    test_panel_workspace_shows_focus()
    test_panel_workspace_none()
    test_panel_budget_trimmed()
    test_panel_causal_shows_phases()
    test_panel_causal_none()
    test_panel_consolidation_stats()
    test_panel_consolidation_none()
    test_panel_debug_shows_entries()
    test_panel_debug_none()
    test_render_spinner_produces_panel()
    test_render_step1_done_produces_panel()
    test_render_streaming_empty()
    test_render_streaming_with_content()
    test_panel_intent_json()
    test_panel_intent_json_none()
    test_panel_memory_with_trace()
    test_panel_memory_none()
    print("OK: CLI v6.0 display helpers")
