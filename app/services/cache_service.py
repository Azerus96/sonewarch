# app/services/cache_service.py

import os
import json
import logging
from typing import Optional, Any, Dict
from datetime import timedelta
from redis import Redis
from collections import defaultdict
from functools import wraps

def handle_cache_errors(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Cache error in {func.__name__}: {str(e)}")
            return None
    return wrapper

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
        self.stats = defaultdict(int)

    @handle_cache_errors
    async def get_result(self, url: str, search_term: str) -> Optional[dict]:
        """Получение результата из кэша"""
        key = self._make_key(url, search_term)
        data = await self.redis.get(key)
        
        if data:
            self.stats['cache_hits'] += 1
            self.logger.debug(f"Cache hit for {key}")
            return json.loads(data)
            
        self.stats['cache_misses'] += 1
        self.logger.debug(f"Cache miss for {key}")
        return None

    @handle_cache_errors
    async def store_result(self, url: str, search_term: str, result: dict) -> None:
        """Сохранение результата в кэш"""
        key = self._make_key(url, search_term)
        await self.redis.setex(
            key,
            int(self.default_ttl.total_seconds()),
            json.dumps(result)
        )
        self.stats['cache_writes'] += 1
        self.logger.debug(f"Stored in cache: {key}")

    @handle_cache_errors
    async def get_multiple(self, urls: list[str], search_term: str) -> Dict[str, Any]:
        """Пакетное получение результатов из кэша"""
        pipeline = self.redis.pipeline()
        keys = [self._make_key(url, search_term) for url in urls]
        
        for key in keys:
            pipeline.get(key)
        
        results = await pipeline.execute()
        
        return {
            url: json.loads(result) if result else None
            for url, result in zip(urls, results)
        }

    @handle_cache_errors
    async def store_multiple(self, results: Dict[str, dict], search_term: str) -> None:
        """Пакетное сохранение результатов в кэш"""
        pipeline = self.redis.pipeline()
        
        for url, result in results.items():
            key = self._make_key(url, search_term)
            pipeline.setex(
                key,
                int(self.default_ttl.total_seconds()),
                json.dumps(result)
            )
        
        await pipeline.execute()
        self.stats['cache_batch_writes'] += 1
        self.logger.debug(f"Stored {len(results)} results in cache")

    @handle_cache_errors
    async def invalidate(self, url: str, search_term: str) -> None:
        """Инвалидация кэша для конкретного URL и поискового запроса"""
        key = self._make_key(url, search_term)
        await self.redis.delete(key)
        self.stats['cache_invalidations'] += 1
        self.logger.debug(f"Invalidated cache for {key}")

    @handle_cache_errors
    async def clear_all(self) -> None:
        """Очистка всего кэша"""
        async for key in self.redis.scan_iter(f"{self.cache_prefix}*"):
            await self.redis.delete(key)
        self.stats['cache_clears'] += 1
        self.logger.info("Cleared all cache")

    @handle_cache_errors
    async def get_stats(self) -> dict:
        """Получение статистики кэша"""
        total_keys = 0
        total_size = 0
        
        async for key in self.redis.scan_iter(f"{self.cache_prefix}*"):
            total_keys += 1
            value = await self.redis.get(key)
            total_size += len(value) if value else 0

        stats = {
            "total_entries": total_keys,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "hits": self.stats['cache_hits'],
            "misses": self.stats['cache_misses'],
            "writes": self.stats['cache_writes'],
            "batch_writes": self.stats['cache_batch_writes'],
            "invalidations": self.stats['cache_invalidations'],
            "clears": self.stats['cache_clears'],
            "hit_rate": self._calculate_hit_rate()
        }
        
        return stats

    def _calculate_hit_rate(self) -> float:
        """Расчет процента попаданий в кэш"""
        total_requests = self.stats['cache_hits'] + self.stats['cache_misses']
        if total_requests == 0:
            return 0.0
        return round((self.stats['cache_hits'] / total_requests) * 100, 2)

    @handle_cache_errors
    async def get_or_set(self, url: str, search_term: str, getter_func) -> Optional[dict]:
        """Получение из кэша или вычисление и сохранение результата"""
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

    @handle_cache_errors
    async def set_ttl(self, url: str, search_term: str, ttl: int) -> bool:
        """Установка времени жизни для конкретного кэша"""
        key = self._make_key(url, search_term)
        return await self.redis.expire(key, ttl)

    @handle_cache_errors
    async def get_ttl(self, url: str, search_term: str) -> int:
        """Получение оставшегося времени жизни кэша"""
        key = self._make_key(url, search_term)
        return await self.redis.ttl(key)

    @handle_cache_errors
    async def cleanup_expired(self) -> int:
        """Очистка просроченных записей"""
        deleted_count = 0
        async for key in self.redis.scan_iter(f"{self.cache_prefix}*"):
            if await self.redis.ttl(key) <= 0:
                await self.redis.delete(key)
                deleted_count += 1
        
        self.logger.info(f"Cleaned up {deleted_count} expired cache entries")
        return deleted_count

    # app/services/cache_service.py (продолжение)

    def _make_key(self, url: str, search_term: str) -> str:
        """Создание ключа для кэша"""
        return f"{self.cache_prefix}{url}:{search_term}"

    @handle_cache_errors
    async def monitor_size(self, max_size_mb: int = 100) -> dict:
        """Мониторинг размера кэша"""
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
            # Автоматическая очистка при превышении размера
            await self._cleanup_by_size(max_size_mb)
            
        return status

    @handle_cache_errors
    async def _cleanup_by_size(self, max_size_mb: int) -> None:
        """Очистка кэша при превышении размера"""
        current_size_mb = (await self.get_stats())['total_size_mb']
        
        if current_size_mb <= max_size_mb:
            return

        # Получаем все ключи с их TTL
        keys_ttl = []
        async for key in self.redis.scan_iter(f"{self.cache_prefix}*"):
            ttl = await self.redis.ttl(key)
            keys_ttl.append((key, ttl))
        
        # Сортируем по TTL (сначала удаляем с меньшим временем жизни)
        keys_ttl.sort(key=lambda x: x[1])
        
        # Удаляем ключи, пока размер не станет приемлемым
        for key, _ in keys_ttl:
            await self.redis.delete(key)
            current_size_mb = (await self.get_stats())['total_size_mb']
            if current_size_mb <= max_size_mb:
                break

    @handle_cache_errors
    async def get_keys_by_pattern(self, pattern: str) -> list[str]:
        """Получение ключей по паттерну"""
        keys = []
        async for key in self.redis.scan_iter(f"{self.cache_prefix}{pattern}"):
            keys.append(key)
        return keys

    @handle_cache_errors
    async def get_cache_info(self) -> dict:
        """Получение подробной информации о состоянии кэша"""
        stats = await self.get_stats()
        keys_by_type = defaultdict(int)
        sizes_by_type = defaultdict(int)
        
        async for key in self.redis.scan_iter(f"{self.cache_prefix}*"):
            key_type = key.split(':')[1] if ':' in key else 'unknown'
            keys_by_type[key_type] += 1
            
            value = await self.redis.get(key)
            sizes_by_type[key_type] += len(value) if value else 0

        return {
            "general_stats": stats,
            "keys_by_type": dict(keys_by_type),
            "sizes_by_type": {k: round(v / (1024 * 1024), 2) 
                             for k, v in sizes_by_type.items()},
            "performance": {
                "hit_rate": self._calculate_hit_rate(),
                "operations_per_second": self._calculate_ops_rate()
            }
        }

    def _calculate_ops_rate(self) -> float:
        """Расчет количества операций в секунду"""
        total_ops = (self.stats['cache_hits'] + 
                    self.stats['cache_misses'] + 
                    self.stats['cache_writes'])
        # Предполагаем, что статистика собирается с момента создания объекта
        time_running = (time.time() - self._start_time)
        if time_running == 0:
            return 0.0
        return round(total_ops / time_running, 2)

    @handle_cache_errors
    async def optimize(self) -> dict:
        """Оптимизация кэша"""
        before_stats = await self.get_stats()
        
        # Удаление устаревших записей
        expired_cleaned = await self.cleanup_expired()
        
        # Очистка записей с низким hit rate
        low_hit_rate_cleaned = await self._cleanup_low_hit_rate()
        
        after_stats = await self.get_stats()
        
        return {
            "space_saved_mb": round(
                before_stats['total_size_mb'] - after_stats['total_size_mb'], 
                2
            ),
            "expired_cleaned": expired_cleaned,
            "low_hit_rate_cleaned": low_hit_rate_cleaned,
            "before_stats": before_stats,
            "after_stats": after_stats
        }

    async def _cleanup_low_hit_rate(self, threshold: float = 0.1) -> int:
        """Очистка записей с низким hit rate"""
        cleaned = 0
        async for key in self.redis.scan_iter(f"{self.cache_prefix}*"):
            if key in self.stats and self.stats[key]['hits'] > 0:
                hit_rate = (self.stats[key]['hits'] / 
                          (self.stats[key]['hits'] + self.stats[key]['misses']))
                if hit_rate < threshold:
                    await self.redis.delete(key)
                    cleaned += 1
        return cleaned

    def __del__(self):
        """Закрытие соединения при удалении объекта"""
        try:
            self.redis.close()
        except:
            pass
