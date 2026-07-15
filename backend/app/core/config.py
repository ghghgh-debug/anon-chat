from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AnonChat TMA"
    DEBUG: bool = True

    # Telegram Bot
    BOT_TOKEN: str = "YOUR_BOT_TOKEN"
    WEBAPP_URL: str = "https://your-app.example.com"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://anon_user:anon_password@localhost:5432/anon_chat"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Centrifugo
    CENTRIFUGO_URL: str = "http://localhost:8000"
    CENTRIFUGO_API_KEY: str = "my_api_key_12345"
    CENTRIFUGO_HMAC_SECRET: str = "my_super_secret_key_12345"
    CENTRIFUGO_TOKEN_TTL: int = 86400  # 24 hours

    # Admin IDs (Telegram user IDs)
    ADMIN_IDS: List[int] = [1394761072, 6276891414, 8649919962]

    # Archive
    ARCHIVE_TTL_DAYS: int = 1  # Auto-delete archive after N days

    # Premium pricing (Telegram Stars)
    PREMIUM_WEEK_PRICE: int = 99
    PREMIUM_MONTH_PRICE: int = 299
    REMOVE_DISLIKE_PRICE: int = 25

    # Rate limiting
    SEARCH_COOLDOWN_SECONDS: int = 5
    REPORT_COOLDOWN_SECONDS: int = 60

    # Media
    MEDIA_UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    # Matching
    ROOM_TTL_SECONDS: int = 300  # Room expires after 5 min if not matched

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
