import redis.asyncio as redis
from typing import Optional
import asyncio
from ..config import get_settings


class RedisClient:
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.settings = get_settings()
    
    async def connect(self):
        """Initialize Redis connection"""
        if self.redis is None:
            self.redis = redis.from_url(self.settings.redis_url)
            # Test connection
            await self.redis.ping()
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            self.redis = None
    
    async def get(self, key: str):
        """Get value from Redis"""
        await self.connect()
        return await self.redis.get(key)
    
    async def set(self, key: str, value, ex: Optional[int] = None):
        """Set value in Redis"""
        await self.connect()
        return await self.redis.set(key, value, ex=ex)
    
    async def delete(self, key: str):
        """Delete key from Redis"""
        await self.connect()
        return await self.redis.delete(key)
    
    async def zadd(self, key: str, mapping: dict, ex: Optional[int] = None):
        """Add to sorted set"""
        await self.connect()
        result = await self.redis.zadd(key, mapping)
        if ex:
            await self.redis.expire(key, ex)
        return result
    
    async def zrange(self, key: str, min: int, max: int, desc: bool = False, by_score: bool = False):
        """Get range from sorted set"""
        await self.connect()
        if by_score:
            result = await self.redis.zrange(key, min, max, desc=desc, withscores=True, byscore=True)
        else:
            result = await self.redis.zrange(key, min, max, desc=desc, withscores=True)
        
        # Extract just the values (not the scores)
        if result:
            return [item[0] for item in result]
        return []
    
    async def zrem(self, key: str, members: str):
        """Remove from sorted set"""
        await self.connect()
        return await self.redis.zrem(key, members)
    
    async def mget(self, *keys):
        """Get multiple values"""
        await self.connect()
        return await self.redis.mget(*keys)
    
    async def exists(self, key: str):
        """Check if key exists"""
        await self.connect()
        return await self.redis.exists(key)


# Global Redis client instance
_redis_client = RedisClient()


async def get_redis_client() -> RedisClient:
    """Get global Redis client instance"""
    return _redis_client


async def init_redis():
    """Initialize Redis connection"""
    await _redis_client.connect()


async def close_redis():
    """Close Redis connection"""
    await _redis_client.disconnect()