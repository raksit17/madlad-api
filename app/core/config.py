from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MADLAD Translation API"
    app_version: str = "1.0.0"

    model_name: str = "google/madlad400-3b-mt"

    # Keep MADLAD as the default so existing installations do not change.
    translation_provider: Literal["madlad", "qwen"] = "madlad"

    # Experimental Qwen mode uses an independently running Ollama server.
    qwen_base_url: str = "http://host.docker.internal:11434"
    qwen_model: str = "qwen3.5:4b"
    qwen_timeout_seconds: float = 180.0
    qwen_temperature: float = 0.1
    qwen_context_tokens: int = 4096
    qwen_max_input_chars: int = 8000

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