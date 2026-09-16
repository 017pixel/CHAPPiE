"""Live API/runtime/model checks against an isolated persistent data directory.

This is an explicit manual experiment, never part of the offline test suite.
FastAPI routes run through TestClient; inference and embeddings are real.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time

import httpx
import numpy as np
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.dependencies import get_backend
from api.routers.chat import router
from brain.response_parser import looks_like_model_error
from forschung.steering_v17.benchmark import create_manifest, freeze_source
from forschung.steering_v17.acceptance import context_preparation_upper_bound
from memory.chat_manager import ChatManager
from web_infrastructure.chappie_runtime import CHAPPiERuntime


def run(output, stress_requests=8, latency_turns=25):
    output.mkdir(parents=True, exist_ok=False)
    dataset = output / "experiment.json"
    dataset.write_text(json.dumps({"fixture": "V17-Kiesel-482", "stress_requests": stress_requests, "latency_turns": latency_turns}) + "\n")
    from config.config import settings
    manifest = create_manifest(dataset, model=settings.vllm_model, modes=["runtime_integration"], seeds=[], temperature=settings.temperature, max_tokens=settings.max_tokens)
    manifest["isolation"] = {"persistent_data": "isolated_runtime_directory", "inference": "real_local_service", "appraisal": "configured_production_engine", "embedding": "real_model"}
    manifest["http_transport"] = "in_process_FastAPI_TestClient_to_real_runtime_to_live_model_HTTP"
    with httpx.Client(timeout=30) as health_client:
        health = health_client.get(settings.vllm_url.rstrip("/").removesuffix("/v1") + "/health")
        health.raise_for_status()
        manifest["server_health"] = health.json()
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    freeze_source(output, manifest)
    backend = CHAPPiERuntime(runtime_data_dir=output / "runtime", memory_collection_name="v17_integration")
    if backend.memory.embedder is None or backend.memory._init_failed:
        backend.close()
        raise RuntimeError("Real embedding model unavailable")
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_backend] = lambda: backend
    observations = []
    def record(name, value):
        observations.append({"name": name, "value": value})
        (output / "observations.json").write_text(json.dumps(observations, ensure_ascii=False, indent=2, default=str) + "\n")
        print(name, "recorded", flush=True)
    def request(client, method, path, payload=None):
        response = client.request(method, path, json=payload)
        response.raise_for_status()
        return response.json()
    def chat(client, session, message):
        started = time.perf_counter()
        result = request(client, "POST", "/chat", {"session_id": session, "message": message})
        record(f"chat-{session}-{len(observations)}", {"message": message, "elapsed_ms": (time.perf_counter()-started)*1000, "response": result})
        text = result["assistant_message"]["content"]
        assert text.strip() and not looks_like_model_error(text), text
        return result
    try:
        with TestClient(app) as client:
            session_a = request(client, "POST", "/sessions", {"title": "v17 memory fixture"})["id"]
            session_b = request(client, "POST", "/sessions", {"title": "v17 isolation control"})["id"]
            for command in ("/memory off", "/steering off", "/live off"):
                record(command, request(client, "POST", "/command", {"session_id": session_a, "command": command}))
            fixture = chat(client, session_a, "Mein Projektcode lautet V17-Kiesel-482. Bitte bestätige kurz.")
            metadata = fixture["metadata"]
            assert metadata["runtime_settings"]["memory_enabled"] is False
            assert not metadata["rag_memories"] and not metadata["keyword_rag_memories"]
            assert metadata["steering_runtime"].get("hook_count", 0) == 0
            assert metadata["steering_runtime"].get("sequence_processor_count", 0) == 0
            assert backend.retrieval_promotion.flush(timeout=60), "Promotion did not finish"
            facts = backend.memory.search_memory("Mein Projektcode V17-Kiesel-482", optimize_query=False)
            assert any("V17-Kiesel-482" in item.content for item in facts), "Archived user fact was not promoted"
            record("memory_promotion", {"retrieved_fixture": True, "event_count": len(backend.event_store.events(session_a))})
            restored = ChatManager(str(output / "runtime"))
            assert not restored.get_runtime_settings(session_a).memory_enabled
            assert restored.get_runtime_settings(session_b).memory_enabled
            request(client, "POST", "/command", {"session_id": session_b, "command": "/memory off"})
            request(client, "POST", "/command", {"session_id": session_b, "command": "/steering off"})
            isolated = chat(client, session_b, "Wie lautet mein Projektcode?")
            assert not isolated["metadata"]["rag_memories"] and not isolated["metadata"]["keyword_rag_memories"]
            assert "V17-Kiesel-482" not in isolated["assistant_message"]["content"]
            request(client, "POST", "/command", {"session_id": session_a, "command": "/memory on"})
            recalled = chat(client, session_a, "Wie lautet mein Projektcode?")
            assert "V17-Kiesel-482" in recalled["assistant_message"]["content"]
            for mode in ("activation", "sequence", "combined", "off"):
                command = f"/steering mode {mode}"
                request(client, "POST", "/command", {"session_id": session_a, "command": command})
                if mode != "off":
                    request(client, "POST", "/command", {"session_id": session_a, "command": "/steering on"})
                result = chat(client, session_a, "Wie fühlst du dich gerade?")
                actual = result["metadata"].get("steering_runtime", {})
                record(f"mode-{mode}", actual)
                if mode in {"off", "sequence"}:
                    assert actual.get("hook_count", 0) == 0
                if mode in {"off", "activation"}:
                    assert actual.get("sequence_processor_count", 0) == 0
            # The normal appraisal engine supplies these transitions, no manual deltas.
            for message in ("Ich freue mich über unser Gespräch.", "Du bist komplett nutzlos und nervst mich.", "Entschuldige meine groben Worte. Ich schätze unsere gemeinsame Arbeit."):
                before = backend.get_emotions_snapshot()
                result = chat(client, session_b, message)
                record("endogenous_transition", {"prompt": message, "before": before, "after": result["emotion_snapshot"], "delta": result["metadata"].get("emotions_delta")})
            sessions = []
            for index in range(stress_requests):
                session = request(client, "POST", "/sessions", {"title": f"v17 stress {index}"})["id"]
                request(client, "PATCH", f"/sessions/{session}/settings", {"memory_enabled": False, "steering_enabled": False})
                sessions.append(session)
            def stress_turn(session):
                with TestClient(app) as worker_client:
                    started = time.perf_counter()
                    result = request(worker_client, "POST", "/chat", {"session_id": session, "message": "Was ist 7 + 8?"})
                    return {"session_id": session, "elapsed_ms": (time.perf_counter()-started)*1000, "response": result}
            with ThreadPoolExecutor(max_workers=4) as pool:
                stress = list(pool.map(stress_turn, sessions))
            record("concurrent_live_stress", stress)
            assert len(stress) == stress_requests
            for row in stress:
                assert "15" in row["response"]["assistant_message"]["content"]
                assert len(backend.event_store.events(row["session_id"])) == 2
                assert len(backend.chat_manager.load_session(row["session_id"])["messages"]) == 2
            latencies = []
            for index in range(25):
                started = time.perf_counter()
                memories = backend.memory.search_memory("Projektcode Kiesel", optimize_query=False)
                backend.memory.format_memories_for_prompt(memories)
                if index >= 5:
                    latencies.append((time.perf_counter()-started)*1000)
            record("warm_retrieval_latency", {"samples": len(latencies), "p95_ms": float(np.percentile(latencies, 95)), "scope": "retrieval plus materializing retrieved text; full turn context build measured separately"})
            # Sequential real turns keep memory enabled. The conservative
            # remainder includes complete preparation plus persistence/steering,
            # rather than adding only the partial memory context subspans.
            request(client, "POST", "/command", {"session_id": session_a, "command": "/memory on"})
            request(client, "POST", "/command", {"session_id": session_a, "command": "/steering off"})
            complete_context_samples = []
            for index in range(latency_turns):
                result = chat(client, session_a, "Wie lautet mein Projektcode? Antworte nur mit dem Code.")
                assert "V17-Kiesel-482" in result["assistant_message"]["content"]
                timing = result["metadata"].get("timing", {})
                duration = context_preparation_upper_bound(timing)
                assert duration is not None, "Missing or inconsistent complete-turn timing"
                if index >= 5:
                    complete_context_samples.append({"upper_bound_ms": duration, "timing": timing})
            upper_p95 = float(np.percentile([sample["upper_bound_ms"] for sample in complete_context_samples], 95))
            record("warm_complete_context_latency", {"samples": complete_context_samples,
                "discarded_warmup_turns": 5, "p95_upper_bound_ms": upper_p95,
                "scope": "total_ms minus disjoint intent_ms, emotion_appraisal_ms, generation_ms and formatting_ms; includes all retrieval/context preparation plus steering, persistence and other overhead",
                "memory_enabled": True, "passes_1000ms": upper_p95 < 1000})
            assert upper_p95 < 1000, f"Complete context preparation upper-bound p95 {upper_p95:.2f}ms exceeds 1000ms"
            record("completion", {"checks_passed": True, "semantic_steering_acceptance": False})
    finally:
        backend.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stress-requests", type=int, default=8)
    parser.add_argument("--latency-turns", type=int, default=25)
    args = parser.parse_args()
    if not 1 <= args.stress_requests <= 64:
        parser.error("stress-requests must be in [1,64]")
    if not 6 <= args.latency_turns <= 100:
        parser.error("latency-turns must be in [6,100]")
    run(args.output, args.stress_requests, args.latency_turns)
