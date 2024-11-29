# app/services/cache_service.py

import redis
import json
import logging
from typing import Optional
from datetime import timedelta

class CacheService:
    def __init__(self, host='localhost', port=6379, db=0):
        self.redis = redis.Redis(host=host, port=port, db=db)
        self.default_ttl = timedelta(hours=24)

    async def get_result(self, url: str, search_term: str) -> Optional[dict]:
        try:
            key = self._make_key(url, search_term)
            data = self.redis.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logging.error(f"Cache get error: {e}")
            return None

    async def store_result(self, url: str, search_term: str, result: dict):
        try:
            key = self._make_key(url, search_term)
            self.redis.setex(
                key,
                self.default_ttl,
                json.dumps(result)
            )
        except Exception as e:
            logging.error(f"Cache store error: {e}")

    def _make_key(self, url: str, search_term: str) -> str:
        return f"search:{url}:{search_term}"

    async def clear_expired(self):
        """Очистка устаревших записей"""
        try:
            script = """
            local keys = redis.call('KEYS', 'search:*')
            local deleted = 0
            for i, key in ipairs(keys) do
                if redis.call('TTL', key) <= 0 then
                    redis.call('DEL', key)
                    deleted = deleted + 1
                end
            end
            return deleted
            """
            deleted = self.redis.eval(script, 0)
            logging.info(f"Cleared {deleted} expired cache entries")
        except Exception as e:
            logging.error(f"Cache cleanup error: {e}")
