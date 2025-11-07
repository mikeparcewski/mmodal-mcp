import time
import base64

from cache import Cache

def test_cache_set_and_get():
    """Tests setting and getting an item from the cache."""
    cache = Cache(ttl=10, max_items=4)
    cache.set("key", "value")
    assert cache.get("key") == b"value"

def test_cache_ttl():
    """Tests the TTL functionality of the cache."""
    cache = Cache(ttl=1, max_items=4)
    cache.set("key", b"value")
    time.sleep(1.1)
    assert cache.get("key") is None

def test_cache_get_nonexistent_key():
    """Tests getting a nonexistent key from the cache."""
    cache = Cache()
    assert cache.get("nonexistent") is None

def test_cache_base64():
    """Tests the base64 encoding and decoding."""
    cache = Cache()
    image_data = b"test-image-data"
    cache.set_base64("image_key", image_data)

    base64_data = cache.get_base64("image_key")
    assert base64.b64decode(base64_data) == image_data

def test_cache_eviction_lru():
    """Ensures the cache evicts the least recently used item when full."""
    cache = Cache(ttl=10, max_items=2)
    cache.set("a", b"a")
    cache.set("b", b"b")
    assert cache.get("a") == b"a"  # mark "a" as recently used
    cache.set("c", b"c")  # should evict "b"

    assert cache.get("b") is None
    assert cache.get("a") == b"a"
    assert cache.get("c") == b"c"
