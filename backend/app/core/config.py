from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Masco Bot"
    DEBUG: bool = False

    # Telegram Bot
    BOT_TOKEN: str = ""
    WEBAPP_URL: str = ""

    # Database
    DATABASE_URL: str = ""

    # Redis
    REDIS_URL: str = ""

    # Centrifugo
    CENTRIFUGO_URL: str = ""
    CENTRIFUGO_API_KEY: str = ""
    CENTRIFUGO_HMAC_SECRET: str = ""
    CENTRIFUGO_TOKEN_TTL: int = 86400  # 24 hours

    # CORS — Restrict to your frontend domain
    ALLOWED_ORIGINS: List[str] = ["https://your-frontend.com"]

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
    
    # Concurrent chat limit per user (abuse prevention)
    MAX_CONCURRENT_CHATS: int = 1

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    if settings.DATABASE_URL and settings.DATABASE_URL.startswith("postgresql://"):
        settings.DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    return settings
