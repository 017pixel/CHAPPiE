from __future__ import annotations

import json
import queue
import threading
from typing import Any, Dict, Generator, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from api.dependencies import get_backend
from api.services.command_service import execute_slash_command
from api.schemas import (
    ChatRequest,
    ChatResponse,
    CommandRequest,
    CommandResponse,
    SessionCreateRequest,
    SessionUpdateRequest,
)

router = APIRouter(tags=["chat"])


def _ensure_session(backend, session_id: Optional[str]) -> Dict[str, Any]:
    normalized_id = backend.chat_manager.ensure_session_id(session_id)
    session = backend.chat_manager.load_session(normalized_id)
    backend.chat_manager.set_active_session(normalized_id)
    return session


def _persist_pending_turn(backend, session_id: str, user_message: Dict[str, Any], assistant_message: Dict[str, Any]):
    session = backend.chat_manager.load_session(session_id)
    messages = list(session.get("messages", []))
    messages.extend([user_message, assistant_message])
    backend.chat_manager.save_session(session_id, messages, title=session.get("title"))


def _build_sync_chat_response(backend, session_id: str, user_message: Dict[str, Any], message_id: str, result: Dict[str, Any]) -> ChatResponse:
    session_id = result.get("replacement_session_id", session_id)
    assistant_message = backend._build_assistant_message(user_message["content"], result, message_id=message_id)
    backend.chat_manager.update_message(
        session_id,
        message_id,
        content=assistant_message["content"],
        role="assistant",
        metadata_updates=assistant_message["metadata"],
    )
    return ChatResponse(
        session_id=session_id,
        message_id=message_id,
        user_message=user_message,
        assistant_message=assistant_message,
        metadata=assistant_message["metadata"],
        life_snapshot=result.get("life_snapshot", {}),
        emotion_snapshot=result.get("emotions", {}),
        debug_entries=result.get("debug_entries", []),
        sleep_status=result.get("sleep_status", {}),
        retry_history=result.get("retry_history", []),
    )


