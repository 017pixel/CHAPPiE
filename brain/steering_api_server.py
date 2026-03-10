"""OpenAI-kompatibler lokaler API-Server mit echtem Activation Steering."""

from __future__ import annotations

import argparse
import json
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Dict
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from .steering_backend import LocalSteeringEngine, extract_steering_payload


def create_app(model_name: str) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.engine = LocalSteeringEngine(model_name)
        yield

    app = FastAPI(title="CHAPPiE Steering API", version="1.0.0", lifespan=lifespan)
    app.state.model_name = model_name
    app.state.engine = None

    @app.get("/health")
    def health() -> Dict[str, Any]:
        return {"status": "ok", "model": app.state.model_name}

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
        stream = bool(body.get("stream", False))
        payload = extract_steering_payload(body)
        chat_kwargs = payload.get("chat_template_kwargs") if isinstance(payload, dict) else None
        created = int(time.time())
        request_id = f"chatcmpl-{uuid4().hex}"

        if stream:
            def _events():
                try:
                    for piece in engine.stream_generate(messages, max_tokens=max_tokens, temperature=temperature, steering_payload=payload, chat_template_kwargs=chat_kwargs):
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
            result = engine.generate(messages, max_tokens=max_tokens, temperature=temperature, steering_payload=payload, chat_template_kwargs=chat_kwargs)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Steering-Server Fehler: {exc}") from exc

        return JSONResponse({
            "id": request_id,
            "object": "chat.completion",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": result["text"]}, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": result["prompt_tokens"],
                "completion_tokens": result["completion_tokens"],
                "total_tokens": result["prompt_tokens"] + result["completion_tokens"],
            },
        })

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="CHAPPiE Steering API Server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--model", default=os.getenv("CHAPPIE_STEERING_MODEL", "Qwen/Qwen3.5-9B"))
    args = parser.parse_args()
    uvicorn.run(create_app(args.model), host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()