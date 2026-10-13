import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY não encontrado. Defina a variável de ambiente OPENAI_API_KEY no arquivo .env."
    )

def get_llm():
    return ChatOpenAI(
        model="gpt-4o-mini",
        openai_api_key=API_KEY,
        temperature=0.2,
        max_retries=5,
    )