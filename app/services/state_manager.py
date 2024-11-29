# app/services/state_manager.py

from dataclasses import dataclass
import json
import time
from typing import Dict, Optional
import asyncio

@dataclass
class SearchState:
    total_urls: int = 0
    processed_urls: int = 0
    found_results: int = 0
    current_status: str = "waiting"
    start_time: float = 0
    error: Optional[str] = None

    def to_dict(self):
        return {
            "total_urls": self.total_urls,
            "processed_urls": self.processed_urls,
            "found_results": self.found_results,
            "current_status": self.current_status,
            "progress": self.calculate_progress(),
            "elapsed_time": round(time.time() - self.start_time, 2),
            "error": self.error
        }

    def calculate_progress(self) -> float:
        if self.total_urls == 0:
            return 0
        return round((self.processed_urls / self.total_urls) * 100, 2)

class StateManager:
    def __init__(self):
        self.states: Dict[str, SearchState] = {}
        self.locks: Dict[str, asyncio.Lock] = {}
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

    async def init_search(self, search_id: str):
        self.states[search_id] = SearchState(start_time=time.time())
        self.locks[search_id] = asyncio.Lock()

    async def update_total_urls(self, search_id: str, total: int):
        async with self.locks[search_id]:
            self.states[search_id].total_urls = total
            self.states[search_id].current_status = "searching"

    async def increment_processed_urls(self, search_id: str):
        async with self.locks[search_id]:
            state = self.states[search_id]
            state.processed_urls += 1
            state.found_results += 1

    async def complete_search(self, search_id: str):
        async with self.locks[search_id]:
            self.states[search_id].current_status = "completed"

    async def fail_search(self, search_id: str, error: str = "Unknown error"):
        async with self.locks[search_id]:
            self.states[search_id].current_status = "error"
            self.states[search_id].error = error

    async def get_state(self, search_id: str) -> Optional[dict]:
        if search_id in self.states:
            return self.states[search_id].to_dict()
        return None

    async def _periodic_cleanup(self):
        while True:
            try:
                current_time = time.time()
                to_remove = [
                    search_id for search_id, state in self.states.items()
                    if current_time - state.start_time > 3600  # 1 час
                ]
                
                for search_id in to_remove:
                    del self.states[search_id]
                    del self.locks[search_id]
                    
                await asyncio.sleep(300)  # Проверка каждые 5 минут
            except Exception as e:
                logging.error(f"State cleanup error: {e}")
                await asyncio.sleep(60)
