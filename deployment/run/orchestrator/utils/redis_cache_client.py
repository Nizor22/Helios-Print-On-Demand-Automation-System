"""
Redis Cache Client for Helios Autonomous Store
Provides caching functionality for performance optimization
"""

import json
import time
from typing import Any, Optional, Dict, List
from loguru import logger

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available - caching disabled")


class RedisCacheClient:
    """Redis cache client for Helios system"""
    
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, password: Optional[str] = None):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.client = None
        self.connected = False
        
        if REDIS_AVAILABLE:
            self._connect()
    
    def _connect(self) -> None:
        """Connect to Redis server"""
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.client.ping()
            self.connected = True
            logger.info(f"✅ Connected to Redis at {self.host}:{self.port}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to connect to Redis: {e}")
            self.connected = False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.connected or not self.client:
            return None
        
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"❌ Redis get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL"""
        if not self.connected or not self.client:
            return False
        
        try:
            serialized = json.dumps(value)
            self.client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"❌ Redis set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.connected or not self.client:
            return False
        
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"❌ Redis delete error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.connected or not self.client:
            return False
        
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.error(f"❌ Redis exists error: {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for existing key"""
        if not self.connected or not self.client:
            return False
        
        try:
            return bool(self.client.expire(key, ttl))
        except Exception as e:
            logger.error(f"❌ Redis expire error: {e}")
            return False
    
    async def close(self) -> None:
        """Close Redis connection"""
        if self.client:
            try:
                self.client.close()
                logger.info("✅ Redis connection closed")
            except Exception as e:
                logger.error(f"❌ Redis close error: {e}")
    
    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        return self.connected
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Redis health status"""
        if not self.connected:
            return {"status": "disconnected", "error": "Not connected to Redis"}
        
        try:
            start_time = time.time()
            self.client.ping()
            response_time = (time.time() - start_time) * 1000
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "host": self.host,
                "port": self.port,
                "db": self.db
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
