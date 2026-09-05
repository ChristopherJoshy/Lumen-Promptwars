"""Central settings: env-driven, Docker and bare-metal share one source."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "backend/.env"), extra="ignore")

    app_name: str = "Lumen"
    app_env: str = "dev"
    database_url: str = ""  # empty -> local SQLite fallback (see db/session.py)
    redis_url: str = "redis://localhost:6379/0"
    s3_endpoint: str = ""
    s3_bucket: str = "lumen-media"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_number: str = ""
    google_fact_check_api_key: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    frontend_url: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
