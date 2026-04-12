"""
LLM Factor Cache - Caching for LLM analysis results
Follows the same pattern as data_cache.py but specialized for LLM factors.
"""

import os
import pickle
import zlib
import hashlib
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

# Default cache TTL: 24 hours (since news and market conditions change daily)
DEFAULT_TTL = 24 * 60 * 60  # seconds

class LLMFactorCache:
    """
    Smart cache for LLM factor predictions.

    Features:
    - Compressed storage (zlib) to save disk space
    - TTL-based expiration (default 24 hours)
    - Hierarchical directory structure to avoid too many files in one directory
    """

    def __init__(
        self,
        cache_dir: str = "data/cache/llm_factors",
        default_ttl: int = DEFAULT_TTL
    ):
        self.cache_dir = cache_dir
        self.default_ttl = default_ttl
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        """Create cache directory if it doesn't exist."""
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_key(self, symbol: str) -> str:
        """Generate a cache key from symbol."""
        # Include date in cache key since factors change daily
        today = datetime.now().strftime("%Y-%m-%d")
        content = f"{symbol}:{today}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> str:
        """Get cache file path with hierarchical structure."""
        # Use first two characters for subdirectory to avoid too many files in one dir
        subdir = cache_key[:2]
        subdir_path = os.path.join(self.cache_dir, subdir)
        os.makedirs(subdir_path, exist_ok=True)
        return os.path.join(subdir_path, f"{cache_key[2:]}.cache")

    def _is_expired(self, timestamp: float, ttl: Optional[int]) -> bool:
        """Check if cache entry is expired."""
        if ttl is None:
            ttl = self.default_ttl
        age = datetime.now().timestamp() - timestamp
        return age > ttl

    def get(self, symbol: str, ttl: Optional[int] = None) -> Optional[Dict[str, float]]:
        """
        Get cached LLM factors for a symbol.

        Args:
            symbol: Stock symbol
            ttl: Custom TTL in seconds (uses default if None)

        Returns:
            Cached factors dict or None if not found/expired
        """
        cache_key = self._get_cache_key(symbol)
        cache_path = self._get_cache_path(cache_key)

        if not os.path.exists(cache_path):
            return None

        try:
            with open(cache_path, 'rb') as f:
                compressed_data = f.read()

            decompressed = zlib.decompress(compressed_data)
            cached_data = pickle.loads(decompressed)

            # Check expiration
            if self._is_expired(cached_data.get('timestamp', 0), ttl):
                os.remove(cache_path)
                return None

            return cached_data.get('factors')

        except Exception as e:
            # If any error reading cache, treat as miss
            try:
                os.remove(cache_path)
            except:
                pass
            return None

    def set(self, symbol: str, factors: Dict[str, float]):
        """
        Save LLM factors to cache.

        Args:
            symbol: Stock symbol
            factors: Dictionary of factor values
        """
        cache_key = self._get_cache_key(symbol)
        cache_path = self._get_cache_path(cache_key)

        cached_data = {
            'symbol': symbol,
            'factors': factors,
            'timestamp': datetime.now().timestamp(),
            'created_at': datetime.now().isoformat()
        }

        try:
            pickled = pickle.dumps(cached_data)
            compressed = zlib.compress(pickled, level=9)
            with open(cache_path, 'wb') as f:
                f.write(compressed)
        except Exception as e:
            print(f"Warning: Failed to cache LLM factors for {symbol}: {e}")

    def clear_expired(self) -> int:
        """
        Clear all expired cache entries.

        Returns:
            Number of expired entries cleared
        """
        cleared = 0
        for root, dirs, files in os.walk(self.cache_dir):
            for file in files:
                if file.endswith('.cache'):
                    path = os.path.join(root, file)
                    try:
                        with open(path, 'rb') as f:
                            compressed_data = f.read()
                        decompressed = zlib.decompress(compressed_data)
                        cached_data = pickle.loads(decompressed)
                        if self._is_expired(cached_data.get('timestamp', 0), None):
                            os.remove(path)
                            cleared += 1
                    except:
                        # Remove corrupted files
                        try:
                            os.remove(path)
                            cleared += 1
                        except:
                            pass
        return cleared

    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about cache usage."""
        total_files = 0
        total_size = 0
        for root, dirs, files in os.walk(self.cache_dir):
            for file in files:
                if file.endswith('.cache'):
                    path = os.path.join(root, file)
                    total_files += 1
                    total_size += os.path.getsize(path)

        return {
            'total_files': total_files,
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024),
            'cache_dir': self.cache_dir
        }

# Global instance
llm_factor_cache = LLMFactorCache()
