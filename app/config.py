
import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

# def _env(key: str, default: str) -> str:
#     v = os.getenv(key)
#     return v if v is not None else default
#
# def _env_int(key: str, default: int) -> int:
#     try:
#         return int(os.getenv(key, str(default)))
#     except ValueError:
#         return default


class Settings:
    
    # API tokens - comma separated list
    api_tokens: List[str] = os.getenv(
        "API_TOKEN", 
        "default-dev-token"
    ).split(",")
    
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

# settings = Settings()

