"""Simple in-memory cache with TTL - could swap to Redis later if needed"""
from typing import Optional, Any
from cachetools import TTLCache
from app.config import settings


# Cache for user assignments - key: "assignment:{experiment_id}:{user_id}"
assignment_cache = TTLCache(
    maxsize=settings.cache_max_size,
    ttl=settings.cache_ttl
)

# Cache for experiment metadata - key: "experiment:{experiment_id}"
experiment_cache = TTLCache(
    maxsize=1000,  # Fewer experiments than assignments
    ttl=settings.cache_ttl * 2  # Experiments change less frequently
)


def get_assignment(experiment_id: int, user_id: str) -> Optional[Any]:
    """Get cached assignment if exists"""
    key = f"assignment:{experiment_id}:{user_id}"
    return assignment_cache.get(key)


def set_assignment(experiment_id: int, user_id: str, value: Any):
    """Cache an assignment"""
    key = f"assignment:{experiment_id}:{user_id}"
    assignment_cache[key] = value


def get_experiment(experiment_id: int) -> Optional[Any]:
    """Get cached experiment if exists"""
    key = f"experiment:{experiment_id}"
    return experiment_cache.get(key)


def set_experiment(experiment_id: int, value: Any):
    """Cache an experiment"""
    key = f"experiment:{experiment_id}"
    experiment_cache[key] = value


def clear_experiment_cache(experiment_id: int):
    """Clear cached experiment (e.g., when updated)"""
    key = f"experiment:{experiment_id}"
    experiment_cache.pop(key, None)

