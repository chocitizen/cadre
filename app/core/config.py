from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    env: str = "development"
    app_name: str = "CADRE Core"
    database_url: str = "sqlite:///./cadre.db"
    api_prefix: str = "/api/v1"
    operations_state_path: str = "/run/lanseir/state/mission-control.json"
    release_id: str = "development"
    api_tokens_json: str = "{}"
    max_request_body_bytes: int = 1_048_576

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CADRE_",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
