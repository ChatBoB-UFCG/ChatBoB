import copy
import os
from threading import Lock
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.core.extractor import ExtractorAgent
from app.core.schema import Schema
from app.utils.session_storage import save_session_data


app = FastAPI(title="ChatBoB API")
schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "examples", "schema_example.json")
schema = Schema.load_from_file(schema_path)
agent = ExtractorAgent(schema)

sessions: Dict[str, Dict[str, Any]] = {}
session_lock = Lock()


class SessionRequest(BaseModel):
    session_id: str = Field(min_length=1)


class MessageRequest(SessionRequest):
    message: str = Field(min_length=1)


def _new_state() -> Dict[str, Any]:
    greeting = {
        "role": "assistant",
        "content": "Olá! Sou o ChatBoB, como posso te chamar?",
    }
    return {
        "last_user_message": "",
        "last_asked_question": "",
        "schema": schema,
        "extracted": {},
        "missing_fields": [],
        "question_to_ask": None,
        "final_json": None,
        "context_messages": [greeting],
        "status_finished": False,
        "next": None,
        "logs": [],
        "_session_saved": False,
    }


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


def _save_finished_session(state: Dict[str, Any]) -> None:
    if not state.get("status_finished") or state.get("final_json") is None or state.get("_session_saved"):
        return
    try:
        save_session_data(state)
    except Exception:
        raise HTTPException(status_code=500, detail="Falha ao salvar os dados da sessão.") from None
    state["_session_saved"] = True


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/start")
def start_session(request: SessionRequest) -> Dict[str, Any]:
    session_id = request.session_id.strip()
    if not session_id:
        raise HTTPException(status_code=422, detail="session_id não pode ficar vazio.")

    with session_lock:
        state = sessions.get(session_id)
        if state is not None:
            return _response(session_id, state)

        active_session = next(
            (key for key, value in sessions.items() if not value.get("status_finished")),
            None,
        )
        if active_session is not None:
            raise HTTPException(status_code=409, detail="Já existe uma sessão ativa.")

        state = _new_state()
        sessions[session_id] = state
        greeting = state["context_messages"][0]["content"]
        return _response(session_id, state, greeting)


@app.post("/message")
def send_message(request: MessageRequest) -> Dict[str, Any]:
    session_id = request.session_id.strip()
    message = request.message.strip()
    if not session_id or not message:
        raise HTTPException(status_code=422, detail="session_id e message não podem ficar vazios.")

    with session_lock:
        state = sessions.get(session_id)
        if state is None:
            raise HTTPException(status_code=404, detail="Sessão não encontrada. Inicie uma sessão primeiro.")

        if state.get("status_finished"):
            return _response(session_id, state)

        updated_state = copy.deepcopy(state)
        try:
            updates = agent.feed_message(message, updated_state)
            if isinstance(updates, dict):
                updated_state.update(updates)
        except Exception:
            raise HTTPException(status_code=500, detail="Falha ao processar a mensagem.") from None

        sessions[session_id] = updated_state
        result = _response(session_id, updated_state)
        _save_finished_session(updated_state)
        return result