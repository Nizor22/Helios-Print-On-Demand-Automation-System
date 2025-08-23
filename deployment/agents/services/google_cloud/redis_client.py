from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional, Union
from loguru import logger

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available - caching will be disabled")


class RedisCacheClient:
    """Redis caching client for Helios with advanced features and fallbacks."""
    
    def __init__(self, 
                 host: str = "localhost", 
                 port: int = 6379, 
                 db: int = 0,
                 password: Optional[str] = None,
                 enable_cache: bool = True):
        self.enable_cache = enable_cache and REDIS_AVAILABLE
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0
        }
        
        if not self.enable_cache:
            logger.info("Redis caching disabled - using in-memory fallback")
            self._fallback_cache = {}
            return
            
        try:
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            
            # Test connection
            self.redis_client.ping()
            logger.info(f"Redis connected successfully to {host}:{port}")
            
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self.enable_cache = False
            self._fallback_cache = {}
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache with fallback to in-memory cache."""
        if not self.enable_cache:
            return self._fallback_cache.get(key, default)
        
        try:
            value = self.redis_client.get(key)
            if value is not None:
                self.cache_stats["hits"] += 1
                return json.loads(value)
            else:
                self.cache_stats["misses"] += 1
                return default
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
            self.cache_stats["errors"] += 1
            return self._fallback_cache.get(key, default)
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with TTL."""
        if not self.enable_cache:
            self._fallback_cache[key] = value
            return True
        
        try:
            serialized_value = json.dumps(value)
            if ttl:
                result = self.redis_client.setex(key, ttl, serialized_value)
            else:
                result = self.redis_client.set(key, serialized_value)
            
            if result:
                self.cache_stats["sets"] += 1
                return True
            return False
        except Exception as e:
            logger.error(f"Redis set error for key {key}: {e}")
            self.cache_stats["errors"] += 1
            # Fallback to in-memory cache
            self._fallback_cache[key] = value
            return True
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.enable_cache:
            self._fallback_cache.pop(key, None)
            return True
        
        try:
            result = self.redis_client.delete(key)
            self.cache_stats["deletes"] += 1
            return result > 0
        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {e}")
            self.cache_stats["errors"] += 1
            self._fallback_cache.pop(key, None)
            return True
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.enable_cache:
            return key in self._fallback_cache
        
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Redis exists error for key {key}: {e}")
            self.cache_stats["errors"] += 1
            return key in self._fallback_cache
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for existing key."""
        if not self.enable_cache:
            return True  # In-memory cache doesn't support TTL
        
        try:
            return bool(self.redis_client.expire(key, ttl))
        except Exception as e:
            logger.error(f"Redis expire error for key {key}: {e}")
            self.cache_stats["errors"] += 1
            return False
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache."""
        if not self.enable_cache:
            return {key: self._fallback_cache.get(key) for key in keys}
        
        try:
            values = self.redis_client.mget(keys)
            result = {}
            for key, value in zip(keys, values):
                if value is not None:
                    result[key] = json.loads(value)
                    self.cache_stats["hits"] += 1
                else:
                    self.cache_stats["misses"] += 1
            
            return result
        except Exception as e:
            logger.error(f"Redis get_many error: {e}")
            self.cache_stats["errors"] += 1
            return {key: self._fallback_cache.get(key) for key in keys}
    
    async def set_many(self, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple values in cache."""
        if not self.enable_cache:
            self._fallback_cache.update(data)
            return True
        
        try:
            pipeline = self.redis_client.pipeline()
            for key, value in data.items():
                serialized_value = json.dumps(value)
                if ttl:
                    pipeline.setex(key, ttl, serialized_value)
                else:
                    pipeline.set(key, serialized_value)
            
            results = pipeline.execute()
            self.cache_stats["sets"] += len(data)
            return all(results)
        except Exception as e:
            logger.error(f"Redis set_many error: {e}")
            self.cache_stats["errors"] += 1
            # Fallback to in-memory cache
            self._fallback_cache.update(data)
            return True
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        if not self.enable_cache:
            # Simple pattern matching for in-memory cache
            keys_to_delete = [key for key in self._fallback_cache.keys() if pattern in key]
            for key in keys_to_delete:
                del self._fallback_cache[key]
            return len(keys_to_delete)
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                self.cache_stats["deletes"] += deleted
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Redis clear_pattern error: {e}")
            self.cache_stats["errors"] += 1
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = self.cache_stats.copy()
        
        if self.enable_cache:
            try:
                info = self.redis_client.info()
                stats.update({
                    "redis_version": info.get("redis_version"),
                    "connected_clients": info.get("connected_clients"),
                    "used_memory_human": info.get("used_memory_human"),
                    "keyspace_hits": info.get("keyspace_hits"),
                    "keyspace_misses": info.get("keyspace_misses")
                })
            except Exception as e:
                logger.error(f"Error getting Redis info: {e}")
        
        # Calculate hit rate
        total_requests = stats["hits"] + stats["misses"]
        stats["hit_rate"] = stats["hits"] / total_requests if total_requests > 0 else 0
        
        return stats
    
    def health_check(self) -> Dict[str, Any]:
        """Check cache health status."""
        if not self.enable_cache:
            return {
                "status": "disabled",
                "fallback": "in_memory",
                "message": "Redis caching disabled, using in-memory fallback"
            }
        
        try:
            # Test basic operations
            test_key = f"health_check_{int(time.time())}"
            test_value = {"test": True, "timestamp": time.time()}
            
            # Test set
            set_result = self.redis_client.set(test_key, json.dumps(test_value), ex=10)
            if not set_result:
                raise Exception("Set operation failed")
            
            # Test get
            retrieved = self.redis_client.get(test_key)
            if not retrieved:
                raise Exception("Get operation failed")
            
            # Test delete
            delete_result = self.redis_client.delete(test_key)
            if not delete_result:
                raise Exception("Delete operation failed")
            
            return {
                "status": "healthy",
                "message": "All cache operations working correctly",
                "stats": self.get_stats()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "message": "Cache health check failed"
            }
    
    async def close(self):
        """Close Redis connection."""
        if self.enable_cache and hasattr(self, 'redis_client'):
            try:
                self.redis_client.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")


# Convenience functions for common caching patterns
class CacheManager:
    """High-level cache management with common patterns."""
    
    def __init__(self, redis_client: RedisCacheClient):
        self.redis = redis_client
    
    async def cache_trend_data(self, trend_name: str, data: Any, ttl: int = 3600) -> bool:
        """Cache trend analysis data."""
        key = f"trend:{trend_name}:analysis"
        return await self.redis.set(key, data, ttl)
    
    async def get_cached_trend_data(self, trend_name: str) -> Optional[Any]:
        """Get cached trend analysis data."""
        key = f"trend:{trend_name}:analysis"
        return await self.redis.get(key)
    
    async def cache_printify_catalog(self, catalog_data: Any, ttl: int = 86400) -> bool:
        """Cache Printify catalog data."""
        key = "printify:catalog:products"
        return await self.redis.set(key, catalog_data, ttl)
    
    async def get_cached_printify_catalog(self) -> Optional[Any]:
        """Get cached Printify catalog data."""
        key = "printify:catalog:products"
        return await self.redis.get(key)
    
    async def cache_api_response(self, endpoint: str, params: Dict[str, Any], response: Any, ttl: int = 300) -> bool:
        """Cache API responses with parameter-based keys."""
        # Create a hash of the endpoint and parameters
        import hashlib
        param_str = json.dumps(params, sort_keys=True)
        param_hash = hashlib.md5(param_str.encode()).hexdigest()
        key = f"api:{endpoint}:{param_hash}"
        
        return await self.redis.set(key, response, ttl)
    
    async def get_cached_api_response(self, endpoint: str, params: Dict[str, Any]) -> Optional[Any]:
        """Get cached API response."""
        import hashlib
        param_str = json.dumps(params, sort_keys=True)
        param_hash = hashlib.md5(param_str.encode()).hexdigest()
        key = f"api:{endpoint}:{param_hash}"
        
        return await self.redis.get(key)
    
    async def invalidate_trend_cache(self, trend_name: str = None):
        """Invalidate trend-related cache entries."""
        if trend_name:
            # Invalidate specific trend
            await self.redis.delete(f"trend:{trend_name}:analysis")
        else:
            # Invalidate all trend cache
            await self.redis.clear_pattern("trend:*")
    
    async def invalidate_product_cache(self):
        """Invalidate product-related cache entries."""
        await self.redis.clear_pattern("printify:*")
        await self.redis.clear_pattern("product:*")
