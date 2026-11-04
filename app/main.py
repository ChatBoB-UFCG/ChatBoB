from fastapi import FastAPI

from app.api import router
from app.core.extractor import ExtractorAgent
from app.services.session_service import SessionService
from app.utils.session_storage import save_session_data


def create_app() -> FastAPI:
    application = FastAPI(title="ChatBoB API")
    agent = ExtractorAgent()
    application.state.session_service = SessionService(agent, save_session_data)
    application.include_router(router)
    return application


app = create_app()
