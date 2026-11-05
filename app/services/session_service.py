import copy
import logging
from threading import Lock
from typing import Any, Callable, Dict, Optional, Tuple


logger = logging.getLogger(__name__)


class SessionServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class SessionService:
    def __init__(
        self,
        agent: Any,
        save_session: Callable[[Dict[str, Any]], Any],
    ):
        self.agent = agent
        self.save_session = save_session
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.session_locks: Dict[str, Lock] = {}
        self.lock = Lock()

    def _new_state(self, schema: Any) -> Dict[str, Any]:
        greeting = {
            "role": "assistant",
            "content": "Olá! Sou o ChatBoB 🤖\n\nPara coletar suas respostas, funciona assim:\n\n- eu faço uma pergunta por vez;\n- você responde com suas palavras.\n\nPodemos começar?",
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

    def start(self, session_id: str, schema: Any) -> Tuple[Dict[str, Any], Optional[str]]:
        with self.lock:
            state = self.sessions.get(session_id)
            if state is not None:
                return state, None

            state = self._new_state(schema)
            self.sessions[session_id] = state
            self.session_locks[session_id] = Lock()
            greeting = state["context_messages"][0]["content"]
            return state, greeting

    def process_message(self, session_id: str, message: str) -> Dict[str, Any]:
        with self.lock:
            session_lock = self.session_locks.get(session_id)
        if session_lock is None:
            raise SessionServiceError(
                404,
                "Sessão não encontrada. Inicie uma sessão primeiro.",
            )

        with session_lock:
            state = self.sessions[session_id]

            if state.get("status_finished"):
                # Tenta de novo se o salvamento falhou no turno que concluiu.
                self._save_finished_session(session_id, state)
                return state

            updated_state = copy.deepcopy(state)
            try:
                updates = self.agent.feed_message(message, updated_state)
                if isinstance(updates, dict):
                    updated_state.update(updates)
            except Exception:
                logger.exception("Falha ao processar a mensagem da sessão %s", session_id)
                raise SessionServiceError(500, "Falha ao processar a mensagem.") from None

            with self.lock:
                self.sessions[session_id] = updated_state
            self._save_finished_session(session_id, updated_state)
            return updated_state

    def _save_finished_session(self, session_id: str, state: Dict[str, Any]) -> None:
        if (
            not state.get("status_finished")
            or state.get("final_json") is None
            or state.get("_session_saved")
        ):
            return
        try:
            self.save_session(state)
        except Exception:
            logger.exception("Falha ao salvar os dados da sessão %s", session_id)
            raise SessionServiceError(
                500,
                "Falha ao salvar os dados da sessão.",
            ) from None
        state["_session_saved"] = True