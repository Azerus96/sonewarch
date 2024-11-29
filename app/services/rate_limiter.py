# app/services/rate_limiter.py

import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
import logging

class RateLimiter:
    def __init__(self, requests_per_second: int = 2, burst_size: int = 5):
        self.requests_per_second = requests_per_second
        self.burst_size = burst_size
        self.domains = defaultdict(lambda: {
            'tokens': burst_size,
            'last_update': datetime.now(),
            'lock': asyncio.Lock()
        })

    async def acquire(self, domain: str):
        domain_data = self.domains[domain]
        async with domain_data['lock']:
            await self._refill_tokens(domain)
            
            while domain_data['tokens'] <= 0:
                await asyncio.sleep(1.0 / self.requests_per_second)
                await self._refill_tokens(domain)
            
            domain_data['tokens'] -= 1

    def release(self, domain: str):
        domain_data = self.domains[domain]
        if domain_data['tokens'] < self.burst_size:
            domain_data['tokens'] += 1

    async def _refill_tokens(self, domain: str):
        domain_data = self.domains[domain]
        now = datetime.now()
        time_passed = (now - domain_data['last_update']).total_seconds()
        new_tokens = time_passed * self.requests_per_second
        
        domain_data['tokens'] = min(
            domain_data['tokens'] + new_tokens,
            self.burst_size
        )
        domain_data['last_update'] = now
