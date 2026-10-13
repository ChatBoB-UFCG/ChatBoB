import os

from fastapi import FastAPI

from app.api import router
from app.core.extractor import ExtractorAgent
from app.core.schema import Schema
from app.services.session_service import SessionService
from app.utils.session_storage import save_session_data


def create_app() -> FastAPI:
    application = FastAPI(title="ChatBoB API")
    schema_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "examples",
        "schema_example.json",
    )
    schema = Schema.load_from_file(schema_path)
    agent = ExtractorAgent(schema)
    application.state.session_service = SessionService(agent, save_session_data, schema)
    application.include_router(router)
    return application


app = create_app()