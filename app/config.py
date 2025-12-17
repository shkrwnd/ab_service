"""Configuration management.

Reads settings from env vars. This is intentionally simple.
"""
import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """App settings loaded from environment variables"""
    
    # API tokens - comma separated list
    api_tokens: List[str] = os.getenv(
        "API_TOKEN", 
        "default-dev-token"
    ).split(",")
    
    # Database
    database_url: str = os.getenv(
        "DATABASE_URL", 
        "sqlite:///./ab_testing.db"
    )
    
    # Cache settings
    cache_ttl: int = int(os.getenv("CACHE_TTL", "3600"))
    cache_max_size: int = int(os.getenv("CACHE_MAX_SIZE", "10000"))
    
    # Server
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))


settings = Settings()

