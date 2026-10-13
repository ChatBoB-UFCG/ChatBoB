from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.services.session_service import SessionService, SessionServiceError


router = APIRouter()


class SessionRequest(BaseModel):
    session_id: str = Field(min_length=1)


class MessageRequest(SessionRequest):
    message: str = Field(min_length=1)


def get_session_service(request: Request) -> SessionService:
    return request.app.state.session_service


def _response(session_id: str, state: Dict[str, Any], message: Optional[str] = None) -> Dict[str, Any]:
    if message is None:
        message = state.get("question_to_ask")
    if message is None and state.get("status_finished"):
        message = "Extração concluída."
    if message is None:
        assistant_messages = [
            item.get("content")
            for item in state.get("context_messages", [])
            if item.get("role") == "assistant"
        ]
        message = assistant_messages[-1] if assistant_messages else None

    return {
        "session_id": session_id,
        "message": message,
        "question_to_ask": state.get("question_to_ask"),
        "finished": state.get("status_finished", False),
        "extracted": state.get("extracted", {}),
        "missing_fields": state.get("missing_fields", []),
        "context_messages": state.get("context_messages", []),
        "logs": state.get("logs", []),
        "final_json": state.get("final_json"),
    }


def _to_http_exception(error: SessionServiceError) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail=error.detail)


@router.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@router.post("/start")
def start_session(
    request: SessionRequest,
    service: SessionService = Depends(get_session_service),
) -> Dict[str, Any]:
    session_id = request.session_id.strip()
    if not session_id:
        raise HTTPException(status_code=422, detail="session_id não pode ficar vazio.")

    try:
        state, greeting = service.start(session_id)
    except SessionServiceError as error:
        raise _to_http_exception(error) from error
    return _response(session_id, state, greeting)


@router.post("/message")
def send_message(
    request: MessageRequest,
    service: SessionService = Depends(get_session_service),
) -> Dict[str, Any]:
    session_id = request.session_id.strip()
    message = request.message.strip()
    if not session_id or not message:
        raise HTTPException(status_code=422, detail="session_id e message não podem ficar vazios.")

    try:
        state = service.process_message(session_id, message)
    except SessionServiceError as error:
        raise _to_http_exception(error) from error
    return _response(session_id, state)
