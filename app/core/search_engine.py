# app/core/search_engine.py
import asyncio
import logging
from typing import List, Set, Optional
from bs4 import BeautifulSoup
import aiohttp
import redis.asyncio as redis
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass
from ..services.connection_pool import ConnectionPool
from ..services.rate_limiter import RateLimiter
from ..services.cache_service import CacheService
from ..services.state_manager import StateManager
from ..utils.text_ranking import TextRanker
from ..utils.error_handler import handle_errors
from .crawler import Crawler
from .parser import Parser
from .text_processor import TextProcessor

@dataclass
class SearchResult:
    url: str
    title: str
    context: str
    count: int
    relevance: float

class SearchEngine:
    def __init__(self):
        self.connection_pool = ConnectionPool()
        self.rate_limiter = RateLimiter()
        self.cache = CacheService()
        self.state_manager = StateManager()
        self.crawler = Crawler(self.connection_pool, self.rate_limiter)
        self.parser = Parser()
        self.text_processor = TextProcessor()
        
    async def search(self, search_id: str, start_url: str, search_term: str, max_pages: int) -> List[SearchResult]:
        try:
            # Инициализация состояния поиска
            await self.state_manager.init_search(search_id)
            
            # Получение URLs для сканирования
            urls = await self.crawler.get_urls(start_url, max_pages)
            await self.state_manager.update_total_urls(search_id, len(urls))
            
            # Создание пула задач для параллельного поиска
            search_tasks = []
            for url in urls:
                if cached_result := await self.cache.get_result(url, search_term):
                    search_tasks.append(cached_result)
                else:
                    task = self.process_url(search_id, url, search_term)
                    search_tasks.append(task)
            
            # Выполнение поиска
            results = await asyncio.gather(*search_tasks, return_exceptions=True)
            valid_results = [r for r in results if isinstance(r, SearchResult)]
            
            # Сортировка результатов по релевантности
            valid_results.sort(key=lambda x: x.relevance, reverse=True)
            
            await self.state_manager.complete_search(search_id)
            return valid_results
            
        except Exception as e:
            logging.error(f"Search error: {e}")
            await self.state_manager.fail_search(search_id)
            raise

    async def process_url(self, search_id: str, url: str, search_term: str) -> Optional[SearchResult]:
        try:
            # Получение контента
            content = await self.crawler.fetch_page(url)
            if not content:
                return None
                
            # Парсинг и поиск
            parsed_content = await self.parser.parse(content)
            if not parsed_content:
                return None
                
            # Поиск текста и определение релевантности
            result = await self.text_processor.process(
                url=url,
                content=parsed_content,
                search_term=search_term
            )
            
            if result:
                await self.cache.store_result(url, search_term, result)
                
            await self.state_manager.increment_processed_urls(search_id)
            return result
            
        except Exception as e:
            logging.error(f"Error processing {url}: {e}")
            return None
