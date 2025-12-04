from typing import Any

from dotenv import load_dotenv
from pydantic import PostgresDsn
from pydantic_settings import BaseSettings

from src.constants import Environment

load_dotenv()

DEFAULT_SUB_DOMAIN: str = "/app"

class Config(BaseSettings):
    DATABASE_URL: PostgresDsn

    SUB_DOMAIN: str = DEFAULT_SUB_DOMAIN
    SITE_DOMAIN: str = "myapp.com"

    ENVIRONMENT: Environment = Environment.PRODUCTION

    SENTRY_DSN: str | None = None

    CORS_ORIGINS: list[str]
    CORS_ORIGINS_REGEX: str | None = None
    CORS_HEADERS: list[str]

    APP_VERSION: str = "2"
    VERSION: str | None

    EMAILJS_USER_ID: str
    EMAILJS_SERVICE_ID: str
    EMAILJS_TEMPLATE_ID: str
    FRONTEND_URL: str = "http://localhost:5173"


settings = Config()

app_configs: dict[str, Any] = {
    "title": "App API",
    "version": settings.VERSION,
}

# if not settings.ENVIRONMENT.is_debug:
#     app_configs["openapi_url"] = None  # hide docs
