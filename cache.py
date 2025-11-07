import base64
import time
from collections import OrderedDict
from threading import RLock
from typing import Any, Optional

from config import settings

class CacheEntry:
    def __init__(self, value: bytes, expires_at: Optional[float]):
        self.value = value
        self.expires_at = expires_at

class Cache:
    """Simple in-memory LRU cache with optional TTL."""

    def __init__(self, ttl: int = settings.cache_ttl_seconds, max_items: int = settings.cache_max_items):
        self._ttl = ttl
        self._max_items = max_items
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = RLock()

    def get(self, key: str) -> Optional[bytes]:
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None

            if entry.expires_at is not None and entry.expires_at <= time.time():
                self._store.pop(key, None)
                return None

            # Mark as recently used
            self._store.move_to_end(key)
            return entry.value

    def set(self, key: str, value: str | bytes | bytearray):
        """Adds an item to the cache with a TTL."""
        with self._lock:
            if isinstance(value, str):
                value = value.encode("utf-8")
            elif not isinstance(value, (bytes, bytearray)):
                raise TypeError("Cache values must be bytes, bytearray, or str.")

            expires_at = time.time() + self._ttl if self._ttl > 0 else None
            self._store[key] = CacheEntry(bytes(value), expires_at)
            self._store.move_to_end(key)

            while len(self._store) > self._max_items:
                self._store.popitem(last=False)

    def get_base64(self, key: str) -> Optional[str]:
        """Retrieves a base64 encoded image from the cache."""
        image_data = self.get(key)
        if image_data:
            return base64.b64encode(image_data).decode("utf-8")
        return None

    def set_base64(self, key: str, image_data: bytes):
        """Adds a base64 encoded image to the cache."""
        self.set(key, image_data)

cache = Cache()
