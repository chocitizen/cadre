from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    env: Literal["development", "test", "production"] = "development"
    app_name: str = "LANSEIR"
    database_url: str = "sqlite:///./cadre.db"
    api_prefix: str = "/api/v1"
    operations_state_path: str = "/run/lanseir/state/mission-control.json"
    release_id: str = "development"
    api_tokens_json: str = "{}"
    max_request_body_bytes: int = 1_048_576
    public_url: str = "http://127.0.0.1:8000"
    session_days: int = 30
    admin_emails: str = ""
    gateway_state_key: str = "canonical"
    github_repository: str = ""
    github_token: str = ""
    railway_project_id: str = ""
    railway_environment: str = "staging"
    railway_token: str = ""
    hostinger_ssh_host: str = ""
    hostinger_operations_enabled: bool = False
    last_validated_commit: str = ""
    rollback_reference: str = "archive/pre-lanseir-autonomy-2026-08-28"
    ai_provider: str = "local"
    ai_model: str = "lanseir-reflection-v1"
    ai_base_url: str = "https://api.openai.com/v1"
    ai_api_key: str = ""
    ai_daily_message_limit: int = 40
    auth_rate_limit_per_minute: int = 20
    request_timeout_seconds: int = 30
    expose_development_tokens: bool = False

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_prefix="CADRE_",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
