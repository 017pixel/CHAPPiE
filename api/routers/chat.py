from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Generator, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from api.dependencies import get_backend
from api.services.command_service import execute_slash_command
from api.schemas import (
    ChatRequest,
    ChatResponse,
    CommandRequest,
    CommandResponse,
    SessionExportResponse,
    SessionCreateRequest,
    SessionUpdateRequest,
    SessionRuntimeSettingsPatch,
)
from web_infrastructure.session_export import (
    SessionExportError,
    backend_data_directory,
    build_session_export,
    write_session_export,
)

router = APIRouter(tags=["chat"])


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_user_message(backend, content: str) -> Dict[str, Any]:
    normalized = content.strip()
    message: Dict[str, Any] = {
        "id": backend.chat_manager.create_message_id(),
        "role": "user",
        "content": content,
        "created_at": _utc_now_iso(),
    }
    if normalized.startswith("/"):
        message["metadata"] = {
            "is_command": True,
            "message_kind": "command",
            "command": normalized,
        }
    return message


def _ensure_session(backend, session_id: Optional[str]) -> Dict[str, Any]:
    normalized_id = backend.chat_manager.ensure_session_id(session_id)
    session = backend.chat_manager.load_session(normalized_id)
    backend.chat_manager.set_active_session(normalized_id)
    return session


def _persist_pending_turn(backend, session_id: str, user_message: Dict[str, Any], assistant_message: Dict[str, Any]):
    backend.chat_manager.append_messages(session_id, [user_message, assistant_message])


def _is_session_reset_command(message: str) -> bool:
    return message.strip().lower() in {"/clear", "/new"}


def _build_sync_chat_response(backend, session_id: str, user_message: Dict[str, Any], message_id: str, result: Dict[str, Any]) -> ChatResponse:
    session_id = result.get("replacement_session_id", session_id)
    assistant_message = backend.build_assistant_message(user_message["content"], result, message_id=message_id)
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

    user_message = _build_user_message(backend, request.message)

    if request.command_mode or request.message.strip().startswith("/"):
        result = execute_slash_command(request.message.strip(), backend, session_id=session_id)
        session_id = result.get("replacement_session_id", session_id)
        message_id = backend.chat_manager.create_message_id()
        pending_message = backend.build_pending_message(message_id)
        _persist_pending_turn(backend, session_id, user_message, pending_message)
        return _build_sync_chat_response(backend, session_id, user_message, message_id, result)

    message_id = backend.chat_manager.create_message_id()
    pending_message = backend.build_pending_message(message_id)
    _persist_pending_turn(backend, session_id, user_message, pending_message)

    result = backend.process(
        request.message,
        history,
        debug_mode=request.debug_mode,
        temporal_context={"user_message_created_at": user_message["created_at"]},
        session_id=session_id,
    )
    return _build_sync_chat_response(backend, session_id, user_message, message_id, result)


