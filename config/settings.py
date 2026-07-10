"""Application settings using pydantic-settings.

Loads configuration from environment variables and .env file.
"""

from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Global application settings.

    All fields can be overridden via environment variables or a .env file
    placed in the project root.
    """

    # --- App ---
    APP_NAME: str = "QuantInvest"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # --- Server ---
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # --- Auth ---
    SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"  # override in env / .env for production

    # --- Storage ---
    DATA_DIR: str = "./data"
    PARQUET_DIR: str = "./data/parquet"
    DB_URL: str = "sqlite:///./data/market.db"

    # --- Data source ---
    AKSHARE_RATE_LIMIT: float = 0.5  # seconds between requests

    # --- Notifications ---
    NOTIFY_WEBHOOK_URL: Optional[str] = None
    NOTIFY_EMAIL_TO: Optional[str] = None

    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = None

    # --- CORS ---
    CORS_ORIGINS: str = "*"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

    @property
    def cors_origin_list(self) -> List[str]:
        if (self.CORS_ORIGINS or "").strip() == "*":
            return ["*"]
        return [o.strip() for o in (self.CORS_ORIGINS or "").split(",") if o.strip()]


settings = Settings()


def ensure_dirs() -> None:
    """Create the data / parquet directories if missing."""
    for d in (PROJECT_ROOT / "data", PROJECT_ROOT / "data" / "parquet"):
        try:
            d.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
