from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = (
        "postgresql+psycopg://motorloop:motorloop-local-only@127.0.0.1:15432/motorloop"
    )
    redis_url: str = "redis://127.0.0.1:6379/0"
    redis_connect_timeout: float = Field(default=2, gt=0, le=30)
    redis_socket_timeout: float = Field(default=5, gt=1, le=60)
    redis_max_connections: int = Field(default=256, ge=10, le=10000)
    websocket_auth_interval: float = Field(default=15, ge=1, le=30)
    jwt_secret: str = "local-development-key-change-before-any-deployment"
    public_origin: str = "http://localhost:8080"
    storage_endpoint: str = "http://localhost:9000"
    storage_public_endpoint: str = "http://localhost:9000"
    storage_access_key: str = "local-motorloop"
    storage_secret_key: str = "local-motorloop-storage-only"
    storage_region: str = "eu-west-1"
    source_bucket: str = "sources"
    playback_bucket: str = "playback"
    media_public_url: str = "http://localhost:8080/media"
    access_minutes: int = 10
    refresh_days: int = 14
    sentry_dsn: str = ""
    otel_endpoint: str = ""
    seed_enabled: bool = True

    @model_validator(mode="after")
    def production_guard(self) -> "Settings":
        if self.app_env == "production":
            raise ValueError(
                "Production adapters are not implemented in this scaffold. "
                "Complete docs/09-scaffold.md release gates before enabling production."
            )
        return self


@lru_cache
def settings() -> Settings:
    return Settings()
