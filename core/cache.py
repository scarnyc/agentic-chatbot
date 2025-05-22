# core/cache.py

import time
import hashlib
import json
import logging
from typing import Any, Optional, Dict, Tuple
from dataclasses import dataclass
from threading import Lock

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Represents a cache entry with data and metadata."""
    data: Any
    timestamp: float
    ttl: float  # Time to live in seconds
    access_count: int = 0
    last_accessed: float = None
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return time.time() - self.timestamp > self.ttl
    
    def access(self) -> Any:
        """Mark entry as accessed and return data."""
        self.access_count += 1
        self.last_accessed = time.time()
        return self.data

class SimpleCache:
    """
    Simple in-memory cache with TTL support for API results.
    Thread-safe implementation for concurrent access.
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 3600):
        """
        Initialize cache.
        Args:
            max_size: Maximum number of entries to store
            default_ttl: Default time-to-live in seconds (1 hour)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size': 0
        }
    
    def _generate_key(self, prefix: str, query: str, **kwargs) -> str:
        """Generate a cache key from prefix, query, and parameters."""
        # Create a consistent key by sorting kwargs
        params = json.dumps(kwargs, sort_keys=True) if kwargs else ""
        content = f"{prefix}:{query}:{params}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _cleanup_expired(self):
        """Remove expired entries from cache."""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if current_time - entry.timestamp > entry.ttl
        ]
        
        for key in expired_keys:
            del self._cache[key]
            self._stats['evictions'] += 1
        
        self._stats['size'] = len(self._cache)
    
    def _evict_lru(self):
        """Evict least recently used entries if cache is full."""
        if len(self._cache) >= self.max_size:
            # Sort by last_accessed (None values go to end)
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: x[1].last_accessed or 0
            )
            
            # Remove oldest 20% of entries
            remove_count = max(1, len(sorted_entries) // 5)
            for key, _ in sorted_entries[:remove_count]:
                del self._cache[key]
                self._stats['evictions'] += 1
        
        self._stats['size'] = len(self._cache)
    
    def get(self, prefix: str, query: str, **kwargs) -> Optional[Any]:
        """
        Get cached result.
        Args:
            prefix: Cache namespace (e.g., 'wikipedia', 'tavily')
            query: The search query
            **kwargs: Additional parameters that affect the result
        Returns:
            Cached data if found and not expired, None otherwise
        """
        key = self._generate_key(prefix, query, **kwargs)
        
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if not entry.is_expired():
                    self._stats['hits'] += 1
                    logger.debug(f"Cache HIT for {prefix}:{query[:50]}...")
                    return entry.access()
                else:
                    # Remove expired entry
                    del self._cache[key]
                    self._stats['evictions'] += 1
            
            self._stats['misses'] += 1
            logger.debug(f"Cache MISS for {prefix}:{query[:50]}...")
            return None
    
    def set(self, prefix: str, query: str, data: Any, ttl: Optional[float] = None, **kwargs):
        """
        Store result in cache.
        Args:
            prefix: Cache namespace
            query: The search query
            data: Data to cache
            ttl: Time to live (uses default if None)
            **kwargs: Additional parameters
        """
        if data is None:
            return  # Don't cache None results
        
        key = self._generate_key(prefix, query, **kwargs)
        ttl = ttl or self.default_ttl
        
        with self._lock:
            # Clean up expired entries
            self._cleanup_expired()
            
            # Evict if necessary
            self._evict_lru()
            
            # Store new entry
            self._cache[key] = CacheEntry(
                data=data,
                timestamp=time.time(),
                ttl=ttl,
                last_accessed=time.time()
            )
            
            self._stats['size'] = len(self._cache)
            logger.debug(f"Cache SET for {prefix}:{query[:50]}... (TTL: {ttl}s)")
    
    def invalidate(self, prefix: str, query: str = None, **kwargs):
        """
        Invalidate cache entries.
        Args:
            prefix: Cache namespace
            query: Specific query to invalidate (all if None)
            **kwargs: Additional parameters
        """
        with self._lock:
            if query is None:
                # Invalidate all entries with prefix
                keys_to_remove = [
                    key for key in self._cache.keys()
                    if key.startswith(f"{prefix}:")
                ]
            else:
                # Invalidate specific entry
                key = self._generate_key(prefix, query, **kwargs)
                keys_to_remove = [key] if key in self._cache else []
            
            for key in keys_to_remove:
                del self._cache[key]
                self._stats['evictions'] += 1
            
            self._stats['size'] = len(self._cache)
            logger.info(f"Invalidated {len(keys_to_remove)} entries for {prefix}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                **self._stats,
                'hit_rate_percent': round(hit_rate, 2),
                'total_requests': total_requests,
                'max_size': self.max_size,
                'default_ttl': self.default_ttl
            }
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            cleared_count = len(self._cache)
            self._cache.clear()
            self._stats = {
                'hits': 0,
                'misses': 0,
                'evictions': 0,
                'size': 0
            }
            logger.info(f"Cleared {cleared_count} cache entries")

# Global cache instance
cache = SimpleCache(
    max_size=1000,  # Store up to 1000 entries
    default_ttl=3600  # 1 hour default TTL
)

def get_cache_stats() -> Dict[str, Any]:
    """Get global cache statistics."""
    return cache.get_stats()

def clear_cache():
    """Clear global cache."""
    cache.clear()