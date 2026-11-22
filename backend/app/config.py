import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables and .env file.
    All runtime parameters, timeouts, concurrency limits, and provider settings
    are centrally configured here without any hardcoded values in business logic.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Bildx AI Image-Ad Generator"
    APP_ENV: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # AI Provider configuration: 'fake', 'gemini', 'openai'
    AI_PROVIDER: str = "fake"

    # Concurrency and Queue bounds
    MAX_CONCURRENT_PROVIDER_CALLS: int = 3
    MAX_QUEUE_CAPACITY: int = 20

    # Timeouts (in seconds)
    PROVIDER_TIMEOUT_SECONDS: float = 15.0
    IMAGE_DOWNLOAD_TIMEOUT_SECONDS: float = 10.0
    IMAGE_DOWNLOAD_MAX_BYTES: int = 10 * 1024 * 1024  # 10 MB strict limit

    # Retry policy for transient failures
    MAX_RETRIES: int = 3
    RETRY_INITIAL_DELAY_SECONDS: float = 0.5
    RETRY_BACKOFF_FACTOR: float = 2.0

    # Storage paths
    OUTPUT_DIR: str = str(Path(__file__).resolve().parent.parent / "output_ads")

    # Real Provider credentials & models (read from environment, never committed)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"

    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # CORS settings
    CORS_ORIGINS: List[str] = ["*"]


# Singleton settings instance
settings = Settings()
os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
