from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Pokédex API"
    app_version: str = "0.1.0"
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+asyncpg://pokedex:pokedex@localhost:5432/pokedex"
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8080"]
    )

    pokeapi_base_url: str = "https://pokeapi.co/api/v2"
    pokeapi_user_agent: str = "pokedex-local/0.1"
    sync_concurrency: int = 4
    sync_page_size: int = 100

    media_root: Path = Path("data/media")
    media_public_path: str = "/media"

    @field_validator("media_public_path")
    @classmethod
    def normalize_media_public_path(cls, value: str) -> str:
        value = "/" + value.strip("/")
        return "" if value == "/" else value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