def _format_sse(event: str, payload: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/chat", response_model=ChatResponse)
def post_chat(request: ChatRequest, backend=Depends(get_backend)):
    session = _ensure_session(backend, request.session_id)
    session_id = session["id"]
    history = list(session.get("messages", []))

    user_message = {"id": backend.chat_manager.create_message_id(), "role": "user", "content": request.message}
    message_id = backend.chat_manager.create_message_id()
    pending_message = backend._build_pending_message(message_id)
    _persist_pending_turn(backend, session_id, user_message, pending_message)

    if request.command_mode or request.message.strip().startswith("/"):
        result = execute_slash_command(request.message.strip(), backend)
        if result.get("replacement_session_id"):
            session_id = result["replacement_session_id"]
            message_id = backend.chat_manager.create_message_id()
            pending_message = backend._build_pending_message(message_id)
            _persist_pending_turn(backend, session_id, user_message, pending_message)
        return _build_sync_chat_response(backend, session_id, user_message, message_id, result)

    result = backend.process(request.message, history, debug_mode=request.debug_mode)
    return _build_sync_chat_response(backend, session_id, user_message, message_id, result)


@router.post("/chat/stream")
def post_chat_stream(request: ChatRequest, backend=Depends(get_backend)):
    session = _ensure_session(backend, request.session_id)
    session_id = session["id"]
    history = list(session.get("messages", []))

    user_message = {"id": backend.chat_manager.create_message_id(), "role": "user", "content": request.message}
    message_id = backend.chat_manager.create_message_id()
    pending_message = backend._build_pending_message(message_id)
    _persist_pending_turn(backend, session_id, user_message, pending_message)

    def event_stream() -> Generator[str, None, None]:
        status_queue: queue.Queue[Dict[str, Any]] = queue.Queue()
        result_box: Dict[str, Any] = {}
        error_box: Dict[str, str] = {}

        def status_callback(event: Dict[str, Any]):
            status_queue.put(event)
            backend.chat_manager.update_message(
                session_id,
                message_id,
                metadata_updates={
                    "pending": True,
                    "status_text": event.get("status_text", "Nachricht wird verarbeitet..."),
                    "current_step": event.get("step"),
                },
            )

        def run_chat():
            try:
                if request.command_mode or request.message.strip().startswith("/"):
                    result_box["result"] = execute_slash_command(request.message.strip(), backend)
                else:
                    result_box["result"] = backend.process(
                        request.message,
                        history,
                        debug_mode=request.debug_mode,
                        status_callback=status_callback,
                    )
            except Exception as exc:
                error_box["message"] = str(exc)

        worker = threading.Thread(target=run_chat, daemon=True)
        worker.start()
        yield _format_sse("turn_started", {"session_id": session_id, "message_id": message_id})

        while worker.is_alive() or not status_queue.empty():
            try:
                event = status_queue.get(timeout=0.2)
                yield _format_sse("status", event)
            except queue.Empty:
                continue

        if error_box:
            backend.chat_manager.update_message(
                session_id,
                message_id,
                content=error_box["message"],
                role="assistant",
                metadata_updates={"pending": False, "status_text": ""},
            )
            yield _format_sse("turn_error", {"session_id": session_id, "message_id": message_id, "error": error_box["message"]})
            return

        result = result_box["result"]
        assistant_message = backend._build_assistant_message(request.message, result, message_id=message_id)
        backend.chat_manager.update_message(
            session_id,
            message_id,
            content=assistant_message["content"],
            role="assistant",
            metadata_updates=assistant_message["metadata"],
        )
        yield _format_sse(
            "turn_finished",
            {
                "session_id": session_id,
                "message_id": message_id,
                "assistant_message": assistant_message,
                "life_snapshot": result.get("life_snapshot", {}),
                "emotion_snapshot": result.get("emotions", {}),
                "debug_entries": result.get("debug_entries", []),
            },
        )

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/command", response_model=CommandResponse)
def post_command(request: CommandRequest, backend=Depends(get_backend)):
    result = execute_slash_command(request.command.strip(), backend)
    output = result["response_text"]
    if not request.session_id:
        return CommandResponse(output=output)

    session_id = result.get("replacement_session_id", request.session_id)
    session = _ensure_session(backend, session_id)
    user_message = {
        "id": backend.chat_manager.create_message_id(),
        "role": "user",
        "content": request.command.strip(),
    }
    assistant_message = {
        "id": backend.chat_manager.create_message_id(),
        "role": "assistant",
        "content": output,
        "metadata": {"pending": False, "status_text": ""},
    }
    history = list(session.get("messages", []))
    history.extend([user_message, assistant_message])
    backend.chat_manager.save_session(session["id"], history, title=session.get("title"))
    return CommandResponse(output=output, session_id=session["id"], session=backend.chat_manager.load_session(session["id"]))


@router.get("/sessions")
def list_sessions(backend=Depends(get_backend)):
    return backend.chat_manager.list_sessions()


@router.get("/sessions/active")
def get_active_session(backend=Depends(get_backend)):
    session = backend.chat_manager.load_active_session()
    return session


@router.get("/sessions/{session_id}")
def get_session(session_id: str, backend=Depends(get_backend)):
    return backend.chat_manager.load_session(session_id)


@router.post("/sessions")
def create_session(request: SessionCreateRequest, backend=Depends(get_backend)):
    session_id = backend.chat_manager.create_session()
    payload = {"id": session_id, "messages": [], "title": request.title or "New Chat", "updated_at": ""}
    backend.chat_manager.set_active_session(session_id)
    return payload


@router.patch("/sessions/{session_id}")
def update_session(session_id: str, request: SessionUpdateRequest, backend=Depends(get_backend)):
    session = backend.chat_manager.load_session(session_id)
    messages = request.messages if request.messages is not None else session.get("messages", [])
    if not messages:
        raise HTTPException(status_code=400, detail="Leere Session-Updates sind nicht erlaubt.")
    title = request.title or session.get("title")
    backend.chat_manager.save_session(session_id, messages, title=title)
    return backend.chat_manager.load_session(session_id)


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, backend=Depends(get_backend)):
    backend.chat_manager.delete_session(session_id)
    return {"success": True, "session_id": session_id}
