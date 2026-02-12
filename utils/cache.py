"""Simple caching utilities for API responses and configuration."""

import json
import time
from pathlib import Path
from typing import Any, Optional


class APICache:
    """Simple file-based cache for API responses with TTL support."""

    def __init__(self, cache_dir: Optional[Path] = None, default_ttl: int = 300):
        """Initialize cache.

        Args:
            cache_dir: Directory to store cache files (default: .cache in project root)
            default_ttl: Default time-to-live in seconds (default: 5 minutes)
        """
        if cache_dir is None:
            project_root = Path(__file__).resolve().parent.parent
            cache_dir = project_root / ".cache"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.default_ttl = default_ttl

    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for a key."""
        # Use hash to handle special characters in key
        import hashlib
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"

    def get(self, key: str, ttl: Optional[int] = None) -> Optional[Any]:
        """Get cached value if it exists and hasn't expired.

        Args:
            key: Cache key (e.g., "orgs/123/sites")
            ttl: Time-to-live in seconds (uses default_ttl if None)

        Returns:
            Cached value or None if not found/expired
        """
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r") as f:
                cached = json.load(f)

            # Check if expired
            ttl = ttl if ttl is not None else self.default_ttl
            age = time.time() - cached["timestamp"]

            if age > ttl:
                # Expired, remove file
                cache_path.unlink()
                return None

            return cached["data"]

        except (json.JSONDecodeError, KeyError, OSError):
            # Corrupted cache, remove it
            cache_path.unlink(missing_ok=True)
            return None

    def set(self, key: str, value: Any) -> None:
        """Store value in cache.

        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
        """
        cache_path = self._get_cache_path(key)

        cached = {
            "timestamp": time.time(),
            "key": key,  # Store original key for debugging
            "data": value
        }

        try:
            with open(cache_path, "w") as f:
                json.dump(cached, f, indent=2)
        except (OSError, TypeError) as e:
            # Failed to cache, but don't fail the operation
            print(f"Warning: Failed to cache {key}: {e}")

    def delete(self, key: str) -> None:
        """Delete cached value.

        Args:
            key: Cache key
        """
        cache_path = self._get_cache_path(key)
        cache_path.unlink(missing_ok=True)

    def clear(self) -> None:
        """Clear all cached values."""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()

    def invalidate_pattern(self, pattern: str) -> None:
        """Invalidate all cache entries matching a pattern.

        Args:
            pattern: Pattern to match against original keys (checks metadata)
        """
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, "r") as f:
                    cached = json.load(f)
                    if pattern in cached.get("key", ""):
                        cache_file.unlink()
            except (json.JSONDecodeError, OSError):
                pass


def cached_api_call(cache: APICache, key: str, fn, *args, ttl: Optional[int] = None, **kwargs):
    """Execute function with caching.

    Args:
        cache: APICache instance
        key: Cache key
        fn: Function to call if cache miss
        *args, **kwargs: Arguments to pass to fn
        ttl: Cache TTL in seconds

    Returns:
        Cached or fresh result

    Example:
        cache = APICache()
        sites = cached_api_call(
            cache,
            f"orgs/{org_id}/sites",
            lambda: session.get(f"{api_root}/api/v1/orgs/{org_id}/sites").json(),
            ttl=600
        )
    """
    cached_value = cache.get(key, ttl=ttl)

    if cached_value is not None:
        print(f"✓ Cache hit: {key}")
        return cached_value

    print(f"→ Cache miss: {key}, fetching...")
    result = fn(*args, **kwargs)
    cache.set(key, result)

    return result
