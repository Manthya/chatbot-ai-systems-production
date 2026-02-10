"""Configuration management for the chatbot system."""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    log_level: str = "INFO"

    # LLM Provider Configuration
    default_llm_provider: str = Field(default="ollama", env="DEFAULT_LLM_PROVIDER")

    # Ollama Configuration
    ollama_base_url: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.2", env="OLLAMA_MODEL")

    # OpenAI Configuration (Phase 3)
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    # Anthropic Configuration (Phase 3)
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-3-haiku-20240307"

    # CORS Configuration
    frontend_url: str = "http://localhost:3000"
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Database Configuration (Phase 2)
    database_url: str | None = None

    # Redis Configuration (Phase 2)
    redis_url: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
