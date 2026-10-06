from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MADLAD Translation API"
    app_version: str = "1.0.0"

    model_name: str = "google/madlad400-3b-mt"

    target_language: str = "th"

    max_input_tokens: int = 1024
    max_new_tokens: int = 512

    num_beams: int = 4

    max_batch_size: int = 8
    max_concurrent_inference: int = 1

    device: str = "auto"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()