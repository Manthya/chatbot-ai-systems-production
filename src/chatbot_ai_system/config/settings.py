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
    ollama_model: str = Field(default="qwen2.5:14b-instruct", env="OLLAMA_MODEL")

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
    database_url: str | None = Field(default=None, env="POSTGRES_URL")

    # Redis Configuration (Phase 2)
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")

    # Phase 5.0: Multimodal & Voice
    media_storage_path: str = Field(default="media", env="MEDIA_STORAGE_PATH")
    max_upload_size_mb: int = Field(default=50, env="MAX_UPLOAD_SIZE_MB")
    supported_image_types: str = "png,jpg,jpeg,gif,webp"
    supported_audio_types: str = "wav,mp3,ogg,m4a,webm"
    supported_video_types: str = "mp4,webm,mov"
    stt_model: str = Field(default="base", env="STT_MODEL")
    stt_device: str = Field(default="cpu", env="STT_DEVICE")
    tts_voice: str = Field(default="en_US-lessac-medium", env="TTS_VOICE")
    vision_model: str = Field(default="llava:7b", env="VISION_MODEL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
