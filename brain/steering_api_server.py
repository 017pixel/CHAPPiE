"""OpenAI-kompatibler lokaler API-Server mit echtem Activation Steering."""

from __future__ import annotations

import argparse
import asyncio
import gc
import json
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from .steering_backend import LocalSteeringEngine, extract_steering_payload, QUANTIZE_ENV


def _auto_quantize_for_model(model_name: str, explicit: Optional[bool]) -> Optional[bool]:
    if explicit is not None:
        return explicit
    try:
        from config.config import is_gemma4_model

        if is_gemma4_model(model_name) and ("26b" in model_name.lower() or "a4b" in model_name.lower()):
            return True
    except Exception:
        pass
    return explicit


def create_app(model_name: str, context_length: int = 8192, quantize: Optional[bool] = None, adapter_path: Optional[str] = None) -> FastAPI:
    resolved_quantize = _auto_quantize_for_model(model_name, quantize)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.restart_status = "loading"
        app.state.restart_progress = 20
        app.state.restart_step = "Modell wird geladen..."
        app.state.restart_estimated_remaining = 60
        app.state.engine = LocalSteeringEngine(model_name, context_length=context_length, quantize=resolved_quantize, adapter_path=adapter_path)
        app.state.restart_status = "ready"
        app.state.restart_progress = 100
        app.state.restart_step = "Fertig!"
        app.state.restart_estimated_remaining = 0
        yield

    app = FastAPI(title="CHAPPiE Steering API", version="1.0.0", lifespan=lifespan)
    app.state.model_name = model_name
    app.state.engine = None
    app.state.context_length = context_length
    app.state.quantize = resolved_quantize
    app.state.adapter_path = adapter_path
    app.state.restart_status = "starting"
    app.state.restart_progress = 0
    app.state.restart_step = "Server startet..."
    app.state.restart_estimated_remaining = 90
    app.state.restart_error = ""

    @app.get("/health")
    def health() -> Dict[str, Any]:
        return {"status": "ok", "model": app.state.model_name, "restart_status": app.state.restart_status}

    @app.get("/v1/models")
    def models() -> Dict[str, Any]:
        now = int(time.time())
        return {"object": "list", "data": [{"id": app.state.model_name, "object": "model", "created": now, "owned_by": "chappie-local"}]}

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request) -> Any:
        engine: LocalSteeringEngine = app.state.engine
        if engine is None:
            raise HTTPException(status_code=503, detail="Model engine not initialized")

        body = await request.json()
        model = body.get("model") or app.state.model_name
        if model != app.state.model_name:
            raise HTTPException(status_code=400, detail=f"Model {model} ist nicht geladen.")
        messages = body.get("messages")
        if not isinstance(messages, list) or not messages:
            raise HTTPException(status_code=400, detail="messages fehlt oder ist leer")

        max_tokens = int(body.get("max_tokens") or body.get("max_completion_tokens") or 256)
        temperature = float(body.get("temperature") or 0.0)
        top_p = body.get("top_p")
        top_k = body.get("top_k")
        extra_body_for_penalty = body.get("extra_body") if isinstance(body.get("extra_body"), dict) else {}
        repetition_penalty = float(body.get("repetition_penalty") or extra_body_for_penalty.get("repetition_penalty") or 1.15)
        stream = bool(body.get("stream", False))
        payload = extract_steering_payload(body)
        chat_kwargs = payload.get("chat_template_kwargs") if isinstance(payload, dict) else None
        created = int(time.time())
        request_id = f"chatcmpl-{uuid4().hex}"

        if stream:
            def _events():
                try:
                    for piece in engine.stream_generate(
                        messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        steering_payload=payload,
                        chat_template_kwargs=chat_kwargs,
                        repetition_penalty=repetition_penalty,
                        top_p=float(top_p) if top_p is not None else None,
                        top_k=int(top_k) if top_k is not None else None,
                    ):
                        chunk = {
                            "id": request_id,
                            "object": "chat.completion.chunk",
                            "created": created,
                            "model": model,
                            "choices": [{"index": 0, "delta": {"content": piece}, "finish_reason": None}],
                        }
                        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                    final_chunk = {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                    }
                    yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as exc:
                    error_chunk = {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [{"index": 0, "delta": {"content": f"\nSteering-Server Fehler: {exc}"}, "finish_reason": "stop"}],
                    }
                    yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"

            return StreamingResponse(_events(), media_type="text/event-stream")

        try:
            result = engine.generate(
                messages,
                max_tokens=max_tokens,
                temperature=temperature,
                steering_payload=payload,
                chat_template_kwargs=chat_kwargs,
                repetition_penalty=repetition_penalty,
                top_p=float(top_p) if top_p is not None else None,
                top_k=int(top_k) if top_k is not None else None,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Steering-Server Fehler: {exc}") from exc

        return JSONResponse({
            "id": request_id,
            "object": "chat.completion",
            "created": created,
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": result["text"],
                    **({"reasoning_content": result["reasoning"]} if result.get("reasoning") else {}),
                },
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": result["prompt_tokens"],
                "completion_tokens": result["completion_tokens"],
                "total_tokens": result["prompt_tokens"] + result["completion_tokens"],
            },
        })

    async def _do_restart(next_model_name: str, next_quantize: Optional[bool]) -> None:
        try:
            app.state.restart_status = "stopping"
            app.state.restart_progress = 10
            app.state.restart_step = "Alte Engine wird freigegeben..."
            app.state.restart_estimated_remaining = 80
            app.state.restart_error = ""
            old_engine = app.state.engine
            app.state.engine = None
            del old_engine
            gc.collect()
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass

            app.state.restart_status = "loading"
            app.state.restart_progress = 25
            app.state.restart_step = "Modell wird geladen..."
            app.state.restart_estimated_remaining = 60
            resolved_next_quantize = _auto_quantize_for_model(next_model_name, next_quantize)
            engine = await asyncio.to_thread(
                LocalSteeringEngine,
                next_model_name,
                None,
                app.state.context_length,
                resolved_next_quantize,
                app.state.adapter_path,
            )

            app.state.restart_status = "calibrating"
            app.state.restart_progress = 80
            app.state.restart_step = "Anchor-Vektoren werden initialisiert..."
            app.state.restart_estimated_remaining = 10
            await asyncio.sleep(0.2)

            app.state.restart_status = "testing"
            app.state.restart_progress = 90
            app.state.restart_step = "Verbindung wird getestet..."
            app.state.restart_estimated_remaining = 3
            test_result = await asyncio.to_thread(
                engine.generate,
                [{"role": "system", "content": "Test"}, {"role": "user", "content": "Hi"}],
                5,
                0.0,
                None,
                {"enable_thinking": False},
            )
            if not test_result.get("text"):
                raise RuntimeError("Test-Generierung fehlgeschlagen")

            app.state.engine = engine
            app.state.model_name = next_model_name
            app.state.quantize = resolved_next_quantize
            app.state.restart_status = "ready"
            app.state.restart_progress = 100
            app.state.restart_step = "Fertig!"
            app.state.restart_estimated_remaining = 0
        except Exception as exc:
            app.state.restart_status = "error"
            app.state.restart_progress = 0
            app.state.restart_step = f"Fehler: {exc}"
            app.state.restart_estimated_remaining = 0
            app.state.restart_error = str(exc)

    @app.post("/v1/steering/restart")
    async def steering_restart(request: Request) -> Dict[str, Any]:
        if app.state.restart_status in {"stopping", "loading", "calibrating", "testing"}:
            raise HTTPException(status_code=409, detail="Restart laeuft bereits")
        body = await request.json()
        next_model_name = str(body.get("model") or body.get("model_name") or app.state.model_name).strip()
        if not next_model_name:
            raise HTTPException(status_code=400, detail="model fehlt")
        next_quantize = body.get("quantize") if "quantize" in body else None
        if next_quantize is not None:
            next_quantize = bool(next_quantize)
        app.state.restart_status = "stopping"
        app.state.restart_progress = 5
        app.state.restart_step = "Restart gestartet..."
        app.state.restart_estimated_remaining = 90
        asyncio.create_task(_do_restart(next_model_name, next_quantize))
        return {"status": "restarting", "model": next_model_name}

    @app.get("/v1/steering/restart-status")
    async def steering_restart_status() -> Dict[str, Any]:
        return {
            "status": app.state.restart_status,
            "progress": app.state.restart_progress,
            "current_step": app.state.restart_step,
            "estimated_remaining": app.state.restart_estimated_remaining,
            "error": app.state.restart_error,
            "model": app.state.model_name,
            "quantize": app.state.quantize,
        }

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="CHAPPiE Steering API Server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--model", default=os.getenv("CHAPPIE_STEERING_MODEL", "Qwen/Qwen3.5-4B"))
    parser.add_argument("--context-length", type=int, default=int(os.getenv("CHAPPIE_STEERING_CONTEXT_LENGTH", "8192")),
                        help="max_position_embeddings cap to limit KV-cache VRAM (default: 8192)")
    parser.add_argument("--quantize", nargs="?", const=True, type=lambda v: bool(v) if isinstance(v, bool) else str(v).lower() in ("1", "true", "yes", "on"),
                        default=os.getenv(QUANTIZE_ENV, "").strip().lower() in ("1", "true", "yes", "on") if os.getenv(QUANTIZE_ENV) else None,
                        help="Enable NF4 4-bit quantization to reduce VRAM (default: auto-detect)")
    parser.add_argument("--adapter", default=os.getenv("CHAPPIE_STEERING_ADAPTER", None),
                        help="Pfad zum LoRA-Adapter (optional)")
    args = parser.parse_args()
    uvicorn.run(create_app(args.model, args.context_length, quantize=args.quantize, adapter_path=args.adapter), host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
