from dataclasses import dataclass
import os
from dotenv import load_dotenv

# Загружаем .env из корня проекта
load_dotenv()


@dataclass
class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    backend_url: str = os.getenv("BACKEND_URL", "http://localhost:3000/ask")


settings = Settings()
