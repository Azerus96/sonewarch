# app/services/connection_pool.py

import aiohttp
from typing import AsyncGenerator
import asyncio

class ConnectionPool:
    def __init__(self, max_connections: int = 100, timeout: int = 30):
        self.connector = aiohttp.TCPConnector(
            limit=max_connections,
            force_close=True,
            enable_cleanup_closed=True
        )
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session = None
        self.lock = asyncio.Lock()

    async def get(self) -> aiohttp.ClientSession:
        async with self.lock:
            if self.session is None or self.session.closed:
                self.session = aiohttp.ClientSession(
                    connector=self.connector,
                    timeout=self.timeout,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (compatible; CustomSearchBot/1.0)',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
                        'Accept-Language': 'en-US,en;q=0.5'
                    }
                )
            return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
