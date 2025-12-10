from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    openai_api_key: str
    openai_model: str = "gpt-4o"

    telegram_bot_token: str
    backend_url: str

    serpapi_key: Optional[str] = None  # ← вот это новое поле!

    google_api_key: Optional[str] = None
    google_cse_id: Optional[str] = None

    class Config:
        env_file = ".env"

settings = Settings()
