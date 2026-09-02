#!/usr/bin/env python3
"""Erzeugt einen GPU-freien Nachweis zum Tool-Prompt-/Providervertrag."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.prompts import CONTEXT_FILE_TOOL_INSTRUCTION, build_system_prompt  # noqa: E402


DEFAULT_OUTPUT = ROOT / "forschung" / "report" / "workspace" / "prompt-tool-contract.json"


def line_number(text: str, needle: str) -> int | None:
    for index, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return index
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    prompts_path = ROOT / "config" / "prompts.py"
    generation_path = ROOT / "web_infrastructure" / "generation.py"
    pipeline_path = ROOT / "web_infrastructure" / "turn_pipeline.py"
    runner_path = ROOT / "forschung" / "session_runner.py"
    prompts_source = prompts_path.read_text(encoding="utf-8")
    generation_source = generation_path.read_text(encoding="utf-8")
    runner_source = runner_path.read_text(encoding="utf-8")
    local_final_prompt = build_system_prompt(include_emotion_status=False, use_chain_of_thought=False)
    tool_gate = 'tools = self._get_context_tools() if settings.llm_provider == LLMProvider.GROQ else None'
    stream_start = line_number(generation_source, "def _generate_response_stream_raw(")
    stream_end = line_number(generation_source, "def _stream_visible_candidate(")
    if stream_start is None or stream_end is None:
        raise RuntimeError("Streaming-Symbole fehlen in web_infrastructure/generation.py")
    stream_source = "\n".join(generation_source.splitlines()[stream_start - 1:stream_end - 1])
    runner_call = "gen = self.backend.process_stream(text, history, debug_mode=True)"

    report = {
        "schema_version": 1,
        "gpu_or_model_calls": 0,
        "prompt_source": str(prompts_path.relative_to(ROOT)),
        "prompt_sha256": hashlib.sha256(prompts_path.read_bytes()).hexdigest(),
        "tool_instruction_appended_when_emotions_and_thinking_disabled": CONTEXT_FILE_TOOL_INSTRUCTION.strip() in local_final_prompt,
        "tool_instruction_demands_post_answer_call": "RUFE NACH DEINER ANTWORT" in CONTEXT_FILE_TOOL_INSTRUCTION,
        "build_prompt_append_line": line_number(prompts_source, "prompt += CONTEXT_FILE_TOOL_INSTRUCTION"),
        "generation_source": str(generation_path.relative_to(ROOT)),
        "pipeline_source": str(pipeline_path.relative_to(ROOT)),
        "runner_source": str(runner_path.relative_to(ROOT)),
        "harness_process_stream_line": line_number(runner_source, runner_call),
        "measured_harness_uses_process_stream": runner_call in runner_source,
        "streaming_path_start_line": stream_start,
        "streaming_plain_generate_line": line_number(generation_source, "return self.generation.generate(messages, config=gen_config), {"),
        "streaming_path_uses_plain_generate": "return self.generation.generate(messages, config=gen_config), {" in stream_source,
        "streaming_path_uses_generate_with_tools": "generate_with_tools" in stream_source,
        "native_tool_gate_line": line_number(generation_source, tool_gate),
        "nonstreaming_native_tools_groq_only": tool_gate in generation_source,
        "interpretation": (
            "Der im Harness gemessene Streaming-Pfad nutzt plain generate ohne strukturierten Toolkanal. "
            "Darum wird dem finalen Prompt standardmaessig keine Toolaufforderung mehr angehaengt. Ein separater "
            "nicht-streamender Antwortpfad kann native Tools weiterhin nur fuer Groq aktivieren."
        ),
        "causal_limit": "Codevertrag; kausale Effekte werden nur in separaten Ablationsprofilen bewertet.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
