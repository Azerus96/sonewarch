# app/services/cache_service.py

import os
import json
import logging
from typing import Optional, Any
from datetime import timedelta
from redis import Redis
from ..utils.error_handler import handle_errors

class CacheService:
    def __init__(self):
        self.redis = Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=int(os.getenv('REDIS_DB', 0)),
            decode_responses=True
        )
        self.logger = logging.getLogger(__name__)
        self.default_ttl = timedelta(hours=24)
        self.cache_prefix = "search_cache:"

    @handle_errors()
    async def get_result(self, url: str, search_term: str) -> Optional[dict]:
        """Получение результата из кэша"""
        try:
            key = self._make_key(url, search_term)
            data = await self.redis.get(key)
            if data:
                self.logger.debug(f"Cache hit for {key}")
                return json.loads(data)
            self.logger.debug(f"Cache miss for {key}")
            return None
        except Exception as e:
            self.logger.error(f"Error getting from cache: {e}")
            return None

    @handle_errors()
    async def store_result(self, url: str, search_term: str, result: dict) -> None:
        """Сохранение результата в кэш"""
        try:
            key = self._make_key(url, search_term)
            await self.redis.setex(
                key,
                int(self.default_ttl.total_seconds()),
                json.dumps(result)
            )
            self.logger.debug(f"Stored in cache: {key}")
        except Exception as e:
            self.logger.error(f"Error storing in cache: {e}")

    @handle_errors()
    async def invalidate(self, url: str, search_term: str) -> None:
        """Инвалидация кэша для конкретного URL и поискового запроса"""
        try:
            key = self._make_key(url, search_term)
            await self.redis.delete(key)
            self.logger.debug(f"Invalidated cache for {key}")
        except Exception as e:
            self.logger.error(f"Error invalidating cache: {e}")

    @handle_errors()
    async def clear_all(self) -> None:
        """Очистка всего кэша"""
        try:
            async for key in self.redis.scan_iter(f"{self.cache_prefix}*"):
                await self.redis.delete(key)
            self.logger.info("Cleared all cache")
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")

    def _make_key(self, url: str, search_term: str) -> str:
        """Создание ключа для кэша"""
        return f"{self.cache_prefix}{url}:{search_term}"

# app/services/cache_service.py (продолжение)

    @handle_errors()
    async def get_stats(self) -> dict:
        """Получение статистики кэша"""
        try:
            total_keys = 0
            size = 0
            async for key in self.redis.scan_iter(f"{self.cache_prefix}*"):
                total_keys += 1
                value = await self.redis.get(key)
                size += len(value) if value else 0

            return {
                "total_entries": total_keys,
                "total_size_bytes": size,
                "total_size_mb": round(size / (1024 * 1024), 2)
            }
        except Exception as e:
            self.logger.error(f"Error getting cache stats: {e}")
            return {"error": str(e)}

    @handle_errors()
    async def get_multiple(self, urls: list[str], search_term: str) -> dict:
        """Пакетное получение результатов из кэша"""
        try:
            pipeline = self.redis.pipeline()
            keys = [self._make_key(url, search_term) for url in urls]
            
            for key in keys:
                pipeline.get(key)
            
            results = await pipeline.execute()
            
            return {
                url: json.loads(result) if result else None
                for url, result in zip(urls, results)
            }
        except Exception as e:
            self.logger.error(f"Error getting multiple cache entries: {e}")
            return {}

    @handle_errors()
    async def store_multiple(self, results: dict[str, dict], search_term: str) -> None:
        """Пакетное сохранение результатов в кэш"""
        try:
            pipeline = self.redis.pipeline()
            
            for url, result in results.items():
                key = self._make_key(url, search_term)
                pipeline.setex(
                    key,
                    int(self.default_ttl.total_seconds()),
                    json.dumps(result)
                )
            
            await pipeline.execute()
            self.logger.debug(f"Stored {len(results)} results in cache")
        except Exception as e:
            self.logger.error(f"Error storing multiple cache entries: {e}")

    @handle_errors()
    async def get_or_set(self, url: str, search_term: str, getter_func) -> Optional[dict]:
        """Получение из кэша или вычисление и сохранение результата"""
        try:
            # Пробуем получить из кэша
            result = await self.get_result(url, search_term)
            if result is not None:
                return result

            # Если нет в кэше, вычисляем
            result = await getter_func()
            if result is not None:
                # Сохраняем в кэш
                await self.store_result(url, search_term, result)
            
            return result
        except Exception as e:
            self.logger.error(f"Error in get_or_set: {e}")
            return None

    @handle_errors()
    async def set_ttl(self, url: str, search_term: str, ttl: int) -> bool:
        """Установка времени жизни для конкретного кэша"""
        try:
            key = self._make_key(url, search_term)
            return await self.redis.expire(key, ttl)
        except Exception as e:
            self.logger.error(f"Error setting TTL: {e}")
            return False

    @handle_errors()
    async def get_ttl(self, url: str, search_term: str) -> int:
        """Получение оставшегося времени жизни кэша"""
        try:
            key = self._make_key(url, search_term)
            return await self.redis.ttl(key)
        except Exception as e:
            self.logger.error(f"Error getting TTL: {e}")
            return -1

    async def cleanup_expired(self) -> int:
        """Очистка просроченных записей"""
        try:
            deleted_count = 0
            async for key in self.redis.scan_iter(f"{self.cache_prefix}*"):
                if await self.redis.ttl(key) <= 0:
                    await self.redis.delete(key)
                    deleted_count += 1
            
            self.logger.info(f"Cleaned up {deleted_count} expired cache entries")
            return deleted_count
        except Exception as e:
            self.logger.error(f"Error cleaning up expired cache: {e}")
            return -1

    async def monitor_size(self, max_size_mb: int = 100) -> dict:
        """Мониторинг размера кэша"""
        try:
            stats = await self.get_stats()
            current_size_mb = stats.get('total_size_mb', 0)
            
            status = {
                "current_size_mb": current_size_mb,
                "max_size_mb": max_size_mb,
                "usage_percent": round((current_size_mb / max_size_mb) * 100, 2),
                "status": "OK"
            }
            
            if current_size_mb > max_size_mb:
                status["status"] = "WARNING"
                # Можно добавить логику очистки старых записей
                
            return status
        except Exception as e:
            self.logger.error(f"Error monitoring cache size: {e}")
            return {"status": "ERROR", "error": str(e)}
