from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AI Developer Debugging Assistant"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # # OpenAI
    # OPENAI_API_KEY: str
    # OPENAI_MODEL: str = "gpt-4o"

    # LLM — set LLM_BASE_URL to use a local/alternative provider (e.g. Ollama)
    OPENAI_API_KEY: str = "ollama"  # ignored when using a local provider
    OPENAI_MODEL: str = "llama3.2"  # override with any model served by your provider
    OPENAI_MAX_TOKENS: int = 4096
    OPENAI_TEMPERATURE: float = 0.2
    LLM_BASE_URL: Optional[str] = "http://localhost:11434/v1"  # None → use OpenAI
    LLM_JSON_MODE: bool = False  # set True only if your model supports response_format json_object

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/debugassistant"

    # Redis (optional)
    REDIS_URL: Optional[str] = None
    CACHE_TTL: int = 3600

    # Log Processing
    MAX_LOG_SIZE_MB: int = 10
    MAX_CHUNK_TOKENS: int = 6000

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
