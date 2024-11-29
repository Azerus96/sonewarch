# app/core/crawler.py

import asyncio
from typing import Set, Optional
from urllib.parse import urljoin, urlparse
import aiohttp
from ..services.connection_pool import ConnectionPool
from ..services.rate_limiter import RateLimiter

class Crawler:
    def __init__(self, connection_pool: ConnectionPool, rate_limiter: RateLimiter):
        self.connection_pool = connection_pool
        self.rate_limiter = rate_limiter
        self.seen_urls: Set[str] = set()
        
    async def get_urls(self, start_url: str, max_pages: int) -> Set[str]:
        self.seen_urls.clear()
        to_visit = {start_url}
        base_domain = urlparse(start_url).netloc
        
        while to_visit and len(self.seen_urls) < max_pages:
            url = to_visit.pop()
            if url in self.seen_urls:
                continue
                
            self.seen_urls.add(url)
            
            # Получение новых URL с страницы
            content = await self.fetch_page(url)
            if content:
                new_urls = self.extract_urls(content, url, base_domain)
                to_visit.update(new_urls - self.seen_urls)
                
        return self.seen_urls

    async def fetch_page(self, url: str) -> Optional[str]:
        try:
            await self.rate_limiter.acquire(urlparse(url).netloc)
            
            async with self.connection_pool.get() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        return None
                    return await response.text()
                    
        except Exception as e:
            logging.error(f"Fetch error for {url}: {e}")
            return None
        finally:
            self.rate_limiter.release(urlparse(url).netloc)

    def extract_urls(self, content: str, base_url: str, base_domain: str) -> Set[str]:
        urls = set()
        try:
            soup = BeautifulSoup(content, 'lxml')
            for link in soup.find_all('a', href=True):
                url = urljoin(base_url, link['href'])
                if urlparse(url).netloc == base_domain:
                    urls.add(url)
        except Exception as e:
            logging.error(f"URL extraction error: {e}")
        return urls
