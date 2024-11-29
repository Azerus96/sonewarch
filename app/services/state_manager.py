# app/services/state_manager.py

import os
import json
import time
import logging
from typing import Dict, Optional
from datetime import datetime
from redis import Redis
from dataclasses import dataclass, asdict

@dataclass
class SearchState:
    total_urls: int = 0
    processed_urls: int = 0
    found_results: int = 0
    current_status: str = "waiting"
    start_time: float = 0
    error: Optional[str] = None
    last_update: float = 0

    def to_dict(self) -> dict:
        data = asdict(self)
        data['progress'] = self.calculate_progress()
        data['elapsed_time'] = round(time.time() - self.start_time, 2)
        return data

    def calculate_progress(self) -> float:
        if self.total_urls == 0:
            return 0
        return round((self.processed_urls / self.total_urls) * 100, 2)

class StateManager:
    def __init__(self):
        self.redis = Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=int(os.getenv('REDIS_DB', 0)),
            decode_responses=True
        )
        self.logger = logging.getLogger(__name__)
        self.state_prefix = "search_state:"
        self.expiration_time = 3600  # 1 час

    async def init_search(self, search_id: str) -> None:
        """Инициализация нового поиска"""
        try:
            state = SearchState(start_time=time.time(), last_update=time.time())
            await self._save_state(search_id, state)
            self.logger.info(f"Initialized search state for {search_id}")
        except Exception as e:
            self.logger.error(f"Error initializing search state: {e}")
            raise

    async def get_state(self, search_id: str) -> Optional[dict]:
        """Получение текущего состояния поиска"""
        try:
            data = await self.redis.get(f"{self.state_prefix}{search_id}")
            if not data:
                return None
            return json.loads(data)
        except Exception as e:
            self.logger.error(f"Error getting search state: {e}")
            return None

    async def update_state(self, search_id: str, **kwargs) -> None:
        """Обновление состояния поиска"""
        try:
            current_state = await self.get_state(search_id)
            if not current_state:
                return

            state = SearchState(**current_state)
            for key, value in kwargs.items():
                if hasattr(state, key):
                    setattr(state, key, value)
            
            state.last_update = time.time()
            await self._save_state(search_id, state)
        except Exception as e:
            self.logger.error(f"Error updating search state: {e}")
            raise

    async def _save_state(self, search_id: str, state: SearchState) -> None:
        """Сохранение состояния в Redis"""
        try:
            key = f"{self.state_prefix}{search_id}"
            await self.redis.setex(
                key,
                self.expiration_time,
                json.dumps(state.to_dict())
            )
        except Exception as e:
            self.logger.error(f"Error saving state: {e}")
            raise

    async def mark_completed(self, search_id: str) -> None:
        """Отметить поиск как завершенный"""
        await self.update_state(
            search_id,
            current_status="completed",
            last_update=time.time()
        )

    async def mark_error(self, search_id: str, error: str) -> None:
        """Отметить поиск как завершенный с ошибкой"""
        await self.update_state(
            search_id,
            current_status="error",
            error=error,
            last_update=time.time()
        )

    async def cleanup_old_states(self) -> None:
        """Очистка устаревших состояний"""
        try:
            current_time = time.time()
            async for key in self.redis.scan_iter(f"{self.state_prefix}*"):
                state_data = await self.redis.get(key)
                if state_data:
                    state = json.loads(state_data)
                    if current_time - state['last_update'] > self.expiration_time:
                        await self.redis.delete(key)
        except Exception as e:
            self.logger.error(f"Error cleaning up old states: {e}")
