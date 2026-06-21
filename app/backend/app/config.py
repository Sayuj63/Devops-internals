from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "sim-provisioning-api"
    env: Literal["dev", "staging", "prod", "test"] = "dev"
    log_level: str = "INFO"
    log_format: Literal["json", "pretty"] = "pretty"

    database_url: str = Field(
        default="sqlite+aiosqlite:///./sim_provisioning.db",
        description="Async SQLAlchemy URL. Use postgresql+asyncpg://... in prod.",
    )

    hlr_base_url: str = "http://localhost:9090"
    hlr_timeout_seconds: float = 2.0
    hlr_max_retries: int = 3

    vault_addr: str = "http://localhost:8200"
    vault_token: str | None = None

    msisdn_country_code: str = "+91"
    activation_latency_buckets_seconds: tuple[float, ...] = (
        0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0,
    )

    cors_origins: list[str] = ["*"]
    request_id_header: str = "X-Request-ID"


@lru_cache
def get_settings() -> Settings:
    return Settings()