@router.post("/chat/stream")
def post_chat_stream(request: ChatRequest, backend=Depends(get_backend)):
    session = _ensure_session(backend, request.session_id)
    session_id = session["id"]
    history = list(session.get("messages", []))

    user_message = _build_user_message(backend, request.message)
    is_command = request.command_mode or request.message.strip().startswith("/")
    reset_command_result = None
    reset_command_error = None
    if is_command and _is_session_reset_command(request.message):
        try:
            reset_command_result = execute_slash_command(request.message.strip(), backend, session_id=session_id)
            session_id = reset_command_result.get("replacement_session_id", session_id)
        except Exception as exc:
            reset_command_error = exc

    message_id = backend.chat_manager.create_message_id()
    pending_message = backend.build_pending_message(message_id)
    _persist_pending_turn(backend, session_id, user_message, pending_message)

    def event_stream() -> Generator[str, None, None]:
        nonlocal session_id, message_id
        yield _format_sse("turn_started", {"session_id": session_id, "message_id": message_id})

        # Slash commands are fast and don't need streaming
        if is_command:
            try:
                if reset_command_error is not None:
                    raise reset_command_error
                result = reset_command_result or execute_slash_command(request.message.strip(), backend, session_id=session_id)
                if result.get("replacement_session_id"):
                    replacement_session_id = result["replacement_session_id"]
                    if replacement_session_id != session_id:
                        session_id = replacement_session_id
                        message_id = backend.chat_manager.create_message_id()
                        pending_message = backend.build_pending_message(message_id)
                        _persist_pending_turn(backend, session_id, user_message, pending_message)

                assistant_message = backend.build_assistant_message(request.message, result, message_id=message_id)
                backend.chat_manager.update_message(
                    session_id,
                    message_id,
                    content=assistant_message["content"],
                    role="assistant",
                    metadata_updates=assistant_message["metadata"],
                )
                # Yield the full response as a single token for consistency
                yield _format_sse("token", {"content": assistant_message["content"]})
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
            except Exception as exc:
                error_text = str(exc)
                backend.chat_manager.update_message(
                    session_id,
                    message_id,
                    content=error_text,
                    role="assistant",
                    metadata_updates={"pending": False, "status_text": "", "stream_error": True, "error_message": error_text, "status": "error"},
                )
                yield _format_sse("turn_error", {"session_id": session_id, "message_id": message_id, "error": error_text})
            return

        # Normal messages: stream tokens
        try:
            for event in backend.process_stream(
                request.message,
                history,
                debug_mode=request.debug_mode,
                temporal_context={"user_message_created_at": user_message["created_at"]},
        session_id=session_id,
            ):
                event_type = event.get("event")
                if event_type == "token":
                    yield _format_sse("token", {
                        "content": event.get("content", ""),
                        "token_type": event.get("token_type", "answer"),
                    })
                elif event_type == "status":
                    yield _format_sse("status", event)
                elif event_type == "error":
                    error_text = event.get("error", "Unbekannter Fehler")
                    backend.chat_manager.update_message(
                        session_id,
                        message_id,
                        content=error_text,
                        role="assistant",
                        metadata_updates={"pending": False, "status_text": "", "stream_error": True, "error_message": error_text, "status": "error"},
                    )
                    yield _format_sse("turn_error", {"session_id": session_id, "message_id": message_id, "error": error_text})
                    return
                elif event_type == "finished":
                    result = event.get("result", {})
                    assistant_message = backend.build_assistant_message(request.message, result, message_id=message_id)
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
                    return

        except Exception as exc:
            error_text = str(exc)
            backend.chat_manager.update_message(
                session_id,
                message_id,
                content=error_text,
                role="assistant",
                metadata_updates={"pending": False, "status_text": "", "stream_error": True, "error_message": error_text, "status": "error"},
            )
            yield _format_sse("turn_error", {"session_id": session_id, "message_id": message_id, "error": error_text})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )


@router.post("/command", response_model=CommandResponse)
def post_command(request: CommandRequest, backend=Depends(get_backend)):
    result = execute_slash_command(request.command.strip(), backend, session_id=request.session_id)
    output = result["response_text"]
    if not request.session_id:
        return CommandResponse(output=output)

    session_id = result.get("replacement_session_id", request.session_id)
    session = _ensure_session(backend, session_id)
    user_message = _build_user_message(backend, request.command.strip())
    assistant_created_at = _utc_now_iso()
    assistant_message = {
        "id": backend.chat_manager.create_message_id(),
        "role": "assistant",
        "content": output,
        "created_at": assistant_created_at,
        "metadata": {
            "pending": False,
            "status_text": "",
            "created_at": assistant_created_at,
            "is_system": True,
            "is_system_response": True,
            "message_kind": "system",
            "command": request.command.strip(),
            "command_trace": result.get("command_trace", {}),
            "raw_response": output,
        },
    }
    backend.chat_manager.append_messages(session["id"], [user_message, assistant_message])
    return CommandResponse(output=output, session_id=session["id"], session=backend.chat_manager.load_session(session["id"]))


@router.get("/sessions")
def list_sessions(backend=Depends(get_backend)):
    return backend.chat_manager.list_sessions()


@router.get("/sessions/active")
def get_active_session(backend=Depends(get_backend)):
    session = backend.chat_manager.load_active_session()
    return session


@router.get("/sessions/{session_id}/export", response_model=SessionExportResponse)
def export_session(
    session_id: str,
    mode: Literal["standard", "debug"] = "standard",
    backend=Depends(get_backend),
):
    try:
        export = build_session_export(backend, session_id, mode=mode)
        fallback_path = write_session_export(export, backend_data_directory(backend))
    except SessionExportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Session-Export fehlgeschlagen: {exc}") from exc
    return {
        "session_id": export["session"]["id"],
        "mode": export["mode"],
        "export": export,
        "fallback_path": str(fallback_path),
    }


@router.get("/sessions/{session_id}")
def get_session(session_id: str, backend=Depends(get_backend)):
    return backend.chat_manager.load_session(session_id)


@router.get("/sessions/{session_id}/settings")
def get_session_settings(session_id: str, backend=Depends(get_backend)):
    try:
        return backend.chat_manager.get_runtime_settings(session_id).to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/sessions/{session_id}/settings")
def patch_session_settings(session_id: str, request: SessionRuntimeSettingsPatch, backend=Depends(get_backend)):
    try:
        return backend.chat_manager.update_runtime_settings(
            session_id, request.model_dump(exclude_unset=True),
        ).to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
