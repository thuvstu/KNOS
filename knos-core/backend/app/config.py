# backend/app/config.py
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://knos:password@localhost:5432/knos",
        alias="DATABASE_URL",
    )

    # Gemini
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    embedding_model: str = Field(
        default="gemini-embedding-2-preview", alias="EMBEDDING_MODEL"
    )
    embedding_dimension: int = Field(default=768, alias="EMBEDDING_DIMENSION")
    llm_model: str = Field(default="gemini-2.5-flash", alias="LLM_MODEL")

    # ollama (optional local LLM)
    ollama_base_url: str = Field(default="", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="qwen2.5:7b", alias="OLLAMA_MODEL")

    # Cloudflare Access
    cf_team_domain: str = Field(default="", alias="CF_TEAM_DOMAIN")
    cf_aud: str = Field(default="", alias="CF_AUD")

    # App
    debug: bool = Field(default=False, alias="DEBUG")
    auto_connect_enabled: bool = Field(default=False, alias="AUTO_CONNECT_ENABLED")
    auto_connect_threshold: float = Field(default=0.82, alias="AUTO_CONNECT_THRESHOLD")

    # Embedding queue
    embedding_queue_interval: float = Field(default=1.0, alias="EMBEDDING_QUEUE_INTERVAL")
    embedding_max_rpm: int = Field(default=10, alias="EMBEDDING_MAX_RPM")

    # YouTube (optional)
    youtube_api_key: str = Field(default="", alias="YOUTUBE_API_KEY")

    class Config:
        env_file = ".env"
        populate_by_name = True
        extra = "ignore"



@lru_cache
def get_settings() -> Settings:
    return Settings()
